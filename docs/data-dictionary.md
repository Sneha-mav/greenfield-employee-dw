# Data Dictionary
 
Three layers: **staging** (raw CSV copy) → **OLTP** (normalized backend) → **OLAP** (star schema).
 
## 1. Staging layer (`sql/01_staging_ddl.sql`)
 
Raw landing tables, loaded as-is from the 5 synthesized CSVs. No primary keys on business columns, no foreign keys, no NOT NULL or CHECK constraints, and no cleaning. Duplicates, NULLs and messy text (for example `'  sales '`) are kept on purpose. Each table has a technical `stg_id` (auto-increment) and a `load_ts` timestamp.
 
| Table | Source CSV | Approx. rows |
|---|---|---|
| `stg_employee` | employees_synth.csv | 101,500 (about 100,000 distinct employees) |
| `stg_employee_history` | employee_history.csv | 136,029 |
| `stg_project` | projects.csv | 500 |
| `stg_assignment` | assignments.csv | 88,280 |
| `stg_review` | reviews.csv | 268,307 |
 
Columns in `stg_employee` that are **not** carried to OLTP: `daily_rate`, `hourly_rate`, `monthly_rate` (synthetic noise), `business_travel`, `distance_from_home`, `education`, `environment_satisfaction`, `job_involvement`, `job_satisfaction`, `num_companies_worked`, `percent_salary_hike`, `performance_rating`, `relationship_satisfaction`, `stock_option_level`, `total_working_years`, `training_times_last_year`, `work_life_balance`, `years_in_current_role`, `years_since_last_promotion`, `years_with_curr_manager`. They stay available in staging.
 
## 2. OLTP layer (`sql/02_oltp_ddl.sql`)
 
Normalized to 3NF. `employee_id` equals the source `employee_number`.
 
### departments
| Column | Type | Key | Description |
|---|---|---|---|
| department_id | INT AUTO_INCREMENT | PK | Department identifier |
| department_name | VARCHAR(100) | UNIQUE, NOT NULL | Cleaned department name |
 
### job_roles
| Column | Type | Key | Description |
|---|---|---|---|
| job_role_id | INT AUTO_INCREMENT | PK | Job role identifier |
| job_role_name | VARCHAR(100) | UNIQUE, NOT NULL | Job role name |
 
### employees
| Column | Type | Key | Description |
|---|---|---|---|
| employee_id | INT | PK | Source `employee_number` |
| first_name, last_name | VARCHAR(100) | NOT NULL | Name |
| email | VARCHAR(200) | UNIQUE, NOT NULL | Email address |
| gender | VARCHAR(20) | | Gender |
| age | TINYINT UNSIGNED | | Age |
| marital_status | VARCHAR(20) | | Marital status |
| city | VARCHAR(100) | | City |
| education_field | VARCHAR(50) | | Field of education |
| hire_date | DATE | NOT NULL | Date hired |
| department_id | INT | FK → departments, NOT NULL | Current department |
| job_role_id | INT | FK → job_roles, NOT NULL | Current role |
| job_level | TINYINT | NOT NULL, CHECK 1–5 | Current level |
| monthly_income | INT | NOT NULL, CHECK > 0 | Current monthly income |
| over_time | TINYINT(1) | NOT NULL | 1 = works overtime |
| attrition | TINYINT(1) | NOT NULL | 1 = left the company |
| years_at_company | SMALLINT | | Years at the company |
 
### employee_history
Every version of an employee's department, role, level and income. This table feeds the SCD2 dimension.
 
| Column | Type | Key | Description |
|---|---|---|---|
| history_id | INT AUTO_INCREMENT | PK | Row identifier |
| employee_id | INT | FK → employees, NOT NULL | Employee |
| department_id | INT | FK → departments, NOT NULL | Department in this version |
| job_role_id | INT | FK → job_roles, NOT NULL | Role in this version |
| job_level | TINYINT | NOT NULL | Level in this version |
| monthly_income | INT | NOT NULL | Income in this version |
| effective_from | DATE | NOT NULL | Version start. UNIQUE with `employee_id` |
| effective_to | DATE | NULL | Version end. NULL = still current |
 
### projects
| Column | Type | Key | Description |
|---|---|---|---|
| project_id | INT | PK | Source project ID |
| project_name | VARCHAR(150) | NOT NULL | Project name |
| department_id | INT | FK → departments, NOT NULL | Owning department |
| status | VARCHAR(30) | NOT NULL | Project status |
| start_date | DATE | NOT NULL | Start date |
| end_date | DATE | NULL | End date |
 
