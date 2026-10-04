# Enterprise Employee Analytics & Data Warehouse

A Streamlit application for employee onboarding, project allocation, performance reviews, SCD Type 2 history, and workforce analytics. The application writes operational activity to a normalized MySQL OLTP model and reports from an OLAP star schema.

## Architecture

- **OLTP:** `employees`, `departments`, `job_roles`, `employee_history`, `projects`, `assignments`, and `reviews`.
- **Warehouse:** `fact_performance_reviews` at one row per employee review; `dim_employee` is SCD Type 2 with a surrogate key, `start_date`, `end_date`, and `is_current`.
- **ETL:** Stored procedures load the dimensions and fact table. The employee dimension preserves a historical version whenever department, role, level, or salary changes.
- **Application:** OOP entities and managers keep database access separate from Streamlit pages.

## Dashboard

The Analytics Dashboard is organized for decisions instead of one long report:

| Tab | Purpose | Key views |
|---|---|---|
| Overview | Identify the immediate workforce priority | Core KPIs, performance trend, attrition by department, priority action |
| Workforce | Prioritize HR follow-up | Workforce risk, hire cohorts, retention review queue |
| Project health | Surface allocation and people risk | Current assignment allocation, ratings, satisfaction, and project action table |
| Employee history | Audit individual employee changes | Department-ranked performers and employee SCD Type 2 history |


### Dashboard controls

Use the **Filters** sidebar to set department, review-year range, project status, minimum review count, retention review threshold, and attrition attention threshold. Reset filters restores the executive default view.

The top navigation contains only HR work: Dashboard, Employees, Projects, Reviews, and Employee changes.

### Interpretation rules

- **Retention watchlist** identifies employees at or below the chosen job-satisfaction threshold. It is a review queue, not an attrition prediction model.
- **High-attention project** means an average active allocation of at least 90%, an average performance rating below 3.2, or average job satisfaction below 2.5.
- **Department attention status** combines attrition with job satisfaction so it remains explainable in a project presentation.

## Local setup

1. Create a MySQL 8+ database and copy `.env.example` to `.env`.
2. Fill in your local database credentials in `.env`. Never commit this file.
3. Create and activate the Python environment, then install packages:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

4. Execute SQL scripts in numeric order from `sql/01_staging_ddl.sql` through `sql/08_analytics_queries.sql`.
5. Generate and load synthetic data, then start Streamlit:

```bash
.venv/bin/python -m synthesizer.run_synthesis
.venv/bin/streamlit run app/main.py
```

## Tests

```bash
.venv/bin/python -m pytest -q
```


