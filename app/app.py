import streamlit as st
import db_queries
import dashboard
import employee_ui
import project_ui
import review_ui
import styles
import importlib

importlib.reload(styles)

st.set_page_config(
    page_title="Employee Analytics Portal",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Init session state for theme (default = Light) ─────────────────────
if "theme" not in st.session_state:
    st.session_state["theme"] = "Light"

# ── Apply CSS immediately so every element is styled on first render ───
styles.apply_custom_css(st.session_state["theme"])

# ── DB connection status ─────────────────────────────────────────────
# db_queries.init_mock_data() is a no-op shim; real data is fetched per page.
db_queries.init_mock_data()

# ── Sidebar branding ───────────────────────────────────────────────────
st.sidebar.markdown("""
<div class="sidebar-brand">
    <div class="sidebar-brand-logo">EA</div>
    <div class="sidebar-brand-title">Employee Analytics</div>
    <div class="sidebar-brand-subtitle">Enterprise HR Portal</div>
</div>
""", unsafe_allow_html=True)

# ── Navigation ─────────────────────────────────────────────────────────
pages = {
    "Dashboard":           "📊  Dashboard",
    "Employees":           "👥  Employees",
    "Projects":            "📋  Projects",
    "Performance Reviews": "⭐  Performance Reviews",
    "Analytics":           "📈  Analytics",
}
selected_page = st.sidebar.radio(
    "Navigation",
    list(pages.keys()),
    format_func=lambda x: pages[x],
)

st.sidebar.markdown("---")

# ── Theme toggle ───────────────────────────────────────────────────────
st.sidebar.markdown("**⚙️  Settings**")
chosen_theme = st.sidebar.radio(
    "Theme",
    ["Light", "Dark"],
    index=0,        # Light is default
    horizontal=True,
)
# Re-apply if the user changes the toggle
if chosen_theme != st.session_state["theme"]:
    st.session_state["theme"] = chosen_theme
    styles.apply_custom_css(chosen_theme)

st.sidebar.markdown("---")

# ── Live DB status indicator ───────────────────────────────────────────
try:
    from src.db_manager import DatabaseConnection
    DatabaseConnection().fetch_one("SELECT 1 AS ok")
    st.sidebar.success("🟢 Database connected", icon=None)
except Exception:
    st.sidebar.warning("🟡 Database unavailable — using sample data")

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 Enterprise HR Systems")

# ── Page routing ───────────────────────────────────────────────────────
if selected_page == "Dashboard":
    dashboard.render_dashboard()
elif selected_page == "Employees":
    employee_ui.render_employees()
elif selected_page == "Projects":
    project_ui.render_projects()
elif selected_page == "Performance Reviews":
    review_ui.render_reviews()
elif selected_page == "Analytics":
    dashboard.render_analytics()
