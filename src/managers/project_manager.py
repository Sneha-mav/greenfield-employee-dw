"""ProjectManager: CRUD for projects and employee assignments."""

from typing import Any, Optional

from src.auth import requires_permission
from src.db_manager import RecordNotFoundError, ValidationError
from src.entities.project import Project
from src.entities.validators import require_int_range, require_text, to_date
from src.managers.base_manager import BaseManager, handle_errors


class ProjectManager(BaseManager):
    """Create, read, update and delete projects; assign employees to them."""

    UPDATABLE = ("project_name", "department_id", "status", "start_date", "end_date")

    @requires_permission("project.create")
    @handle_errors("create project")
    def create(self, project: Project, refresh_warehouse: bool = False) -> Project:
        """Insert a project, assigning the next project_id if needed."""
        with self.db.transaction() as cur:
            self._require(cur, "departments", "department_id", project.department_id, "Department")

            # Prevent duplicate project names (case-insensitive)
            cur.execute(
                "SELECT project_id FROM projects WHERE LOWER(project_name) = LOWER(%s)",
                (project.project_name,),
            )
            if cur.fetchone():
                raise ValidationError(
                    f"A project named '{project.project_name}' already exists. "
                    "Please use a unique project name."
                )

            if project.project_id is None:
                project.project_id = self._next_id(cur, "projects", "project_id")
            self._insert(cur, "projects", project.to_dict())
        self.log.info("Created project %s", project.project_id)
        if refresh_warehouse:
            self.db.call_procedure("sp_load_dim_project")
        return project

    @handle_errors("get project")
    def get(self, project_id: int) -> Project:
        """Return one project or raise RecordNotFoundError."""
        row = self.db.fetch_one("SELECT * FROM projects WHERE project_id = %s", (project_id,))
        if row is None:
            raise RecordNotFoundError(f"Project {project_id} does not exist")
        return Project.from_row(row)

    @handle_errors("list projects")
    def list_projects(
        self, status: Optional[str] = None, department_id: Optional[int] = None,
        limit: int = 0, offset: int = 0,
    ) -> list:
        """Return projects, optionally filtered by status/department. limit=0 means all."""
        conditions, params = [], []
        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        if department_id is not None:
            conditions.append("department_id = %s")
            params.append(department_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = max(0, int(offset))
        limit = int(limit)
        if limit > 0:
            rows = self.db.fetch_all(
                f"SELECT * FROM projects {where} ORDER BY project_id LIMIT %s OFFSET %s",
                (*params, limit, offset),
            )
        else:
            rows = self.db.fetch_all(
                f"SELECT * FROM projects {where} ORDER BY project_id",
                tuple(params),
            )
        return [Project.from_row(row) for row in rows]

    @handle_errors("update project")
    def update(self, project_id: int, **fields: Any) -> Project:
        """Update project_name, department_id, status, start_date or end_date."""
        project = self.get(project_id)
        values = self._validated_values(project, fields, self.UPDATABLE)
        with self.db.transaction() as cur:
            if "department_id" in values:
                self._require(cur, "departments", "department_id", values["department_id"], "Department")
            self._update_fields(cur, "projects", "project_id", project_id, values)
        return project

    @handle_errors("delete project")
    def delete(self, project_id: int) -> None:
        """Delete a project only if it has no assignments and no reviews."""
        with self.db.transaction() as cur:
            self._require(cur, "projects", "project_id", project_id, "Project")
            assignments = self._count(cur, "assignments", "project_id", project_id)
            reviews = self._count(cur, "reviews", "project_id", project_id)
            if assignments or reviews:
                raise ValidationError(
                    f"Project {project_id} has {assignments} assignment(s) and {reviews} "
                    "review(s) and cannot be deleted."
                )
            cur.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))

    MAX_ALLOCATION = 100
    @handle_errors("employee_capacity")
    def _check_employee_capacity(self, cur, employee_id, allocation, start, end):
        """Raise ValidationError if the new assignment pushes the employee over 100% on any day."""
        cur.execute(
            "SELECT allocation_pct, start_date, end_date FROM assignments "
            "WHERE employee_id = %s "
            "AND (end_date IS NULL OR end_date >= %s) "
            "AND (%s IS NULL OR start_date <= %s)",
            (employee_id, start, end, end),
        )
        existing = cur.fetchall()
        if not existing:
            return

        # Load only changes when an assignment starts, so checking those days is enough.
        check_days = {start} | {r["start_date"] for r in existing if r["start_date"] > start}
        worst_day, worst_total = start, 0
        for day in check_days:
            total = allocation + sum(
                (r["allocation_pct"] or 0) for r in existing
                if r["start_date"] <= day and (r["end_date"] is None or r["end_date"] >= day)
            )
            if total > worst_total:
                worst_day, worst_total = day, total

        if worst_total > self.MAX_ALLOCATION:
            raise ValidationError(
                f"Employee {employee_id} would be allocated {worst_total}% on {worst_day} "
                f"(max {self.MAX_ALLOCATION}%). Reduce the allocation or change the dates."
            )

    @requires_permission("assignment.create")
    @handle_errors("assign employee")
    def assign_employee(
        self, project_id: int, employee_id: int, role_on_project: str,
        allocation_pct: int, start_date: Any, end_date: Any = None,
    ) -> int:
        """Assign an employee to a project and return the new assignment_id."""
        role = require_text(role_on_project, "role_on_project")
        allocation = require_int_range(allocation_pct, "allocation_pct", 1, 100)
        start = to_date(start_date, "start_date")
        end = to_date(end_date, "end_date", required=False)
        if end and end < start:
            raise ValidationError("end_date cannot be before start_date")

        with self.db.transaction() as cur:
            self._require(cur, "projects", "project_id", project_id, "Project")
            self._require(cur, "employees", "employee_id", employee_id, "Employee")
            cur.execute("SELECT 1 FROM employees WHERE employee_id = %s FOR UPDATE", (employee_id,))
            cur.fetchall()
            self._check_employee_capacity(cur, employee_id, allocation, start, end)
            assignment_id = self._next_id(cur, "assignments", "assignment_id")
            self._insert(cur, "assignments", {
                "assignment_id": assignment_id, "employee_id": employee_id,
                "project_id": project_id, "role_on_project": role,
                "allocation_pct": allocation, "start_date": start, "end_date": end,
            })
        return assignment_id

    @handle_errors("list assignments")
    def list_assignments(self, project_id: int) -> list:
        """Return the project's assignments (as dicts) with employee names."""
        self.get(project_id)  # raises RecordNotFoundError if missing
        return self.db.fetch_all(
            "SELECT a.assignment_id, a.employee_id, "
            "CONCAT(e.first_name, ' ', e.last_name) AS employee_name, "
            "a.role_on_project, a.allocation_pct, a.start_date, a.end_date "
            "FROM assignments a JOIN employees e ON e.employee_id = a.employee_id "
            "WHERE a.project_id = %s ORDER BY a.assignment_id",
            (project_id,),
        )