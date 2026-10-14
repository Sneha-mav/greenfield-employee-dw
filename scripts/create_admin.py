"""Idempotent admin seeding and lockout recovery.

Usage:
    python scripts/create_admin.py                   # Interactive: prompts for username and password
    python scripts/create_admin.py --reset-password USERNAME  # Reset password for locked out user

Environment variables (optional, overrides interactive prompt):
    INITIAL_ADMIN_USERNAME
    INITIAL_ADMIN_PASSWORD
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.auth import hash_password, validate_password, validate_username
from src.db_manager import DatabaseConnection


def _has_any_admin(db: DatabaseConnection) -> bool:
    """Return True if at least one admin row exists in app_users."""
    row = db.fetch_one("SELECT COUNT(*) AS n FROM app_users WHERE role = 'admin'")
    return row is not None and int(row["n"]) > 0


def create_admin() -> None:
    """Create the initial admin user if none exists. Idempotent."""
    db = DatabaseConnection()

    if _has_any_admin(db):
        print("An admin user already exists. Skipping creation.")
        return

    # Read credentials from environment or interactive prompt
    username = os.environ.get("INITIAL_ADMIN_USERNAME", "").strip()
    password = os.environ.get("INITIAL_ADMIN_PASSWORD", "").strip()

    if not username:
        username = input("Admin username: ").strip()
    if not password:
        password = getpass.getpass("Admin password (min 12 chars, upper+lower+digit): ")

    # Validate
    username = validate_username(username)
    validate_password(password, username)

    pw_hash = hash_password(password)

    with db.transaction() as cur:
        # Double-check inside the transaction
        cur.execute("SELECT COUNT(*) AS n FROM app_users WHERE role = 'admin'")
        if int(cur.fetchone()["n"]) > 0:
            print("An admin user already exists (concurrent creation). Skipping.")
            return

        cur.execute(
            """
            INSERT INTO app_users (
                username, password_hash, role, is_active, must_change_password,
                failed_attempts, password_changed_at
            ) VALUES (%s, %s, 'admin', 1, 1, 0, NOW())
            """,
            (username, pw_hash),
        )
        print(f"Admin user '{username}' created successfully (must_change_password=1).")


def reset_password(username: str) -> None:
    """Reset a user's password for lockout recovery."""
    db = DatabaseConnection()

    row = db.fetch_one(
        "SELECT user_id, username FROM app_users WHERE username = %s",
        (username.strip().lower(),),
    )
    if not row:
        print(f"User '{username}' not found.")
        sys.exit(1)

    password = os.environ.get("INITIAL_ADMIN_PASSWORD", "").strip()
    if not password:
        password = getpass.getpass(f"New password for '{row['username']}': ")

    validate_password(password, row["username"])
    pw_hash = hash_password(password)

    with db.transaction() as cur:
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
            (pw_hash, row["user_id"]),
        )
    print(f"Password reset for '{row['username']}' (must_change_password=1, lockout cleared).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create initial admin or reset a user password.")
    parser.add_argument(
        "--reset-password",
        metavar="USERNAME",
        help="Reset the password for the specified user (lockout recovery).",
    )
    args = parser.parse_args()

    if args.reset_password:
        reset_password(args.reset_password)
    else:
        create_admin()


if __name__ == "__main__":
    main()
