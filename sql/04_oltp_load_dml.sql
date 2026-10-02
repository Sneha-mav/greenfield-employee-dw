-- ============================================================
-- 04_oltp_load_dml.sql
-- STAGING -> OLTP (3NF). Cleans the dirty staging data using CTEs + window functions.
--   * Text is trimmed / whitespace-collapsed; the most frequent spelling wins per name (departments, roles).
--   * Duplicates are removed with ROW_NUMBER() (latest landed row, i.e. highest stg_id, wins).
--   * Invalid rows (missing keys, out-of-range level/rating/income) are filtered out.
--   * employee_history.effective_to is REBUILT with LEAD() so versions never overlap or leave gaps.
-- Re-runnable: INSERT IGNORE + unique keys skip rows that already exist.
-- Run order: 01 -> 02 -> 03 -> 05 -> 04 (this file) -> 06 -> 07
-- ============================================================

-- ------------------------------------------------------------
-- 1) departments  (names come from employees, history and projects)
--    GROUP BY ... COLLATE utf8mb4_bin so 'sales' and 'Sales' are counted as different spellings,
--    then ROW_NUMBER() keeps the most frequent spelling per case-insensitive name.
-- ------------------------------------------------------------
INSERT IGNORE INTO departments (department_name)
WITH raw_names AS (
    SELECT TRIM(REGEXP_REPLACE(department, '[[:space:]]+', ' ')) AS nm FROM stg_employee
    UNION ALL
    SELECT TRIM(REGEXP_REPLACE(department, '[[:space:]]+', ' ')) FROM stg_employee_history
    UNION ALL
    SELECT TRIM(REGEXP_REPLACE(department, '[[:space:]]+', ' ')) FROM stg_project
),
counted AS (
    SELECT nm COLLATE utf8mb4_bin AS nm, COUNT(*) AS cnt
    FROM raw_names
    WHERE nm IS NOT NULL AND nm <> ''
    GROUP BY nm COLLATE utf8mb4_bin
),
ranked AS (
    SELECT nm,
           ROW_NUMBER() OVER (PARTITION BY LOWER(nm) ORDER BY cnt DESC, nm) AS rn
    FROM counted
)
SELECT nm FROM ranked WHERE rn = 1 ORDER BY nm;

-- ------------------------------------------------------------
-- 2) job_roles
-- ------------------------------------------------------------
INSERT IGNORE INTO job_roles (job_role_name)
WITH raw_names AS (
    SELECT TRIM(REGEXP_REPLACE(job_role, '[[:space:]]+', ' ')) AS nm FROM stg_employee
    UNION ALL
    SELECT TRIM(REGEXP_REPLACE(job_role, '[[:space:]]+', ' ')) FROM stg_employee_history
),
counted AS (
    SELECT nm COLLATE utf8mb4_bin AS nm, COUNT(*) AS cnt
    FROM raw_names
    WHERE nm IS NOT NULL AND nm <> ''
    GROUP BY nm COLLATE utf8mb4_bin
),
ranked AS (
    SELECT nm,
           ROW_NUMBER() OVER (PARTITION BY LOWER(nm) ORDER BY cnt DESC, nm) AS rn
    FROM counted
)
SELECT nm FROM ranked WHERE rn = 1 ORDER BY nm;

-- ------------------------------------------------------------
-- 3) employees  (employee_id = source employee_number)
--    dedup #1: one row per employee_number
--    dedup #2: email is UNIQUE, so NULL/duplicate emails get a generated fallback address
-- ------------------------------------------------------------
INSERT IGNORE INTO employees
    (employee_id, first_name, last_name, email, gender, age, marital_status, city, education_field,
     hire_date, department_id, job_role_id, job_level, monthly_income, over_time, attrition, years_at_company)
