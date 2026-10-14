"""Tests for app/main.py auth gate using streamlit.testing.v1.AppTest.

Verifies:
1. _current_user is cleared at start of every rerun and on every failure path (inactive, expired, DB error).
2. If get_user_by_id raises, user is treated as logged out (fail closed), never reusing an old snapshot.
"""

import datetime
from unittest.mock import patch
import pytest
from streamlit.testing.v1 import AppTest


def test_main_unauthenticated_clears_current_user():
    """Unauthenticated access should have no _current_user and show login."""
    at = AppTest.from_file("app/main.py")
    at.run()
    assert "_current_user" not in at.session_state or at.session_state["_current_user"] is None


def test_main_inactive_user_clears_session_and_fails_closed():
    """If user is inactive, _current_user is cleared and session is reset."""
    with patch("src.managers.auth_manager.AuthManager.get_user_by_id") as mock_get:
        mock_get.return_value = {
            "user_id": 1,
            "username": "alice",
            "role": "admin",
            "is_active": False,
            "must_change_password": False,
        }
        at = AppTest.from_file("app/main.py")
        at.session_state["auth"] = {
            "user_id": 1,
            "login_at": datetime.datetime.now(),
            "last_activity": datetime.datetime.now(),
        }
        at.session_state["_current_user"] = {
            "user_id": 1,
            "username": "alice",
            "role": "admin",
        }
        at.run()
        assert "_current_user" not in at.session_state or at.session_state["_current_user"] is None
        assert "auth" not in at.session_state


def test_main_db_error_on_get_user_by_id_fails_closed():
    """If get_user_by_id raises, fail closed: treat as logged out, never reuse snapshot."""
    with patch("src.managers.auth_manager.AuthManager.get_user_by_id", side_effect=RuntimeError("DB Connection Lost")):
        at = AppTest.from_file("app/main.py")
        at.session_state["auth"] = {
            "user_id": 1,
            "login_at": datetime.datetime.now(),
            "last_activity": datetime.datetime.now(),
        }
        at.session_state["_current_user"] = {
            "user_id": 1,
            "username": "alice",
            "role": "admin",
        }
        at.run()
        assert "_current_user" not in at.session_state or at.session_state["_current_user"] is None
        assert "auth" not in at.session_state


def test_main_idle_timeout_expires_session():
    """If idle for >30m, session is expired and _current_user cleared."""
    with patch("src.managers.auth_manager.AuthManager.get_user_by_id") as mock_get, \
         patch("src.managers.auth_manager.AuthManager.log_audit"):
        mock_get.return_value = {
            "user_id": 1,
            "username": "alice",
            "role": "admin",
            "is_active": True,
            "must_change_password": False,
        }
        at = AppTest.from_file("app/main.py")
        old_time = datetime.datetime.now() - datetime.timedelta(minutes=31)
        at.session_state["auth"] = {
            "user_id": 1,
            "login_at": old_time,
            "last_activity": old_time,
        }
        at.session_state["_current_user"] = {
            "user_id": 1,
            "username": "alice",
            "role": "admin",
        }
        at.run()
        assert "_current_user" not in at.session_state or at.session_state["_current_user"] is None
        assert "auth" not in at.session_state
        assert at.session_state["_auth_expired"] is True


def test_main_absolute_timeout_expires_session():
    """If session age >8h, session is expired and _current_user cleared."""
    with patch("src.managers.auth_manager.AuthManager.get_user_by_id") as mock_get, \
         patch("src.managers.auth_manager.AuthManager.log_audit"):
        mock_get.return_value = {
            "user_id": 1,
            "username": "alice",
            "role": "admin",
            "is_active": True,
            "must_change_password": False,
        }
        at = AppTest.from_file("app/main.py")
        old_login = datetime.datetime.now() - datetime.timedelta(hours=8, minutes=1)
        recent_activity = datetime.datetime.now()
        at.session_state["auth"] = {
            "user_id": 1,
            "login_at": old_login,
            "last_activity": recent_activity,
        }
        at.session_state["_current_user"] = {
            "user_id": 1,
            "username": "alice",
            "role": "admin",
        }
        at.run()
        assert "_current_user" not in at.session_state or at.session_state["_current_user"] is None
        assert "auth" not in at.session_state
        assert at.session_state["_auth_expired"] is True
