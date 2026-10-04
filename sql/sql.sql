CREATE DATABASE mydb;

SELECT NOW();
USE trainingdb;
SELECT MAX(salary) AS sal
FROM employeess
WHERE salary<(SELECT MAX(salary) 
FROM employeess);
USE employee_dw;
SHOW TABLES;
SELECT COUNT(*) FROM employees;

USE employee_dw;

SELECT COUNT(*) FROM stg_employee;
SELECT COUNT(*) FROM stg_employee_history;
SELECT COUNT(*) FROM stg_project;
SELECT COUNT(*) FROM stg_review;
SELECT COUNT(*) FROM stg_assignment;

USE employee_dw;

SELECT COUNT(*) AS total_dates
FROM dim_date;

SELECT MIN(full_date), MAX(full_date)
FROM dim_date;


SELECT 'stg_employee' AS table_name, COUNT(*) AS total FROM stg_employee
UNION ALL SELECT 'stg_employee_history', COUNT(*) FROM stg_employee_history
UNION ALL SELECT 'stg_project', COUNT(*) FROM stg_project
UNION ALL SELECT 'stg_assignment', COUNT(*) FROM stg_assignment
UNION ALL SELECT 'stg_review', COUNT(*) FROM stg_review;

DESCRIBE stg_employee;
DESCRIBE stg_employee_history;
DESCRIBE stg_project;
DESCRIBE stg_assignment;
DESCRIBE stg_review;

SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'employee_dw'
AND TABLE_NAME IN (
    'stg_employee',
    'stg_employee_history',
    'stg_project',
    'stg_assignment',
    'stg_review'
)
ORDER BY TABLE_NAME, ORDINAL_POSITION;

DESCRIBE stg_employee;
DESCRIBE stg_employee_history;
DESCRIBE stg_project;
DESCRIBE stg_assignment;
DESCRIBE stg_review;


SELECT 'stg_employee' AS table_name, COUNT(*) AS total
FROM stg_employee
UNION ALL
SELECT 'stg_employee_history', COUNT(*)
FROM stg_employee_history
UNION ALL
SELECT 'stg_project', COUNT(*)
FROM stg_project
UNION ALL
SELECT 'stg_assignment', COUNT(*)
FROM stg_assignment
UNION ALL
SELECT 'stg_review', COUNT(*)
FROM stg_review;
SELECT VERSION();
SHOW TABLES;

SELECT 'departments' AS table_name, COUNT(*) AS total FROM departments
UNION ALL SELECT 'job_roles', COUNT(*) FROM job_roles
UNION ALL SELECT 'employees', COUNT(*) FROM employees
UNION ALL SELECT 'employee_history', COUNT(*) FROM employee_history
UNION ALL SELECT 'projects', COUNT(*) FROM projects
UNION ALL SELECT 'assignments', COUNT(*) FROM assignments
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews;

SELECT COUNT(*) AS total_dates FROM dim_date;

SELECT 'departments' AS table_name, COUNT(*) AS total FROM departments
UNION ALL SELECT 'job_roles', COUNT(*) FROM job_roles
UNION ALL SELECT 'employees', COUNT(*) FROM employees
UNION ALL SELECT 'employee_history', COUNT(*) FROM employee_history
UNION ALL SELECT 'projects', COUNT(*) FROM projects
UNION ALL SELECT 'assignments', COUNT(*) FROM assignments
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews;

DESCRIBE dim_department;
DESCRIBE dim_project;
DESCRIBE dim_employee;