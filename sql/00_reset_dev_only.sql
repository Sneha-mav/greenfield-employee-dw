-- ============================================================
-- DEV ONLY: drops every table so the schema can be rebuilt from scratch.
-- not to run this against shared or production data.
-- ============================================================
SET FOREIGN_KEY_CHECKS = 0;
 
-- OLAP
DROP TABLE IF EXISTS fact_performance_reviews;
DROP TABLE IF EXISTS dim_employee;
DROP TABLE IF EXISTS dim_project;
DROP TABLE IF EXISTS dim_department;   
DROP TABLE IF EXISTS dim_date;
 
-- OLTP
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS assignments;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS employee_history;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS job_roles;
DROP TABLE IF EXISTS departments;
 
-- Staging
DROP TABLE IF EXISTS stg_review;
DROP TABLE IF EXISTS stg_assignment;
DROP TABLE IF EXISTS stg_project;
DROP TABLE IF EXISTS stg_employee_history;
DROP TABLE IF EXISTS stg_employee;
 
SET FOREIGN_KEY_CHECKS = 1;
 