WITH cleaned AS (
    SELECT s.stg_id,
           s.employee_number,
           TRIM(s.first_name)                                        AS first_name,
           TRIM(s.last_name)                                         AS last_name,
           NULLIF(LOWER(TRIM(s.email)), '')                          AS email,
           NULLIF(TRIM(s.gender), '')                                AS gender,
           CASE WHEN s.age BETWEEN 18 AND 70 THEN s.age END          AS age,
           NULLIF(TRIM(s.marital_status), '')                        AS marital_status,
           NULLIF(TRIM(s.city), '')                                  AS city,
           NULLIF(TRIM(s.education_field), '')                       AS education_field,
           s.hire_date,
           TRIM(REGEXP_REPLACE(s.department, '[[:space:]]+', ' '))   AS department,
           TRIM(REGEXP_REPLACE(s.job_role,   '[[:space:]]+', ' '))   AS job_role,
           s.job_level,
           s.monthly_income,
           CASE WHEN LOWER(TRIM(s.over_time)) IN ('yes','y','1','true') THEN 1 ELSE 0 END AS over_time,
           CASE WHEN LOWER(TRIM(s.attrition)) IN ('yes','y','1','true') THEN 1 ELSE 0 END AS attrition,
           CASE WHEN s.years_at_company >= 0 THEN s.years_at_company END AS years_at_company
    FROM stg_employee s
    WHERE s.employee_number IS NOT NULL
      AND NULLIF(TRIM(s.first_name), '') IS NOT NULL
      AND NULLIF(TRIM(s.last_name), '')  IS NOT NULL
      AND s.hire_date IS NOT NULL
      AND s.job_level BETWEEN 1 AND 5
      AND s.monthly_income > 0
),
dedup AS (
    SELECT c.*,
           ROW_NUMBER() OVER (PARTITION BY c.employee_number ORDER BY c.stg_id DESC) AS rn
    FROM cleaned c
),
one_per_emp AS (
    SELECT d.*,
           ROW_NUMBER() OVER (PARTITION BY d.email ORDER BY d.employee_number) AS email_rn
    FROM dedup d
    WHERE d.rn = 1
)
SELECT u.employee_number,
       u.first_name,
       u.last_name,
       CASE WHEN u.email IS NULL OR u.email_rn > 1
            THEN CONCAT(LOWER(REPLACE(u.first_name, ' ', '')), '.', LOWER(REPLACE(u.last_name, ' ', '')),
                        '.', u.employee_number, '@example.com')
            ELSE u.email END,
       u.gender, u.age, u.marital_status, u.city, u.education_field,
       u.hire_date,
       d.department_id,
       jr.job_role_id,
       u.job_level,
       u.monthly_income,
       u.over_time,
       u.attrition,
       u.years_at_company
FROM one_per_emp u
JOIN departments d ON d.department_name = u.department
JOIN job_roles  jr ON jr.job_role_name  = u.job_role;

-- ------------------------------------------------------------
-- 4) employee_history  (feeds the SCD2 dimension)
--    effective_to is recomputed: next version's effective_from - 1 day; NULL on the latest version.
-- ------------------------------------------------------------
INSERT IGNORE INTO employee_history
    (employee_id, department_id, job_role_id, job_level, monthly_income, effective_from, effective_to)
WITH cleaned AS (
    SELECT h.stg_id,
           h.employee_number                                          AS employee_id,
           TRIM(REGEXP_REPLACE(h.department, '[[:space:]]+', ' '))    AS department,
           TRIM(REGEXP_REPLACE(h.job_role,   '[[:space:]]+', ' '))    AS job_role,
           h.job_level,
           h.monthly_income,
           h.effective_from
    FROM stg_employee_history h
    JOIN employees e ON e.employee_id = h.employee_number          -- drops orphan history rows
    WHERE h.effective_from IS NOT NULL
      AND h.job_level BETWEEN 1 AND 5
      AND h.monthly_income > 0
),
dedup AS (
    SELECT c.*,
           ROW_NUMBER() OVER (PARTITION BY c.employee_id, c.effective_from ORDER BY c.stg_id DESC) AS rn
    FROM cleaned c
),
versions AS (
    SELECT d.*,
           LEAD(d.effective_from) OVER (PARTITION BY d.employee_id ORDER BY d.effective_from) AS next_from
    FROM dedup d
    WHERE d.rn = 1
)
SELECT v.employee_id,
       dep.department_id,
       jr.job_role_id,
       v.job_level,
       v.monthly_income,
       v.effective_from,
       v.next_from - INTERVAL 1 DAY
FROM versions v
JOIN departments dep ON dep.department_name = v.department
JOIN job_roles   jr  ON jr.job_role_name    = v.job_role;

-- Employees with no history at all get one baseline version (so every employee exists in the SCD2 dim)
INSERT IGNORE INTO employee_history
    (employee_id, department_id, job_role_id, job_level, monthly_income, effective_from, effective_to)
SELECT e.employee_id, e.department_id, e.job_role_id, e.job_level, e.monthly_income, e.hire_date, NULL
FROM employees e
LEFT JOIN employee_history h ON h.employee_id = e.employee_id
WHERE h.history_id IS NULL;

