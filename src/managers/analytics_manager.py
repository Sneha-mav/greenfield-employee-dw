"""AnalyticsManager: read-only warehouse queries plus the warehouse refresh.
"""

from src.managers.base_manager import BaseManager, handle_errors


class AnalyticsManager(BaseManager):
    """Analytics over fact_performance_reviews and the dimensions."""

    @handle_errors("get rating trend")
    def rating_trend_by_year(self) -> list:
        """Average rating per year with the change versus the previous year."""
        return self.db.fetch_all(
            "SELECT d.year AS review_year, COUNT(*) AS review_count, "
            "ROUND(AVG(f.performance_rating), 2) AS avg_rating, "
            "ROUND(AVG(f.performance_rating) - LAG(AVG(f.performance_rating)) "
            "OVER (ORDER BY d.year), 2) AS change_vs_prev_year "
            "FROM fact_performance_reviews f "
            "JOIN dim_date d ON d.date_key = f.review_date_key "
            "GROUP BY d.year ORDER BY d.year"
        )

    @handle_errors("get top performers")
    def top_performers_per_department(self, top_n: int = 5, min_reviews: int = 3) -> list:
        """Top ``top_n`` employees per department by average rating (DENSE_RANK)."""
        return self.db.fetch_all(
            "SELECT * FROM ("
            " SELECT e.department_name, e.employee_id, e.full_name, "
            "  ROUND(AVG(f.performance_rating), 2) AS avg_rating, COUNT(*) AS review_count, "
            "  DENSE_RANK() OVER (PARTITION BY e.department_name "
            "   ORDER BY AVG(f.performance_rating) DESC, COUNT(*) DESC) AS dept_rank "
            " FROM fact_performance_reviews f "
            " JOIN dim_employee e ON e.employee_key = f.employee_key "
            " GROUP BY e.department_name, e.employee_id, e.full_name "
            " HAVING COUNT(*) >= %s"
            ") ranked WHERE dept_rank <= %s "
            "ORDER BY department_name, dept_rank, full_name",
            (int(min_reviews), int(top_n)),
        )

    @handle_errors("get attrition by department")
    def attrition_by_department(self) -> list:
        """Headcount, leavers and attrition rate per department (current rows)."""
        return self.db.fetch_all(
            "SELECT department_name, COUNT(*) AS headcount, SUM(attrition) AS leavers, "
            "ROUND(100 * SUM(attrition) / COUNT(*), 2) AS attrition_rate_pct "
            "FROM dim_employee WHERE is_current = 1 "
            "GROUP BY department_name ORDER BY attrition_rate_pct DESC"
        )

    @handle_errors("get at-risk watch-list")
    def at_risk_watchlist(self, max_satisfaction: float = 2.0, limit: int = 50) -> list:
        """Current employees (not yet left) whose average job satisfaction is low."""
        return self.db.fetch_all(
            "SELECT cur.employee_id, cur.full_name, cur.department_name, cur.job_role, "
            "ROUND(AVG(f.job_satisfaction), 2) AS avg_job_satisfaction, "
            "ROUND(AVG(f.performance_rating), 2) AS avg_rating, COUNT(*) AS review_count "
            "FROM fact_performance_reviews f "
            "JOIN dim_employee e ON e.employee_key = f.employee_key "
            "JOIN dim_employee cur ON cur.employee_id = e.employee_id AND cur.is_current = 1 "
            "WHERE cur.attrition = 0 "
            "GROUP BY cur.employee_id, cur.full_name, cur.department_name, cur.job_role "
            "HAVING AVG(f.job_satisfaction) <= %s "
            "ORDER BY avg_job_satisfaction, avg_rating LIMIT %s",
            (float(max_satisfaction), max(1, min(int(limit), 500))),
        )

    @handle_errors("get project bottlenecks")
    def project_bottlenecks(self, min_reviews: int = 5, limit: int = 20) -> list:
        """Projects with the lowest average rating and satisfaction."""
        return self.db.fetch_all(
            "SELECT p.project_id, p.project_name, p.status, COUNT(*) AS review_count, "
            "ROUND(AVG(f.performance_rating), 2) AS avg_rating, "
            "ROUND(AVG(f.job_satisfaction), 2) AS avg_job_satisfaction "
            "FROM fact_performance_reviews f "
            "JOIN dim_project p ON p.project_key = f.project_key "
            "WHERE p.project_key <> -1 "
            "GROUP BY p.project_id, p.project_name, p.status "
            "HAVING COUNT(*) >= %s "
            "ORDER BY avg_rating ASC, avg_job_satisfaction ASC LIMIT %s",
            (int(min_reviews), max(1, min(int(limit), 500))),
        )

    @handle_errors("refresh warehouse")
    def refresh_warehouse(self) -> list:
        """CALL sp_run_warehouse_etl() and return its summary rows."""
        result_sets = self.db.call_procedure("sp_run_warehouse_etl")
        self.log.info("Warehouse refreshed")
        return result_sets[0] if result_sets else []

    @handle_errors("validate warehouse")
    def validate_warehouse(self) -> dict:
        """Compare OLTP and warehouse row counts. Reviews dated outside the
        dim_date range are skipped by the fact load, so a small gap can be normal."""
        def count(sql: str) -> int:
            return int(self.db.fetch_one(sql)["n"])

        oltp_reviews = count("SELECT COUNT(*) AS n FROM reviews")
        fact_reviews = count("SELECT COUNT(*) AS n FROM fact_performance_reviews")
        oltp_employees = count("SELECT COUNT(*) AS n FROM employees")
        current_dim = count("SELECT COUNT(*) AS n FROM dim_employee WHERE is_current = 1")
        duplicate_current = count(
            "SELECT COUNT(*) AS n FROM (SELECT employee_id FROM dim_employee "
            "WHERE is_current = 1 GROUP BY employee_id HAVING COUNT(*) > 1) t"
        )
        return {
            "oltp_reviews": oltp_reviews,
            "fact_reviews": fact_reviews,
            "reviews_missing_in_fact": oltp_reviews - fact_reviews,
            "oltp_employees": oltp_employees,
            "current_dim_employees": current_dim,
            "employees_match": oltp_employees == current_dim,
            "employees_with_multiple_current_rows": duplicate_current,
        }