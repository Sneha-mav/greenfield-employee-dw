"""Unit tests for AuthManager and core auth functions (src/auth.py, src/managers/auth_manager.py).

Uses mocked database interactions to ensure no tests touch the live database.
"""

from datetime import datetime, timedelta
import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.auth import (
    AUTH_ERROR_MESSAGE,
    DUMMY_HASH,
    MAX_FAILED_ATTEMPTS,
    PermissionDenied,
    check_password,
    get_current_user,
    hash_password,
    has_permission,
    mask_columns,
    mask_value_if_no_salary,
    override_user,
    requires_permission,
    set_current_user,
    validate_password,
    validate_username,
)
from src.db_manager import RecordNotFoundError, ValidationError
from src.managers.auth_manager import AuthManager


# ==============================================================================
# 1. Validation & Cryptography Unit Tests
# ==============================================================================

def test_validate_username_success():
    """Valid usernames are trimmed and lowercased."""
    assert validate_username("alice") == "alice"
    assert validate_username("  Bob_123.test-user  ") == "bob_123.test-user"


def test_validate_username_failures():
    """Invalid usernames raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_username("")

    with pytest.raises(ValueError, match="3-50 characters"):
        validate_username("ab")  # too short

    with pytest.raises(ValueError, match="3-50 characters"):
        validate_username("a" * 51)  # too long

    with pytest.raises(ValueError, match="3-50 characters"):
        validate_username("user@domain")  # invalid character '@'

    with pytest.raises(ValueError, match="3-50 characters"):
        validate_username("user name")  # invalid space


def test_validate_password_success():
    """Compliant passwords pass validation."""
    validate_password("ValidP@ssword123", username="testuser")
    validate_password("StrongPass123!", username="alice")


def test_validate_password_failures():
    """Test all password policy violation rules."""
    with pytest.raises(ValueError, match="at least 12 characters"):
        validate_password("Short1!", username="user")

    with pytest.raises(ValueError, match="uppercase letter"):
        validate_password("lowercaseonly123!", username="user")

    with pytest.raises(ValueError, match="lowercase letter"):
        validate_password("UPPERCASEONLY123!", username="user")

    with pytest.raises(ValueError, match="at least one digit"):
        validate_password("NoDigitsAllowedHere!", username="user")

    with pytest.raises(ValueError, match="identical to the username"):
        validate_password("AliceInWonderland1", username="AliceInWonderland1")

    with pytest.raises(ValueError, match="72-byte"):
        validate_password("A1" + "a" * 80, username="user")


def test_hash_and_check_password():
    """Verify bcrypt hashing and verification."""
    password = "SecurePassword123!"
    pw_hash = hash_password(password)

    assert pw_hash.startswith("$2b$12$")
    assert check_password(password, pw_hash) is True
    assert check_password("WrongPassword123!", pw_hash) is False
    assert check_password("", pw_hash) is False


def test_dummy_hash_timing_equalization():
    """Verify DUMMY_HASH is valid bcrypt at cost 12 and safely fails checking."""
    assert DUMMY_HASH.startswith("$2b$12$")
    assert check_password("AnyPassword123!", DUMMY_HASH) is False


# ==============================================================================
# 2. Context & Decorator Unit Tests
# ==============================================================================

def test_override_user_context():
    """Verify override_user sets and cleans up the active user snapshot."""
    assert get_current_user() is None

    user_data = {
        "user_id": 10,
        "username": "test_hr",
        "role": "hr_manager",
        "is_active": True,
        "must_change_password": False,
        "password_hash": "should_be_stripped",
    }

    with override_user(user_data) as current:
        assert current["username"] == "test_hr"
        assert "password_hash" not in current
        active = get_current_user()
        assert active["user_id"] == 10
        assert "password_hash" not in active
        assert has_permission("salary.view") is True
        assert has_permission("project.create") is False

    assert get_current_user() is None


def test_has_permission_inactive_user():
    """Inactive users have no permissions, even if role is admin."""
    user = {"user_id": 1, "username": "admin", "role": "admin", "is_active": False}
    with override_user(user):
        assert has_permission("dashboard.view") is False
        assert has_permission("user.manage") is False


def test_requires_permission_decorator_allowed():
    """Decorator allows execution when user has permission."""
    @requires_permission("employee.onboard")
    def sample_write(arg1):
        return f"success: {arg1}"

    user = {"user_id": 2, "username": "hr1", "role": "hr_manager", "is_active": True}
    with override_user(user):
        result = sample_write("data")
        assert result == "success: data"


def test_requires_permission_decorator_denied_logs_audit():
    """Decorator blocks execution and writes access_denied audit when permission missing."""
    @requires_permission("project.create")
    def sample_project_create():
        return "created"

    user = {"user_id": 3, "username": "hr1", "role": "hr_manager", "is_active": True}

    with patch.object(AuthManager, "log_audit") as mock_audit:
        with override_user(user):
            with pytest.raises(PermissionDenied, match="project.create"):
                sample_project_create()

        mock_audit.assert_called_once()
        args, kwargs = mock_audit.call_args
        assert kwargs.get("event_type") == "access_denied"
        assert kwargs.get("actor_user_id") == 3
        assert kwargs.get("username_attempted") == "hr1"
        assert kwargs.get("details") == {
            "permission": "project.create",
            "method": "sample_project_create",
        }


def test_requires_permission_preserves_metadata():
    """Decorator must preserve wrapped function's name and docstring."""
    @requires_permission("employee.onboard")
    def documented_func():
        """This is a docstring."""
        pass

    assert documented_func.__name__ == "documented_func"
    assert documented_func.__doc__ == "This is a docstring."


