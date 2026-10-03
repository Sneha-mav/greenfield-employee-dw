"""EmployeeManager: CRUD for employees plus the SCD Type 2 change flow."""

from datetime import timedelta
from typing import Any, Optional

from src.db_manager import RecordNotFoundError, ValidationError
from src.entities.employee import Employee
from src.entities.validators import require_int_range, require_positive, to_date
from src.managers.base_manager import BaseManager, handle_errors


class EmployeeManager(BaseManager):
    """Create, read, update, terminate and delete employees."""

    UPDATABLE = (
        "first_name", "last_name", "email", "gender", "age", "marital_status",
        "city", "education_field", "over_time", "years_at_company",
    )

    
    @handle_errors("create employee")
    def create(self, employee: Employee, refresh_warehouse: bool = False) -> Employee:
        """Insert the employee and its first history row; assign the next id if needed."""
        with self.db.transaction() as cur:
            self._require(cur, "departments", "department_id", employee.department_id, "Department")
            self._require(cur, "job_roles", "job_role_id", employee.job_role_id, "Job role")
            if employee.employee_id is None:
                employee.employee_id = self._next_id(cur, "employees", "employee_id")
            self._insert(cur, "employees", employee.to_dict())
            self._insert(cur, "employee_history", {
                "employee_id": employee.employee_id,
                "department_id": employee.department_id,
                "job_role_id": employee.job_role_id,
                "job_level": employee.job_level,
                "monthly_income": employee.monthly_income,
                "effective_from": employee.hire_date,
                "effective_to": None,
            })
        self.log.info("Created employee %s", employee.employee_id)
        if refresh_warehouse:
            self.refresh_dimension(employee.employee_id)
        return employee

    @handle_errors("get employee")
    def get_by_id(self, employee_id: int) -> Employee:
        """Return one employee or raise RecordNotFoundError."""
        row = self.db.fetch_one("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
        if row is None:
            raise RecordNotFoundError(f"Employee {employee_id} does not exist")
        return Employee.from_row(row)

    @handle_errors("list employees")
    def list_employees(
        self,
        department_id: Optional[int] = None,
        job_role_id: Optional[int] = None,
        attrition: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
       
        conditions, params = [], []
        if department_id is not None:
            conditions.append("department_id = %s")
            params.append(department_id)
        if job_role_id is not None:
            conditions.append("job_role_id = %s")
            params.append(job_role_id)
        if attrition is not None:
            conditions.append("attrition = %s")
            params.append(int(attrition))
        if search:
            conditions.append("(first_name LIKE %s OR last_name LIKE %s OR email LIKE %s)")
            params.extend([f"%{search}%"] * 3)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        rows = self.db.fetch_all(
            f"SELECT * FROM employees {where} ORDER BY employee_id LIMIT %s OFFSET %s",
            (*params, limit, offset),
        )
        return [Employee.from_row(row) for row in rows]

   
    @handle_errors("update employee")
    def update(self, employee_id: int, **fields: Any) -> Employee:
        """Update non-SCD fields (see UPDATABLE). Department, role, level and
        salary changes must go through update_department / change_role_or_salary."""
        employee = self.get_by_id(employee_id)
        values = self._validated_values(employee, fields, self.UPDATABLE)
        with self.db.transaction() as cur:
            self._update_fields(cur, "employees", "employee_id", employee_id, values)
        return employee

    @handle_errors("terminate employee")
    def terminate(self, employee_id: int, refresh_warehouse: bool = False) -> None:
        """Mark the employee as left (attrition = 1)."""
        with self.db.transaction() as cur:
            self._require(cur, "employees", "employee_id", employee_id, "Employee")
            cur.execute("UPDATE employees SET attrition = 1 WHERE employee_id = %s", (employee_id,))
        if refresh_warehouse:
            self.refresh_dimension(employee_id)

    @handle_errors("delete employee")
    def delete(self, employee_id: int) -> None:
        """Delete only an employee with no assignments, no reviews and no history
        beyond the initial row. Otherwise refuse; use terminate() instead."""
        with self.db.transaction() as cur:
            self._require(cur, "employees", "employee_id", employee_id, "Employee")
            history = self._count(cur, "employee_history", "employee_id", employee_id)
            assignments = self._count(cur, "assignments", "employee_id", employee_id)
            reviews = self._count(cur, "reviews", "employee_id", employee_id)
            if assignments or reviews or history > 1:
                raise ValidationError(
                    f"Employee {employee_id} has {history} history row(s), {assignments} "
                    f"assignment(s) and {reviews} review(s) and cannot be deleted. "
                    "Use terminate() instead."
                )
            cur.execute("DELETE FROM employee_history WHERE employee_id = %s", (employee_id,))
            cur.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))

   
    @handle_errors("update department")
    def update_department(
        self, employee_id: int, new_department_name: str, effective_date: Any,
        refresh_warehouse: bool = True,
    ) -> None:
        """Move an employee to another department as of ``effective_date``."""
        self._new_version(
            employee_id, effective_date, refresh_warehouse,
            department_name=new_department_name,
        )

    @handle_errors("change role or salary")
    def change_role_or_salary(
        self, employee_id: int, effective_date: Any,
        job_role_name: Optional[str] = None,
        job_level: Optional[int] = None,
        monthly_income: Optional[float] = None,
        refresh_warehouse: bool = True,
    ) -> None:
        """Change role, level and/or salary as of ``effective_date``."""
        if job_role_name is None and job_level is None and monthly_income is None:
            raise ValidationError("Provide at least one of job_role_name, job_level, monthly_income")
        self._new_version(
            employee_id, effective_date, refresh_warehouse,
            job_role_name=job_role_name, job_level=job_level, monthly_income=monthly_income,
        )

    def _new_version(
        self, employee_id: int, effective_date: Any, refresh_warehouse: bool,
        department_name: Optional[str] = None, job_role_name: Optional[str] = None,
        job_level: Optional[int] = None, monthly_income: Optional[float] = None,
    ) -> None:
        """One transaction: close the old history row, add the new one, update
        employees. Then (optionally) CALL sp_load_dim_employee."""
        effective = to_date(effective_date, "effective_date")
        if job_level is not None:
            job_level = require_int_range(job_level, "job_level", 1, 5)
        if monthly_income is not None:
            monthly_income = require_positive(monthly_income, "monthly_income")

        with self.db.transaction() as cur:
            cur.execute(
                "SELECT history_id, department_id, job_role_id, job_level, monthly_income, "
                "effective_from FROM employee_history WHERE employee_id = %s "
                "ORDER BY effective_from DESC LIMIT 1 FOR UPDATE",
                (employee_id,),
            )
            last = cur.fetchone()
            if last is None:
                raise RecordNotFoundError(f"Employee {employee_id} has no history rows or does not exist")
            latest_start = to_date(last["effective_from"], "effective_from")
            if effective <= latest_start:
                raise ValidationError(
                    f"effective_date must be after the latest effective_from ({latest_start})"
                )

            current = {k: last[k] for k in ("department_id", "job_role_id", "job_level", "monthly_income")}
            new = dict(current)
            if department_name is not None:
                new["department_id"] = self._lookup_id(
                    cur, "departments", "department_id", "department_name", department_name, "Department")
            if job_role_name is not None:
                new["job_role_id"] = self._lookup_id(
                    cur, "job_roles", "job_role_id", "job_role_name", job_role_name, "Job role")
            if job_level is not None:
                new["job_level"] = job_level
            if monthly_income is not None:
                new["monthly_income"] = monthly_income
            if new == current:
                raise ValidationError("The new values are the same as the current ones; nothing to change")

            cur.execute(
                "UPDATE employee_history SET effective_to = %s WHERE history_id = %s",
                (effective - timedelta(days=1), last["history_id"]),
            )
            self._insert(cur, "employee_history", {
                "employee_id": employee_id, **new,
                "effective_from": effective, "effective_to": None,
            })
            self._update_fields(cur, "employees", "employee_id", employee_id, new)

        self.log.info("Employee %s: new history version effective %s", employee_id, effective)
        if refresh_warehouse:
            self.refresh_dimension(employee_id)

    def _lookup_id(self, cur: Any, table: str, id_col: str, name_col: str, name: str, label: str) -> int:
        cur.execute(f"SELECT {id_col} FROM {table} WHERE {name_col} = %s", (name,))
        row = cur.fetchone()
        if row is None:
            raise RecordNotFoundError(f"{label} '{name}' does not exist")
        return row[id_col]

    
    @handle_errors("refresh employee dimension")
    def refresh_dimension(self, employee_id: Optional[int] = None) -> None:
        """CALL sp_load_dim_employee for one employee (or all when None)."""
        self.db.call_procedure("sp_load_dim_employee", (employee_id,))