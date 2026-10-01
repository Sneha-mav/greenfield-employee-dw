-- ============================================================
-- OLAP layer: star schema.
-- FACT GRAIN: one row per employee per review.
-- Dimensions: dim_date, dim_department, dim_project, dim_employee (SCD Type 2)
-- Surrogate keys (*_key) everywhere; business keys (*_id) kept for lookups.
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_date (
    date_key   INT PRIMARY KEY,              -- YYYYMMDD 
    full_date  DATE NOT NULL UNIQUE,
    year       SMALLINT NOT NULL,
    quarter    TINYINT  NOT NULL,
    month      TINYINT  NOT NULL,
    month_name VARCHAR(10) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_department (
    department_key  INT AUTO_INCREMENT PRIMARY KEY,
    department_id   INT NOT NULL UNIQUE,     -- business key (OLTP)
    department_name VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dim_project (
    project_key  INT AUTO_INCREMENT PRIMARY KEY,
    project_id   INT NULL UNIQUE,            -- business key (OLTP); NULL for 'Unassigned'
    project_name VARCHAR(150) NOT NULL,
    status       VARCHAR(30)  NOT NULL,
    start_date   DATE NULL,
    end_date     DATE NULL
) ENGINE=InnoDB;

-- Special row so reviews without a project still join (project_key = -1)
INSERT INTO dim_project (project_key, project_id, project_name, status)
VALUES (-1, NULL, 'Unassigned', 'N/A')
ON DUPLICATE KEY UPDATE project_name = VALUES(project_name);

-- SCD Type 2
-- (job_level and change_type are carried along from employee_history).
-- Current row: is_current = 1 and end_date = '9999-12-31'.
CREATE TABLE IF NOT EXISTS dim_employee (
    employee_key    INT AUTO_INCREMENT PRIMARY KEY,   -- surrogate key
    employee_id     INT NOT NULL,                     -- business key (OLTP)
    full_name       VARCHAR(210) NOT NULL,
    gender          VARCHAR(20),
    hire_date       DATE,
    attrition       TINYINT(1),
    -- tracked (SCD2) attributes
    department_name VARCHAR(100) NOT NULL,
    job_role        VARCHAR(100) NOT NULL,
    job_level       TINYINT,
    monthly_income  INT NOT NULL,
    -- SCD2 housekeeping
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL DEFAULT '9999-12-31',
    is_current      TINYINT(1) NOT NULL DEFAULT 1,
    KEY idx_dim_emp_bk (employee_id, is_current),
    KEY idx_dim_emp_range (employee_id, start_date, end_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS fact_performance_reviews (
    review_fact_key          BIGINT AUTO_INCREMENT PRIMARY KEY,
    review_id                INT NOT NULL UNIQUE,   -- degenerate dim; makes the ETL re-runnable
    employee_key             INT NOT NULL,          -- dim row valid on the review date
    department_key           INT NOT NULL,
    project_key              INT NOT NULL DEFAULT -1,
    review_date_key          INT NOT NULL,
    performance_rating       TINYINT NOT NULL,
    review_score             DECIMAL(6,1),
    job_satisfaction         TINYINT,
    environment_satisfaction TINYINT,
    salary_hike_pct          DECIMAL(6,2),
    monthly_income_at_review INT,
    CONSTRAINT fk_fact_emp  FOREIGN KEY (employee_key)    REFERENCES dim_employee(employee_key),
    CONSTRAINT fk_fact_dept FOREIGN KEY (department_key)  REFERENCES dim_department(department_key),
    CONSTRAINT fk_fact_proj FOREIGN KEY (project_key)     REFERENCES dim_project(project_key),
    CONSTRAINT fk_fact_date FOREIGN KEY (review_date_key) REFERENCES dim_date(date_key),
    KEY idx_fact_date (review_date_key),
    KEY idx_fact_dept (department_key)
) ENGINE=InnoDB;
