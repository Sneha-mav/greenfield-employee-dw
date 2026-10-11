"""Project entity: attributes, validation and behaviour for one project."""

from datetime import date
from typing import Any, Optional

from src.db_manager import ValidationError
from src.entities.validators import require_text, to_date


class Project:
    """A row from the OLTP ``projects`` table."""

    FIELDS = ("project_id", "project_name", "department_id", "status", "start_date", "end_date")
    VALID_STATUSES = ("Active", "Completed", "On Hold", "Unknown")

    def __init__(
        self,
        project_name: str,
        department_id: int,
        status: str = "Active",
        start_date: Any = None,
        end_date: Any = None,
        project_id: Optional[int] = None,
    ) -> None:
        self._start_date: Optional[date] = None
        self._end_date: Optional[date] = None
        self.project_id = project_id
        self.project_name = project_name
        self.department_id = department_id
        self.status = status
        self.start_date = start_date
        self.end_date = end_date

    @property
    def project_name(self) -> str:
        return self._project_name

    @project_name.setter
    def project_name(self, value: str) -> None:
        self._project_name = require_text(value, "project_name")

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        if value not in self.VALID_STATUSES:
            raise ValidationError(f"status must be one of {', '.join(self.VALID_STATUSES)}")
        self._status = value

    @property
    def start_date(self) -> Optional[date]:
        return self._start_date

    @start_date.setter
    def start_date(self, value: Any) -> None:
        self._start_date = to_date(value, "start_date", required=False)
        self._check_dates()

    @property
    def end_date(self) -> Optional[date]:
        return self._end_date

    @end_date.setter
    def end_date(self, value: Any) -> None:
        self._end_date = to_date(value, "end_date", required=False)
        self._check_dates()

    def _check_dates(self) -> None:
        if self._start_date and self._end_date and self._end_date < self._start_date:
            raise ValidationError("end_date cannot be before start_date")

    @property
    def is_open(self) -> bool:
        """True while the project is not Completed (Active or On Hold)."""
        return self.status != "Completed"

    @classmethod
    def from_row(cls, row: dict) -> "Project":
        """Build a Project from a database row (extra keys are ignored)."""
        data = {f: row[f] for f in cls.FIELDS if f in row}
        try:
            return cls(**data)
        except TypeError as exc:
            raise ValidationError(f"Row is missing required project fields: {exc}") from exc

    def to_dict(self) -> dict:
        """Return all table columns as a dict."""
        return {f: getattr(self, f) for f in self.FIELDS}

    def __repr__(self) -> str:
        return f"Project(id={self.project_id}, name={self.project_name!r}, status={self.status!r})"