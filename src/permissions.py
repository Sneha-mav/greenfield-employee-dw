"""Role-Based Access Control (RBAC) Permissions Definition.

Single source of truth for all application roles and permission mappings.
Application code checks permissions, never role names.
"""

from typing import Dict, FrozenSet

# Complete set of 18 permission keys
ALL_PERMISSIONS: FrozenSet[str] = frozenset({
    "dashboard.view",
    "dashboard.watchlist",
    "dashboard.export",
    "employee.search",
    "employee.history.view",
    "salary.view",
    "employee.onboard",
    "employee.transfer",
    "employee.update_role",
    "project.view",
    "project.create",
    "assignment.view",
    "assignment.create",
    "review.view",
    "review.submit",
    "account.password",
    "user.manage",
    "audit.view",
})

# Base read permissions shared across roles
READ_ALL: FrozenSet[str] = frozenset({
    "dashboard.view",
    "employee.search",
    "employee.history.view",
    "project.view",
    "assignment.view",
    "review.view",
    "account.password",
})

# Role -> FrozenSet of permissions
ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "admin": ALL_PERMISSIONS,
    "hr_manager": frozenset(
        READ_ALL | {
            "dashboard.watchlist",
            "dashboard.export",
            "salary.view",
            "employee.onboard",
            "employee.transfer",
            "employee.update_role",
        }
    ),
    "project_manager": frozenset(
        READ_ALL | {
            "project.create",
            "assignment.create",
            "review.submit",
        }
    ),
    "analyst": READ_ALL,
}


def has_permission(role: str, permission: str) -> bool:
    """Check if the given role possesses the specified permission key."""
    if not role or not permission:
        return False
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
