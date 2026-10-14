"""Unit tests for RBAC permissions module (src/permissions.py).

Tests verify that roles, permissions, and guardrail invariants (such as
employee.update_role implying salary.view) are strictly enforced.
"""

import pytest

from src.permissions import (
    ALL_PERMISSIONS,
    READ_ALL,
    ROLE_PERMISSIONS,
    has_permission,
)


def test_permission_keys_count():
    """Verify that there are exactly 18 permission keys, matching the RBAC specification."""
    assert len(ALL_PERMISSIONS) == 18, f"Expected 18 permission keys, got {len(ALL_PERMISSIONS)}"


def test_role_permissions_structure():
    """Verify that ROLE_PERMISSIONS maps valid roles to frozensets."""
    expected_roles = {"admin", "hr_manager", "project_manager", "analyst"}
    assert set(ROLE_PERMISSIONS.keys()) == expected_roles

    for role, perms in ROLE_PERMISSIONS.items():
        assert isinstance(perms, frozenset), f"Role '{role}' permissions must be a frozenset"
        # No permission outside ALL_PERMISSIONS can be present
        assert perms.issubset(ALL_PERMISSIONS), f"Role '{role}' contains unknown permissions"


def test_admin_has_every_permission():
    """Verify that admin role possesses all 18 permissions."""
    assert ROLE_PERMISSIONS["admin"] == ALL_PERMISSIONS
    for perm in ALL_PERMISSIONS:
        assert has_permission("admin", perm) is True


def test_analyst_has_read_all_only():
    """Verify that analyst possesses exactly READ_ALL permissions and no write permissions."""
    assert ROLE_PERMISSIONS["analyst"] == READ_ALL
    assert len(READ_ALL) == 7

    # Can read
    assert has_permission("analyst", "dashboard.view") is True
    assert has_permission("analyst", "employee.search") is True
    assert has_permission("analyst", "employee.history.view") is True

    # Cannot write or see salary/watchlist
    assert has_permission("analyst", "salary.view") is False
    assert has_permission("analyst", "dashboard.watchlist") is False
    assert has_permission("analyst", "dashboard.export") is False
    assert has_permission("analyst", "employee.onboard") is False
    assert has_permission("analyst", "project.create") is False
    assert has_permission("analyst", "user.manage") is False


def test_hr_manager_permissions():
    """Verify hr_manager permissions."""
    hr_perms = ROLE_PERMISSIONS["hr_manager"]
    assert hr_perms.issuperset(READ_ALL)
    assert "salary.view" in hr_perms
    assert "employee.onboard" in hr_perms
    assert "employee.transfer" in hr_perms
    assert "employee.update_role" in hr_perms
    assert "dashboard.watchlist" in hr_perms
    assert "dashboard.export" in hr_perms

    # Does NOT have project write or review submit or user manage
    assert "project.create" not in hr_perms
    assert "assignment.create" not in hr_perms
    assert "review.submit" not in hr_perms
    assert "user.manage" not in hr_perms


def test_project_manager_permissions():
    """Verify project_manager permissions."""
    pm_perms = ROLE_PERMISSIONS["project_manager"]
    assert pm_perms.issuperset(READ_ALL)
    assert "project.create" in pm_perms
    assert "assignment.create" in pm_perms
    assert "review.submit" in pm_perms

    # Does NOT have salary view or employee write or user manage
    assert "salary.view" not in pm_perms
    assert "employee.onboard" not in pm_perms
    assert "employee.transfer" not in pm_perms
    assert "employee.update_role" not in pm_perms
    assert "user.manage" not in pm_perms


def test_update_role_implies_salary_view_for_every_role():
    """Invariant check: any role with employee.update_role MUST also have salary.view.

    Checked across ALL configured roles to prevent privilege misconfigurations.
    """
    for role, perms in ROLE_PERMISSIONS.items():
        if "employee.update_role" in perms:
            assert "salary.view" in perms, (
                f"Role '{role}' has 'employee.update_role' but lacks 'salary.view'. "
                "Users cannot update salary without permission to view it."
            )


def test_has_permission_function():
    """Test helper function edge cases."""
    assert has_permission("", "dashboard.view") is False
    assert has_permission("admin", "") is False
    assert has_permission("unknown_role", "dashboard.view") is False
    assert has_permission("analyst", "nonexistent.permission") is False