# ==============================================================================
# 3. Masking Helpers Unit Tests
# ==============================================================================

def test_mask_columns_without_salary_view():
    """Columns are masked as 'Restricted' when salary.view is not granted."""
    df = pd.DataFrame([
        {"name": "Alice", "monthly_income": 8000, "salary_hike_pct": 12.5},
        {"name": "Bob", "monthly_income": 9500, "salary_hike_pct": 10.0},
    ])

    user = {"user_id": 4, "username": "analyst1", "role": "analyst", "is_active": True}
    with override_user(user):
        masked = mask_columns(df, ["monthly_income", "salary_hike_pct"])
        assert list(masked["monthly_income"]) == ["Restricted", "Restricted"]
        assert list(masked["salary_hike_pct"]) == ["Restricted", "Restricted"]
        assert list(masked["name"]) == ["Alice", "Bob"]
        assert mask_value_if_no_salary(8000) == "Restricted"


def test_mask_columns_with_salary_view():
    """Columns remain unchanged when salary.view is granted."""
    df = pd.DataFrame([
        {"name": "Alice", "monthly_income": 8000},
    ])

    user = {"user_id": 5, "username": "hr1", "role": "hr_manager", "is_active": True}
    with override_user(user):
        masked = mask_columns(df, ["monthly_income"])
        assert list(masked["monthly_income"]) == [8000]
        assert mask_value_if_no_salary(8000) == 8000


# ==============================================================================
# 4. AuthManager Mocked Database Unit Tests
# ==============================================================================

@pytest.fixture
def mock_auth_manager():
    """Fixture providing AuthManager with a mocked DB connection."""
    with patch("src.db_manager.DatabaseConnection") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        manager = AuthManager()
        manager.db = mock_db
        yield manager


def test_authenticate_unknown_user(mock_auth_manager):
    """Unknown user returns None and writes login_failure audit."""
    cur = MagicMock()
    cur.fetchone.return_value = None
    mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur

    with patch("src.managers.auth_manager.check_password") as mock_checkpw:
        result = mock_auth_manager.authenticate("nonexistent", "SomePassword123!")

        assert result is None
        mock_checkpw.assert_called_once_with("SomePassword123!", DUMMY_HASH)
        # Check audit insert
        audit_call = cur.execute.call_args_list[-1]
        assert "login_failure" in audit_call[0][1]


def test_authenticate_inactive_user(mock_auth_manager):
    """Inactive user returns None and writes login_failure audit."""
    cur = MagicMock()
    cur.fetchone.return_value = {
        "user_id": 1,
        "username": "inactive_user",
        "password_hash": hash_password("ValidPassword123!"),
        "role": "analyst",
        "is_active": 0,
        "must_change_password": 0,
        "failed_attempts": 0,
        "locked_until": None,
        "db_now": datetime.now(),
    }
    mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur

    with patch("src.managers.auth_manager.check_password") as mock_checkpw:
        result = mock_auth_manager.authenticate("inactive_user", "ValidPassword123!")

        assert result is None
        mock_checkpw.assert_called_once_with("ValidPassword123!", DUMMY_HASH)
        audit_call = cur.execute.call_args_list[-1]
        assert "login_failure" in audit_call[0][1]


