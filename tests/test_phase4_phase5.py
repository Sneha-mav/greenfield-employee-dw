"""Tests for Phase 4 and Phase 5 RBAC requirements.

Verifies:
1. Manager write methods decorated with @requires_permission (all 6 methods)
   - Fail closed when unauthorized
   - Raise PermissionDenied
   - Allow execution when authorized
2. Every view-level salary spot is masked for analyst and project_manager roles:
   - has_permission("salary.view") is False
   - can_show_gantt() is False
   - View 1: salary metric and table column
   - View 3: salary_hike_pct in review history
   - View 4: monthly_income in SCD2 history and Gantt suppression
   - View 5: monthly_income in employee history, Gantt suppression, salary band protection, watchlist/CSV gating
3. Admin page (6_Admin.py) guard require_permission("user.manage")
"""

from datetime import date
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.auth import (
    PermissionDenied,
    can_show_gantt,
    has_permission,
    mask_columns,
    override_user,
)
from src.entities.employee import Employee
from src.entities.project import Project
from src.entities.review import Review
from src.managers.employee_manager import EmployeeManager
from src.managers.project_manager import ProjectManager
from src.managers.review_manager import ReviewManager


# ==============================================================================
# 1. Manager Write Methods RBAC Tests (Six Decorated Methods)
# ==============================================================================

@pytest.mark.parametrize("role", ["analyst"])
def test_manager_write_methods_denied_for_analyst(role):
    """Analyst has none of the write permissions; all six manager writes must raise PermissionDenied."""
    user = {"user_id": 100, "username": "analyst1", "role": role, "is_active": True}

    with override_user(user):
        em = EmployeeManager()
        pm = ProjectManager()
        rm = ReviewManager()

        # 1. EmployeeManager.create (requires employee.onboard)
        with pytest.raises(PermissionDenied, match="employee.onboard"):
            em.create(MagicMock(spec=Employee))

        # 2. EmployeeManager.update_department (requires employee.transfer)
        with pytest.raises(PermissionDenied, match="employee.transfer"):
            em.update_department(1, "Engineering", date(2024, 1, 1))

        # 3. EmployeeManager.change_role_or_salary (requires employee.update_role)
        with pytest.raises(PermissionDenied, match="employee.update_role"):
            em.change_role_or_salary(1, date(2024, 1, 1), job_level=3)

        # 4. ProjectManager.create (requires project.create)
        with pytest.raises(PermissionDenied, match="project.create"):
            pm.create(MagicMock(spec=Project))

        # 5. ProjectManager.assign_employee (requires assignment.create)
        with pytest.raises(PermissionDenied, match="assignment.create"):
            pm.assign_employee(1, 1, "Developer", 50, date(2024, 1, 1))

        # 6. ReviewManager.create (requires review.submit)
        with pytest.raises(PermissionDenied, match="review.submit"):
            rm.create(MagicMock(spec=Review))


def test_project_manager_allowed_only_pm_methods():
    """Project manager can create projects, assign employees, submit reviews, but NOT onboard or transfer."""
    user = {"user_id": 101, "username": "pm1", "role": "project_manager", "is_active": True}

    with override_user(user):
        em = EmployeeManager()
        pm = ProjectManager()
        rm = ReviewManager()

        # Forbidden for project_manager:
        with pytest.raises(PermissionDenied, match="employee.onboard"):
            em.create(MagicMock(spec=Employee))

        with pytest.raises(PermissionDenied, match="employee.transfer"):
            em.update_department(1, "Engineering", date(2024, 1, 1))

        with pytest.raises(PermissionDenied, match="employee.update_role"):
            em.change_role_or_salary(1, date(2024, 1, 1), job_level=3)

        # Allowed for project_manager (permission check passes; underlying call may fail on mock DB):
        with patch.object(ProjectManager, "create", wraps=pm.create) as mock_p_create, \
             patch.object(ProjectManager, "assign_employee", wraps=pm.assign_employee) as mock_p_assign, \
             patch.object(ReviewManager, "create", wraps=rm.create) as mock_r_create:

            # They don't raise PermissionDenied:
            try:
                pm.create(MagicMock(spec=Project))
            except PermissionDenied:
                pytest.fail("ProjectManager.create should not raise PermissionDenied for project_manager")
            except Exception:
                pass  # DB error or validation is fine

            try:
                pm.assign_employee(1, 1, "Developer", 50, date(2024, 1, 1))
            except PermissionDenied:
                pytest.fail("ProjectManager.assign_employee should not raise PermissionDenied for project_manager")
            except Exception:
                pass

            try:
                rm.create(MagicMock(spec=Review))
            except PermissionDenied:
                pytest.fail("ReviewManager.create should not raise PermissionDenied for project_manager")
            except Exception:
                pass


