-- 05_dim_date_load.sql
-- Fills hr_dw.dim_date for 2015-01-01 .. 2030-12-31 using a recursive CTE.
-- Safe to re-run (INSERT IGNORE on the unique date).

USE hr_dw;
SET SESSION cte_max_recursion_depth = 10000;   -- MySQL 8: default is 1000, we need ~5,900 days

INSERT IGNORE INTO dim_date
    (date_key, full_date, year, quarter, month, month_name, week_of_year, day_of_month, day_name, is_weekend)
WITH RECURSIVE calendar AS (
    SELECT DATE('2015-01-01') AS d
    UNION ALL
    SELECT d + INTERVAL 1 DAY FROM calendar WHERE d < '2030-12-31'
)
SELECT
    YEAR(d) * 10000 + MONTH(d) * 100 + DAY(d),
    d,
    YEAR(d),
    QUARTER(d),
    MONTH(d),
    MONTHNAME(d),
    WEEK(d, 3),
    DAY(d),
    DAYNAME(d),
    CASE WHEN DAYOFWEEK(d) IN (1, 7) THEN 1 ELSE 0 END
FROM calendar;