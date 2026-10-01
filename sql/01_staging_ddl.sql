-- ============================================================
-- STAGING layer: raw landing tables for the 5 synthesized CSVs, no pk,fk,not null,check constraints, no data cleaning.
-- stg_id (technical row id) gives ROW_NUMBER() a stable tie-breaker.
-- Re-runnable: tables are dropped and recreated.
-- ============================================================
DROP TABLE IF EXISTS stg_review;
DROP TABLE IF EXISTS stg_assignment;
DROP TABLE IF EXISTS stg_project;
DROP TABLE IF EXISTS stg_employee_history;
DROP TABLE IF EXISTS stg_employee;

-- employees_synth.csv  (~101,500 rows, dirty)
CREATE TABLE stg_employee (
    stg_id                     BIGINT AUTO_INCREMENT PRIMARY KEY,
    age                        INT,
    attrition                  VARCHAR(10),
    business_travel            VARCHAR(30),
    daily_rate                 INT,
    department                 VARCHAR(100),
    distance_from_home         INT,
    education                  INT,
    education_field            VARCHAR(50),
    employee_number            INT,
    environment_satisfaction   INT,
    gender                     VARCHAR(20),
    hourly_rate                INT,
    job_involvement            INT,
    job_level                  INT,
    job_role                   VARCHAR(100),
    job_satisfaction           INT,
    marital_status             VARCHAR(20),
    monthly_income             INT,
    monthly_rate               INT,
    num_companies_worked       INT,
    over_time                  VARCHAR(10),
    percent_salary_hike        INT,
    performance_rating         INT,
    relationship_satisfaction  INT,
    stock_option_level         INT,
    total_working_years        INT,
    training_times_last_year   INT,
    work_life_balance          INT,
    years_at_company           INT,
    years_in_current_role      INT,
    years_since_last_promotion INT,
    years_with_curr_manager    INT,
    first_name                 VARCHAR(100),
    last_name                  VARCHAR(100),
    email                      VARCHAR(200),
    city                       VARCHAR(100),
    hire_date                  DATE,
    load_ts                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_stg_emp_num (employee_number)
) ENGINE=InnoDB;

-- employee_history.csv  (~136,029 rows)
CREATE TABLE stg_employee_history (
    stg_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_number INT,
    department      VARCHAR(100),
    job_role        VARCHAR(100),
    job_level       INT,
    monthly_income  INT,
    effective_from  DATE,
    effective_to    DATE,
    change_type     VARCHAR(30),
    load_ts         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_stg_hist_emp (employee_number, effective_from)
) ENGINE=InnoDB;

-- projects.csv  (500 rows)
CREATE TABLE stg_project (
    stg_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id   INT,
    project_name VARCHAR(150),
    department   VARCHAR(100),
    status       VARCHAR(30),
    start_date   DATE,
    end_date     DATE,
    load_ts      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- assignments.csv  (~88,280 rows)
CREATE TABLE stg_assignment (
    stg_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    assignment_id   INT,
    employee_number INT,
    project_id      INT,
    role_on_project VARCHAR(50),
    allocation_pct  INT,
    start_date      DATE,
    end_date        DATE,
    load_ts         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- reviews.csv  (~268,307 rows)
CREATE TABLE stg_review (
    stg_id                   BIGINT AUTO_INCREMENT PRIMARY KEY,
    review_id                INT,
    employee_number          INT,
    project_id               INT,
    review_date              DATE,
    performance_rating       INT,
    review_score             DECIMAL(6,1),
    job_satisfaction         INT,
    environment_satisfaction INT,
    salary_hike_pct          DECIMAL(6,2),
    load_ts                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_stg_rev_emp (employee_number)
) ENGINE=InnoDB;