def test_admin_allowed_all_six_methods():
    """Admin has all permissions; none of the six manager methods raise PermissionDenied."""
    user = {"user_id": 1, "username": "admin", "role": "admin", "is_active": True}

    with override_user(user):
        em = EmployeeManager()
        pm = ProjectManager()
        rm = ReviewManager()

        methods = [
            lambda: em.create(MagicMock(spec=Employee)),
            lambda: em.update_department(1, "Eng", date(2024, 1, 1)),
            lambda: em.change_role_or_salary(1, date(2024, 1, 1), job_level=3),
            lambda: pm.create(MagicMock(spec=Project)),
            lambda: pm.assign_employee(1, 1, "Dev", 50, date(2024, 1, 1)),
            lambda: rm.create(MagicMock(spec=Review)),
        ]

        for method in methods:
            try:
                method()
            except PermissionDenied as exc:
                pytest.fail(f"Admin must not be denied: {exc}")
            except Exception:
                pass  # Underlying mock DB error is expected


# ==============================================================================
# 2. View-Level Salary Masking Tests for analyst and project_manager
# ==============================================================================

@pytest.mark.parametrize("role", ["analyst", "project_manager"])
def test_salary_permission_and_gantt_denied_for_non_salary_roles(role):
    """salary.view and can_show_gantt() must be False for analyst and project_manager."""
    user = {"user_id": 200, "username": "user", "role": role, "is_active": True}
    with override_user(user):
        assert has_permission("salary.view") is False
        assert can_show_gantt() is False


@pytest.mark.parametrize("role", ["admin", "hr_manager"])
def test_salary_permission_and_gantt_allowed_for_salary_roles(role):
    """salary.view and can_show_gantt() must be True for admin and hr_manager."""
    user = {"user_id": 201, "username": "hr_or_admin", "role": role, "is_active": True}
    with override_user(user):
        assert has_permission("salary.view") is True
        assert can_show_gantt() is True


@pytest.mark.parametrize("role", ["analyst", "project_manager"])
def test_view1_salary_spots_masked_for_non_salary_roles(role):
    """View 1: Employee ID metric and Name search table mask monthly income."""
    user = {"user_id": 200, "username": "user", "role": role, "is_active": True}
    with override_user(user):
        # Spot 1: Search by ID metric format check
        monthly_income = 7500.0
        income_str = f"${monthly_income:,.0f}" if has_permission("salary.view") else "Restricted"
        assert income_str == "Restricted"

        # Spot 2: Search by Name table check
        raw_df = pd.DataFrame([
            {"ID": 1, "Name": "Alice", "Monthly Income": "$7,500"},
            {"ID": 2, "Name": "Bob", "Monthly Income": "$8,200"},
        ])
        masked_df = mask_columns(raw_df, ["Monthly Income"])
        assert list(masked_df["Monthly Income"]) == ["Restricted", "Restricted"]
        # Ensure raw_df was not mutated
        assert list(raw_df["Monthly Income"]) == ["$7,500", "$8,200"]


@pytest.mark.parametrize("role", ["analyst", "project_manager"])
def test_view3_salary_spots_masked_for_non_salary_roles(role):
    """View 3: salary_hike_pct is masked for analyst and project_manager."""
    user = {"user_id": 200, "username": "user", "role": role, "is_active": True}
    with override_user(user):
        reviews_df = pd.DataFrame([
            {"review_id": 1, "performance_rating": 4, "salary_hike_pct": 12.5},
            {"review_id": 2, "performance_rating": 5, "salary_hike_pct": 15.0},
        ])
        masked = mask_columns(reviews_df.copy(), ["salary_hike_pct"])
        assert list(masked["salary_hike_pct"]) == ["Restricted", "Restricted"]
        assert list(reviews_df["salary_hike_pct"]) == [12.5, 15.0]


@pytest.mark.parametrize("role", ["analyst", "project_manager"])
def test_view4_salary_spots_masked_for_non_salary_roles(role):
    """View 4: monthly_income in SCD2 history is masked and Gantt is suppressed."""
    user = {"user_id": 200, "username": "user", "role": role, "is_active": True}
    with override_user(user):
        scd2_df = pd.DataFrame([
            {"version_num": 1, "department_name": "Sales", "monthly_income": 6000},
            {"version_num": 2, "department_name": "Marketing", "monthly_income": 7200},
        ])
        masked = mask_columns(scd2_df.copy(), ["monthly_income"])
        assert list(masked["monthly_income"]) == ["Restricted", "Restricted"]
        assert can_show_gantt() is False


