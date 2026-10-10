"""Page 1 — Onboard Employee."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.theme import inject_css, section_header
from app.components.forms import onboard_employee_form
from src.db_manager import DatabaseError, ValidationError
from src.entities.employee import Employee
from src.managers import AnalyticsManager, EmployeeManager

inject_css()

st.title("Onboard Employee")
st.caption("Adds the employee to the OLTP database with their first history record.")

@st.cache_data(ttl=600)
def _load_refs() -> tuple:
    am = AnalyticsManager()
    return am.list_departments(), am.list_job_roles()

try:
    departments, job_roles = _load_refs()
except DatabaseError as exc:
    st.error(f"Could not connect to database: {exc}")
    st.stop()

if not departments or not job_roles:
    st.warning("No departments or job roles found. Run the SQL setup scripts first.")
    st.stop()

section_header("Employee Details")
data = onboard_employee_form(departments, job_roles)

if data is not None:
    try:
        employee = Employee(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            hire_date=data["hire_date"],
            department_id=data["department_id"],
            job_role_id=data["job_role_id"],
            job_level=data["job_level"],
            monthly_income=data["monthly_income"],
            gender=data["gender"],
            age=data["age"],
            marital_status=data["marital_status"],
            city=data["city"],
            education_field=data["education_field"],
            over_time=data["over_time"],
        )
        em = EmployeeManager()
        employee = em.create(employee, refresh_warehouse=True)
        st.success(
            f"**{employee.full_name}** onboarded successfully "
            f"(Employee ID: {employee.employee_id})."
        )
    except ValidationError as exc:
        st.error(f"Validation error: {exc}")
    except DatabaseError as exc:
        st.error(f"Database error: {exc}")

st.divider()
section_header("Search Employee")

search_mode = st.radio("Search by", ["Employee ID", "Name"], horizontal=True)

if search_mode == "Employee ID":
    col1, col2 = st.columns([1, 3])
    with col1:
        lookup_id = st.number_input("Employee ID", min_value=1, step=1, key="lookup_id")
        do_lookup = st.button("Search", use_container_width=True)

    if do_lookup:
        try:
            em  = EmployeeManager()
            emp = em.get_by_id(int(lookup_id))
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Name",           emp.full_name)
            col_b.metric("Department ID",  str(emp.department_id))
            col_c.metric("Job Level",      str(emp.job_level))
            col_a.metric("Monthly Income", f"${emp.monthly_income:,.0f}")
            col_b.metric("Hire Date",      str(emp.hire_date))
            col_c.metric("Status",         "Active" if emp.is_active else "Inactive")
        except DatabaseError as exc:
            st.warning(str(exc))

else:
    col1, col2 = st.columns([2, 1])
    with col1:
        name_query = st.text_input("Enter first name, last name or part of name")
    with col2:
        st.write("")
        st.write("")
        do_name_search = st.button("Search", use_container_width=True, key="name_search_btn")

    if do_name_search:
        if not name_query.strip():
            st.warning("Please enter a name to search.")
        else:
            try:
                em      = EmployeeManager()
                results = em.list_employees(search=name_query.strip(), limit=20)
                if not results:
                    st.warning(f"No employees found matching '{name_query}'.")
                else:
                    import pandas as pd
                    st.caption(f"{len(results)} result(s) found")
                    df = pd.DataFrame([{
                        "ID":             e.employee_id,
                        "Name":           e.full_name,
                        "Department ID":  e.department_id,
                        "Job Level":      e.job_level,
                        "Monthly Income": f"${e.monthly_income:,.0f}",
                        "Hire Date":      str(e.hire_date),
                        "Status":         "Active" if e.is_active else "Inactive",
                    } for e in results])
                    st.dataframe(df, use_container_width=True, hide_index=True)
            except DatabaseError as exc:
                st.warning(str(exc))
