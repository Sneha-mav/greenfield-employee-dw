"""AnalyticsManager: read-only warehouse queries plus the warehouse refresh."""
from src.managers.base_manager import BaseManager, handle_errors
class AnalyticsManager(BaseManager):
    """Analytics over fact_performance_reviews and the dimensions."""
    @handle_errors("get rating trend")
    def rating_trend_by_year(self) -> list:
        """Average rating and score per year with YoY change (two-level CTE)."""
        return self.db.fetch_all(
            "WITH yearly AS ("
            "  SELECT d.year AS review_year, COUNT(*) AS review_count,"
            "         ROUND(AVG(f.performance_rating), 2) AS avg_rating,"
            "         ROUND(AVG(f.review_score), 2) AS avg_score"
            "  FROM fact_performance_reviews f"
            "  JOIN dim_date d ON d.date_key = f.review_date_key"
            "  GROUP BY d.year"
            ") "
            "SELECT y.*,"
            "  ROUND(avg_rating - LAG(avg_rating) OVER (ORDER BY review_year), 2)"
            "      AS change_vs_prev_year,"
            "  ROUND(avg_score  - LAG(avg_score)  OVER (ORDER BY review_year), 2)"
            "      AS score_change_vs_prev_year "
            "FROM yearly y ORDER BY review_year"
        )
    @handle_errors("get top performers")
    def top_performers_per_department(self, top_n: int = 5, min_reviews: int = 3) -> list:
        """Top ``top_n`` employees per department by average rating (DENSE_RANK)."""
        return self.db.fetch_all(
            "SELECT * FROM ("
            " SELECT cur.department_name, cur.employee_id, cur.full_name,"
            "  ROUND(AVG(f.performance_rating), 2) AS avg_rating,"
            "  ROUND(AVG(f.review_score), 2) AS avg_score,"
            "  COUNT(*) AS review_count,"
            "  DENSE_RANK() OVER (PARTITION BY cur.department_name"
            "   ORDER BY AVG(f.performance_rating) DESC, AVG(f.review_score) DESC)"
            "   AS dept_rank"
            " FROM fact_performance_reviews f"
            " JOIN dim_employee e ON e.employee_key = f.employee_key"
            " JOIN dim_employee cur ON cur.employee_id = e.employee_id AND cur.is_current = 1"
            " GROUP BY cur.department_name, cur.employee_id, cur.full_name"
            " HAVING COUNT(*) >= %s"
            ") ranked WHERE dept_rank <= %s"
            " ORDER BY department_name, dept_rank, full_name",
            (int(min_reviews), int(top_n)),
        )
    @handle_errors("get attrition by department")
    def attrition_by_department(self) -> list:
        """Headcount, leavers, attrition rate, and avg satisfaction per department."""
        return self.db.fetch_all(
            "SELECT department_name,"
            "  COUNT(*) AS headcount,"
            "  SUM(attrition) AS leavers,"
            "  ROUND(100 * SUM(attrition) / NULLIF(COUNT(*), 0), 2) AS attrition_rate_pct,"
            "  ROUND(AVG(job_satisfaction), 2) AS avg_job_satisfaction,"
            "  ROUND(AVG(environment_satisfaction), 2) AS avg_env_satisfaction,"
            "  ROUND(AVG(salary_hike_pct), 2) AS avg_salary_hike_pct "
            "FROM dim_employee de "
            "LEFT JOIN fact_performance_reviews f ON f.employee_key = de.employee_key "
            "WHERE de.is_current = 1 "
            "  AND de.department_name IS NOT NULL "
            "  AND TRIM(de.department_name) <> '' "
            "  AND de.department_name <> '0' "
            "GROUP BY department_name ORDER BY attrition_rate_pct DESC"
        )
    @handle_errors("get at-risk watch-list")
    def at_risk_watchlist(self, max_satisfaction: float = 2.0, limit: int = 50) -> list:
        """Current employees (not yet left) with low average job satisfaction."""
        return self.db.fetch_all(
            "SELECT cur.employee_id, cur.full_name, cur.department_name, cur.job_role,"
            "  ROUND(AVG(f.job_satisfaction), 2) AS avg_job_satisfaction,"
            "  ROUND(AVG(f.environment_satisfaction), 2) AS avg_env_satisfaction,"
            "  ROUND(AVG(f.performance_rating), 2) AS avg_rating,"
            "  COUNT(*) AS review_count "
            "FROM fact_performance_reviews f"
            " JOIN dim_employee e   ON e.employee_key   = f.employee_key"
            " JOIN dim_employee cur ON cur.employee_id  = e.employee_id"
            "                      AND cur.is_current   = 1 "
            "WHERE cur.attrition = 0 "
            "GROUP BY cur.employee_id, cur.full_name, cur.department_name, cur.job_role "
            "HAVING AVG(f.job_satisfaction) <= %s "
            "ORDER BY avg_job_satisfaction, avg_rating LIMIT %s",
            (float(max_satisfaction), max(1, min(int(limit), 500))),
        )
    @handle_errors("get project bottlenecks")
    def project_bottlenecks(self, min_reviews: int = 5, limit: int = 20) -> list:
        """Projects with the lowest average rating and satisfaction (ranked)."""
        return self.db.fetch_all(
            "WITH stats AS ("
            "  SELECT p.project_id, p.project_name, p.status,"
            "    COUNT(*) AS review_count,"
            "    ROUND(AVG(f.performance_rating), 2) AS avg_rating,"
            "    ROUND(AVG(f.job_satisfaction), 2) AS avg_job_satisfaction "
            "  FROM fact_performance_reviews f"
            "  JOIN dim_project p ON p.project_key = f.project_key"
            "  WHERE p.project_key <> -1"
            "  GROUP BY p.project_id, p.project_name, p.status"
            "  HAVING COUNT(*) >= %s"
            ") "
            "SELECT s.*,"
            "  RANK() OVER (ORDER BY avg_rating, avg_job_satisfaction) AS bottleneck_rank "
            "FROM stats s "
            "ORDER BY bottleneck_rank LIMIT %s",
            (int(min_reviews), max(1, min(int(limit), 500))),
        )
    @handle_errors("get allocation-aware project health")
    def project_health(self, min_reviews: int = 3, limit: int = 50) -> list:
        """Project workload and people signals, including current assignment allocation."""
        return self.db.fetch_all(
            "WITH allocation AS ("
            "  SELECT a.project_id, COUNT(*) AS active_assignments,"
            "         ROUND(AVG(a.allocation_pct), 1) AS avg_allocation_pct "
            "  FROM assignments a "
            "  WHERE a.end_date IS NULL OR a.end_date >= CURDATE() "
            "  GROUP BY a.project_id"
            "), reviews_by_project AS ("
            "  SELECT p.project_id, p.project_name, p.status, d.department_name,"
            "         COUNT(f.review_fact_key) AS review_count,"
            "         ROUND(AVG(f.performance_rating), 2) AS avg_rating,"
            "         ROUND(AVG(f.job_satisfaction), 2) AS avg_job_satisfaction "
            "  FROM dim_project p "
            "  JOIN projects op ON op.project_id = p.project_id "
            "  JOIN departments d ON d.department_id = op.department_id "
            "  LEFT JOIN fact_performance_reviews f ON f.project_key = p.project_key "
            "  WHERE p.project_key <> -1 "
            "  GROUP BY p.project_id, p.project_name, p.status, d.department_name"
            ") "
            "SELECT r.*, COALESCE(a.active_assignments, 0) AS active_assignments,"
            "       COALESCE(a.avg_allocation_pct, 0) AS avg_allocation_pct "
            "FROM reviews_by_project r "
            "LEFT JOIN allocation a ON a.project_id = r.project_id "
            "WHERE r.review_count >= %s "
            "ORDER BY r.avg_rating, r.avg_job_satisfaction LIMIT %s",
            (max(1, int(min_reviews)), max(1, min(int(limit), 500))),
        )

    @handle_errors("get hire cohort attrition")
    def attrition_by_hire_cohort(self) -> list:
        """Attrition rate per hire-year cohort, counted at employee level (not review level)."""
        return self.db.fetch_all(
            "WITH cohort AS ("
            "  SELECT YEAR(hire_date) AS hire_year,"
            "    employee_id, attrition"
            "  FROM dim_employee WHERE is_current = 1"
            "),"
            "ratings AS ("
            "  SELECT YEAR(e.hire_date) AS hire_year,"
            "    ROUND(AVG(f.performance_rating), 2) AS avg_rating"
            "  FROM dim_employee e"
            "  JOIN fact_performance_reviews f ON f.employee_key = e.employee_key"
            "  WHERE e.is_current = 1"
            "  GROUP BY YEAR(e.hire_date)"
            ") "
            "SELECT c.hire_year,"
            "  COUNT(*) AS headcount,"
            "  SUM(c.attrition) AS leavers,"
            "  ROUND(100.0 * SUM(c.attrition) / NULLIF(COUNT(*), 0), 1) AS attrition_pct,"
            "  COALESCE(MAX(r.avg_rating), 0) AS avg_rating "
            "FROM cohort c"
            " LEFT JOIN ratings r ON r.hire_year = c.hire_year "
            "GROUP BY c.hire_year "
            "ORDER BY c.hire_year"
        )
    @handle_errors("get employee scd2 history")
    def get_employee_scd2_history(self, employee_id: int) -> list:
        """All dim_employee versions for one employee, with a version number."""
        return self.db.fetch_all(
            "SELECT employee_id, full_name, department_name, job_role,"
            "  job_level, monthly_income, start_date, end_date, is_current,"
            "  ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY start_date)"
            "      AS version_num "
            "FROM dim_employee "
            "WHERE employee_id = %s "
            "ORDER BY start_date",
            (int(employee_id),),
        )
    @handle_errors("get salary band attrition")
    def salary_band_attrition(self) -> list:
        """Attrition rate per salary quintile (NTILE 5 on monthly_income)."""
        return self.db.fetch_all(
            "WITH banded AS ("
            "  SELECT employee_id, attrition, monthly_income,"
            "    NTILE(5) OVER (ORDER BY monthly_income) AS salary_band "
            "  FROM dim_employee WHERE is_current = 1"
            "),"
            "bands AS ("
            "  SELECT salary_band,"
            "    MIN(monthly_income) AS band_min,"
            "    MAX(monthly_income) AS band_max,"
            "    COUNT(*) AS headcount,"
            "    SUM(attrition) AS leavers,"
            "    ROUND(100.0 * SUM(attrition) / NULLIF(COUNT(*), 0), 1) AS attrition_pct "
            "  FROM banded GROUP BY salary_band"
            ") "
            "SELECT salary_band,"
            "  CONCAT('$', FORMAT(band_min,0), ' - $', FORMAT(band_max,0)) AS band_label,"
            "  headcount, leavers, attrition_pct "
            "FROM bands ORDER BY salary_band"
        )
    @handle_errors("refresh warehouse")
    def refresh_warehouse(self) -> list:
        """CALL sp_run_warehouse_etl() and return its summary rows."""
        result_sets = self.db.call_procedure("sp_run_warehouse_etl")
        self.log.info("Warehouse refreshed")
        return result_sets[0] if result_sets else []
    @handle_errors("validate warehouse")
    def validate_warehouse(self) -> dict:
        """Compare OLTP and warehouse row counts."""
        def count(sql: str) -> int:
            return int(self.db.fetch_one(sql)["n"])
        oltp_reviews   = count("SELECT COUNT(*) AS n FROM reviews")
        fact_reviews   = count("SELECT COUNT(*) AS n FROM fact_performance_reviews")
        oltp_employees = count("SELECT COUNT(*) AS n FROM employees")
        current_dim    = count("SELECT COUNT(*) AS n FROM dim_employee WHERE is_current = 1")
        dup_current    = count(
            "SELECT COUNT(*) AS n FROM ("
            "  SELECT employee_id FROM dim_employee"
            "  WHERE is_current = 1 GROUP BY employee_id HAVING COUNT(*) > 1"
            ") t"
        )
        return {
            "oltp_reviews": oltp_reviews,
            "fact_reviews": fact_reviews,
            "reviews_missing_in_fact": oltp_reviews - fact_reviews,
            "oltp_employees": oltp_employees,
            "current_dim_employees": current_dim,
            "employees_match": oltp_employees == current_dim,
            "employees_with_multiple_current_rows": dup_current,
        }
    @handle_errors("get department list")
    def list_departments(self) -> list:
        """All departments ordered by name."""
        return self.db.fetch_all(
            "SELECT department_id, department_name FROM departments ORDER BY department_name"
        )
    @handle_errors("get job role list")
    def list_job_roles(self) -> list:
        """All job roles ordered by name."""
        return self.db.fetch_all(
            "SELECT job_role_id, job_role_name FROM job_roles ORDER BY job_role_name"
        )