@pytest.mark.parametrize("role", ["analyst", "project_manager"])
def test_view5_salary_and_watchlist_gating_for_non_salary_roles(role):
    """View 5: Dashboard employee history masks monthly_income, Gantt is hidden, watchlist and CSV export are gated."""
    user = {"user_id": 200, "username": "user", "role": role, "is_active": True}
    with override_user(user):
        # Salary spot in employee history
        history_df = pd.DataFrame([
            {"full_name": "Charlie", "monthly_income": 9500},
        ])
        masked = mask_columns(history_df.copy(), ["monthly_income"])
        assert list(masked["monthly_income"]) == ["Restricted"]
        assert can_show_gantt() is False

        # Watchlist and export permissions
        assert has_permission("dashboard.watchlist") is False
        assert has_permission("dashboard.export") is False


# ==============================================================================
# 3. View 6 (Admin) Guard Tests
# ==============================================================================

def test_admin_page_guard_denies_unauthorized_roles():
    """6_Admin.py require_permission('user.manage') stops execution for non-admins."""
    with patch("src.managers.auth_manager.AuthManager.log_audit"):
        # For analyst
        with override_user({"user_id": 300, "username": "analyst", "role": "analyst", "is_active": True}):
            at = AppTest.from_file("app/views/6_Admin.py")
            at.run()
            assert "You do not have permission to access this page." in at.error[0].value

        # For hr_manager
        with override_user({"user_id": 301, "username": "hr", "role": "hr_manager", "is_active": True}):
            at = AppTest.from_file("app/views/6_Admin.py")
            at.run()
            assert "You do not have permission to access this page." in at.error[0].value

        # For project_manager
        with override_user({"user_id": 302, "username": "pm", "role": "project_manager", "is_active": True}):
            at = AppTest.from_file("app/views/6_Admin.py")
            at.run()
            assert "You do not have permission to access this page." in at.error[0].value


# ==============================================================================
# 4. Real View AppTest Tests (Views 1, 3, 4, 5) for analyst and project_manager
# ==============================================================================