def test_authenticate_locked_user(mock_auth_manager):
    """Locked user returns None and writes login_failure audit."""
    now = datetime.now()
    cur = MagicMock()
    cur.fetchone.return_value = {
        "user_id": 2,
        "username": "locked_user",
        "password_hash": hash_password("ValidPassword123!"),
        "role": "analyst",
        "is_active": 1,
        "must_change_password": 0,
        "failed_attempts": 5,
        "locked_until": now + timedelta(minutes=10),
        "db_now": now,
    }
    mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur

    with patch("src.managers.auth_manager.check_password") as mock_checkpw:
        result = mock_auth_manager.authenticate("locked_user", "ValidPassword123!")

        assert result is None
        mock_checkpw.assert_called_once_with("ValidPassword123!", DUMMY_HASH)


def test_authenticate_wrong_password_increments_failed(mock_auth_manager):
    """Wrong password increments failed_attempts."""
    now = datetime.now()
    cur = MagicMock()
    cur.fetchone.return_value = {
        "user_id": 3,
        "username": "user1",
        "password_hash": hash_password("CorrectPass123!"),
        "role": "analyst",
        "is_active": 1,
        "must_change_password": 0,
        "failed_attempts": 2,
        "locked_until": None,
        "db_now": now,
    }
    mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur

    result = mock_auth_manager.authenticate("user1", "WrongPassword123!")
    assert result is None

    # Check update failed_attempts
    update_call = [c for c in cur.execute.call_args_list if "UPDATE app_users SET failed_attempts" in c[0][0]]
    assert len(update_call) == 1
    assert update_call[0][0][1] == (3, 3)


def test_authenticate_fifth_failure_locks_account(mock_auth_manager):
    """5th consecutive failed attempt locks the account for 15 minutes."""
    now = datetime.now()
    cur = MagicMock()
    cur.fetchone.return_value = {
        "user_id": 4,
        "username": "user2",
        "password_hash": hash_password("CorrectPass123!"),
        "role": "analyst",
        "is_active": 1,
        "must_change_password": 0,
        "failed_attempts": 4,
        "locked_until": None,
        "db_now": now,
    }
    mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur

    result = mock_auth_manager.authenticate("user2", "WrongPassword123!")
    assert result is None

    # Verify update with lockout
    lock_updates = [
        c for c in cur.execute.call_args_list
        if c[0][0].strip().startswith("UPDATE") and "locked_until" in c[0][0]
    ]
    assert len(lock_updates) == 1
    assert lock_updates[0][0][1] == (5, 15, 4)

    # Verify account_locked audit record
    audits = [c for c in cur.execute.call_args_list if "INSERT INTO app_audit_log" in c[0][0]]
    event_types = [c[0][1][0] for c in audits]
    assert "login_failure" in event_types
    assert "account_locked" in event_types


def test_authenticate_success(mock_auth_manager):
    """Successful login resets attempts, updates last_login, returns snapshot without password_hash."""
    now = datetime.now()
    pw = "SuperSecurePass123!"
    cur = MagicMock()
    cur.fetchone.return_value = {
        "user_id": 5,
        "username": "good_user",
        "password_hash": hash_password(pw),
        "role": "analyst",
        "is_active": 1,
        "must_change_password": 0,
        "failed_attempts": 3,
        "locked_until": None,
        "db_now": now,
    }
    mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur

    result = mock_auth_manager.authenticate("good_user", pw)
    assert result is not None
    assert result["user_id"] == 5
    assert result["username"] == "good_user"
    assert "password_hash" not in result

    # Verify reset query
    reset_updates = [c for c in cur.execute.call_args_list if "failed_attempts = 0" in c[0][0]]
    assert len(reset_updates) == 1


# ==============================================================================
# 5. Guardrail Unit Tests (Admin self-change & last-admin)
# ==============================================================================

def test_change_role_self_demotion_rejected(mock_auth_manager):
    """Admin cannot change their own role."""
    with pytest.raises(ValidationError, match="Admins cannot change their own role"):
        mock_auth_manager.change_role(target_user_id=1, new_role="analyst", actor_user_id=1)


def test_change_role_last_admin_demotion_rejected(mock_auth_manager):
    """Cannot demote the last active admin."""
    cur = MagicMock()
    # Target is admin
    cur.fetchone.side_effect = [
        {"user_id": 2, "role": "admin", "is_active": 1},  # target user
        {"n": 1},  # count of active admins
    ]
    mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur

    with pytest.raises(ValidationError, match="Cannot demote the last active admin"):
        mock_auth_manager.change_role(target_user_id=2, new_role="hr_manager", actor_user_id=1)


