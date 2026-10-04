"""Page 4 — Employee Changes."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.components.theme import inject_css, section_header
from app.components.forms import change_role_form, update_department_form
from app.components.charts import scd2_gantt
from app.components.tables import scd2_history_table
from src.db_manager import DatabaseError, ValidationError
from src.managers import AnalyticsManager, EmployeeManager

inject_css()

st.title("Employee changes")

# ── Load reference data ───────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def _load_refs() -> tuple:
    am = AnalyticsManager()
    return am.list_departments(), am.list_job_roles()

try:
    departments, job_roles = _load_refs()
except DatabaseError as exc:
    st.error(f"Could not connect to database: {exc}")
    st.stop()


def _show_history_after_change(employee_id: int) -> None:
    """Load and render the updated SCD2 history immediately after a change."""
    try:
        am      = AnalyticsManager()
        history = am.get_employee_scd2_history(employee_id)
        if history:
            df       = pd.DataFrame(history)
            emp_name = str(df.iloc[0]["full_name"]) if "full_name" in df.columns else ""
            st.divider()
            section_header("Updated Version History")
            scd2_history_table(df)
            st.plotly_chart(scd2_gantt(df, emp_name), use_container_width=True)
    except DatabaseError:
        pass  # non-critical — the change itself succeeded


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_dept, tab_role, tab_view = st.tabs([
    "Department Transfer",
    "Role / Level / Salary",
    "History",
])


# ── Tab 1: Department transfer ────────────────────────────────────────────────
with tab_dept:
    st.caption("Transfer effective on the selected date.")
    data = update_department_form(departments)
    if data is not None:
        try:
            em = EmployeeManager()
            em.update_department(
                employee_id=data["employee_id"],
                new_department_name=data["new_department_name"],
                effective_date=data["effective_date"],
                refresh_warehouse=True,
            )
            st.success(
                f"Employee {data['employee_id']} transferred to "
                f"**{data['new_department_name']}** effective {data['effective_date']}."
            )
            _show_history_after_change(data["employee_id"])
        except ValidationError as exc:
            st.error(f"Validation error: {exc}")
        except DatabaseError as exc:
            st.error(f"Database error: {exc}")


# ── Tab 2: Role / level / salary change ───────────────────────────────────────
with tab_role:
    st.caption("Select the fields to update.")
    data = change_role_form(job_roles)
    if data is not None:
        try:
            em = EmployeeManager()
            em.change_role_or_salary(
                employee_id=data["employee_id"],
                effective_date=data["effective_date"],
                job_role_name=data["job_role_name"],
                job_level=data["job_level"],
                monthly_income=data["monthly_income"],
                refresh_warehouse=True,
            )
            parts = []
            if data["job_role_name"]:
                parts.append(f"role → **{data['job_role_name']}**")
            if data["job_level"] is not None:
                parts.append(f"level → **{data['job_level']}**")
            if data["monthly_income"] is not None:
                parts.append(f"income → **${data['monthly_income']:,.0f}**")
            st.success(
                f"Employee {data['employee_id']}: {', '.join(parts)} "
                f"effective {data['effective_date']}."
            )
            _show_history_after_change(data["employee_id"])
        except ValidationError as exc:
            st.error(f"Validation error: {exc}")
        except DatabaseError as exc:
            st.error(f"Database error: {exc}")


# ── Tab 3: View history ───────────────────────────────────────────────────────
with tab_view:
    st.caption("Enter an employee ID to view changes.")

    col_a, col_b = st.columns([2, 1])
    view_id  = col_a.number_input("Employee ID", min_value=1, step=1, key="view_scd2_id")
    view_btn = col_b.button("Load history", use_container_width=True, key="view_scd2_btn")

    if view_btn:
        try:
            am      = AnalyticsManager()
            history = am.get_employee_scd2_history(int(view_id))
            if not history:
                st.warning(
                    f"No warehouse history found for employee {view_id}. "
                    "They may not yet be loaded into dim_employee."
                )
            else:
                df       = pd.DataFrame(history)
                versions = len(df)
                emp_name = str(df.iloc[0]["full_name"]) if "full_name" in df.columns else ""

                c1, c2, c3 = st.columns(3)
                c1.metric("Employee",       emp_name)
                c2.metric("Changes",  str(versions))
                c3.metric("Currently Active",
                           "Yes" if int(df["is_current"].max()) == 1 else "No")

                scd2_history_table(df)
                st.plotly_chart(scd2_gantt(df, emp_name), use_container_width=True)

                if versions > 1:
                    depts = df["department_name"].nunique()
                    roles = df["job_role"].nunique()
                    st.caption(
                        f"{versions} recorded changes across "
                        f"{depts} department(s) and {roles} role(s)."
                    )
        except DatabaseError as exc:
            st.error(str(exc))