-- ------------------------------------------------------------
-- 5) projects  (source project_id is preserved)
-- ------------------------------------------------------------
INSERT IGNORE INTO projects (project_id, project_name, department_id, status, start_date, end_date)
WITH dedup AS (
    SELECT s.*,
           ROW_NUMBER() OVER (PARTITION BY s.project_id ORDER BY s.stg_id DESC) AS rn
    FROM stg_project s
    WHERE s.project_id IS NOT NULL
      AND NULLIF(TRIM(s.project_name), '') IS NOT NULL
      AND s.start_date IS NOT NULL
)
SELECT d.project_id,
       TRIM(d.project_name),
       dep.department_id,
       COALESCE(NULLIF(TRIM(d.status), ''), 'Unknown'),
       d.start_date,
       CASE WHEN d.end_date >= d.start_date THEN d.end_date END      -- bad end dates become NULL
FROM dedup d
JOIN departments dep ON dep.department_name = TRIM(REGEXP_REPLACE(d.department, '[[:space:]]+', ' '))
WHERE d.rn = 1;

-- ------------------------------------------------------------
-- 6) assignments  (source assignment_id is preserved)
-- ------------------------------------------------------------
INSERT IGNORE INTO assignments
    (assignment_id, employee_id, project_id, role_on_project, allocation_pct, start_date, end_date)
WITH dedup AS (
    SELECT s.*,
           ROW_NUMBER() OVER (PARTITION BY s.assignment_id ORDER BY s.stg_id DESC) AS rn
    FROM stg_assignment s
    WHERE s.assignment_id IS NOT NULL
      AND s.start_date IS NOT NULL
)
SELECT d.assignment_id,
       d.employee_number,
       d.project_id,
       NULLIF(TRIM(d.role_on_project), ''),
       CASE WHEN d.allocation_pct BETWEEN 1 AND 100 THEN d.allocation_pct END,
       d.start_date,
       CASE WHEN d.end_date >= d.start_date THEN d.end_date END
FROM dedup d
JOIN employees e ON e.employee_id = d.employee_number
JOIN projects  p ON p.project_id  = d.project_id
WHERE d.rn = 1;

-- ------------------------------------------------------------
-- 7) reviews  (source review_id is preserved; unknown project -> NULL, "Unassigned" in the DW)
-- ------------------------------------------------------------
INSERT IGNORE INTO reviews
    (review_id, employee_id, project_id, review_date, performance_rating, review_score,
     job_satisfaction, environment_satisfaction, salary_hike_pct)
WITH dedup AS (
    SELECT s.*,
           ROW_NUMBER() OVER (PARTITION BY s.review_id ORDER BY s.stg_id DESC) AS rn
    FROM stg_review s
    WHERE s.review_id IS NOT NULL
      AND s.review_date IS NOT NULL
      AND s.performance_rating BETWEEN 1 AND 5
)
SELECT d.review_id,
       d.employee_number,
       p.project_id,
       d.review_date,
       d.performance_rating,
       d.review_score,
       CASE WHEN d.job_satisfaction         BETWEEN 1 AND 4 THEN d.job_satisfaction         END,
       CASE WHEN d.environment_satisfaction BETWEEN 1 AND 4 THEN d.environment_satisfaction END,
       CASE WHEN d.salary_hike_pct >= 0 THEN d.salary_hike_pct END
FROM dedup d
JOIN employees e      ON e.employee_id = d.employee_number
LEFT JOIN projects p  ON p.project_id  = d.project_id
WHERE d.rn = 1;

-- ------------------------------------------------------------
-- Sanity checks (rows lost = rows rejected by the cleaning rules above)
-- ------------------------------------------------------------
SELECT 'employees'        AS tbl, (SELECT COUNT(DISTINCT employee_number) FROM stg_employee) AS distinct_in_staging, (SELECT COUNT(*) FROM employees)        AS loaded
UNION ALL SELECT 'employee_history', (SELECT COUNT(*) FROM stg_employee_history), (SELECT COUNT(*) FROM employee_history)
UNION ALL SELECT 'projects',         (SELECT COUNT(DISTINCT project_id)  FROM stg_project),    (SELECT COUNT(*) FROM projects)
UNION ALL SELECT 'assignments',      (SELECT COUNT(DISTINCT assignment_id) FROM stg_assignment),(SELECT COUNT(*) FROM assignments)
UNION ALL SELECT 'reviews',          (SELECT COUNT(DISTINCT review_id)   FROM stg_review),     (SELECT COUNT(*) FROM reviews);

-- Snapshot vs latest history version: should return 0 rows. If not, the synthesizer's last history row
-- doesn't match the employee's current attributes (SCD2 "current" row would disagree with OLTP).
SELECT e.employee_id
FROM employees e
JOIN employee_history h ON h.employee_id = e.employee_id AND h.effective_to IS NULL
WHERE NOT (e.department_id = h.department_id AND e.job_role_id = h.job_role_id
           AND e.job_level = h.job_level AND e.monthly_income = h.monthly_income)
LIMIT 20;