### assignments
| Column | Type | Key | Description |
|---|---|---|---|
| assignment_id | INT | PK | Source assignment ID |
| employee_id | INT | FK → employees, NOT NULL | Assigned employee |
| project_id | INT | FK → projects, NOT NULL | Project |
| role_on_project | VARCHAR(50) | | Role on the project |
| allocation_pct | TINYINT UNSIGNED | CHECK 1–100 | Percent of time allocated |
| start_date | DATE | NOT NULL | Start date |
| end_date | DATE | NULL | End date |
 
### reviews
| Column | Type | Key | Description |
|---|---|---|---|
| review_id | INT | PK | Source review ID |
| employee_id | INT | FK → employees, NOT NULL | Reviewed employee |
| project_id | INT | FK → projects, NULL | Related project, if any |
| review_date | DATE | NOT NULL | Date of review |
| performance_rating | TINYINT | NOT NULL, CHECK 1–5 | Performance rating |
| review_score | DECIMAL(6,1) | | Review score |
| job_satisfaction | TINYINT | | Job satisfaction |
| environment_satisfaction | TINYINT | | Environment satisfaction |
| salary_hike_pct | DECIMAL(6,2) | | Salary hike percent |
 
## 3. OLAP layer (`sql/03_olap_ddl.sql`)
 
Star schema. **Fact grain:** one row per employee per review.
 
### dim_date
| Column | Type | Key | Description |
|---|---|---|---|
| date_key | INT | PK | Date as `YYYYMMDD` |
| full_date | DATE | UNIQUE | Calendar date |
| year, quarter, month | SMALLINT / TINYINT | | Date parts |
| month_name | VARCHAR(10) | | Month name |
 
### dim_department
| Column | Type | Key | Description |
|---|---|---|---|
| department_key | INT AUTO_INCREMENT | PK (surrogate) | Warehouse key |
| department_id | INT | UNIQUE | Business key from OLTP |
| department_name | VARCHAR(100) | | Department name |
 
### dim_project
| Column | Type | Key | Description |
|---|---|---|---|
| project_key | INT AUTO_INCREMENT | PK (surrogate) | Warehouse key. `-1` = Unassigned |
| project_id | INT | UNIQUE, NULL | Business key. NULL for Unassigned |
| project_name | VARCHAR(150) | | Project name |
| status | VARCHAR(30) | | Project status |
 
### dim_employee (SCD Type 2)
| Column | Type | Key | Description |
|---|---|---|---|
| employee_key | INT AUTO_INCREMENT | PK (surrogate) | Warehouse key, one per version |
| employee_id | INT | | Business key from OLTP |
| full_name | VARCHAR(210) | | First and last name |
| gender | VARCHAR(20) | | Gender |
| hire_date | DATE | | Hire date |
| attrition | TINYINT(1) | | 1 = left the company |
| department_name | VARCHAR(100) | SCD2 tracked | Department in this version |
| job_role | VARCHAR(100) | SCD2 tracked | Role in this version |
| job_level | TINYINT | SCD2 tracked | Level in this version |
| monthly_income | INT | SCD2 tracked | Income in this version |
| start_date | DATE | SCD2 | Version start |
| end_date | DATE | SCD2 | Version end. `9999-12-31` for the current row |
| is_current | TINYINT(1) | SCD2 | 1 = current version |
 
### fact_performance_reviews
| Column | Type | Key | Description |
|---|---|---|---|
| review_fact_key | BIGINT AUTO_INCREMENT | PK | Fact row key |
| review_id | INT | UNIQUE | Degenerate dimension, keeps the ETL re-runnable |
| employee_key | INT | FK → dim_employee | Version valid on the review date |
| department_key | INT | FK → dim_department | Department at review time |
| project_key | INT | FK → dim_project | Project, or `-1` if none |
| review_date_key | INT | FK → dim_date | Review date |
| performance_rating | TINYINT | | Rating (measure) |
| review_score | DECIMAL(6,1) | | Score (measure) |
| job_satisfaction | TINYINT | | Measure |
| environment_satisfaction | TINYINT | | Measure |
| salary_hike_pct | DECIMAL(6,2) | | Measure |