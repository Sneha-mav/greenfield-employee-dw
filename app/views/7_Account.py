"""Account page — change own password, clear must_change_password."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.theme import inject_css
from src.auth import get_current_user
from src.db_manager import DatabaseError, ValidationError
from src.managers.auth_manager import AuthManager

inject_css()

st.title("👤 My Account")

user = get_current_user()
if not user:
    st.error("You must be logged in to access this page.")
    st.stop()

st.markdown(f"**Username:** `{user['username']}`")
st.markdown(f"**Role:** `{user['role']}`")

if user.get("must_change_password"):
    st.warning("You must change your password before continuing.")

st.divider()
st.subheader("Change Password")

with st.form("change_password_form"):
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password",
                                  help="Min 12 chars, upper + lower + digit, not your username")
    confirm_password = st.text_input("Confirm New Password", type="password")
    submitted = st.form_submit_button("Change Password", use_container_width=True)

if submitted:
    if not current_password or not new_password or not confirm_password:
        st.error("All fields are required.")
    elif new_password != confirm_password:
        st.error("New password and confirmation do not match.")
    else:
        try:
            am = AuthManager()
            am.change_own_password(user["user_id"], current_password, new_password)
            st.success("Password changed successfully.")
            # Clear must_change_password in the session snapshot to allow normal navigation
            if "_current_user" in st.session_state and st.session_state["_current_user"]:
                st.session_state["_current_user"]["must_change_password"] = False
            # Clear navigation key so main.py rebuilds page list
            st.session_state.pop("primary_navigation", None)
            st.rerun()
        except ValidationError as exc:
            st.error(str(exc))
        except DatabaseError as exc:
            st.error(f"Could not change password: {exc}")
