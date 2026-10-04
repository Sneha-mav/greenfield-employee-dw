-- ============================================================
-- OLTP layer: normalized (3NF). 
-- employee_id = the source employee_number 
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
    department_id   INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS job_roles (
    job_role_id   INT AUTO_INCREMENT PRIMARY KEY,
    job_role_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS employees (
    employee_id       INT PRIMARY KEY,
    first_name        VARCHAR(100) NOT NULL,
    last_name         VARCHAR(100) NOT NULL,
    email             VARCHAR(200) NOT NULL UNIQUE,
    gender            VARCHAR(20),
    age               TINYINT UNSIGNED,
    marital_status    VARCHAR(20),
    city              VARCHAR(100),
    education_field   VARCHAR(50),
    hire_date         DATE NOT NULL,
    department_id     INT NOT NULL,
    job_role_id       INT NOT NULL,
    job_level         TINYINT NOT NULL,
    monthly_income    INT NOT NULL,
    over_time         TINYINT(1) NOT NULL DEFAULT 0,
    attrition         TINYINT(1) NOT NULL DEFAULT 0,
    years_at_company  SMALLINT,
    CONSTRAINT fk_emp_dept FOREIGN KEY (department_id) REFERENCES departments(department_id),
    CONSTRAINT fk_emp_role FOREIGN KEY (job_role_id)   REFERENCES job_roles(job_role_id),
    CONSTRAINT chk_emp_level  CHECK (job_level BETWEEN 1 AND 5),
    CONSTRAINT chk_emp_income CHECK (monthly_income > 0),
    KEY idx_emp_dept (department_id)
) ENGINE=InnoDB;

-- Every version of an employee's department / role / level / salary.(feeds the scd2 type)
CREATE TABLE IF NOT EXISTS employee_history (
    history_id     INT AUTO_INCREMENT PRIMARY KEY,
    employee_id    INT NOT NULL,
    department_id  INT NOT NULL,
    job_role_id    INT NOT NULL,
    job_level      TINYINT NOT NULL,
    monthly_income INT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to   DATE NULL,
    CONSTRAINT fk_hist_emp  FOREIGN KEY (employee_id)   REFERENCES employees(employee_id),
    CONSTRAINT fk_hist_dept FOREIGN KEY (department_id) REFERENCES departments(department_id),
    CONSTRAINT fk_hist_role FOREIGN KEY (job_role_id)   REFERENCES job_roles(job_role_id),
    CONSTRAINT uq_hist UNIQUE (employee_id, effective_from)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS projects (
    project_id    INT AUTO_INCREMENT PRIMARY KEY,
    project_name  VARCHAR(150) NOT NULL,
    department_id INT NOT NULL,
    status        VARCHAR(30) NOT NULL,
    start_date    DATE NOT NULL,
    end_date      DATE NULL,
    CONSTRAINT fk_proj_dept FOREIGN KEY (department_id) REFERENCES departments(department_id)
) ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS assignments (
    assignment_id   INT AUTO_INCREMENT PRIMARY KEY,
    employee_id     INT NOT NULL,
    project_id      INT NOT NULL,
    role_on_project VARCHAR(50),
    allocation_pct  TINYINT UNSIGNED,
    start_date      DATE NOT NULL,
    end_date        DATE NULL,
    CONSTRAINT fk_asg_emp  FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    CONSTRAINT fk_asg_proj FOREIGN KEY (project_id)  REFERENCES projects(project_id),
    CONSTRAINT chk_asg_alloc CHECK (allocation_pct BETWEEN 1 AND 100),
    KEY idx_asg_emp (employee_id),
    KEY idx_asg_proj (project_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reviews (
    review_id                INT AUTO_INCREMENT PRIMARY KEY,
    employee_id              INT NOT NULL,
    project_id               INT NULL,
    review_date              DATE NOT NULL,
    performance_rating       TINYINT NOT NULL,
    review_score             DECIMAL(6,1),
    job_satisfaction         TINYINT,
    environment_satisfaction TINYINT,
    salary_hike_pct          DECIMAL(6,2),
    CONSTRAINT fk_rev_emp  FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    CONSTRAINT fk_rev_proj FOREIGN KEY (project_id)  REFERENCES projects(project_id),
    CONSTRAINT chk_rev_rating CHECK (performance_rating BETWEEN 1 AND 5),
    KEY idx_rev_emp_date (employee_id, review_date),
    KEY idx_rev_date (review_date)
) ENGINE=InnoDB;
