-- ============================================================
-- 06_sp_load_dimensions.sql
-- OLTP -> OLAP dimension loaders (stored procedures).
--   sp_load_dim_department()      Type 1 upsert
--   sp_load_dim_project()         Type 1 upsert  (row -1 'Unassigned' is created in 03_olap_ddl.sql)
--   sp_load_dim_employee(emp_id)  SCD Type 2. Pass NULL for all employees, or one employee_id
--                                 (the Streamlit "Update Department" page can CALL it for just that person).
-- All are re-runnable / incremental.
-- Run in the mysql client or Workbench (DELIMITER is a client command).
-- ============================================================
DELIMITER //

-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_load_dim_department//
CREATE PROCEDURE sp_load_dim_department()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO dim_department (department_id, department_name)
    SELECT department_id, department_name
    FROM departments
    ON DUPLICATE KEY UPDATE department_name = VALUES(department_name);
    COMMIT;
END//

-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_load_dim_project//
CREATE PROCEDURE sp_load_dim_project()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO dim_project (project_id, project_name, status, start_date, end_date)
    SELECT project_id, project_name, status, start_date, end_date
    FROM projects
    ON DUPLICATE KEY UPDATE
        project_name = VALUES(project_name),
        status       = VALUES(status),
        start_date   = VALUES(start_date),
        end_date     = VALUES(end_date);
    COMMIT;
END//