@pytest.mark.parametrize("role", ["analyst", "project_manager"])
def test_view1_apptest_tabs_for_non_onboard_roles(role):
    """View 1: analyst and project_manager see ONLY Search tab, no write Onboard tab."""
    user = {"user_id": 400, "username": "user", "role": role, "is_active": True}
    with patch("src.managers.analytics_manager.AnalyticsManager.list_departments", return_value=[{"department_id": 1, "department_name": "Sales"}]), \
         patch("src.managers.analytics_manager.AnalyticsManager.list_job_roles", return_value=[{"job_role_id": 1, "job_role_name": "Rep"}]):
        at = AppTest.from_file("app/views/1_Onboard_Employee.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert [t.label for t in at.tabs] == ["Search Employee"]


def test_view1_apptest_tabs_for_admin():
    """View 1: admin sees both Onboard and Search tabs."""
    user = {"user_id": 1, "username": "admin", "role": "admin", "is_active": True}
    with patch("src.managers.analytics_manager.AnalyticsManager.list_departments", return_value=[{"department_id": 1, "department_name": "Sales"}]), \
         patch("src.managers.analytics_manager.AnalyticsManager.list_job_roles", return_value=[{"job_role_id": 1, "job_role_name": "Rep"}]):
        at = AppTest.from_file("app/views/1_Onboard_Employee.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert [t.label for t in at.tabs] == ["Onboard Employee", "Search Employee"]


def test_view3_apptest_tabs_for_analyst():
    """View 3: analyst sees ONLY Review History tab, no Submit Review tab."""
    user = {"user_id": 401, "username": "analyst1", "role": "analyst", "is_active": True}
    with patch("src.managers.project_manager.ProjectManager.list_projects", return_value=[]):
        at = AppTest.from_file("app/views/3_Reviews.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert [t.label for t in at.tabs] == ["Review History"]


def test_view3_apptest_tabs_for_project_manager():
    """View 3: project_manager sees both Submit Review and Review History tabs."""
    user = {"user_id": 402, "username": "pm1", "role": "project_manager", "is_active": True}
    with patch("src.managers.project_manager.ProjectManager.list_projects", return_value=[]):
        at = AppTest.from_file("app/views/3_Reviews.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert [t.label for t in at.tabs] == ["Submit Review", "Review History"]


@pytest.mark.parametrize("role", ["analyst", "project_manager"])
def test_view4_apptest_tabs_for_non_hr_roles(role):
    """View 4: analyst and project_manager see ONLY History tab, no Transfer or Role change tabs."""
    user = {"user_id": 403, "username": "user", "role": role, "is_active": True}
    with patch("src.managers.analytics_manager.AnalyticsManager.list_departments", return_value=[{"department_id": 1, "department_name": "Sales"}]), \
         patch("src.managers.analytics_manager.AnalyticsManager.list_job_roles", return_value=[{"job_role_id": 1, "job_role_name": "Rep"}]):
        at = AppTest.from_file("app/views/4_Update_Department.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert [t.label for t in at.tabs] == ["History"]


def test_view4_apptest_tabs_for_admin():
    """View 4: admin sees all three tabs."""
    user = {"user_id": 1, "username": "admin", "role": "admin", "is_active": True}
    with patch("src.managers.analytics_manager.AnalyticsManager.list_departments", return_value=[{"department_id": 1, "department_name": "Sales"}]), \
         patch("src.managers.analytics_manager.AnalyticsManager.list_job_roles", return_value=[{"job_role_id": 1, "job_role_name": "Rep"}]):
        at = AppTest.from_file("app/views/4_Update_Department.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert [t.label for t in at.tabs] == ["Department Transfer", "Role / Level / Salary", "History"]


@pytest.mark.parametrize("role", ["analyst", "project_manager"])
def test_view5_apptest_gating_for_non_hr_roles(role):
    """View 5: Dashboard marks retention flags as Restricted and hides watchlist queue for analyst/PM."""
    user = {"user_id": 404, "username": "user", "role": role, "is_active": True}
    with patch("src.managers.analytics_manager.AnalyticsManager.rating_trend_by_year", return_value=[]), \
         patch("src.managers.analytics_manager.AnalyticsManager.attrition_by_department", return_value=[]), \
         patch("src.managers.analytics_manager.AnalyticsManager.top_performers_per_department", return_value=[]), \
         patch("src.managers.analytics_manager.AnalyticsManager.at_risk_watchlist", return_value=[{"employee_id": 1}]), \
         patch("src.managers.analytics_manager.AnalyticsManager.project_health", return_value=[]), \
         patch("src.managers.analytics_manager.AnalyticsManager.attrition_by_hire_cohort", return_value=[]), \
         patch("src.managers.analytics_manager.AnalyticsManager.salary_band_attrition", return_value=[]):
        at = AppTest.from_file("app/views/5_Analytics_Dashboard.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        # Tab list matches all 4 sections
        assert [t.label for t in at.tabs] == ["Overview", "Workforce", "Project health", "Employee history"]
        # Retention flags metric is Restricted
        assert any("Restricted" in str(m.value) for m in at.metric)
        # Watchlist expander shows unauthorized notice
        assert any("You do not have permission to view the retention review queue." in str(i.value) for i in at.info)


def test_view7_account_apptest():
    """View 7: Account page renders username, role, and change password form."""
    user = {"user_id": 1, "username": "admin", "role": "admin", "is_active": True, "must_change_password": True}
    at = AppTest.from_file("app/views/7_Account.py")
    at.session_state["_current_user"] = user
    at.run(timeout=10)
    assert not at.exception
    assert any("You must change your password before continuing." in str(w.value) for w in at.warning)


def test_view6_admin_apptest():
    """View 6: Admin page renders Users and Audit Log tabs for admin."""
    user = {"user_id": 1, "username": "admin", "role": "admin", "is_active": True}
    with patch("src.managers.auth_manager.AuthManager.get_all_users", return_value=[user]), \
         patch("src.managers.auth_manager.AuthManager.get_audit_log", return_value=[]):
        at = AppTest.from_file("app/views/6_Admin.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert not at.exception
        assert [t.label for t in at.tabs] == ["Users", "Audit log"]


def test_view2_projects_apptest_analyst():
    """View 2: analyst sees only View Assignments and Search Assignment tabs."""
    user = {"user_id": 401, "username": "analyst1", "role": "analyst", "is_active": True}
    with patch("src.managers.analytics_manager.AnalyticsManager.list_departments", return_value=[]), \
         patch("src.managers.project_manager.ProjectManager.list_projects", return_value=[]):
        at = AppTest.from_file("app/views/2_Projects.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert not at.exception
        assert [t.label for t in at.tabs] == ["View Assignments", "Search Assignment"]


def test_view2_projects_apptest_admin():
    """View 2: admin sees Create Project, Assign Employee, View Assignments, and Search Assignment tabs."""
    user = {"user_id": 1, "username": "admin", "role": "admin", "is_active": True}
    with patch("src.managers.analytics_manager.AnalyticsManager.list_departments", return_value=[]), \
         patch("src.managers.project_manager.ProjectManager.list_projects", return_value=[]):
        at = AppTest.from_file("app/views/2_Projects.py")
        at.session_state["_current_user"] = user
        at.run(timeout=10)
        assert not at.exception
        assert [t.label for t in at.tabs] == ["Create Project", "Assign Employee", "View Assignments", "Search Assignment"]


def test_view0_login_apptest():
    """View 0: Login page renders centered card with username/password inputs and submit button."""
    at = AppTest.from_file("app/views/0_Login.py")
    at.run(timeout=10)
    assert not at.exception
    # Verify inputs are present
    assert any("Username" in str(inp.label) for inp in at.text_input)
    assert any("Password" in str(inp.label) for inp in at.text_input)
    assert any("Sign In" in str(btn.label) for btn in at.button)






