"""Authentication and Authorization Core.

Handles password hashing, credential validation, session snapshots,
permission checks, decorators, and audit integration.
"""

from contextlib import contextmanager
from contextvars import ContextVar
import functools
import re
from typing import Any, Callable, Dict, Optional, Sequence

import bcrypt
import pandas as pd

from src import permissions

# Core constants
MAX_FAILED_ATTEMPTS: int = 5
LOCKOUT_MINUTES: int = 15
BCRYPT_COST: int = 12
IDLE_TIMEOUT_MINUTES: int = 30
ABSOLUTE_TIMEOUT_HOURS: int = 8
MIN_PASSWORD_LENGTH: int = 12
USERNAME_REGEX: str = r"^[a-z0-9._-]{3,50}$"

# Precomputed cost-12 bcrypt hash for timing equalization on unknown/inactive/locked accounts
DUMMY_HASH: str = "$2b$12$n5z8MOUn71/raa9iWQEb8OPIf7BsvmRUTvhjvSuEOOhltUIU9bDS."

# Uniform error message across all authentication failure modes
AUTH_ERROR_MESSAGE: str = "Invalid username or password, or account temporarily locked."


class PermissionDenied(Exception):
    """Raised when an action or method is attempted without the required permission."""
    pass


# Thread-safe context variable for tests and background scripts
_user_override: ContextVar[Optional[Dict[str, Any]]] = ContextVar("user_override", default=None)


def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieve the current user snapshot.

    Priority:
    1. Active ContextVar override (used in unit tests / scripts)
    2. Streamlit session state (isolated per user session thread)
    3. None (outside Streamlit or unauthenticated)
    """
    override = _user_override.get()
    if override is not None:
        return override

    try:
        import streamlit as st
        if hasattr(st, "session_state") and "_current_user" in st.session_state:
            return st.session_state["_current_user"]
    except Exception:
        pass

    return None


def set_current_user(snapshot: Optional[Dict[str, Any]]) -> None:
    """Store the per-run user snapshot in st.session_state.

    Snapshot must never contain password_hash.
    """
    if snapshot is not None and "password_hash" in snapshot:
        snapshot = {k: v for k, v in snapshot.items() if k != "password_hash"}

    try:
        import streamlit as st
        if hasattr(st, "session_state"):
            if snapshot is None:
                st.session_state.pop("_current_user", None)
            else:
                st.session_state["_current_user"] = snapshot
    except Exception:
        pass


@contextmanager
def override_user(user: Optional[Dict[str, Any]]):
    """Context manager to override the current user in tests and background scripts."""
    sanitized = user.copy() if user else None
    if sanitized and "password_hash" in sanitized:
        sanitized.pop("password_hash")
    token = _user_override.set(sanitized)
    try:
        yield sanitized
    finally:
        _user_override.reset(token)


def has_permission(permission_key: str, user: Optional[Dict[str, Any]] = None) -> bool:
    """Check if the specified user (or current user) holds permission_key."""
    if user is None:
        user = get_current_user()

    if not user or not user.get("is_active", True):
        return False

    role = user.get("role")
    return permissions.has_permission(role, permission_key)


def require_permission(permission_key: str) -> None:
    """Page-level guard: stops Streamlit execution if permission is denied."""
    if not has_permission(permission_key):
        user = get_current_user()
        actor_id = user.get("user_id") if user else None
        username = user.get("username") if user else None

        try:
            from src.managers.auth_manager import AuthManager
            AuthManager().log_audit(
                event_type="access_denied",
                actor_user_id=actor_id,
                target_user_id=None,
                username_attempted=username,
                details={"permission": permission_key, "context": "page_guard"},
            )
        except Exception:
            pass

        import streamlit as st
        st.error("You do not have permission to access this page.")
        st.stop()


def requires_permission(permission_key: str) -> Callable:
    """Decorator for manager write methods enforcing RBAC permissions."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = get_current_user()
            if not has_permission(permission_key, user):
                actor_id = user.get("user_id") if user else None
                username = user.get("username") if user else None

                try:
                    from src.managers.auth_manager import AuthManager
                    AuthManager().log_audit(
                        event_type="access_denied",
                        actor_user_id=actor_id,
                        target_user_id=None,
                        username_attempted=username,
                        details={"permission": permission_key, "method": fn.__name__},
                    )
                except Exception:
                    pass

                raise PermissionDenied(
                    f"Permission '{permission_key}' required to execute {fn.__name__}."
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def mask_columns(df: pd.DataFrame, cols: Sequence[str], mask_value: Any = "Restricted") -> pd.DataFrame:
    """Mask specified columns in DataFrame if current user lacks salary.view permission.

    Always returns a NEW DataFrame when masking. Never mutates the input.
    """
    if has_permission("salary.view"):
        return df

    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = mask_value
    return out


def can_show_gantt() -> bool:
    """Return True if the scd2_gantt chart can be rendered.

    scd2_gantt (in components/charts.py) calls float() on monthly_income,
    so passing "Restricted" would crash it. Instead of breaking the
    component, views hide the entire chart when salary.view is denied.
    """
    return has_permission("salary.view")



def mask_value_if_no_salary(val: Any, mask_value: str = "Restricted") -> Any:
    """Return val if user has salary.view permission, else return mask_value."""
    if has_permission("salary.view"):
        return val
    return mask_value


def validate_username(username: str) -> str:
    """Validate and normalize username.

    Rules:
    - Must be non-empty string
    - Trimmed and lowercased
    - 3 to 50 characters matching ^[a-z0-9._-]+$
    """
    if not username or not isinstance(username, str):
        raise ValueError("Username cannot be empty.")

    cleaned = username.strip().lower()
    if not re.match(USERNAME_REGEX, cleaned):
        raise ValueError(
            "Username must be 3-50 characters long and contain only lowercase letters, "
            "digits, dots, hyphens, and underscores."
        )
    return cleaned


def validate_password(password: str, username: Optional[str] = None) -> None:
    """Validate password according to security policy.

    Rules:
    - Minimum 12 characters
    - Must not exceed 72 bytes (bcrypt restriction)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - Must not equal username (case-insensitive)
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password cannot be empty.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")

    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password exceeds 72-byte maximum length limit.")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")

    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit.")

    if username:
        norm_user = username.strip().lower()
        if password.strip().lower() == norm_user:
            raise ValueError("Password cannot be identical to the username.")


def hash_password(password: str) -> str:
    """Hash password using bcrypt at BCRYPT_COST (12 rounds)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(BCRYPT_COST)).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False
