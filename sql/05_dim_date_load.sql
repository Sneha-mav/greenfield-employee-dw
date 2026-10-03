-- ============================================================
-- 05_dim_date_load.sql
-- Fills dim_date for 2015-01-01 .. 2030-12-31 with a recursive CTE.
-- Columns follow the data dictionary: date_key, full_date, year, quarter, month, month_name.
-- Re-runnable: INSERT IGNORE skips dates that already exist.
-- Run it against the database that holds your tables (no USE statement on purpose).
-- ============================================================
SET SESSION cte_max_recursion_depth = 10000;   

INSERT IGNORE INTO dim_date (date_key, full_date, year, quarter, month, month_name)
WITH RECURSIVE calendar AS (
    SELECT DATE('2015-01-01') AS d
    UNION ALL
    SELECT d + INTERVAL 1 DAY FROM calendar WHERE d < '2030-12-31'
)
SELECT
    YEAR(d) * 10000 + MONTH(d) * 100 + DAY(d) AS date_key,
    d                                          AS full_date,
    YEAR(d),
    QUARTER(d),
    MONTH(d),
    MONTHNAME(d)
FROM calendar;
