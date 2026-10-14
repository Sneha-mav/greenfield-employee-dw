"""Login page — shown to unauthenticated users only."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.theme import (
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    inject_css,
)
from src.auth import AUTH_ERROR_MESSAGE
from src.managers.auth_manager import AuthManager

inject_css()

# Custom styles specific to the centered login portal
st.markdown(
    f"""
    <style>
    .login-container {{
        max-width: 440px;
        margin: 0 auto;
        padding-top: 1.5rem;
    }}
    .login-header-box {{
        text-align: center;
        margin-bottom: 1.5rem;
    }}
    .login-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        background-color: #EFF6FF;
        color: {COLOR_ACCENT};
        border: 1px solid #BFDBFE;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
    }}
    .login-title {{
        font-size: 1.65rem;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        margin: 0 0 0.4rem 0;
        letter-spacing: -0.02em;
    }}
    .login-subtitle {{
        font-size: 0.875rem;
        color: {COLOR_TEXT_SECONDARY};
        margin: 0;
        line-height: 1.45;
    }}
    [data-testid="stForm"] {{
        background: {COLOR_SURFACE} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 12px !important;
        padding: 1.75rem !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.02) !important;
    }}
    .login-footer {{
        text-align: center;
        color: {COLOR_TEXT_MUTED};
        font-size: 0.75rem;
        margin-top: 1.5rem;
        line-height: 1.5;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Centered 3-column layout
_, col_center, _ = st.columns([1, 1.4, 1])

with col_center:
    # Header Branding
    st.markdown(
        """
        <div class="login-header-box">
            <div class="login-badge">🛡️ Enterprise Access</div>
            <div class="login-title">Sign In</div>
            <p class="login-subtitle">
                Enterprise Employee Analytics & Data Warehouse Portal
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Show "expired" notice if redirected from timeout
    if st.session_state.get("_auth_expired"):
        st.warning("⚠️ Your session has expired due to inactivity. Please log in again.")
        st.session_state.pop("_auth_expired", None)

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input(
            "Username",
            placeholder="Enter username (e.g., admin)",
            autocomplete="username",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="••••••••••••",
            autocomplete="current-password",
        )
        
        st.write("")  # Spacing
        submitted = st.form_submit_button(
            "Sign In →",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not username or not password:
            st.error(AUTH_ERROR_MESSAGE)
        else:
            try:
                am = AuthManager()
                user = am.authenticate(username, password)
                if user is None:
                    st.error(AUTH_ERROR_MESSAGE)
                else:
                    import datetime as _dt
                    now = _dt.datetime.now()
                    st.session_state["auth"] = {
                        "user_id": user["user_id"],
                        "login_at": now,
                        "last_activity": now,
                    }
                    # Clear stale navigation key so filtered pages rebuild cleanly
                    st.session_state.pop("primary_navigation", None)
                    st.rerun()
            except Exception:
                st.error(AUTH_ERROR_MESSAGE)

    # Access Information & Footer
    with st.expander("ℹ️ Access & Role Information"):
        st.markdown(
            """
            * **Admin**: User management, system audit logs, full access.
            * **HR Manager**: Employee onboarding, department transfers, compensation updates.
            * **Project Manager**: Project planning, team allocations, performance reviews.
            * **Analyst**: Read-only workforce analytics and reports (individual compensation masked).
            """
        )

    st.markdown(
        """
        <div class="login-footer">
            🔒 Protected by Antigravity RBAC & bcrypt security<br>
            All access events and changes are audited.
        </div>
        """,
        unsafe_allow_html=True,
    )
