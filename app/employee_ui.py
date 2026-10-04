import streamlit as st
import datetime
from db_queries import (
    get_employees, get_employee_count, get_departments, get_job_roles,
    add_employee, update_employee_department, suggest_employee_id,
    reset_fallback_flag, show_fallback_warning,
)


def render_employees():
    reset_fallback_flag()
    st.markdown("<h1>Employee Management</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#475569;font-size:1.05rem;margin-top:-12px;margin-bottom:12px;'>"
        "Manage employee records, onboarding and department history.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Add new employee ───────────────────────────────────────────────────
    with st.expander("➕  Add New Employee", expanded=False):
        st.info(
            "✅ **Database Write Enabled.** Employee records are saved to MySQL and "
            "synced to OLAP dimensions."
        )
        # Suggest a unique ID (cached per session so re-renders are fast)
        if "suggested_emp_id" not in st.session_state:
            st.session_state["suggested_emp_id"] = suggest_employee_id()

        with st.form("onboard_form", clear_on_submit=True):
            st.markdown("#### Employee Details")
            st.markdown("<hr>", unsafe_allow_html=True)

            # Show the suggested ID and let the user override it
            st.caption(
                f"🔑 **Suggested unique ID:** `EMP{st.session_state['suggested_emp_id']:05d}` — "
                "You may enter a different number below, but it must not already be in use."
            )

            dept_list = get_departments()
            role_list = get_job_roles()

            c1, c2 = st.columns(2)
            with c1:
                emp_id    = st.text_input(
                    "Employee ID",
                    value=f"EMP{st.session_state['suggested_emp_id']:05d}",
                    help="Must be unique. Format: EMP followed by digits, e.g. EMP00101.",
                )
                name      = st.text_input("Full Name",          placeholder="e.g. Jane Doe")
                age       = st.number_input("Age",              min_value=18, max_value=100, step=1)
                gender    = st.selectbox("Gender",              ["Male", "Female", "Other"])
                join_date = st.date_input("Joining Date")
            with c2:
                dept       = st.selectbox("Department",         dept_list) if dept_list else st.text_input("Department")
                role       = st.selectbox("Job Role",           role_list) if role_list else st.text_input("Job Role")
                salary     = st.number_input("Salary (USD)",    min_value=0, step=1000)
                experience = st.number_input("Experience (Yrs)", min_value=0, step=1)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("💼  Save Employee Record"):
                errors = []
                if not emp_id.strip():   errors.append("Employee ID is required.")
                if not name.strip():     errors.append("Full Name is required.")
                if not dept:             errors.append("Department is required.")
                if not role:             errors.append("Job Role is required.")
                if age <= 0:             errors.append("Age must be a positive value.")
                if salary < 0:           errors.append("Salary cannot be negative.")
                for err in errors:
                    st.error(err)
                if not errors:
                    try:
                        add_employee({
                            "ID": emp_id, "Name": name, "Age": age, "Gender": gender,
                            "Department": dept, "Job Role": role, "Salary": salary,
                            "Joining Date": join_date, "Experience": experience,
                        })
                        st.success(f"✅ Employee **{name}** ({emp_id}) added successfully!")
                        # Advance the suggested ID so the next open shows a fresh suggestion
                        st.session_state["suggested_emp_id"] = suggest_employee_id()
                    except Exception as ex:
                        st.error(f"🚫 {ex}")

    # ── SCD Type 2 department update ─────────────────────────────────────
    with st.expander("🔄  Update Employee Department  (SCD Type 2)", expanded=False):
        st.info(
            "✅ **Database Write Enabled.** Updating a department closes the current "
            "`employee_history` record and inserts a new version (SCD Type 2). "
            "Changes are immediately synchronized to the OLAP dimension."
        )
        # Populate the dropdown from the real DB (first page only, for performance)
        df_active = get_employees(active_only=True, page=1)
        choices = (df_active["ID"].astype(str) + "  —  " + df_active["Name"]).tolist() \
                  if not df_active.empty else []

        with st.form("update_dept_form", clear_on_submit=True):
            st.markdown("#### Change Department")
            st.markdown("<hr>", unsafe_allow_html=True)
            st.info(
                "**SCD Type 2:** The current record is closed (end-dated) and a new active "
                "record is inserted with the updated department. History is preserved."
            )
            selected = st.selectbox("Select Employee", choices) if choices else st.text_input("Employee ID")
            dept_list = get_departments()
            new_dept = st.selectbox("New Department", dept_list) if dept_list else st.text_input("New Department", placeholder="e.g. Sales")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🔄  Update Department"):
                if not selected:
                    st.error("Please select an employee.")
                elif not new_dept:
                    st.error("New Department is required.")
                else:
                    eid = selected.split("  —  ")[0].strip() if "  —  " in selected else selected
                    try:
                        update_employee_department(eid, new_dept)
                        st.success(f"✅ Department for employee **{eid}** updated to **{new_dept}** successfully!")
                    except Exception as ex:
                        st.error(f"🚫 {ex}")

    # ── Employee Directory with pagination ───────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 👥  Employee Directory")
    show_history = st.checkbox("Show historical (closed) SCD Type 2 records", value=False)

    # Page selector — shown before fetch so the correct page is loaded
    total_count  = get_employee_count(active_only=not show_history)
    total_pages  = max(1, -(-total_count // 500))   # ceiling division
    page = st.number_input(
        f"Page (500 records/page — {total_count:,} total records)",
        min_value=1, max_value=total_pages, value=1, step=1,
        key="emp_page",
    )
    df_emp = get_employees(active_only=not show_history, page=page)
    show_fallback_warning()  # single banner after all fetches

    col_s, col_f = st.columns(2)
    search = col_s.text_input("🔍  Search by Name or ID", placeholder="Search...")
    dept_options = ["All"] + get_departments()
    dept_f = col_f.selectbox(
        "📁  Filter by Department",
        dept_options,
        key="emp_dept_filter",
    )

    filtered = df_emp
    if search:
        filtered = filtered[
            filtered["Name"].astype(str).str.contains(search, case=False, na=False) |
            filtered["ID"].astype(str).str.contains(search, case=False, na=False)
        ]
    if dept_f != "All":
        filtered = filtered[filtered["Department"] == dept_f]

    if not filtered.empty:
        st.caption(
            f"Showing page {page} of {total_pages} — "
            f"{len(filtered):,} rows after filter (of {len(df_emp):,} on this page)."
        )
        st.dataframe(filtered, width="stretch", hide_index=True)
    else:
        st.info("No employees match the current filters.")
