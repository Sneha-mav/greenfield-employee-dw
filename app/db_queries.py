"""db_queries.py — Real-database data layer for the Employee Analytics Portal.

Drop-in replacement for mock_data.py.  Every public function has the same
signature as its mock counterpart so UI modules only need to change their
import line.

All four write operations (add_employee, add_project, add_review,
update_employee_department) are fully enabled and write directly to MySQL
using parameterized SQL inside transactions.

On DatabaseError the function falls back to mock_data, sets
st.session_state["_db_fallback"] = True, and logs the error
(without exposing credentials or connection strings).
"""

from __future__ import annotations

import logging
import sys
import os

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Import the DB layer.  sys.path is extended so this module works whether
# Streamlit is run from the project root or from the app/ sub-directory.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import re
from src.db_manager import DatabaseConnection, DatabaseError, ValidationError  # noqa: E402

import mock_data as _mock  # noqa: E402  (fallback)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PAGE_SIZE = 500  # rows returned per page for the employee directory


def _db() -> DatabaseConnection:
    """Return the singleton DB connection (pool is lazily created)."""
    return DatabaseConnection()


def _set_fallback(exc: Exception) -> None:
    """Log the error (no credentials) and flag the session for a warning banner."""
    # Log only the exception type and message — never the connection string.
    logger.error(
        "Database query failed (%s: %s). Falling back to mock data.",
        type(exc).__name__,
        exc,
    )
    st.session_state["_db_fallback"] = True


def reset_fallback_flag() -> None:
    """Call once at the top of each page render to clear the previous flag."""
    st.session_state["_db_fallback"] = False


def show_fallback_warning() -> None:
    """Render exactly one warning banner when mock data is in use.

    Call this once near the top of every page render function, after
    reset_fallback_flag() and after all data-fetch calls have been made.
    """
    if st.session_state.get("_db_fallback", False):
        st.warning(
            "⚠️ **Live database unavailable** — displaying sample data. "
            "Check your `.env` settings and MySQL connection, then refresh the page."
        )


# ---------------------------------------------------------------------------
# 1. Employees
# ---------------------------------------------------------------------------

# SQL: OLTP  employees ← departments ← job_roles
# active_only=True  → attrition = 0  (current employees)
# active_only=False → all rows from employees JOIN employee_history
#                     so every SCD2 version is visible with its OWN
#                     department, job role, job level, and salary.

_SQL_EMPLOYEES_CURRENT = """
    SELECT
        e.employee_id                               AS `ID`,
        CONCAT(e.first_name, ' ', e.last_name)      AS `Name`,
        e.age                                       AS `Age`,
        e.gender                                    AS `Gender`,
        d.department_name                           AS `Department`,
        r.job_role_name                             AS `Job Role`,
        e.monthly_income                            AS `Salary`,
        e.hire_date                                 AS `Joining Date`,
        e.years_at_company                          AS `Experience`,
        IF(e.attrition = 0, 1, 0)                  AS `Is Active`,
        e.hire_date                                 AS `Effective Start Date`,
        NULL                                        AS `Effective End Date`
    FROM employees e
    JOIN departments d ON d.department_id = e.department_id
    JOIN job_roles   r ON r.job_role_id   = e.job_role_id
    WHERE e.attrition = 0
    ORDER BY e.employee_id DESC
    LIMIT %s OFFSET %s
"""

# When history is shown: one row per SCD2 version in employee_history.
# Each version carries its OWN department, job role, job level, and salary —
# not the current employee snapshot values.
_SQL_EMPLOYEES_HISTORY = """
    SELECT
        e.employee_id                               AS `ID`,
        CONCAT(e.first_name, ' ', e.last_name)      AS `Name`,
        e.age                                       AS `Age`,
        e.gender                                    AS `Gender`,
        d.department_name                           AS `Department`,
        r.job_role_name                             AS `Job Role`,
        h.monthly_income                            AS `Salary`,
        e.hire_date                                 AS `Joining Date`,
        e.years_at_company                          AS `Experience`,
        IF(h.effective_to IS NULL, 1, 0)            AS `Is Active`,
        h.effective_from                            AS `Effective Start Date`,
        h.effective_to                              AS `Effective End Date`
    FROM employee_history h
    JOIN employees   e ON e.employee_id   = h.employee_id
    JOIN departments d ON d.department_id = h.department_id
    JOIN job_roles   r ON r.job_role_id   = h.job_role_id
    ORDER BY h.employee_id DESC, h.effective_from DESC
    LIMIT %s OFFSET %s
"""

