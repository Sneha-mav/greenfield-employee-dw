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

## Security & Role-Based Access Control (RBAC)

The application enforces a multi-layered Role-Based Access Control (RBAC) system:

1. **Authentication & Session Gate (`app/main.py`):** Unauthenticated sessions are restricted strictly to `0_Login.py`. Authenticated users have their snapshot rebuilt from the database on every rerun. Sessions enforce a 30-minute idle timeout and an 8-hour absolute timeout. If `must_change_password = 1`, navigation is constrained to `7_Account.py`.
2. **Dynamic UI Filtering:** Views dynamically build tab lists based on fine-grained permissions so unauthorized write interfaces are never rendered.
3. **Manager Method Guards:** Core write operations are decorated with `@requires_permission(...)`, raising `PermissionDenied` and recording `access_denied` audit logs if violated.
4. **Data Privacy & Salary Masking:** Individual compensation details (`monthly_income`, `salary_hike_pct`) are masked with `"Restricted"` for unauthorized roles (`analyst`, `project_manager`). Gantt timeline visualization is gated via `can_show_gantt()`.

---

### Database Setup & Auth Migration

1. Run the existing DDL and data generation scripts (`sql/01_staging_ddl.sql` through `sql/08_analytics_queries.sql`).
2. Run the idempotent authentication and audit schema:

```bash
mysql -u root -p employee_dw < sql/09_auth_ddl.sql
```

This creates:
- `app_users`: User credentials, bcrypt cost-12 hashes, lockout counters (`failed_attempts`, `locked_until`), and status flags.
- `app_audit_log`: Security audit trail capturing logins, failures, lockouts, password resets, role changes, deactivations, and permission denials.

---

### Seeding Initial Administrator

`sql/09_auth_ddl.sql` automatically includes an idempotent seed for the initial administrator (`admin` / `AdminPass1234!`), meaning **no extra scripts are required on fresh or cloud database setups**.

Alternatively, you can run or reset admin credentials via the Python script:

```bash
# Interactive prompt (prompts securely for password via getpass):
python scripts/create_admin.py

# Or non-interactive via environment variables:
INITIAL_ADMIN_USERNAME=admin INITIAL_ADMIN_PASSWORD=AdminSecurePassword123! python scripts/create_admin.py

# Operator lockout recovery / password reset:
python scripts/create_admin.py --reset-password admin
```

The script is idempotent: it exits without changes if an active administrator already exists. Newly created users have `must_change_password = 1` and must set a new password on their first login.


---

### Roles & Permissions Matrix

The system defines 18 permissions across 4 application roles:

| Permission Key | admin | hr_manager | project_manager | analyst | Scope / Purpose |
|:---|:---:|:---:|:---:|:---:|:---|
| `account.password` | YES | YES | YES | YES | Change own account password |
| `assignment.create` | YES | — | YES | — | Assign employee to project |
| `assignment.view` | YES | YES | YES | YES | View project assignments |
| `audit.view` | YES | — | — | — | Access read-only security audit log |
| `dashboard.export` | YES | YES | — | — | Download retention review queue CSV |
| `dashboard.view` | YES | YES | YES | YES | View executive analytics dashboard |
| `dashboard.watchlist` | YES | YES | — | — | View retention review queue table & count |
| `employee.history.view` | YES | YES | YES | YES | View employee SCD Type 2 history |
| `employee.onboard` | YES | YES | — | — | Onboard new employee into OLTP & DW |
| `employee.search` | YES | YES | YES | YES | Search employees by ID or name |
| `employee.transfer` | YES | YES | — | — | Execute department transfer (SCD2) |
| `employee.update_role` | YES | YES | — | — | Change role, level, or compensation |
| `project.create` | YES | — | YES | — | Create new project |
| `project.view` | YES | YES | YES | YES | View project details |
| `review.submit` | YES | — | YES | — | Submit employee performance review |
| `review.view` | YES | YES | YES | YES | View employee performance reviews |
| `salary.view` | YES | YES | — | — | View unmasked salary and hike percentages |
| `user.manage` | YES | — | — | — | Access admin console (users, roles, resets) |

---

### Running Tests

Execute the automated test suite covering unit tests, RBAC decorators, timing equalization, fail-closed guards, and view rendering via Streamlit `AppTest`:

```bash
# Run complete test suite:
.venv/bin/python -m pytest tests/ -v

# Run specific RBAC & view-level tests:
.venv/bin/python -m pytest tests/test_permissions.py tests/test_auth_manager.py tests/test_main_auth_gate.py tests/test_phase4_phase5.py -v
```

---

### Running the Application

```bash
.venv/bin/streamlit run app/main.py
```

---

## Acceptance Checklist (Mapped to Spec)

| Requirement / Spec Item | Status | Verification Detail |
|---|:---:|---|
| **Unauthenticated gate** | Passed | Unauthenticated users only see Login page (`0_Login.py`); protected pages hidden. |
| **Uniform auth error message** | Passed | All authentication failures (unknown user, bad password, inactive, locked) display identical generic message with constant dummy hash timing equalization. |
| **Account lockout** | Passed | 5 consecutive bad passwords lock account for 15 minutes based on DB clock (`locked_until = DATE_ADD(NOW(), INTERVAL 15 MINUTE)`). |
| **Fail-closed session state** | Passed | User snapshot rebuilt from DB by PK on every run; missing/inactive user or DB connection error clears session and stops execution. |
| **Idle & absolute timeouts** | Passed | 30-min idle timeout and 8-hour absolute timeout return user to Login with `_auth_expired` notice and log `session_expired` audit event. |
| **Forced password change** | Passed | `must_change_password = 1` confines navigation to Account page until updated. |
| **Admin safety guardrails** | Passed | AuthManager prevents admin self-demotion, self-deactivation, and demoting/deactivating the last active admin. |
| **Role tab filtering** | Passed | `analyst` sees no write tabs; `project_manager` sees Create/Assign/Submit tabs; `hr_manager` sees HR tabs and salary, but no project/review write tabs. |
| **Salary data masking** | Passed | `monthly_income` and `salary_hike_pct` masked with `"Restricted"` on copies after `@st.cache_data` boundary for `analyst` and `project_manager`. |
| **Gantt timeline safety** | Passed | `can_show_gantt()` hides timeline chart and renders informational note when user lacks `salary.view`. |
| **Watchlist & CSV export gating** | Passed | Retention review queue table requires `dashboard.watchlist`; CSV export button requires `dashboard.export`. |
| **Manager write decorators** | Passed | 6 manager write methods decorated with `@requires_permission`; unauthorized calls raise `PermissionDenied` and log `access_denied`. |
| **Views catch `PermissionDenied`** | Passed | Views 1–4 catch `PermissionDenied` explicitly and show `st.error()` without crashing. |
| **Idempotent admin seed** | Passed | `scripts/create_admin.py` safely checks existing admin presence; supports `--reset-password` recovery. |
| **Preservation of existing flows** | Passed | Permitted roles successfully execute onboard, transfer, role change, project creation, assignment, and reviews. |



