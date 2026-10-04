"""Page 2 — Projects."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.theme import inject_css, section_header
from app.components.forms import assign_employee_form, create_project_form
from app.components.tables import assignments_table
from src.db_manager import DatabaseError, ValidationError
from src.entities.project import Project
from src.managers import AnalyticsManager, ProjectManager

inject_css()

st.title("Projects")
st.caption("Create projects, assign employees, and view current allocations.")

@st.cache_data(ttl=300)
def _load_refs() -> tuple:
    am = AnalyticsManager()
    pm = ProjectManager()
    departments = am.list_departments()
    projects    = pm.list_projects(limit=500)
    proj_dicts  = [{"project_id": p.project_id, "project_name": p.project_name}
                   for p in projects]
    return departments, proj_dicts

try:
    departments, projects = _load_refs()
except DatabaseError as exc:
    st.error(f"Could not connect to database: {exc}")
    st.stop()

tab_create, tab_assign, tab_view = st.tabs(["Create Project", "Assign Employee", "View Assignments"])

with tab_create:
    section_header("New Project")

    if "project_success_msg" in st.session_state:
        st.success(st.session_state.pop("project_success_msg"))

    data = create_project_form(departments)
    if data is not None:
        try:
            project = Project(
                project_name=data["project_name"],
                department_id=data["department_id"],
                status=data["status"],
                start_date=data["start_date"],
                end_date=data["end_date"],
            )
            pm = ProjectManager()
            project = pm.create(project, refresh_warehouse=True)
            st.session_state["project_success_msg"] = (
                f"Project **{project.project_name}** created (ID: {project.project_id})."
            )
            st.cache_data.clear()
            st.rerun()
        except ValidationError as exc:
            st.error(f"Validation error: {exc}")
        except DatabaseError as exc:
            st.error(f"Database error: {exc}")

with tab_assign:
    section_header("Assign Employee to Project")
    if not projects:
        st.caption("No projects found. Create a project first.")
    else:
        data = assign_employee_form(projects)
        if data is not None:
            try:
                pm = ProjectManager()
                assignment_id = pm.assign_employee(**data)
                st.success(
                    f"Employee {data['employee_id']} assigned to project "
                    f"{data['project_id']} (Assignment ID: {assignment_id})."
                )
            except ValidationError as exc:
                st.error(f"Validation error: {exc}")
            except DatabaseError as exc:
                st.error(f"Database error: {exc}")

with tab_view:
    section_header("View Project Assignments")
    if not projects:
        st.caption("No projects found.")
    else:
        import pandas as pd
        proj_label_map = {
            f"[{p['project_id']}] {p['project_name']}": p["project_id"]
            for p in projects
        }
        selected_label = st.selectbox("Select project", list(proj_label_map.keys()))
        selected_id    = proj_label_map[selected_label]

        if st.button("Load assignments"):
            try:
                pm   = ProjectManager()
                proj = pm.get(selected_id)
                asns = pm.list_assignments(selected_id)

                c1, c2, c3 = st.columns(3)
                c1.metric("Project",     proj.project_name)
                c2.metric("Status",      proj.status)
                c3.metric("Assignments", str(len(asns)))

                assignments_table(pd.DataFrame(asns) if asns else pd.DataFrame())
            except DatabaseError as exc:
                st.error(str(exc))
