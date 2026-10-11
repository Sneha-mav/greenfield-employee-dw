"""ReviewManager: CRUD for performance reviews."""

from typing import Any

from src.db_manager import RecordNotFoundError, ValidationError
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
        """Insert a review. Rejects duplicate (employee_id, review_date, project_id)."""
        with self.db.transaction() as cur:
            self._require(cur, "employees", "employee_id", review.employee_id, "Employee")
            if review.project_id is not None:
                self._require(cur, "projects", "project_id", review.project_id, "Project")

            # Prevent duplicate reviews for the same employee/date/project combination
            cur.execute(
                "SELECT review_id FROM reviews "
                "WHERE employee_id = %s AND review_date = %s AND "
                "COALESCE(project_id, -1) = COALESCE(%s, -1)",
                (review.employee_id, review.review_date, review.project_id),
            )
            if cur.fetchone():
                raise ValidationError(
                    f"A review for employee {review.employee_id} on "
                    f"{review.review_date} already exists for this project."
                )

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
        """Return all reviews of one employee as dicts with employee name, newest first."""
        return self.db.fetch_all(
            "SELECT r.review_id, r.employee_id, "
            "CONCAT(e.first_name, ' ', e.last_name) AS employee_name, "
            "r.project_id, p.project_name, r.review_date, "
            "r.performance_rating, r.review_score, "
            "r.job_satisfaction, r.environment_satisfaction, r.salary_hike_pct "
            "FROM reviews r "
            "JOIN employees e ON e.employee_id = r.employee_id "
            "LEFT JOIN projects p ON p.project_id = r.project_id "
            "WHERE r.employee_id = %s "
            "ORDER BY r.review_date DESC, r.review_id DESC",
            (employee_id,),
        )

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