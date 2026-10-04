"""Review entity: attributes, validation and behaviour for one performance review."""

from datetime import date
from typing import Any, Optional

from src.db_manager import ValidationError
from src.entities.validators import require_int_range, to_date


class Review:
    """A row from the OLTP ``reviews`` table."""

    FIELDS = (
        "review_id", "employee_id", "project_id", "review_date",
        "performance_rating", "review_score", "job_satisfaction",
        "environment_satisfaction", "salary_hike_pct",
    )
    HIGH_PERFORMER_RATING = 4

    def __init__(
        self,
        employee_id: int,
        review_date: Any,
        performance_rating: int,
        project_id: Optional[int] = None,
        review_score: Optional[float] = None,
        job_satisfaction: Optional[int] = None,
        environment_satisfaction: Optional[int] = None,
        salary_hike_pct: Optional[float] = None,
        review_id: Optional[int] = None,
    ) -> None:
        self.review_id = review_id
        self.employee_id = employee_id
        self.project_id = project_id
        self.review_date = review_date
        self.performance_rating = performance_rating
        self.review_score = review_score
        self.job_satisfaction = job_satisfaction
        self.environment_satisfaction = environment_satisfaction
        self.salary_hike_pct = salary_hike_pct

    @property
    def review_date(self) -> date:
        return self._review_date

    @review_date.setter
    def review_date(self, value: Any) -> None:
        self._review_date = to_date(value, "review_date")

    @property
    def performance_rating(self) -> int:
        return self._performance_rating

    @performance_rating.setter
    def performance_rating(self, value: int) -> None:
        self._performance_rating = require_int_range(value, "performance_rating", 1, 5)

    @property
    def is_high_performer(self) -> bool:
        """True when the rating is 4 or 5."""
        return self.performance_rating >= self.HIGH_PERFORMER_RATING

    @classmethod
    def from_row(cls, row: dict) -> "Review":
        """Build a Review from a database row (extra keys are ignored)."""
        data = {f: row[f] for f in cls.FIELDS if f in row}
        try:
            return cls(**data)
        except TypeError as exc:
            raise ValidationError(f"Row is missing required review fields: {exc}") from exc

    def to_dict(self) -> dict:
        """Return all table columns as a dict."""
        return {f: getattr(self, f) for f in self.FIELDS}

    def __repr__(self) -> str:
        return (
            f"Review(id={self.review_id}, employee={self.employee_id}, "
            f"rating={self.performance_rating})"
        )