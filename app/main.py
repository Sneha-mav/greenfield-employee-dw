"""Application entry point with RBAC auth gate, session management, and filtered navigation."""

import datetime as _dt
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.auth import get_current_user, has_permission, set_current_user
from src.managers.auth_manager import AuthManager

st.set_page_config(page_title="Enterprise Employee Analytics", layout="wide")


# =============================================================================
# Auth gate: runs at the top of every rerun
# =============================================================================

def _clear_session(*, expired: bool = False, logged_out: bool = False, do_rerun: bool = True) -> None:
    """Remove auth state and rerun. Sets expired or logged_out flag for the login page."""
    st.session_state.pop("auth", None)
    st.session_state.pop("_current_user", None)
    st.session_state.pop("primary_navigation", None)
    set_current_user(None)
    if expired:
        st.session_state["_auth_expired"] = True
    if logged_out:
        st.session_state["_logged_out"] = True
    if do_rerun:
        st.rerun()


def _do_logout() -> None:
    """Log out current user: audit event, clear session without redundant rerun callback error."""
    user = get_current_user()
    if user:
        try:
            AuthManager().log_audit(
                event_type="logout",
                actor_user_id=user["user_id"],
                target_user_id=user["user_id"],
                username_attempted=user["username"],
            )
        except Exception:
            pass
    _clear_session(logged_out=True, do_rerun=False)


# ── Step 1: Clear stale snapshot from previous rerun ─────────────────────────
# This MUST happen before any code that might read the old snapshot.
set_current_user(None)

auth_data = st.session_state.get("auth")

if auth_data:
    # ── Rebuild user snapshot from DB on every rerun ──────────────────────
    try:
        am = AuthManager()
        db_user = am.get_user_by_id(auth_data["user_id"])
    except Exception:
        # DB error → fail closed: treat as logged out
        db_user = None

    if db_user is None or not db_user.get("is_active"):
        # User deleted, deactivated, or DB unreachable
        _clear_session()
        st.stop()  # belt-and-suspenders: _clear_session calls st.rerun,
                    # but st.stop ensures we never fall through in tests

    # Build per-run snapshot (never includes password_hash)
    snapshot = {
        "user_id": db_user["user_id"],
        "username": db_user["username"],
        "role": db_user["role"],
        "is_active": db_user["is_active"],
        "must_change_password": db_user["must_change_password"],
    }
    set_current_user(snapshot)

    # ── Detect user switch (same browser, different login) ────────────────
    prev_user = st.session_state.get("_prev_user_id")
    if prev_user is not None and prev_user != snapshot["user_id"]:
        st.session_state.pop("primary_navigation", None)
    st.session_state["_prev_user_id"] = snapshot["user_id"]

    # ── Timeout checks ───────────────────────────────────────────────────
    now = _dt.datetime.now()
    login_at = auth_data.get("login_at", now)
    last_activity = auth_data.get("last_activity", now)

    # Idle timeout: 30 minutes
    idle_delta = (now - last_activity).total_seconds()
    if idle_delta > 30 * 60:
        try:
            am.log_audit(
                event_type="session_expired",
                actor_user_id=snapshot["user_id"],
                username_attempted=snapshot["username"],
                details={"reason": "idle_timeout", "idle_seconds": int(idle_delta)},
            )
        except Exception:
            pass
        _clear_session(expired=True)
        st.stop()

    # Absolute timeout: 8 hours
    abs_delta = (now - login_at).total_seconds()
    if abs_delta > 8 * 60 * 60:
        try:
            am.log_audit(
                event_type="session_expired",
                actor_user_id=snapshot["user_id"],
                username_attempted=snapshot["username"],
                details={"reason": "absolute_timeout", "session_seconds": int(abs_delta)},
            )
        except Exception:
            pass
        _clear_session(expired=True)
        st.stop()

    # ── Update last_activity (after timeout checks pass) ──────────────────
    auth_data["last_activity"] = now
    st.session_state["auth"] = auth_data


# =============================================================================
# Page routing
# =============================================================================

user = get_current_user()

if not user:
    # ── Unauthenticated: show only Login ──────────────────────────────────
    login_page = st.Page("views/0_Login.py", title="Login", default=True)
    st.navigation([login_page], position="hidden")
    login_page.run()

elif user.get("must_change_password"):
    # ── Forced password change: show only Account ─────────────────────────
    st.session_state.pop("primary_navigation", None)
    account_page = st.Page("views/7_Account.py", title="Account", default=True)
    with st.sidebar:
        st.caption("EMPLOYEE ANALYTICS")
        st.markdown(f"👤 **{user['username']}** ({user['role']})")
        st.warning("Password change required")
        st.button("Logout", on_click=_do_logout, use_container_width=True)
    st.navigation([account_page], position="hidden")
    account_page.run()

else:
    # ── Authenticated: filtered page list based on permissions ────────────
    pages = {}

    if has_permission("dashboard.view"):
        pages["Dashboard"] = st.Page("views/5_Analytics_Dashboard.py", title="Dashboard", default=True)
    if has_permission("employee.search"):
        pages["Employees"] = st.Page("views/1_Onboard_Employee.py", title="Employees")
    if has_permission("project.view"):
        pages["Projects"] = st.Page("views/2_Projects.py", title="Projects")
    if has_permission("review.view"):
        pages["Reviews"] = st.Page("views/3_Reviews.py", title="Reviews")
    if has_permission("employee.history.view"):
        pages["Employee changes"] = st.Page("views/4_Update_Department.py", title="Employee changes")

    # Always add Account for authenticated users
    pages["Account"] = st.Page("views/7_Account.py", title="Account")

    # Admin page requires user.manage
    if has_permission("user.manage"):
        pages["Admin"] = st.Page("views/6_Admin.py", title="Admin")

    if not pages:
        # Fallback: should not happen, but fail safely
        pages["Account"] = st.Page("views/7_Account.py", title="Account", default=True)

    # ── Sidebar with user info and navigation ─────────────────────────────
    page_keys = list(pages)

    with st.sidebar:
        st.caption("EMPLOYEE ANALYTICS")
        st.markdown(f"👤 **{user['username']}** ({user['role']})")
        st.button("Logout", on_click=_do_logout, use_container_width=True)
        st.divider()

        # Validate the saved radio selection against current filtered pages
        saved_nav = st.session_state.get("primary_navigation")
        if saved_nav not in page_keys:
            st.session_state["primary_navigation"] = page_keys[0]

        selection = st.radio(
            "Primary navigation",
            page_keys,
            label_visibility="collapsed",
            key="primary_navigation",
        )

    page = st.navigation([pages[selection]], position="hidden")
    page.run()