_SQL_EMPLOYEES_CURRENT_COUNT = "SELECT COUNT(*) AS n FROM employees WHERE attrition = 0"
_SQL_EMPLOYEES_HISTORY_COUNT = "SELECT COUNT(*) AS n FROM employee_history"


def get_employees(active_only: bool = False, page: int = 1) -> pd.DataFrame:
    """Return a page of employee records.

    Parameters
    ----------
    active_only : bool
        True  → current employees only (attrition = 0, OLTP snapshot).
        False → one row per SCD2 version from employee_history, each with the
                department/role/salary valid for that version.
    page : int
        1-based page number (page_size = 500 rows).

    Returns
    -------
    pd.DataFrame with columns matching mock_data exactly:
        ID, Name, Age, Gender, Department, Job Role, Salary,
        Joining Date, Experience, Is Active,
        Effective Start Date, Effective End Date
    """
    reset_fallback_flag()
    offset = (_PAGE_SIZE * (page - 1))
    try:
        if active_only:
            rows = _db().fetch_all(_SQL_EMPLOYEES_CURRENT, (_PAGE_SIZE, offset))
        else:
            rows = _db().fetch_all(_SQL_EMPLOYEES_HISTORY, (_PAGE_SIZE, offset))
        if not rows:
            return pd.DataFrame(
                columns=["ID", "Name", "Age", "Gender", "Department",
                         "Job Role", "Salary", "Joining Date", "Experience",
                         "Is Active", "Effective Start Date", "Effective End Date"]
            )
        df = pd.DataFrame(rows)
        # Ensure date columns are python date objects (mysql.connector returns date already)
        for col in ("Joining Date", "Effective Start Date", "Effective End Date"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        df["Is Active"] = df["Is Active"].astype(bool)
        return df
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return _mock.get_employees(active_only=active_only)


def get_employee_count(active_only: bool = False) -> int:
    """Return total employee count (used for pagination UI)."""
    try:
        sql = _SQL_EMPLOYEES_CURRENT_COUNT if active_only else _SQL_EMPLOYEES_HISTORY_COUNT
        row = _db().fetch_one(sql)
        return int(row["n"]) if row else 0
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return len(_mock.get_employees(active_only=active_only))


def get_departments() -> list[str]:
    """Return sorted list of department names for filter dropdowns."""
    try:
        rows = _db().fetch_all("SELECT department_name FROM departments ORDER BY department_name")
        return [r["department_name"] for r in rows]
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        df = _mock.get_employees()
        return sorted(df["Department"].dropna().unique().tolist())


def get_job_roles() -> list[str]:
    """Return sorted list of job role names for the Add Employee form."""
    try:
        rows = _db().fetch_all("SELECT job_role_name FROM job_roles ORDER BY job_role_name")
        return [r["job_role_name"] for r in rows]
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        df = _mock.get_employees()
        return sorted(df["Job Role"].dropna().unique().tolist()) if "Job Role" in df.columns else []


def suggest_employee_id() -> int:
    """Return the next safe unused numeric employee_id.

    Strategy: MAX(employee_id) + 1 is safe for suggesting IDs in the UI
    because the actual INSERT will fail with a clear duplicate-key error
    if a concurrent session uses the same ID.  The UI pre-fills this value
    so the user always starts with a unique suggestion.
    """
    try:
        row = _db().fetch_one("SELECT COALESCE(MAX(employee_id), 100000) + 1 AS next_id FROM employees")
        return int(row["next_id"])
    except (DatabaseError, Exception):
        return 100001  # safe fallback if DB is unavailable



# ---------------------------------------------------------------------------
# 2. Dashboard KPIs
# ---------------------------------------------------------------------------

_SQL_KPI_EMPLOYEES   = "SELECT COUNT(*) AS n FROM employees WHERE attrition = 0"
_SQL_KPI_DEPARTMENTS = "SELECT COUNT(DISTINCT department_id) AS n FROM employees WHERE attrition = 0"
_SQL_KPI_PROJECTS    = "SELECT COUNT(*) AS n FROM projects"
# Average performance_rating from OLTP reviews (authoritative grain for KPI)
_SQL_KPI_AVG_PERF    = "SELECT ROUND(AVG(performance_rating), 1) AS n FROM reviews"


def get_dashboard_data() -> dict:
    """Return KPI dict: total_employees, total_departments, total_projects, avg_performance.

    Uses OLTP tables for authoritative counts.
    Falls back to mock_data.get_dashboard_data() on error.
    """
    reset_fallback_flag()
    try:
        db = _db()
        total_employees   = int((db.fetch_one(_SQL_KPI_EMPLOYEES)   or {}).get("n", 0))
        total_departments = int((db.fetch_one(_SQL_KPI_DEPARTMENTS) or {}).get("n", 0))
        total_projects    = int((db.fetch_one(_SQL_KPI_PROJECTS)    or {}).get("n", 0))
        avg_perf_raw      = (db.fetch_one(_SQL_KPI_AVG_PERF)        or {}).get("n", 0)
        avg_performance   = float(avg_perf_raw) if avg_perf_raw is not None else 0.0
        return {
            "total_employees":   total_employees,
            "total_departments": total_departments,
            "total_projects":    total_projects,
            "avg_performance":   round(avg_performance, 1),
        }
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return _mock.get_dashboard_data()


# ---------------------------------------------------------------------------
# 3. Department breakdown (for pie chart)
# ---------------------------------------------------------------------------

_SQL_DEPT_BREAKDOWN = """
    SELECT d.department_name AS `Department`, COUNT(*) AS `Count`
    FROM employees e
    JOIN departments d ON d.department_id = e.department_id
    WHERE e.attrition = 0
    GROUP BY d.department_name
    ORDER BY `Count` DESC
"""


def get_department_breakdown() -> pd.DataFrame:
    """Return DataFrame(Department, Count) for the workforce-by-department pie chart."""
    try:
        rows = _db().fetch_all(_SQL_DEPT_BREAKDOWN)
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Department", "Count"])
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        df = _mock.get_employees(active_only=True)
        if df.empty:
            return pd.DataFrame(columns=["Department", "Count"])
        return df["Department"].value_counts().reset_index().rename(
            columns={"index": "Department", "Department": "Count"}
        )


# ---------------------------------------------------------------------------
# 4. Projects
# ---------------------------------------------------------------------------

# Returns project list joined to departments for the department name.
# Also appends an "Assigned Employees" count so the existing bar chart works.
_SQL_PROJECTS = """
    SELECT
        p.project_id                                AS `Project ID`,
        p.project_name                              AS `Project Name`,
        d.department_name                           AS `Department`,
        p.status                                    AS `Status`,
        p.start_date                                AS `Start Date`,
        p.end_date                                  AS `End Date`,
        COUNT(a.assignment_id)                      AS `Assigned Employees`
    FROM projects p
    JOIN departments d ON d.department_id = p.department_id
    LEFT JOIN assignments a ON a.project_id = p.project_id
    GROUP BY p.project_id, p.project_name, d.department_name, p.status, p.start_date, p.end_date
    ORDER BY p.project_id
"""


def get_projects() -> pd.DataFrame:
    """Return DataFrame of all projects with assignment counts.

    Columns: Project ID, Project Name, Department, Status,
             Start Date, End Date, Assigned Employees
    """
    reset_fallback_flag()
    try:
        rows = _db().fetch_all(_SQL_PROJECTS)
        if not rows:
            return pd.DataFrame(
                columns=["Project ID", "Project Name", "Department",
                         "Status", "Start Date", "End Date", "Assigned Employees"]
            )
        df = pd.DataFrame(rows)
        for col in ("Start Date", "End Date"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        return df
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return _mock.get_projects()


# ---------------------------------------------------------------------------
# 5. Reviews
# ---------------------------------------------------------------------------

_SQL_REVIEWS = """
    SELECT
        r.review_id                                 AS `Review ID`,
        CONCAT(e.first_name, ' ', e.last_name)      AS `Employee`,
        r.review_date                               AS `Review Date`,
        r.performance_rating                        AS `Rating`,
        r.review_score                              AS `Review Score`,
        r.job_satisfaction                          AS `Job Satisfaction`,
        r.environment_satisfaction                  AS `Environment Satisfaction`,
        r.salary_hike_pct                           AS `Salary Hike %`,
        r.manager_comments                          AS `Manager Comments`,
        r.goals                                     AS `Goals`
    FROM reviews r
    JOIN employees e ON e.employee_id = r.employee_id
    ORDER BY r.review_date DESC
    LIMIT %s OFFSET %s
"""

_SQL_REVIEWS_COUNT = "SELECT COUNT(*) AS n FROM reviews"


def get_reviews(page: int = 1) -> pd.DataFrame:
    """Return a page of performance reviews."""
    reset_fallback_flag()
    offset = _PAGE_SIZE * (page - 1)
    try:
        rows = _db().fetch_all(_SQL_REVIEWS, (_PAGE_SIZE, offset))
        if not rows:
            return pd.DataFrame(
                columns=["Review ID", "Employee", "Review Date", "Rating",
                         "Review Score", "Job Satisfaction",
                         "Environment Satisfaction", "Salary Hike %",
                         "Manager Comments", "Goals"]
            )
        df = pd.DataFrame(rows)
        df["Review Date"] = pd.to_datetime(df["Review Date"], errors="coerce").dt.date
        for col in ["Review Score", "Job Satisfaction", "Environment Satisfaction", "Salary Hike %"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ["Manager Comments", "Goals"]:
            if col in df.columns:
                df[col] = df[col].fillna("-").astype(str)
        return df
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return _mock.get_reviews()


def get_review_count() -> int:
    """Return total review count (for pagination)."""
    try:
        row = _db().fetch_one(_SQL_REVIEWS_COUNT)
        return int(row["n"]) if row else 0
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return len(_mock.get_reviews())


# ---------------------------------------------------------------------------
# 6. Analytics — OLAP queries (from 08_analytics_queries.sql)
# ---------------------------------------------------------------------------

# 6a. Year-over-year performance trend (Query 1 from 08_analytics_queries.sql)
_SQL_YOY_TREND = """
    WITH yearly AS (
        SELECT
            dt.year,
            COUNT(*)                            AS reviews,
            ROUND(AVG(f.performance_rating), 3) AS avg_rating,
            ROUND(AVG(f.review_score), 2)       AS avg_score
        FROM fact_performance_reviews f
        JOIN dim_date dt ON dt.date_key = f.review_date_key
        GROUP BY dt.year
    )
    SELECT
        y.year                                                                  AS `Year`,
        y.reviews                                                               AS `Reviews`,
        y.avg_rating                                                            AS `Avg Rating`,
        y.avg_score                                                             AS `Avg Score`,
        ROUND(y.avg_rating - LAG(y.avg_rating) OVER (ORDER BY y.year), 3)      AS `YoY Rating Δ`,
        ROUND(y.avg_score  - LAG(y.avg_score)  OVER (ORDER BY y.year), 2)      AS `YoY Score Δ`
    FROM yearly y
    ORDER BY y.year
"""


def get_yoy_trend() -> pd.DataFrame:
    """Return year-over-year performance trend from the OLAP fact table.

    Columns: Year, Reviews, Avg Rating, Avg Score, YoY Rating Δ, YoY Score Δ
    Falls back to a static mock DataFrame on error.
    """
    try:
        rows = _db().fetch_all(_SQL_YOY_TREND)
        if not rows:
            return pd.DataFrame(columns=["Year", "Avg Rating"])
        df = pd.DataFrame(rows)
        df["Year"] = df["Year"].astype(str)
        return df
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return pd.DataFrame({
            "Year":       ["2020", "2021", "2022", "2023", "2024", "2025"],
            "Avg Rating": [3.8,    4.0,    3.9,    4.2,    4.1,    4.3],
        })


# 6b. Top performers per department (Query 2 from 08_analytics_queries.sql)
_SQL_TOP_PERFORMERS = """
    WITH emp_scores AS (
        SELECT
            dd.department_name                          AS `Department`,
            de.employee_id,
            de.full_name                                AS `Name`,
            COUNT(*)                                    AS `Reviews`,
            ROUND(AVG(f.review_score), 2)               AS `Avg Score`,
            ROUND(AVG(f.performance_rating), 2)         AS `Rating`
        FROM fact_performance_reviews f
        JOIN dim_employee   de ON de.employee_key   = f.employee_key
        JOIN dim_department dd ON dd.department_key = f.department_key
        {dept_filter}
        GROUP BY dd.department_name, de.employee_id, de.full_name
        HAVING COUNT(*) >= 3
    ),
    ranked AS (
        SELECT es.*,
               DENSE_RANK() OVER (
                   PARTITION BY es.`Department`
                   ORDER BY es.`Avg Score` DESC, es.`Rating` DESC
               ) AS `Rank`
        FROM emp_scores es
    )
    SELECT * FROM ranked WHERE `Rank` <= 5
    ORDER BY `Department`, `Rank`, employee_id
"""


def get_top_performers(department: str | None = None) -> pd.DataFrame:
    """Return top-5 performers per department from the OLAP star schema.

    Parameters
    ----------
    department : str or None
        Filter to a single department name, or None for all departments.

    Returns DataFrame with columns:
        Department, Name, Reviews, Avg Score, Rating, Rank
    """
    try:
        if department and department != "All":
            sql = _SQL_TOP_PERFORMERS.format(
                dept_filter="WHERE dd.department_name = %s"
            )
            rows = _db().fetch_all(sql, (department,))
        else:
            sql = _SQL_TOP_PERFORMERS.format(dept_filter="")
            rows = _db().fetch_all(sql)
        if not rows:
            return pd.DataFrame(
                columns=["Department", "Name", "Reviews", "Avg Score", "Rating", "Rank"]
            )
        return pd.DataFrame(rows)
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return pd.DataFrame(
            columns=["Department", "Name", "Reviews", "Avg Score", "Rating", "Rank"]
        )


# 6c. Attrition risk by department (Query 3a from 08_analytics_queries.sql)
_SQL_ATTRITION_RISK = """
    SELECT
        dd.department_name                              AS `Department`,
        COUNT(DISTINCT de.employee_id)                  AS `Employees`,
        ROUND(100 * AVG(de.attrition), 1)               AS `Attrition %`,
        ROUND(AVG(f.job_satisfaction), 2)               AS `Avg Job Satisfaction`,
        ROUND(AVG(f.environment_satisfaction), 2)       AS `Avg Env Satisfaction`,
        ROUND(AVG(f.salary_hike_pct), 2)                AS `Avg Salary Hike %`
    FROM dim_employee de
    JOIN fact_performance_reviews f
        ON f.employee_key   = de.employee_key
    JOIN dim_department dd
        ON dd.department_name = de.department_name
    GROUP BY dd.department_name
    ORDER BY `Attrition %` DESC
"""


def get_attrition_risk() -> pd.DataFrame:
    """Return attrition risk metrics by department from the OLAP star schema.

    Columns: Department, Employees, Attrition %, Avg Job Satisfaction,
             Avg Env Satisfaction, Avg Salary Hike %
    """
    try:
        rows = _db().fetch_all(_SQL_ATTRITION_RISK)
        if not rows:
            return pd.DataFrame(
                columns=["Department", "Employees", "Attrition %",
                         "Avg Job Satisfaction", "Avg Env Satisfaction",
                         "Avg Salary Hike %"]
            )
        return pd.DataFrame(rows)
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return pd.DataFrame(
            columns=["Department", "Employees", "Attrition %",
                     "Avg Job Satisfaction", "Avg Env Satisfaction",
                     "Avg Salary Hike %"]
        )


# 6d. Avg performance by department (for Analytics filter page)
_SQL_DEPT_AVG_PERF = """
    SELECT
        dd.department_name                          AS `Department`,
        ROUND(AVG(f.performance_rating), 2)         AS `Rating`,
        YEAR(dt.full_date)                          AS `Year`
    FROM fact_performance_reviews f
    JOIN dim_department dd ON dd.department_key = f.department_key
    JOIN dim_date       dt ON dt.date_key       = f.review_date_key
    {dept_filter}
    {year_filter}
    GROUP BY dd.department_name, YEAR(dt.full_date)
    ORDER BY dd.department_name
"""


def get_dept_avg_performance(
    department: str | None = None, year: int | None = None
) -> pd.DataFrame:
    """Return average performance_rating per department (optionally filtered).

    Columns: Department, Rating, Year
    """
    try:
        params: list = []
        dept_clause = ""
        year_clause = ""
        if department and department != "All":
            dept_clause = "WHERE dd.department_name = %s"
            params.append(department)
        if year:
            year_clause = ("AND" if params else "WHERE") + " YEAR(dt.full_date) = %s"
            params.append(year)
        sql = _SQL_DEPT_AVG_PERF.format(
            dept_filter=dept_clause, year_filter=year_clause
        )
        rows = _db().fetch_all(sql, params if params else None)
        if not rows:
            return pd.DataFrame(columns=["Department", "Rating"])
        return pd.DataFrame(rows)
    except (DatabaseError, Exception) as exc:
        _set_fallback(exc)
        return pd.DataFrame(columns=["Department", "Rating"])


# ---------------------------------------------------------------------------
# 7. Write operations
# ---------------------------------------------------------------------------

def add_employee(data: dict) -> None:
    """Insert a new employee and their initial SCD2 history record into the database."""
    reset_fallback_flag()
    db = _db()

    raw_id = str(data.get("ID", ""))
    digits = re.sub(r"\D", "", raw_id)
    if not digits:
        raise ValidationError(f"Invalid Employee ID '{raw_id}': Must contain numbers.")
    emp_id = int(digits)

    parts = str(data.get("Name", "")).strip().split(maxsplit=1)
    first_name = parts[0] if parts else "Unknown"
    last_name = parts[1] if len(parts) > 1 else ""
    email = f"{first_name.lower()}.{last_name.lower()}{emp_id}@example.com".replace(" ", "")

    dept_name = str(data.get("Department", "")).strip()
    role_name = str(data.get("Job Role", "")).strip()
    
    dept_row = db.fetch_one("SELECT department_id FROM departments WHERE department_name = %s", (dept_name,))
    if not dept_row:
        raise ValidationError(f"Department '{dept_name}' does not exist.")
    dept_id = dept_row["department_id"]

    role_row = db.fetch_one("SELECT job_role_id FROM job_roles WHERE job_role_name = %s", (role_name,))
    if not role_row:
        raise ValidationError(f"Job Role '{role_name}' does not exist.")
    role_id = role_row["job_role_id"]

    try:
        with db.transaction() as cur:
            cur.execute("""
                INSERT INTO employees (
                    employee_id, first_name, last_name, email, gender, age,
                    hire_date, department_id, job_role_id, job_level,
                    monthly_income, years_at_company
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                emp_id, first_name, last_name, email, data.get("Gender"), data.get("Age"),
                data.get("Joining Date"), dept_id, role_id, 1,
                data.get("Salary"), data.get("Experience")
            ))

            cur.execute("""
                INSERT INTO employee_history (
                    employee_id, department_id, job_role_id, job_level,
                    monthly_income, effective_from, effective_to
                ) VALUES (%s, %s, %s, %s, %s, %s, NULL)
            """, (
                emp_id, dept_id, role_id, 1,
                data.get("Salary"), data.get("Joining Date")
            ))
    except DatabaseError as e:
        if "Duplicate entry" in str(e):
            raise ValidationError(f"Employee ID '{raw_id}' (parsed as {emp_id}) is already in use.")
        raise

    try:
        db.call_procedure("sp_load_dim_employee", [emp_id])
    except Exception as e:
        logger.error("Failed to sync employee %s to OLAP: %s", emp_id, e)
        raise ValidationError(f"Employee created in OLTP, but OLAP sync failed: {e}")


def add_project(data: dict) -> None:
    """Insert a new project and assignments into the database."""
    reset_fallback_flag()
    db = _db()

    p_name = str(data.get("Project Name", "")).strip()
    if not p_name:
        raise ValidationError("Project Name is required.")
        
    dept_name = str(data.get("Department", "")).strip()
    dept_row = db.fetch_one("SELECT department_id FROM departments WHERE department_name = %s", (dept_name,))
    if not dept_row:
        raise ValidationError(f"Department '{dept_name}' does not exist.")
    dept_id = dept_row["department_id"]

    start_date = data.get("Start Date")
    end_date = data.get("End Date")
    if start_date and end_date and end_date < start_date:
        raise ValidationError("End Date cannot be before Start Date.")

    # Parse Manager ID
    manager_id = None
    manager_str = str(data.get("Project Manager", "")).strip()
    if manager_str:
        digits = re.sub(r"\D", "", manager_str.split("—")[0])
        if digits:
            manager_id = int(digits)

    # Parse Assigned Employees IDs
    assigned_ids = set()
    for emp_str in data.get("Assigned Employees", []):
        digits = re.sub(r"\D", "", str(emp_str).split("—")[0])
        if digits:
            assigned_ids.add(int(digits))

    try:
        with db.transaction() as cur:
            # 1. Insert Project
            cur.execute("""
                INSERT INTO projects (project_name, department_id, status, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (p_name, dept_id, "Active", start_date, end_date))
            
            project_id = cur.lastrowid

            # 2. Insert Assignments
            # First insert the manager
            if manager_id:
                cur.execute("""
                    INSERT INTO assignments (employee_id, project_id, role_on_project, allocation_pct, start_date, end_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (manager_id, project_id, "Manager", 100, start_date, end_date))
                # Remove manager from assigned_ids so we don't insert them twice
                assigned_ids.discard(manager_id)
            
            # Insert team members
            for emp_id in assigned_ids:
                cur.execute("""
                    INSERT INTO assignments (employee_id, project_id, role_on_project, allocation_pct, start_date, end_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (emp_id, project_id, "Team Member", 100, start_date, end_date))
    except DatabaseError as e:
        if "foreign key constraint fails" in str(e).lower() and "fk_asg_emp" in str(e).lower():
            raise ValidationError("One or more assigned employees do not exist in the database.")
        raise

    # 3. Sync to OLAP
    try:
        db.call_procedure("sp_load_dim_project", [])
    except Exception as e:
        logger.error("OLAP sync failed for project %s: %s", project_id, e)
        raise ValidationError(f"Project created in OLTP, but OLAP sync failed: {e}")


def add_review(data: dict) -> None:
    """Insert a new performance review into the database and sync to OLAP."""
    reset_fallback_flag()
    db = _db()

    emp_str = str(data.get("Employee", ""))
    digits = re.sub(r"\D", "", emp_str.split("—")[0])
    if not digits:
        raise ValidationError("Invalid Employee selection.")
    emp_id = int(digits)

    rev_date = data.get("Review Date")
    rating = data.get("Performance Rating")

    if not rev_date:
        raise ValidationError("Review Date is required.")
    
    try:
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            raise ValueError
    except (ValueError, TypeError):
        raise ValidationError("Performance Rating must be an integer between 1 and 5.")

    manager_comments = data.get("Manager Comments")
    goals = data.get("Goals")

    try:
        with db.transaction() as cur:
            cur.execute("""
                INSERT INTO reviews (employee_id, review_date, performance_rating, manager_comments, goals)
                VALUES (%s, %s, %s, %s, %s)
            """, (emp_id, rev_date, rating_int, manager_comments, goals))
    except DatabaseError as e:
        if "foreign key constraint fails" in str(e).lower() and "fk_rev_emp" in str(e).lower():
            raise ValidationError("The selected employee does not exist in the database.")
        raise

    try:
        db.call_procedure("sp_load_fact_performance_reviews", [10000])
    except Exception as e:
        logger.error("OLAP sync failed for review insertion: %s", e)
        raise ValidationError(f"Review created in OLTP, but OLAP sync failed: {e}")


def update_employee_department(emp_id: str, new_department: str) -> bool:
    """Change employee's department and manage SCD2 history."""
    reset_fallback_flag()
    db = _db()

    raw_id = str(emp_id)
    digits = re.sub(r"\D", "", raw_id)
    if not digits:
        raise ValidationError(f"Invalid Employee ID '{raw_id}': Must contain numbers.")
    e_id = int(digits)

    new_dept_name = str(new_department).strip()
    
    dept_row = db.fetch_one("SELECT department_id FROM departments WHERE department_name = %s", (new_dept_name,))
    if not dept_row:
        raise ValidationError(f"Department '{new_dept_name}' does not exist.")
    new_dept_id = dept_row["department_id"]

    try:
        with db.transaction() as cur:
            # 1. Lock and fetch current history record
            cur.execute(
                "SELECT * FROM employee_history WHERE employee_id = %s AND effective_to IS NULL FOR UPDATE",
                (e_id,)
            )
            current_hist = cur.fetchone()
            if not current_hist:
                raise ValidationError(f"Employee {e_id} has no current history record (or does not exist).")
            
            if current_hist["department_id"] == new_dept_id:
                raise ValidationError(f"Employee {e_id} is already in the '{new_dept_name}' department.")

            # 2. Update employee_history
            hist_id = current_hist["history_id"]
            
            # Check if there's a same-day update
            cur.execute("SELECT CURDATE() as today")
            today = cur.fetchone()["today"]

            if current_hist["effective_from"] == today:
                # Same-day update: replace in place to prevent 0-day duration overlaps
                cur.execute(
                    "UPDATE employee_history SET department_id = %s WHERE history_id = %s",
                    (new_dept_id, hist_id)
                )
            else:
                # Normal update: Close old record and insert new one
                cur.execute(
                    "UPDATE employee_history SET effective_to = DATE_SUB(CURDATE(), INTERVAL 1 DAY) WHERE history_id = %s",
                    (hist_id,)
                )
                cur.execute("""
                    INSERT INTO employee_history (
                        employee_id, department_id, job_role_id, job_level,
                        monthly_income, effective_from, effective_to
                    ) VALUES (%s, %s, %s, %s, %s, CURDATE(), NULL)
                """, (
                    e_id, new_dept_id, current_hist["job_role_id"],
                    current_hist["job_level"], current_hist["monthly_income"]
                ))

            # 3. Update the master employees table
            cur.execute(
                "UPDATE employees SET department_id = %s WHERE employee_id = %s",
                (new_dept_id, e_id)
            )
    except DatabaseError as e:
        raise e

    try:
        db.call_procedure("sp_load_dim_employee", [e_id])
    except Exception as e:
        logger.error("OLAP sync failed for employee %s: %s", e_id, e)
        # We raise a warning or error to UI about sync failure
        raise ValidationError(f"Department updated in OLTP, but OLAP sync failed: {e}")

    return True


# ---------------------------------------------------------------------------
# 8. init_mock_data compatibility shim
#    app.py calls this on startup; it is a no-op here since we don't use
#    session_state DataFrames.  Kept so app.py doesn't need to be changed
#    beyond swapping the import.
# ---------------------------------------------------------------------------

def init_mock_data() -> None:
    """No-op compatibility shim — real data is fetched on demand from MySQL."""
    pass
