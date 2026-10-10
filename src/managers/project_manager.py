"""ProjectManager: CRUD for projects and employee assignments."""

from typing import Any, Optional

from src.db_manager import RecordNotFoundError, ValidationError
from src.entities.project import Project
from src.entities.validators import require_int_range, require_text, to_date
from src.managers.base_manager import BaseManager, handle_errors


class ProjectManager(BaseManager):
    """Create, read, update and delete projects; assign employees to them."""

    UPDATABLE = ("project_name", "department_id", "status", "start_date", "end_date")

    @handle_errors("create project")
    def create(self, project: Project, refresh_warehouse: bool = False) -> Project:
        """Insert a project, assigning the next project_id if needed."""
        with self.db.transaction() as cur:
            self._require(cur, "departments", "department_id", project.department_id, "Department")
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

            # Check total allocation across all active assignments for this employee
            # Active = end_date is NULL or in the future
            cur.execute(
                "SELECT COALESCE(SUM(allocation_pct), 0) AS total_alloc "
                "FROM assignments "
                "WHERE employee_id = %s "
                "AND (end_date IS NULL OR end_date >= CURDATE())",
                (employee_id,),
            )
            row = cur.fetchone()
            current_total = int(row["total_alloc"]) if row else 0

            if current_total + allocation > 100:
                remaining = 100 - current_total
                raise ValidationError(
                    f"Employee {employee_id} already has {current_total}% allocation across "
                    f"active assignments. Adding {allocation}% would exceed 100%. "
                    f"Maximum available: {remaining}%."
                )

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