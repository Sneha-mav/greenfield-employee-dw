"""Application entry point with compact sidebar HR navigation."""

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Enterprise Employee Analytics", layout="wide")

pages = {
    "Dashboard": st.Page("views/5_Analytics_Dashboard.py", title="Dashboard", default=True),
    "Employees": st.Page("views/1_Onboard_Employee.py", title="Employees"),
    "Projects": st.Page("views/2_Projects.py", title="Projects"),
    "Reviews": st.Page("views/3_Reviews.py", title="Reviews"),
    "Employee changes": st.Page("views/4_Update_Department.py", title="Employee changes"),
}

with st.sidebar:
    st.caption("EMPLOYEE ANALYTICS")
    selection = st.radio(
        "Primary navigation",
        list(pages),
        label_visibility="collapsed",
        key="primary_navigation",
    )
page = st.navigation([pages[selection]], position="hidden")
page.run()
