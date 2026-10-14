"""Manager for authentication, user management, and security audit logging."""

import json
import logging
import secrets
import string
from typing import Any, Dict, List, Optional

from src.auth import (
    AUTH_ERROR_MESSAGE,
    DUMMY_HASH,
    LOCKOUT_MINUTES,
    MAX_FAILED_ATTEMPTS,
    check_password,
    hash_password,
    validate_password,
    validate_username,
)
from src.db_manager import DatabaseError, RecordNotFoundError, ValidationError
from src.managers.base_manager import BaseManager

logger = logging.getLogger(__name__)

VALID_ROLES = ("admin", "hr_manager", "project_manager", "analyst")


class AuthManager(BaseManager):
    """Handles user authentication, credentials, guardrails, and audit logging."""

    def _insert_audit(
        self,
        cur: Any,
        event_type: str,
        actor_user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        username_attempted: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal helper to insert an audit record into app_audit_log within an active transaction."""
        details_json = json.dumps(details) if details is not None else None
        cur.execute(
            """
            INSERT INTO app_audit_log (
                event_type, actor_user_id, target_user_id, username_attempted, details, created_at
            ) VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (event_type, actor_user_id, target_user_id, username_attempted, details_json),
        )

    def log_audit(
        self,
        event_type: str,
        actor_user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        username_attempted: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Public method to record an audit event in an independent transaction."""
        try:
            with self.db.transaction() as cur:
                self._insert_audit(
                    cur,
                    event_type=event_type,
                    actor_user_id=actor_user_id,
                    target_user_id=target_user_id,
                    username_attempted=username_attempted,
                    details=details,
                )
        except Exception as exc:
            self.log.error("Failed to write audit log (%s): %s", event_type, exc)

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials with timing equalization and lockout enforcement.

        Returns safe user snapshot dict on success, or None on failure.
        All failure modes display AUTH_ERROR_MESSAGE.
        """
        norm_user = username.strip().lower() if username else ""

        if not norm_user or not password:
            check_password(password or "", DUMMY_HASH)
            self.log_audit("login_failure", username_attempted=norm_user)
            return None

        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT user_id, username, password_hash, role, is_active, must_change_password,
                       failed_attempts, locked_until, NOW() AS db_now
                FROM app_users
                WHERE username = %s
                FOR UPDATE
                """,
                (norm_user,),
            )
            row = cur.fetchone()

            # Unknown account
            if not row:
                check_password(password, DUMMY_HASH)
                self._insert_audit(cur, "login_failure", username_attempted=norm_user)
                return None

            user_id = row["user_id"]

            # Inactive account
            if not row["is_active"]:
                check_password(password, DUMMY_HASH)
                self._insert_audit(
                    cur,
                    "login_failure",
                    actor_user_id=user_id,
                    username_attempted=norm_user,
                    details={"reason": "inactive"},
                )
                return None

            # Locked account check using DB clock
            if row["locked_until"] and row["locked_until"] > row["db_now"]:
                check_password(password, DUMMY_HASH)
                self._insert_audit(
                    cur,
                    "login_failure",
                    actor_user_id=user_id,
                    username_attempted=norm_user,
                    details={"reason": "locked"},
                )
                return None

            # Verify password
            if not check_password(password, row["password_hash"]):
                new_failed = row["failed_attempts"] + 1
                if new_failed >= MAX_FAILED_ATTEMPTS:
                    cur.execute(
                        """
                        UPDATE app_users
                        SET failed_attempts = %s,
                            locked_until = DATE_ADD(NOW(), INTERVAL %s MINUTE)
                        WHERE user_id = %s
                        """,
                        (new_failed, LOCKOUT_MINUTES, user_id),
                    )
                    self._insert_audit(
                        cur,
                        "login_failure",
                        actor_user_id=user_id,
                        username_attempted=norm_user,
                    )
                    self._insert_audit(
                        cur,
                        "account_locked",
                        actor_user_id=user_id,
                        target_user_id=user_id,
                        username_attempted=norm_user,
                    )
                else:
                    cur.execute(
                        "UPDATE app_users SET failed_attempts = %s WHERE user_id = %s",
                        (new_failed, user_id),
                    )
                    self._insert_audit(
                        cur,
                        "login_failure",
                        actor_user_id=user_id,
                        username_attempted=norm_user,
                    )
                return None

            # Successful authentication: reset failed count and lockout, update last_login
            cur.execute(
                """
                UPDATE app_users
                SET failed_attempts = 0,
                    locked_until = NULL,
                    last_login = NOW()
                WHERE user_id = %s
                """,
                (user_id,),
            )
            self._insert_audit(
                cur,
                "login_success",
                actor_user_id=user_id,
                target_user_id=user_id,
                username_attempted=norm_user,
            )

            return {
                "user_id": row["user_id"],
                "username": row["username"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
                "must_change_password": bool(row["must_change_password"]),
            }

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a user by ID without exposing password_hash."""
        row = self.db.fetch_one(
            """
            SELECT user_id, username, role, is_active, must_change_password,
                   created_at, last_login, created_by
            FROM app_users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        if not row:
            return None

        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "must_change_password": bool(row["must_change_password"]),
            "created_at": row["created_at"],
            "last_login": row["last_login"],
            "created_by": row["created_by"],
        }

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieve a user by username without exposing password_hash."""
        norm_user = username.strip().lower() if username else ""
        row = self.db.fetch_one(
            """
            SELECT user_id, username, role, is_active, must_change_password,
                   created_at, last_login, created_by
            FROM app_users
            WHERE username = %s
            """,
            (norm_user,),
        )
        if not row:
            return None

        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "must_change_password": bool(row["must_change_password"]),
            "created_at": row["created_at"],
            "last_login": row["last_login"],
            "created_by": row["created_by"],
        }

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieve all users without password hashes, ordered by creation time."""
        rows = self.db.fetch_all(
            """
            SELECT user_id, username, role, is_active, must_change_password,
                   failed_attempts, locked_until, created_at, last_login, created_by
            FROM app_users
            ORDER BY user_id ASC
            """
        )
        return [
            {
                "user_id": r["user_id"],
                "username": r["username"],
                "role": r["role"],
                "is_active": bool(r["is_active"]),
                "must_change_password": bool(r["must_change_password"]),
                "failed_attempts": r["failed_attempts"],
                "locked_until": r["locked_until"],
                "created_at": r["created_at"],
                "last_login": r["last_login"],
                "created_by": r["created_by"],
            }
            for r in rows
        ]

    # Alias for convenience and backward compatibility with views
    list_users = get_all_users


    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new user with temporary password and must_change_password=1."""
        norm_username = validate_username(username)
        validate_password(password, norm_username)

        if role not in VALID_ROLES:
            raise ValidationError(f"Invalid role '{role}'. Must be one of: {', '.join(VALID_ROLES)}")

        pw_hash = hash_password(password)

        with self.db.transaction() as cur:
            cur.execute("SELECT user_id FROM app_users WHERE username = %s", (norm_username,))
            if cur.fetchone():
                raise ValidationError(f"Username '{norm_username}' already exists.")

            cur.execute(
                """
                INSERT INTO app_users (
                    username, password_hash, role, is_active, must_change_password,
                    failed_attempts, created_by, password_changed_at
                ) VALUES (%s, %s, %s, 1, 1, 0, %s, NOW())
                """,
                (norm_username, pw_hash, role, created_by),
            )
            new_id = cur.lastrowid

            self._insert_audit(
                cur,
                "user_created",
                actor_user_id=created_by,
                target_user_id=new_id,
                username_attempted=norm_username,
                details={"role": role},
            )

            return {
                "user_id": new_id,
                "username": norm_username,
                "role": role,
                "is_active": True,
                "must_change_password": True,
            }

    def _count_active_admins(self, cur: Any) -> int:
        """Count active admins within an active transaction cursor."""
        cur.execute("SELECT COUNT(*) AS n FROM app_users WHERE role = 'admin' AND is_active = 1")
        row = cur.fetchone()
        return int(row["n"]) if row else 0

    def change_role(self, target_user_id: int, new_role: str, actor_user_id: int) -> None:
        """Change a user's role with guardrails against self-demotion and last-admin removal."""
        if target_user_id == actor_user_id:
            raise ValidationError("Admins cannot change their own role.")

        if new_role not in VALID_ROLES:
            raise ValidationError(f"Invalid role '{new_role}'. Must be one of: {', '.join(VALID_ROLES)}")

        with self.db.transaction() as cur:
            cur.execute(
                "SELECT user_id, role, is_active FROM app_users WHERE user_id = %s FOR UPDATE",
                (target_user_id,),
            )
            target = cur.fetchone()
            if not target:
                raise RecordNotFoundError(f"User {target_user_id} not found.")

            old_role = target["role"]
            if old_role == "admin" and new_role != "admin" and target["is_active"]:
                if self._count_active_admins(cur) <= 1:
                    raise ValidationError("Cannot demote the last active admin.")

            cur.execute(
                "UPDATE app_users SET role = %s WHERE user_id = %s",
                (new_role, target_user_id),
            )
            self._insert_audit(
                cur,
                "role_changed",
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                details={"old_role": old_role, "new_role": new_role},
            )

    def deactivate_user(self, target_user_id: int, actor_user_id: int) -> None:
        """Deactivate a user with guardrails against self-deactivation and last-admin deactivation."""
        if target_user_id == actor_user_id:
            raise ValidationError("Admins cannot deactivate their own account.")

        with self.db.transaction() as cur:
            cur.execute(
                "SELECT user_id, role, is_active FROM app_users WHERE user_id = %s FOR UPDATE",
                (target_user_id,),
            )
            target = cur.fetchone()
            if not target:
                raise RecordNotFoundError(f"User {target_user_id} not found.")

            if target["role"] == "admin" and target["is_active"]:
                if self._count_active_admins(cur) <= 1:
                    raise ValidationError("Cannot deactivate the last active admin.")

            cur.execute("UPDATE app_users SET is_active = 0 WHERE user_id = %s", (target_user_id,))
            self._insert_audit(
                cur,
                "user_deactivated",
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
            )

    def activate_user(self, target_user_id: int, actor_user_id: int) -> None:
        """Activate a previously deactivated user."""
        with self.db.transaction() as cur:
            cur.execute("SELECT user_id FROM app_users WHERE user_id = %s FOR UPDATE", (target_user_id,))
            if not cur.fetchone():
                raise RecordNotFoundError(f"User {target_user_id} not found.")

            cur.execute("UPDATE app_users SET is_active = 1 WHERE user_id = %s", (target_user_id,))
            self._insert_audit(
                cur,
                "user_activated",
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
            )

    def reset_password(
        self,
        target_user_id: int,
        actor_user_id: int,
        temp_password: Optional[str] = None,
    ) -> str:
        """Reset a user's password to a temporary password, forcing change on next login."""
        with self.db.transaction() as cur:
            cur.execute(
                "SELECT user_id, username FROM app_users WHERE user_id = %s FOR UPDATE",
                (target_user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise RecordNotFoundError(f"User {target_user_id} not found.")

            username = row["username"]

            if not temp_password:
                # Generate a compliant temporary password: 16 chars with upper, lower, digits, symbols
                chars = string.ascii_letters + string.digits + "!@#$%^&*"
                # Ensure at least one upper, lower, digit
                temp_password = (
                    secrets.choice(string.ascii_uppercase)
                    + secrets.choice(string.ascii_lowercase)
                    + secrets.choice(string.digits)
                    + secrets.choice("!@#$%^&*")
                    + "".join(secrets.choice(chars) for _ in range(12))
                )

            validate_password(temp_password, username)
            pw_hash = hash_password(temp_password)

            cur.execute(
                """
                UPDATE app_users
                SET password_hash = %s,
                    must_change_password = 1,
                    failed_attempts = 0,
                    locked_until = NULL,
                    password_changed_at = NOW()
                WHERE user_id = %s
                """,
                (pw_hash, target_user_id),
            )
            self._insert_audit(
                cur,
                "password_reset",
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
            )

            return temp_password

    def change_own_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change user's own password, clearing must_change_password on success."""
        with self.db.transaction() as cur:
            cur.execute(
                "SELECT user_id, username, password_hash FROM app_users WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise RecordNotFoundError(f"User {user_id} not found.")

            if not check_password(current_password, row["password_hash"]):
                raise ValidationError("Current password is incorrect.")

            validate_password(new_password, row["username"])
            pw_hash = hash_password(new_password)

            cur.execute(
                """
                UPDATE app_users
                SET password_hash = %s,
                    must_change_password = 0,
                    password_changed_at = NOW()
                WHERE user_id = %s
                """,
                (pw_hash, user_id),
            )
            self._insert_audit(
                cur,
                "password_changed",
                actor_user_id=user_id,
                target_user_id=user_id,
            )

    def get_audit_log(
        self,
        limit: int = 200,
        event_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent audit events, optionally filtered by event_type."""
        if event_type_filter and event_type_filter.lower() != "all":
            query = """
                SELECT audit_id, event_type, actor_user_id, target_user_id,
                       username_attempted, details, created_at
                FROM app_audit_log
                WHERE event_type = %s
                ORDER BY created_at DESC, audit_id DESC
                LIMIT %s
            """
            rows = self.db.fetch_all(query, (event_type_filter, limit))
        else:
            query = """
                SELECT audit_id, event_type, actor_user_id, target_user_id,
                       username_attempted, details, created_at
                FROM app_audit_log
                ORDER BY created_at DESC, audit_id DESC
                LIMIT %s
            """
            rows = self.db.fetch_all(query, (limit,))

        # Parse JSON details if returned as string
        for r in rows:
            if isinstance(r.get("details"), str):
                try:
                    r["details"] = json.loads(r["details"])
                except Exception:
                    pass
        return rows
