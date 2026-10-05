"""Page 2 — Projects."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.theme import inject_css, section_header
from app.components.forms import assign_multiple_employees_form, create_project_form
from app.components.tables import assignments_table
from src.db_manager import DatabaseError, ValidationError
from src.entities.project import Project
from src.managers import AnalyticsManager, ProjectManager

inject_css()

st.title("Projects")
st.caption("Create projects, assign employees, and view current allocations.")

@st.cache_data(ttl=300)
def _load_refs(version: int = 0) -> tuple:
    am = AnalyticsManager()
    pm = ProjectManager()
    departments = am.list_departments()
    projects    = pm.list_projects()
    proj_dicts  = [{"project_id": p.project_id, "project_name": p.project_name}
                   for p in projects]
    return departments, proj_dicts

if "projects_version" not in st.session_state:
    st.session_state["projects_version"] = 0

try:
    departments, projects = _load_refs(version=st.session_state["projects_version"])
except DatabaseError as exc:
    st.error(f"Could not connect to database: {exc}")
    st.stop()

tab_create, tab_assign, tab_view, tab_search = st.tabs(["Create Project", "Assign Employee", "View Assignments", "Search Assignment"])

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
            st.session_state["projects_version"] += 1
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
        assignments = assign_multiple_employees_form(projects)
        if assignments is not None:
            success, failed = [], []
            for data in assignments:
                try:
                    pm = ProjectManager()
                    assignment_id = pm.assign_employee(**data)
                    success.append(f"Employee {data['employee_id']} → Assignment ID {assignment_id}")
                except (ValidationError, DatabaseError) as exc:
                    failed.append(f"Employee {data['employee_id']}: {exc}")
            if success:
                st.success(f"{len(success)} assignment(s) created:\n" + "\n".join(f"- {s}" for s in success))
            if failed:
                for f in failed:
                    st.error(f)

with tab_search:
    section_header("Search Assignment by ID")
    assignment_id_input = st.number_input("Assignment ID", min_value=1, step=1, key="search_assignment_id")
    if st.button("Search", use_container_width=True, key="btn_search_assignment"):
        try:
            pm   = ProjectManager()
            rows = pm.db.fetch_all(
                "SELECT a.assignment_id, a.employee_id, "
                "CONCAT(e.first_name, ' ', e.last_name) AS employee_name, "
                "p.project_name, a.role_on_project, a.allocation_pct, "
                "a.start_date, a.end_date "
                "FROM assignments a "
                "JOIN employees e ON e.employee_id = a.employee_id "
                "JOIN projects p ON p.project_id = a.project_id "
                "WHERE a.assignment_id = %s",
                (int(assignment_id_input),),
            )
            if not rows:
                st.warning(f"No assignment found with ID {int(assignment_id_input)}.")
            else:
                row = rows[0]
                c1, c2, c3 = st.columns(3)
                c1.metric("Assignment ID",  str(row["assignment_id"]))
                c2.metric("Employee",       row["employee_name"])
                c3.metric("Employee ID",    str(row["employee_id"]))
                c1.metric("Project",        row["project_name"])
                c2.metric("Role",           row["role_on_project"])
                c3.metric("Allocation %",   str(row["allocation_pct"]))
                c1.metric("Start Date",     str(row["start_date"]))
                c2.metric("End Date",       str(row["end_date"]) if row["end_date"] else "Ongoing")
        except DatabaseError as exc:
            st.error(str(exc))

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
