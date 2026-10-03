"""ReviewManager: CRUD for performance reviews."""

from typing import Any

from src.db_manager import RecordNotFoundError
from src.entities.review import Review
from src.managers.base_manager import BaseManager, handle_errors


class ReviewManager(BaseManager):
    """Create, read, update and delete reviews."""

    UPDATABLE = (
        "project_id", "review_date", "performance_rating", "review_score",
        "job_satisfaction", "environment_satisfaction", "salary_hike_pct",
    )

    @handle_errors("create review")
    def create(self, review: Review, refresh_warehouse: bool = False) -> Review:
        """Insert a review (next review_id if needed). The warehouse is only
        refreshed when ``refresh_warehouse`` is True; otherwise call
        ``refresh_warehouse()`` later, e.g. from the UI."""
        with self.db.transaction() as cur:
            self._require(cur, "employees", "employee_id", review.employee_id, "Employee")
            if review.project_id is not None:
                self._require(cur, "projects", "project_id", review.project_id, "Project")
            if review.review_id is None:
                review.review_id = self._next_id(cur, "reviews", "review_id")
            self._insert(cur, "reviews", review.to_dict())
        self.log.info("Created review %s", review.review_id)
        if refresh_warehouse:
            self.refresh_warehouse()
        return review

    @handle_errors("get review")
    def get(self, review_id: int) -> Review:
        """Return one review or raise RecordNotFoundError."""
        row = self.db.fetch_one("SELECT * FROM reviews WHERE review_id = %s", (review_id,))
        if row is None:
            raise RecordNotFoundError(f"Review {review_id} does not exist")
        return Review.from_row(row)

    @handle_errors("list reviews")
    def list_for_employee(self, employee_id: int) -> list:
        """Return all reviews of one employee, newest first."""
        rows = self.db.fetch_all(
            "SELECT * FROM reviews WHERE employee_id = %s ORDER BY review_date DESC, review_id DESC",
            (employee_id,),
        )
        return [Review.from_row(row) for row in rows]

    @handle_errors("update review")
    def update(self, review_id: int, **fields: Any) -> Review:
        """Update review fields"""
        review = self.get(review_id)
        values = self._validated_values(review, fields, self.UPDATABLE)
        with self.db.transaction() as cur:
            if values.get("project_id") is not None:
                self._require(cur, "projects", "project_id", values["project_id"], "Project")
            self._update_fields(cur, "reviews", "review_id", review_id, values)
        return review

    @handle_errors("delete review")
    def delete(self, review_id: int) -> None:
        """Delete a review."""
        with self.db.transaction() as cur:
            self._require(cur, "reviews", "review_id", review_id, "Review")
            cur.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))

    @handle_errors("refresh fact table")
    def refresh_warehouse(self) -> None:
        """CALL sp_load_fact_performance_reviews(0): load reviews not yet in the fact table.
        The load is incremental, so edits or deletes of old reviews are not propagated."""
        self.db.call_procedure("sp_load_fact_performance_reviews", (0,))