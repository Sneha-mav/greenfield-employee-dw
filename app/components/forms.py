"""Streamlit form components — one function per form.
Each function renders a form and returns a dict of validated field values
on submit, or None if the form has not been submitted yet.
No manager calls inside — forms only collect input.
"""
from datetime import date
from typing import Optional
import streamlit as st

# ── Employee onboarding ───────────────────────────────────────────────────────
def onboard_employee_form(departments: list, job_roles: list) -> Optional[dict]:
    """Render the new-employee onboarding form.
    Returns a dict of field values on submit, None otherwise.
    """
    dept_map = {d["department_name"]: d["department_id"] for d in departments}
    role_map = {r["job_role_name"]:   r["job_role_id"]   for r in job_roles}

    with st.form("onboard_employee", clear_on_submit=False):
        st.markdown("#### Personal Details")
        c1, c2 = st.columns(2)
        first_name = c1.text_input("First Name *")
        last_name  = c2.text_input("Last Name *")
        email      = st.text_input("Email Address *")

        c3, c4, c5 = st.columns(3)
        gender         = c3.selectbox("Gender", ["Male", "Female", "Other"])
        age            = c4.number_input("Age", min_value=18, max_value=65, value=30)
        marital_status = c5.selectbox("Marital Status", ["Single", "Married", "Divorced"])

        c6, c7 = st.columns(2)
        city            = c6.text_input("City")
        education_field = c7.selectbox(
            "Education Field",
            ["Life Sciences", "Medical", "Marketing", "Technical Degree",
             "Human Resources", "Other"],
        )

        st.markdown("#### Role & Compensation")
        c8, c9 = st.columns(2)
        dept_name = c8.selectbox("Department *", list(dept_map.keys()))
        role_name = c9.selectbox("Job Role *", list(role_map.keys()))

        c10, c11, c12 = st.columns(3)
        job_level      = c10.slider("Job Level", min_value=1, max_value=5, value=2)
        monthly_income = c11.number_input("Monthly Income ($)", min_value=1000,
                                          max_value=50000, value=5000, step=100)
        over_time      = c12.selectbox("Over Time", ["No", "Yes"])

        hire_date = st.date_input("Hire Date *", value=date.today())
        submitted = st.form_submit_button("Onboard employee", type="primary",
                                          use_container_width=True)

    if not submitted:
        return None

    # Client-side validation
    errors = []
    if not first_name.strip():
        errors.append("First name is required.")
    if not last_name.strip():
        errors.append("Last name is required.")
    if not email.strip() or "@" not in email:
        errors.append("A valid email address is required.")
    if errors:
        for e in errors:
            st.error(e)
        return None

    return dict(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email.strip(),
        gender=gender,
        age=int(age),
        marital_status=marital_status,
        city=city.strip() or None,
        education_field=education_field,
        department_id=dept_map[dept_name],
        job_role_id=role_map[role_name],
        job_level=int(job_level),
        monthly_income=float(monthly_income),
        over_time=1 if over_time == "Yes" else 0,
        hire_date=hire_date,
    )


# ── Project creation ──────────────────────────────────────────────────────────
def create_project_form(departments: list) -> Optional[dict]:
    """Render the new-project form. Returns field dict or None."""
    dept_map = {d["department_name"]: d["department_id"] for d in departments}

    with st.form("create_project", clear_on_submit=False):
        project_name = st.text_input("Project Name *")
        c1, c2 = st.columns(2)
        dept_name = c1.selectbox("Owning Department *", list(dept_map.keys()))
        status    = c2.selectbox("Status", ["Active", "On Hold", "Completed"])
        c3, c4 = st.columns(2)
        start_date = c3.date_input("Start Date", value=date.today())
        end_date   = c4.date_input("End Date (optional)", value=None)
        submitted  = st.form_submit_button("Create project", type="primary",
                                           use_container_width=True)

    if not submitted:
        return None
    if not project_name.strip():
        st.error("Project name is required.")
        return None
    if end_date and end_date < start_date:
        st.error("End date cannot be before start date.")
        return None

    return dict(
        project_name=project_name.strip(),
        department_id=dept_map[dept_name],
        status=status,
        start_date=start_date,
        end_date=end_date,
    )


