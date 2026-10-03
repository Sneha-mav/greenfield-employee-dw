-- ============================================================
-- 08_analytics_queries.sql
-- Dashboard queries (Phase 4) + warehouse validation checks. Star schema only.
-- ============================================================

-- ---------- 1. Year-over-year performance trend (LAG) ----------
WITH yearly AS (
    SELECT dt.year,
           COUNT(*)                          AS reviews,
           ROUND(AVG(f.performance_rating),3) AS avg_rating,
           ROUND(AVG(f.review_score),2)      AS avg_score
    FROM fact_performance_reviews f
    JOIN dim_date dt ON dt.date_key = f.review_date_key
    GROUP BY dt.year
)
SELECT y.*,
       ROUND(avg_rating - LAG(avg_rating) OVER (ORDER BY year), 3) AS yoy_rating_change,
       ROUND(avg_score  - LAG(avg_score)  OVER (ORDER BY year), 2) AS yoy_score_change
FROM yearly y
ORDER BY year;

-- ---------- 2. Top performers per department (DENSE_RANK) ----------
-- Department = department at the time of the review (from the fact), min 3 reviews to qualify.
WITH emp_scores AS (
    SELECT dd.department_name,
           de.employee_id,
           de.full_name,
           COUNT(*)                           AS reviews,
           ROUND(AVG(f.review_score), 2)      AS avg_score,
           ROUND(AVG(f.performance_rating),2) AS avg_rating
    FROM fact_performance_reviews f
    JOIN dim_employee   de ON de.employee_key   = f.employee_key
    JOIN dim_department dd ON dd.department_key = f.department_key
    GROUP BY dd.department_name, de.employee_id, de.full_name
    HAVING COUNT(*) >= 3
),
ranked AS (
    SELECT es.*,
           DENSE_RANK() OVER (PARTITION BY department_name ORDER BY avg_score DESC, avg_rating DESC) AS dept_rank
    FROM emp_scores es
)
SELECT * FROM ranked
WHERE dept_rank <= 5
ORDER BY department_name, dept_rank, employee_id;

-- ---------- 3a. Attrition risk by department ----------
SELECT dd.department_name,
       COUNT(DISTINCT de.employee_id)                         AS employees,
       ROUND(100 * AVG(de.attrition), 1)                      AS attrition_pct,
       ROUND(AVG(f.job_satisfaction), 2)                      AS avg_job_satisfaction,
       ROUND(AVG(f.environment_satisfaction), 2)              AS avg_env_satisfaction,
       ROUND(AVG(f.salary_hike_pct), 2)                       AS avg_salary_hike_pct
FROM dim_employee de
JOIN fact_performance_reviews f ON f.employee_key   = de.employee_key
JOIN dim_department dd          ON dd.department_name = de.department_name
GROUP BY dd.department_name
ORDER BY attrition_pct DESC;

-- ---------- 3b. Watch-list: current employees still here but with low satisfaction (NTILE) ----------
WITH emp_sat AS (
    SELECT de.employee_id, de.full_name, de.department_name, de.job_role,
           ROUND(AVG(f.job_satisfaction), 2) AS avg_job_sat,
           ROUND(AVG(f.salary_hike_pct), 2)  AS avg_hike
    FROM dim_employee de
    JOIN fact_performance_reviews f ON f.employee_key = de.employee_key
    WHERE de.is_current = 1 AND de.attrition = 0
    GROUP BY de.employee_id, de.full_name, de.department_name, de.job_role
),
bucketed AS (
    SELECT es.*, NTILE(10) OVER (ORDER BY avg_job_sat, avg_hike) AS risk_decile   -- 1 = highest risk
    FROM emp_sat es
)
SELECT * FROM bucketed WHERE risk_decile = 1 ORDER BY avg_job_sat, avg_hike LIMIT 50;

-- ---------- 4. Project bottlenecks ----------
WITH project_stats AS (
    SELECT dp.project_id, dp.project_name, dp.status,
           COUNT(*)                          AS reviews,
           ROUND(AVG(f.performance_rating),2) AS avg_rating,
           ROUND(AVG(f.job_satisfaction),2)   AS avg_job_sat
    FROM fact_performance_reviews f
    JOIN dim_project dp ON dp.project_key = f.project_key
    WHERE dp.project_key <> -1
    GROUP BY dp.project_id, dp.project_name, dp.status
    HAVING COUNT(*) >= 10
)
SELECT ps.*, RANK() OVER (ORDER BY avg_rating, avg_job_sat) AS bottleneck_rank
FROM project_stats ps
ORDER BY bottleneck_rank
LIMIT 20;

-- ============================================================
-- VALIDATION CHECKS (all should return 0 rows / 0)
-- ============================================================

-- V1. Exactly one current row per employee
SELECT employee_id, COUNT(*) AS current_rows
FROM dim_employee WHERE is_current = 1
GROUP BY employee_id HAVING COUNT(*) <> 1;

-- V2. No gaps or overlaps between consecutive versions of an employee
WITH v AS (
    SELECT employee_id, start_date, end_date,
           LEAD(start_date) OVER (PARTITION BY employee_id ORDER BY start_date) AS next_start
    FROM dim_employee
)
SELECT * FROM v WHERE next_start IS NOT NULL AND end_date + INTERVAL 1 DAY <> next_start;

-- V3. is_current flag agrees with the 9999-12-31 end date
SELECT employee_key FROM dim_employee
WHERE (is_current = 1 AND end_date <> '9999-12-31') OR (is_current = 0 AND end_date = '9999-12-31');

-- V4. Reviews that did not make it into the fact table (bad date range etc.)
SELECT COUNT(*) AS missing_in_fact
FROM reviews r LEFT JOIN fact_performance_reviews f ON f.review_id = r.review_id
WHERE f.review_id IS NULL;

-- V5. Fact rows whose dim_employee version does NOT cover the review date (fell back to nearest version)
SELECT COUNT(*) AS fallback_matches
FROM fact_performance_reviews f
JOIN dim_employee de ON de.employee_key = f.employee_key
JOIN dim_date dt     ON dt.date_key     = f.review_date_key
WHERE dt.full_date NOT BETWEEN de.start_date AND de.end_date;

-- Demo: an employee with several SCD2 versions
SELECT employee_id, full_name, department_name, job_role, job_level, monthly_income, start_date, end_date, is_current
FROM dim_employee
WHERE employee_id = (SELECT employee_id FROM dim_employee GROUP BY employee_id HAVING COUNT(*) > 2 LIMIT 1)
ORDER BY start_date;