def test_deactivate_user_self_deactivation_rejected(mock_auth_manager):
    """Admin cannot deactivate their own account."""
    with pytest.raises(ValidationError, match="Admins cannot deactivate their own account"):
        mock_auth_manager.deactivate_user(target_user_id=1, actor_user_id=1)


def test_deactivate_user_last_admin_rejected(mock_auth_manager):
    """Cannot deactivate the last active admin."""
    cur = MagicMock()
    cur.fetchone.side_effect = [
        {"user_id": 2, "role": "admin", "is_active": 1},  # target user
        {"n": 1},  # count of active admins
    ]
    mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur

    with pytest.raises(ValidationError, match="Cannot deactivate the last active admin"):
        mock_auth_manager.deactivate_user(target_user_id=2, actor_user_id=1)


def test_audit_event_types_coverage(mock_auth_manager):
    """Ensure standard audit events (login_success, login_failure, account_locked, logout, session_expired) log correctly."""
    events = ["login_success", "login_failure", "account_locked", "logout", "session_expired", "access_denied"]

    for ev in events:
        cur = MagicMock()
        mock_auth_manager.db.transaction.return_value.__enter__.return_value = cur
        mock_auth_manager.log_audit(
            event_type=ev,
            actor_user_id=1,
            target_user_id=2,
            username_attempted="alice",
            details={"test": True},
        )
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0][1]
        assert args[0] == ev
        assert args[1] == 1
        assert args[2] == 2
        assert args[3] == "alice"
        assert json.loads(args[4]) == {"test": True}


# ==============================================================================
# 6. Fail-Closed, Immutability, and Audit Resilience Tests
# ==============================================================================

def test_no_current_user_denies_has_permission():
    """has_permission(key) must DENY (return False) when there is no current user (fail closed)."""
    # Ensure no override is set
    assert get_current_user() is None
    assert has_permission("dashboard.view") is False
    assert has_permission("user.manage") is False
    assert has_permission("salary.view") is False
    assert has_permission("account.password") is False


def test_no_current_user_denies_requires_permission():
    """@requires_permission must raise PermissionDenied when there is no current user (fail closed)."""
    @requires_permission("employee.onboard")
    def protected_func():
        return "should never run"

    assert get_current_user() is None
    with patch.object(AuthManager, "log_audit"):
        with pytest.raises(PermissionDenied, match="employee.onboard"):
            protected_func()


def test_mask_columns_never_mutates_input():
    """mask_columns must work on a copy and never modify the original DataFrame."""
    from src.auth import can_show_gantt

    original = pd.DataFrame([
        {"name": "Alice", "monthly_income": 8000, "salary_hike_pct": 12.5},
        {"name": "Bob", "monthly_income": 9500, "salary_hike_pct": 10.0},
    ])
    original_copy = original.copy()

    user = {"user_id": 10, "username": "analyst1", "role": "analyst", "is_active": True}
    with override_user(user):
        masked = mask_columns(original, ["monthly_income", "salary_hike_pct"])

        # Verify the masking happened on the returned frame
        assert list(masked["monthly_income"]) == ["Restricted", "Restricted"]
        assert list(masked["salary_hike_pct"]) == ["Restricted", "Restricted"]

        # Verify the original is UNTOUCHED
        pd.testing.assert_frame_equal(original, original_copy)

        # Verify the returned frame is a DIFFERENT object
        assert masked is not original

        # Also verify can_show_gantt says False for analyst
        assert can_show_gantt() is False

    # And True for hr_manager
    hr_user = {"user_id": 11, "username": "hr1", "role": "hr_manager", "is_active": True}
    with override_user(hr_user):
        assert can_show_gantt() is True


def test_audit_failure_does_not_suppress_permission_denied():
    """If the access_denied audit insert fails, PermissionDenied must still be raised."""
    @requires_permission("project.create")
    def protected_project_create():
        return "created"

    user = {"user_id": 5, "username": "analyst1", "role": "analyst", "is_active": True}

    # Make the audit log call explode
    with patch.object(AuthManager, "log_audit", side_effect=RuntimeError("DB connection lost")):
        with override_user(user):
            with pytest.raises(PermissionDenied, match="project.create"):
                protected_project_create()