def assign_employee_form(projects: list) -> Optional[dict]:
    """Render the assign-employee-to-project form."""
    proj_map = {f"[{p['project_id']}] {p['project_name']}": p["project_id"]
                for p in projects}

    with st.form("assign_employee", clear_on_submit=False):
        st.markdown("#### Assign Employee to Project")
        c1, c2 = st.columns(2)
        proj_label  = c1.selectbox("Project *", list(proj_map.keys()))
        employee_id = c2.number_input("Employee ID *", min_value=1, step=1)

        c3, c4 = st.columns(2)
        COMMON_ROLES = [
            "Developer", "Senior Developer", "Tech Lead", "Project Manager",
            "Business Analyst", "QA Engineer", "DevOps Engineer", "Data Engineer",
            "Designer", "Scrum Master", "Product Owner", "Consultant", "Custom...",
        ]
        role_selection = c3.selectbox("Role on Project *", COMMON_ROLES)
        allocation_pct = c4.slider("Allocation %", min_value=10, max_value=100,
                                   value=100, step=10)

        role_on_proj = ""
        if role_selection == "Custom...":
            role_on_proj = st.text_input("Enter custom role *")

        c5, c6 = st.columns(2)
        start_date = c5.date_input("Assignment Start *", value=date.today())
        end_date   = c6.date_input("Assignment End (optional)", value=None)
        submitted  = st.form_submit_button("Assign employee", type="primary",
                                           use_container_width=True)

    if not submitted:
        return None
    if role_selection != "Custom...":
        role_on_proj = role_selection
    if not role_on_proj.strip():
        st.error("Role on project is required.")
        return None

    return dict(
        project_id=proj_map[proj_label],
        employee_id=int(employee_id),
        role_on_project=role_on_proj.strip(),
        allocation_pct=int(allocation_pct),
        start_date=start_date,
        end_date=end_date,
    )


COMMON_ROLES = [
    "Developer", "Senior Developer", "Tech Lead", "Project Manager",
    "Business Analyst", "QA Engineer", "DevOps Engineer", "Data Engineer",
    "Designer", "Scrum Master", "Product Owner", "Consultant", "Custom...",
]


def assign_multiple_employees_form(projects: list) -> Optional[list]:
    """Render a dynamic form to assign multiple employees to one project.
    Returns a list of assignment dicts on submit, None otherwise.
    """
    proj_map = {f"[{p['project_id']}] {p['project_name']}": p["project_id"]
                for p in projects}

    # ── Project + dates (outside form so Add row button works) ───────────────
    c1, c2 = st.columns(2)
    proj_label = c1.selectbox("Project *", list(proj_map.keys()), key="bulk_project")
    c3, c4 = st.columns(2)
    start_date = c3.date_input("Assignment Start *", value=date.today(), key="bulk_start")
    end_date   = c4.date_input("Assignment End (optional)", value=None, key="bulk_end")

    # ── Dynamic employee rows ─────────────────────────────────────────────────
    if "bulk_employee_rows" not in st.session_state:
        st.session_state["bulk_employee_rows"] = 1

    st.markdown("#### Employees")
    rows = []
    for i in range(st.session_state["bulk_employee_rows"]):
        st.markdown(f"**Employee {i + 1}**")
        r1, r2, r3 = st.columns([1, 2, 1])
        emp_id     = r1.number_input("Employee ID *", min_value=1, step=1,
                                     key=f"bulk_emp_id_{i}")
        role_sel   = r2.selectbox("Role *", COMMON_ROLES, key=f"bulk_role_{i}")
        alloc      = r3.slider("Allocation %", min_value=10, max_value=100,
                               value=100, step=10, key=f"bulk_alloc_{i}")
        custom_role = ""
        if role_sel == "Custom...":
            custom_role = st.text_input("Custom role *", key=f"bulk_custom_{i}")
        rows.append((emp_id, role_sel, alloc, custom_role))

    # ── Add / Remove row buttons ──────────────────────────────────────────────
    btn1, btn2, btn3 = st.columns([1, 1, 4])
    if btn1.button("＋ Add employee", key="bulk_add_row"):
        st.session_state["bulk_employee_rows"] += 1
        st.rerun()
    if btn2.button("－ Remove last", key="bulk_remove_row",
                   disabled=st.session_state["bulk_employee_rows"] <= 1):
        st.session_state["bulk_employee_rows"] -= 1
        st.rerun()

    st.divider()
    submitted = st.button("Assign all employees", type="primary",
                          use_container_width=True, key="bulk_submit")

    if not submitted:
        return None

    # ── Validate ──────────────────────────────────────────────────────────────
    assignments = []
    errors = []
    for i, (emp_id, role_sel, alloc, custom_role) in enumerate(rows):
        role = custom_role.strip() if role_sel == "Custom..." else role_sel
        if not role:
            errors.append(f"Employee {i + 1}: role is required.")
            continue
        assignments.append(dict(
            project_id=proj_map[proj_label],
            employee_id=int(emp_id),
            role_on_project=role,
            allocation_pct=int(alloc),
            start_date=start_date,
            end_date=end_date,
        ))

    if errors:
        for e in errors:
            st.error(e)
        return None

    # Reset row count on successful submit
    st.session_state["bulk_employee_rows"] = 1
    return assignments