-- ------------------------------------------------------------
-- SCD Type 2 for dim_employee
--   Tracked attributes : department_name, job_role, job_level, monthly_income
--   Type 1 attributes  : full_name, gender, hire_date, attrition (overwritten on every version)
--
--   Step A  CTE + window functions turn employee_history into clean "versions":
--           LAG() flags a real change, a running SUM() numbers each run of identical attributes
--           (gaps-and-islands), runs are collapsed, LEAD() derives end dates.
--   Step B  Expire: dim rows still flagged current whose version is now closed in the source.
--   Step C  Insert: versions that don't exist in the dim yet (this is the initial load AND the
--           "department changed" path: the new version gets a fresh surrogate key).
--   Step D  Type 1 refresh of the non-tracked attributes.
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_load_dim_employee//
CREATE PROCEDURE sp_load_dim_employee(IN p_employee_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        DROP TEMPORARY TABLE IF EXISTS tmp_emp_versions;
        RESIGNAL;
    END;

    DROP TEMPORARY TABLE IF EXISTS tmp_emp_versions;
    CREATE TEMPORARY TABLE tmp_emp_versions (
        employee_id     INT         NOT NULL,
        department_name VARCHAR(100) NOT NULL,
        job_role        VARCHAR(100) NOT NULL,
        job_level       TINYINT,
        monthly_income  INT         NOT NULL,
        start_date      DATE        NOT NULL,
        end_date        DATE        NOT NULL,
        is_current      TINYINT(1)  NOT NULL,
        KEY idx_tmp_ver (employee_id, start_date)
    ) ENGINE=InnoDB;

    START TRANSACTION;

    -- Step A: build clean versions from OLTP history
    INSERT INTO tmp_emp_versions
        (employee_id, department_name, job_role, job_level, monthly_income, start_date, end_date, is_current)
    WITH hist_raw AS (
        SELECT h.employee_id, d.department_name, r.job_role_name AS job_role,
               h.job_level, h.monthly_income, h.effective_from, h.history_id
        FROM employee_history h
        JOIN departments d ON d.department_id = h.department_id
        JOIN job_roles   r ON r.job_role_id   = h.job_role_id
        WHERE p_employee_id IS NULL OR h.employee_id = p_employee_id
    ),
    hist AS (
        SELECT employee_id, department_name, job_role, job_level, monthly_income, effective_from
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY employee_id, effective_from ORDER BY history_id DESC) as rn
            FROM hist_raw
        ) x WHERE rn = 1
    ),
    flagged AS (
        SELECT hist.*,
               CASE
                   WHEN LAG(employee_id) OVER w IS NULL THEN 1          -- first version of the employee
                   WHEN department_name <=> LAG(department_name) OVER w
                    AND job_role        <=> LAG(job_role)        OVER w
                    AND job_level       <=> LAG(job_level)       OVER w
                    AND monthly_income  <=> LAG(monthly_income)  OVER w THEN 0   -- nothing tracked changed
                   ELSE 1
               END AS is_change
        FROM hist
        WINDOW w AS (PARTITION BY employee_id ORDER BY effective_from)
    ),
    grouped AS (
        SELECT flagged.*,
               SUM(is_change) OVER (PARTITION BY employee_id ORDER BY effective_from
                                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS grp
        FROM flagged
    ),
    collapsed AS (
        SELECT employee_id, grp,
               MIN(department_name) AS department_name,
               MIN(job_role)        AS job_role,
               MIN(job_level)       AS job_level,
               MIN(monthly_income)  AS monthly_income,
               MIN(effective_from)  AS start_date
        FROM grouped
        GROUP BY employee_id, grp
    ),
    versioned AS (
        SELECT c.*,
               LEAD(start_date) OVER (PARTITION BY employee_id ORDER BY start_date) AS next_start
        FROM collapsed c
    )
    SELECT employee_id, department_name, job_role, job_level, monthly_income, start_date,
           COALESCE(next_start - INTERVAL 1 DAY, DATE '9999-12-31'),
           IF(next_start IS NULL, 1, 0)
    FROM versioned;

    -- Step B: expire rows that the source has closed
    UPDATE dim_employee d
    JOIN tmp_emp_versions t
      ON t.employee_id = d.employee_id
     AND t.start_date  = d.start_date
    SET d.end_date   = t.end_date,
        d.is_current = 0
    WHERE d.is_current = 1
      AND t.is_current = 0;

    -- Step C.1: Update tracked attributes for same-day updates on the existing current version
    UPDATE dim_employee d
    JOIN tmp_emp_versions t
      ON t.employee_id = d.employee_id
    SET d.department_name = t.department_name,
        d.job_role        = t.job_role,
        d.job_level       = t.job_level,
        d.monthly_income  = t.monthly_income,
        d.end_date        = t.end_date
    WHERE d.is_current = 1
      AND t.is_current = 1
      AND NOT (d.department_name <=> t.department_name
           AND d.job_role        <=> t.job_role
           AND d.job_level       <=> t.job_level
           AND d.monthly_income  <=> t.monthly_income
           AND d.end_date        <=> t.end_date);

    -- Step C.2: insert versions the dimension has not seen yet (new surrogate key per version)
    INSERT INTO dim_employee
        (employee_id, full_name, gender, hire_date, attrition,
         department_name, job_role, job_level, monthly_income,
         start_date, end_date, is_current)
    SELECT t.employee_id,
           CONCAT(e.first_name, ' ', e.last_name),
           e.gender, e.hire_date, e.attrition,
           t.department_name, t.job_role, t.job_level, t.monthly_income,
           t.start_date, t.end_date, t.is_current
    FROM tmp_emp_versions t
    JOIN employees e ON e.employee_id = t.employee_id
    WHERE NOT EXISTS (SELECT 1 FROM dim_employee d
                      WHERE d.employee_id = t.employee_id
                        AND d.start_date  = t.start_date)
    ORDER BY t.employee_id, t.start_date;

    -- Step D: Type 1 refresh of non-tracked attributes (all versions of the employee)
    UPDATE dim_employee d
    JOIN employees e ON e.employee_id = d.employee_id
    SET d.full_name = CONCAT(e.first_name, ' ', e.last_name),
        d.gender    = e.gender,
        d.hire_date = e.hire_date,
        d.attrition = e.attrition
    WHERE (p_employee_id IS NULL OR d.employee_id = p_employee_id)
      AND NOT (d.full_name <=> CONCAT(e.first_name, ' ', e.last_name)
           AND d.gender    <=> e.gender
           AND d.hire_date <=> e.hire_date
           AND d.attrition <=> e.attrition);

    COMMIT;
    DROP TEMPORARY TABLE IF EXISTS tmp_emp_versions;
END//

DELIMITER ;

CALL sp_load_dim_department();
CALL sp_load_dim_project();
CALL sp_load_dim_employee(NULL);
SET SQL_SAFE_UPDATES = 0;
CALL sp_load_dim_employee(NULL);
