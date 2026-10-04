"""Phase 3 check against the dev database.

Run from the repo root:  python -m tests.demorun_phase3

It creates one demo employee, changes their department (SCD Type 2), adds a
review, terminates them, runs the analytics, then removes every demo row.
"""

import logging
from datetime import date, datetime

from src.db_manager import DatabaseConnection, ValidationError
from src.entities.employee import Employee
from src.entities.review import Review
from src.managers.analytics_manager import AnalyticsManager
from src.managers.employee_manager import EmployeeManager
from src.managers.review_manager import ReviewManager


def cleanup(db: DatabaseConnection, emp_id: int) -> None:
    """Remove the demo employee from OLTP and the warehouse."""
    with db.transaction() as cur:
        cur.execute(
            "DELETE FROM fact_performance_reviews WHERE employee_key IN "
            "(SELECT employee_key FROM dim_employee WHERE employee_id = %s)", (emp_id,))
        cur.execute("DELETE FROM dim_employee WHERE employee_id = %s", (emp_id,))
        cur.execute("DELETE FROM reviews WHERE employee_id = %s", (emp_id,))
        cur.execute("DELETE FROM assignments WHERE employee_id = %s", (emp_id,))
        cur.execute("DELETE FROM employee_history WHERE employee_id = %s", (emp_id,))
        cur.execute("DELETE FROM employees WHERE employee_id = %s", (emp_id,))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    db = DatabaseConnection()
    employees, reviews, analytics = EmployeeManager(), ReviewManager(), AnalyticsManager()

    depts = db.fetch_all("SELECT department_id, department_name FROM departments ORDER BY department_id")
    role = db.fetch_one("SELECT job_role_id FROM job_roles ORDER BY job_role_id LIMIT 1")
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")

    emp = employees.create(
        Employee(
            first_name="Demo", last_name="Tester", email=f"demo.{stamp}@example.com",
            hire_date=date(2020, 1, 1), department_id=depts[0]["department_id"],
            job_role_id=role["job_role_id"], job_level=2, monthly_income=5000,
            gender="Female", age=30, marital_status="Single", city="Mumbai",
        ),
        refresh_warehouse=True,
    )
    try:
        print(f"1. Created {emp} in {depts[0]['department_name']}")

        employees.update(emp.employee_id, city="Pune")
        print("2. Updated city ->", employees.get_by_id(emp.employee_id).city)

        employees.update_department(emp.employee_id, depts[1]["department_name"], date(2024, 1, 1))
        print("3. SCD check: dim_employee rows (expect old closed + one current):")
        for row in db.fetch_all(
            "SELECT employee_key, department_name, start_date, end_date, is_current "
            "FROM dim_employee WHERE employee_id = %s ORDER BY start_date", (emp.employee_id,)):
            print("  ", row)

        try:
            employees.update_department(emp.employee_id, depts[0]["department_name"], date(2023, 1, 1))
        except ValidationError as exc:
            print("4. Back-dated change refused as expected:", exc)

        review = reviews.create(
            Review(employee_id=emp.employee_id, review_date=date(2024, 6, 1),
                   performance_rating=5, job_satisfaction=3),
            refresh_warehouse=True,
        )
        print(f"5. Created {review}, high performer: {review.is_high_performer}")

        employees.terminate(emp.employee_id, refresh_warehouse=True)
        print("6. Terminated, is_active:", employees.get_by_id(emp.employee_id).is_active)

        try:
            employees.delete(emp.employee_id)
        except ValidationError as exc:
            print("7. Delete refused as expected:", exc)

        print("8. Attrition by department:", analytics.attrition_by_department())
        print("9. Rating trend:", analytics.rating_trend_by_year())
        print("10. Top performers (sample):", analytics.top_performers_per_department(top_n=2)[:3])
        print("11. Watch-list (sample):", analytics.at_risk_watchlist(limit=3))
        print("12. Project bottlenecks (sample):", analytics.project_bottlenecks(limit=3))
        print("13. Validation:", analytics.validate_warehouse())
    finally:
        cleanup(db, emp.employee_id)
        print("Demo data removed.")


if __name__ == "__main__":
    main()