# Architecture and Schema Contract

Three schemas on one MySQL 8.0+ server: hr_staging, hr_oltp, hr_dw.
Flow: CSVs -> hr_staging -> (SQL cleaning with CTEs and window functions) -> hr_oltp -> (stored procedures) -> hr_dw -> Streamlit.

## Source CSVs (data/synthesized, not committed)
- employees_synth.csv: 101,500 rows (100,000 employees plus 1,500 intentional duplicates, some NULLs, some bad casing)
- employee_history.csv: SCD2 source, one row per version (employee_number, department, job_role, job_level, monthly_income, effective_from, effective_to, change_type)
- projects.csv, assignments.csv, reviews.csv

## hr_staging
stg_employees, stg_employee_history, stg_projects, stg_assignments, stg_reviews (same column names as the CSVs, all nullable)

## hr_oltp (normalized)
departments, job_roles, employees (employee_id = employee_number), employee_history, projects, assignments, reviews (project_id may be NULL)

## hr_dw (star schema)
- dim_employee: employee_key (surrogate), employee_id (business key), start_date, end_date, is_current. SCD Type 2 on department_name, job_role, job_level, monthly_income.
- dim_department: department_key, department_id
- dim_project: project_key, project_id (key 0 = Unknown / No Project)
- dim_date: date_key = YYYYMMDD
- fact_performance_reviews: one row per review. Foreign keys employee_key, department_key, project_key, date_key.
- Current rows: end_date = '9999-12-31', is_current = 1.
- The fact's employee_key is the dim_employee version valid on the review date.

## Stored procedures (names agreed here, written on Day 2)
sp_load_oltp_from_staging, sp_load_dim_department, sp_load_dim_project, sp_load_dim_employee_initial, sp_load_fact_reviews, sp_run_full_etl,
sp_apply_employee_change(IN p_employee_id INT, IN p_new_department VARCHAR(100), IN p_effective_date DATE)

## SQL run order
01_staging_ddl, 02_oltp_ddl, 03_olap_ddl, 05_dim_date_load (then the Day 2 procedure scripts)