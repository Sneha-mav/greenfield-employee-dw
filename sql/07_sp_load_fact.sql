-- ============================================================
-- 07_sp_load_fact.sql
-- OLTP reviews -> fact_performance_reviews (grain: one row per employee per review).
--   sp_load_fact_performance_reviews(batch_size)  incremental, loads in review_id batches (default 50,000)
--   sp_run_warehouse_etl()                        runs dimensions then fact, prints a summary
--
-- Key lookup for each review:
--   * employee_key  = the dim_employee version valid ON the review date (SCD2 point-in-time join).
--     ROW_NUMBER() ranks the employee's versions: covering version first, otherwise the nearest one
--     (e.g. a review dated before the first recorded version still maps to that first version).
--   * department_key = department of that version (department at review time, not today's).
--   * project_key    = dim_project, or -1 'Unassigned' when the review has no project.
--   * review_date_key = YYYYMMDD; reviews outside dim_date (2015-2030) are skipped and reported.
-- ============================================================
DELIMITER //

DROP PROCEDURE IF EXISTS sp_load_fact_performance_reviews//
CREATE PROCEDURE sp_load_fact_performance_reviews(IN p_batch_size INT)
BEGIN
    DECLARE v_min   INT;
    DECLARE v_max   INT;
    DECLARE v_lo    INT;
    DECLARE v_batch INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    SET v_batch = COALESCE(NULLIF(p_batch_size, 0), 50000);

    SELECT MIN(review_id), MAX(review_id) INTO v_min, v_max FROM reviews;
    SET v_lo = v_min;

    WHILE v_lo IS NOT NULL AND v_lo <= v_max DO
        START TRANSACTION;

        INSERT INTO fact_performance_reviews
            (review_id, employee_key, department_key, project_key, review_date_key,
             performance_rating, review_score, job_satisfaction, environment_satisfaction,
             salary_hike_pct, monthly_income_at_review)
        WITH batch AS (
            SELECT r.*
            FROM reviews r
            WHERE r.review_id BETWEEN v_lo AND v_lo + v_batch - 1
              AND NOT EXISTS (SELECT 1 FROM fact_performance_reviews f WHERE f.review_id = r.review_id)
        ),
        ranked AS (
            SELECT b.review_id, b.project_id, b.review_date, b.performance_rating, b.review_score,
                   b.job_satisfaction, b.environment_satisfaction, b.salary_hike_pct,
                   e.employee_key, e.department_name, e.monthly_income,
                   ROW_NUMBER() OVER (
                       PARTITION BY b.review_id
                       ORDER BY CASE WHEN b.review_date BETWEEN e.start_date AND e.end_date THEN 0 ELSE 1 END,
                                ABS(DATEDIFF(b.review_date, e.start_date))
                   ) AS rn
            FROM batch b
            JOIN dim_employee e ON e.employee_id = b.employee_id
        )
        SELECT x.review_id,
               x.employee_key,
               dd.department_key,
               COALESCE(dp.project_key, -1),
               dt.date_key,
               x.performance_rating,
               x.review_score,
               x.job_satisfaction,
               x.environment_satisfaction,
               x.salary_hike_pct,
               x.monthly_income
        FROM ranked x
        JOIN dim_department dd      ON dd.department_name = x.department_name
        LEFT JOIN dim_project dp    ON dp.project_id      = x.project_id
        JOIN dim_date dt            ON dt.full_date       = x.review_date
        WHERE x.rn = 1;

        COMMIT;
        SET v_lo = v_lo + v_batch;
    END WHILE;
END//

-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_run_warehouse_etl//
CREATE PROCEDURE sp_run_warehouse_etl()
BEGIN
    CALL sp_load_dim_department();
    CALL sp_load_dim_project();
    CALL sp_load_dim_employee(NULL);
    CALL sp_load_fact_performance_reviews(50000);

    SELECT 'dim_department' AS tbl, COUNT(*) AS row_count FROM dim_department
    UNION ALL SELECT 'dim_project',  COUNT(*) FROM dim_project
    UNION ALL SELECT 'dim_employee', COUNT(*) FROM dim_employee
    UNION ALL SELECT 'dim_employee (current)', COUNT(*) FROM dim_employee WHERE is_current = 1
    UNION ALL SELECT 'oltp reviews', COUNT(*) FROM reviews
    UNION ALL SELECT 'fact_performance_reviews', COUNT(*) FROM fact_performance_reviews
    UNION ALL SELECT 'reviews NOT in fact (check)', COUNT(*)
        FROM reviews r LEFT JOIN fact_performance_reviews f ON f.review_id = r.review_id
        WHERE f.review_id IS NULL;
END//

DELIMITER ;

-- Usage:
--   CALL sp_run_warehouse_etl();                -- full / incremental run
--   CALL sp_load_dim_employee(1234);            -- after changing one employee's department in OLTP
--   CALL sp_load_fact_performance_reviews(0);   -- fact only (0 = default batch size)