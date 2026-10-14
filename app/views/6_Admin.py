"""Page 6 — Admin Console.

Requires user.manage permission to view this page.
The Audit Log tab additionally requires audit.view permission.
Features:
- User list
- Create user (with temporary password, must_change_password=1)
- Change user role (with self-demotion and last-admin guardrails)
- Activate / deactivate user (with self-deactivation and last-admin guardrails)
- Reset user password (sets temp password and must_change_password=1)
- Read-only Audit Log (latest 200 events with event_type filter)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.components.theme import inject_css, section_header
from src.auth import (
    PermissionDenied,
    get_current_user,
    has_permission,
    require_permission,
)
from src.db_manager import DatabaseError, ValidationError
from src.managers.auth_manager import AuthManager, VALID_ROLES

inject_css()

# Page-level guard: stops execution if user lacks user.manage
require_permission("user.manage")

st.title("User Administration")
st.caption("Manage application users, assign roles, and review security audit logs.")

current_user = get_current_user()
actor_id = current_user.get("user_id") if current_user else None

am = AuthManager()

tabs_to_show = ["Users"]
if has_permission("audit.view"):
    tabs_to_show.append("Audit log")

tabs = st.tabs(tabs_to_show)
tab_by_label = dict(zip(tabs_to_show, tabs))

# =============================================================================
# Tab 1: Users
# =============================================================================
if "Users" in tab_by_label:
    with tab_by_label["Users"]:
        try:
            users = am.get_all_users()
        except DatabaseError as exc:
            st.error(f"Could not load users: {exc}")
            users = []

        section_header("Existing Users")
        if users:
            df_users = pd.DataFrame([{
                "ID": u.get("user_id"),
                "Username": u.get("username"),
                "Role": u.get("role"),
                "Status": "Active" if u.get("is_active") else "Inactive",
                "Must Change Pwd": "Yes" if u.get("must_change_password") else "No",
                "Failed Attempts": u.get("failed_attempts", 0),
                "Locked Until": str(u["locked_until"]) if u.get("locked_until") else "None",
                "Created At": str(u.get("created_at", "")),
                "Last Login": str(u["last_login"]) if u.get("last_login") else "Never",
            } for u in users])
            st.dataframe(df_users, use_container_width=True, hide_index=True)
        else:
            st.info("No users found.")

        st.divider()

        user_options = {
            f"[{u['user_id']}] {u['username']} ({u['role']}, {'Active' if u['is_active'] else 'Inactive'})": u
            for u in users
        }

        col_left, col_right = st.columns(2)

        # ── Action 1: Create User ─────────────────────────────────────────────
        with col_left:
            section_header("Create New User")
            with st.form("create_user_form", clear_on_submit=True):
                new_username = st.text_input("Username (3-50 chars, lowercase alphanumeric)", key="new_username")
                new_password = st.text_input("Initial Temporary Password (min 12 chars)", type="password", key="new_password")
                new_role = st.selectbox("Role", VALID_ROLES, key="new_role")
                create_submitted = st.form_submit_button("Create User", use_container_width=True)

            if create_submitted:
                try:
                    created = am.create_user(
                        username=new_username.strip(),
                        password=new_password,
                        role=new_role,
                        created_by=actor_id,
                    )
                    st.success(f"User **{created['username']}** created with role **{created['role']}**.")
                    st.rerun()
                except (ValidationError, PermissionDenied) as exc:
                    st.error(str(exc))
                except DatabaseError as exc:
                    st.error(f"Database error: {exc}")

        # ── Action 2: Change Role ─────────────────────────────────────────────
        with col_right:
            section_header("Change User Role")
            if user_options:
                with st.form("change_role_form"):
                    selected_label = st.selectbox("Select user", list(user_options.keys()), key="role_target_user")
                    selected_user = user_options[selected_label]
                    role_choice = st.selectbox("New role", VALID_ROLES, index=VALID_ROLES.index(selected_user["role"]), key="role_choice")
                    role_submitted = st.form_submit_button("Update Role", use_container_width=True)

                if role_submitted:
                    try:
                        am.change_role(
                            target_user_id=selected_user["user_id"],
                            new_role=role_choice,
                            actor_user_id=actor_id,
                        )
                        st.success(f"Role updated to **{role_choice}** for user **{selected_user['username']}**.")
                        st.rerun()
                    except (ValidationError, PermissionDenied) as exc:
                        st.error(str(exc))
                    except DatabaseError as exc:
                        st.error(f"Database error: {exc}")
            else:
                st.caption("No users available.")

        st.divider()
        col_act, col_reset = st.columns(2)

        # ── Action 3: Activate / Deactivate ───────────────────────────────────
        with col_act:
            section_header("Activate / Deactivate User")
            if user_options:
                target_label_act = st.selectbox("Select user to toggle", list(user_options.keys()), key="act_target_user")
                target_user_act = user_options[target_label_act]

                is_active = target_user_act["is_active"]
                btn_label = "Deactivate Account" if is_active else "Activate Account"

                if st.button(btn_label, use_container_width=True, key="btn_toggle_active"):
                    try:
                        if is_active:
                            am.deactivate_user(target_user_id=target_user_act["user_id"], actor_user_id=actor_id)
                            st.success(f"User **{target_user_act['username']}** deactivated.")
                        else:
                            am.activate_user(target_user_id=target_user_act["user_id"], actor_user_id=actor_id)
                            st.success(f"User **{target_user_act['username']}** activated.")
                        st.rerun()
                    except (ValidationError, PermissionDenied) as exc:
                        st.error(str(exc))
                    except DatabaseError as exc:
                        st.error(f"Database error: {exc}")
            else:
                st.caption("No users available.")

        # ── Action 4: Reset Password ──────────────────────────────────────────
        with col_reset:
            section_header("Reset User Password")
            if user_options:
                with st.form("reset_pwd_form", clear_on_submit=True):
                    target_label_reset = st.selectbox("Select user to reset", list(user_options.keys()), key="reset_target_user")
                    target_user_reset = user_options[target_label_reset]
                    custom_temp_pwd = st.text_input(
                        "Custom Temporary Password (leave blank to auto-generate)",
                        type="password",
                        key="reset_temp_pwd",
                    )
                    reset_submitted = st.form_submit_button("Reset Password", use_container_width=True)

                if reset_submitted:
                    try:
                        temp_pass = am.reset_password(
                            target_user_id=target_user_reset["user_id"],
                            actor_user_id=actor_id,
                            temp_password=custom_temp_pwd.strip() if custom_temp_pwd.strip() else None,
                        )
                        st.success(
                            f"Password reset for **{target_user_reset['username']}**.\n\n"
                            f"Temporary password: `{temp_pass}`\n\n"
                            "User will be required to change password on next login."
                        )
                    except (ValidationError, PermissionDenied) as exc:
                        st.error(str(exc))
                    except DatabaseError as exc:
                        st.error(f"Database error: {exc}")
            else:
                st.caption("No users available.")


# =============================================================================
# Tab 2: Audit Log (Requires audit.view)
# =============================================================================
if "Audit log" in tab_by_label:
    with tab_by_label["Audit log"]:
        section_header("Security Audit Log (Latest 200 events)")

        event_types = [
            "All",
            "login_success",
            "login_failure",
            "account_locked",
            "logout",
            "session_expired",
            "user_created",
            "role_changed",
            "user_deactivated",
            "user_activated",
            "password_changed",
            "password_reset",
            "access_denied",
        ]

        selected_event = st.selectbox("Filter by event type", event_types, index=0, key="audit_event_filter")

        try:
            logs = am.get_audit_log(limit=200, event_type_filter=selected_event)
            if logs:
                df_audit = pd.DataFrame([{
                    "Audit ID": l["audit_id"],
                    "Timestamp": str(l["created_at"]),
                    "Event Type": l["event_type"],
                    "Actor ID": l["actor_user_id"] if l["actor_user_id"] is not None else "-",
                    "Target ID": l["target_user_id"] if l["target_user_id"] is not None else "-",
                    "Username": l["username_attempted"] if l["username_attempted"] else "-",
                    "Details": str(l["details"]) if l["details"] else "-",
                } for l in logs])
                st.dataframe(df_audit, use_container_width=True, hide_index=True)
            else:
                st.info("No audit log events found matching the filter.")
        except DatabaseError as exc:
            st.error(f"Could not load audit log: {exc}")