# ── Performance review ────────────────────────────────────────────────────────
def submit_review_form(projects: list) -> Optional[dict]:
    """Render the performance-review submission form."""
    proj_options = {"None (no project)": None}
    proj_options.update({
        f"[{p['project_id']}] {p['project_name']}": p["project_id"]
        for p in projects
    })

    with st.form("submit_review", clear_on_submit=False):
        employee_id = st.number_input("Employee ID *", min_value=1, step=1)
        c1, c2 = st.columns(2)
        review_date = c1.date_input("Review Date *", value=date.today())
        proj_label  = c2.selectbox("Project (optional)", list(proj_options.keys()))

        st.markdown("#### Ratings")
        c3, c4 = st.columns(2)
        performance_rating = c3.slider("Performance Rating (1–5)", 1, 5, 3)
        review_score       = c4.slider("Review Score (0–100)", 0, 100, 70)

        c5, c6, c7 = st.columns(3)
        job_satisfaction      = c5.slider("Job Satisfaction (1–4)", 1, 4, 3)
        env_satisfaction      = c6.slider("Environment Satisfaction (1–4)", 1, 4, 3)
        salary_hike_pct       = c7.number_input("Salary Hike %", min_value=0.0,
                                                 max_value=100.0, value=10.0, step=0.5)

        submitted = st.form_submit_button("Submit review", type="primary",
                                          use_container_width=True)

    if not submitted:
        return None

    return dict(
        employee_id=int(employee_id),
        review_date=review_date,
        project_id=proj_options[proj_label],
        performance_rating=int(performance_rating),
        review_score=float(review_score),
        job_satisfaction=int(job_satisfaction),
        environment_satisfaction=int(env_satisfaction),
        salary_hike_pct=float(salary_hike_pct),
    )


# ── SCD Type 2 change forms ───────────────────────────────────────────────────

def update_department_form(departments: list) -> Optional[dict]:
    """Department transfer — triggers SCD Type 2."""
    dept_names = [d["department_name"] for d in departments]

    with st.form("update_department", clear_on_submit=False):
        c1, c2 = st.columns(2)
        employee_id    = c1.number_input("Employee ID *", min_value=1, step=1)
        new_dept       = c2.selectbox("New Department *", dept_names)
        effective_date = st.date_input("Effective Date *", value=date.today())
        submitted = st.form_submit_button("Apply Transfer", type="primary",
                                          use_container_width=True)

    if not submitted:
        return None

    return dict(
        employee_id=int(employee_id),
        new_department_name=new_dept,
        effective_date=effective_date,
    )


def change_role_form(job_roles: list) -> Optional[dict]:
    """Role / level / salary change — triggers SCD Type 2."""
    role_names = ["No change"] + [r["job_role_name"] for r in job_roles]

    employee_id    = st.number_input("Employee ID *", min_value=1, step=1, key="cr_employee_id")

    c1, c2 = st.columns(2)
    role_name      = c1.selectbox("New Job Role", role_names,
                                  help="Select 'No change' to leave the role as-is.",
                                  key="cr_role_name")
    effective_date = c2.date_input("Effective Date *", value=date.today(), key="cr_effective_date")

    c3, c4 = st.columns(2)
    change_level  = c3.checkbox("Update Job Level",      key="cr_change_level")
    change_salary = c4.checkbox("Update Monthly Income", key="cr_change_salary")

    job_level      = None
    monthly_income = None

    if change_level:
        job_level = st.slider("New Job Level", min_value=1, max_value=5, value=3,
                              key="cr_job_level")

    if change_salary:
        monthly_income = st.number_input(
            "New Monthly Income ($)", min_value=1000, max_value=100000,
            value=5000, step=100, key="cr_monthly_income",
        )

    submitted = st.button("Apply Change", type="primary",
                          use_container_width=True, key="cr_submit")

    if not submitted:
        return None

    selected_role = role_name if role_name != "No change" else None

    if selected_role is None and job_level is None and monthly_income is None:
        st.error("Select at least one field to change.")
        return None

    return dict(
        employee_id=int(employee_id),
        effective_date=effective_date,
        job_role_name=selected_role,
        job_level=int(job_level) if job_level is not None else None,
        monthly_income=float(monthly_income) if monthly_income is not None else None,
    )
