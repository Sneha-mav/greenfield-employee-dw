# Requirement audit

This audit records what is present in the repository. “Complete” means source code and SQL are present; it does not claim a live MySQL execution unless noted.

| Requirement | Existing implementation/file | Status | Dashboard impact |
|---|---|---:|---|
| 100,000+ synthetic dataset using pandas and Faker | `synthesizer/run_synthesis.py`, `data_synthesizer.py`, `entity_generator.py`; target is `100_000` | Complete | Supplies a realistic analytical volume.
| Historical employee records for SCD Type 2 | `synthesizer/history_generator.py`, writes `employee_history.csv` | Complete | Enables employee history lookup and timeline.
| Staging, OLTP, and OLAP schemas | `sql/01_staging_ddl.sql`, `02_oltp_ddl.sql`, `03_olap_ddl.sql` | Complete | Separates operational entry from reporting.
| Normalized employees, departments, projects, reviews, assignments | `sql/02_oltp_ddl.sql` | Complete | Powers Employees, Projects, Reviews, and Employee changes pages.
| Star schema: fact reviews and four dimensions | `sql/03_olap_ddl.sql` | Complete | Powers the Analytics dashboard.
| Surrogate keys and employee SCD Type 2 fields | `sql/03_olap_ddl.sql`; `employee_key`, `start_date`, `end_date`, `is_current` | Complete | Supports accurate historical reporting.
| Stored procedures, CTEs, window functions, ETL | `sql/06_sp_load_dimensions.sql`, `07_sp_load_fact.sql`, `08_analytics_queries.sql` | Complete | Produces validated dashboard measures and ranked views.
| OOP Singleton database layer, entities, DAL managers, error handling | `src/db_manager.py`, `src/entities/`, `src/managers/` | Complete | Keeps Streamlit pages separated from database logic.
| Employee onboarding, project creation/assignment, review submission, employee changes | `app/views/1_Onboard_Employee.py` through `4_Update_Department.py`, `app/components/forms.py` | Complete | Available in the top HR navigation.
| Change UI triggers employee warehouse update | `src/managers/employee_manager.py`, `sp_load_dim_employee` | Complete | Maintains SCD Type 2 history after department, role, level, or salary changes.
| Year-over-year performance trend | `AnalyticsManager.rating_trend_by_year`, `charts.yoy_trend_line` | Complete | Overview chart.
| Department-ranked top performers using `DENSE_RANK()` | `src/managers/analytics_manager.py` | Complete | Employee history tab.
| Attrition and threshold-based retention review queue | `analytics_manager.py`, dashboard Workforce tab | Complete | Workforce tab; clearly presented as a review queue, not a prediction.
| Allocation-aware project bottleneck analysis | `analytics_manager.py`, dashboard Project health tab | Complete | Project health tab.
| Warehouse reconciliation and SCD integrity validation | `AnalyticsManager.validate_warehouse` | Complete | Available in the data-access layer; intentionally not shown in the executive dashboard.
| Editable ER and dimensional-model diagrams | No editable `.drawio`, Lucidchart export, or equivalent source found | Missing | Does not block the dashboard; required for final project submission.
| Git feature-branch workflow and pull requests | Repository has a GitHub remote and current local branch is `feature/hr-dashboard-polish`; no PR was created in this audit | Partial | Dashboard work is isolated locally; PR workflow still needs to be completed.
| Streamlit Community Cloud deployment | Deployment configuration/readiness is present, but no verified public URL was found | Partial | Local app is ready; cloud deployment still needs a configured database/secrets and a deployment verification.

## Feature-preservation map

| Existing feature | Final location | Verification method |
|---|---|---|
| Performance trend and review volume | Overview | Fixture-based Streamlit test and `charts.yoy_trend_line` |
| Attrition by department | Overview | Fixture-based Streamlit test and `charts.attrition_by_dept_bar` |
| Department scorecard | Overview expander | Dashboard logic test |
| Top performers (`DENSE_RANK`) | Employee history | SQL source inspection and manager query |
| Retention review queue | Workforce expander | Fixture-based Streamlit test |
| Hire-cohort attrition | Workforce | Fixture-based Streamlit test |
| Salary-band attrition (`NTILE`) | Workforce expander | Manager query and dashboard fixture |
| Allocation-aware project health | Project health | Dashboard logic test |
| Project bottleneck/action table | Project health expander | Dashboard fixture |
| SCD Type 2 timeline | Employee history after selection | `AnalyticsManager.get_employee_scd2_history` and chart function |

| Employee onboarding | Employees navigation | Existing Streamlit form |
| Project creation and assignment | Projects navigation | Existing Streamlit forms |
| Review submission | Reviews navigation | Existing Streamlit form |
| Department, role, level, salary changes | Employee changes navigation | Existing Streamlit forms and SCD procedure |
