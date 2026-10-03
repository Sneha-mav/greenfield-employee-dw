"""Tests for src.db_manager. DB tests are skipped if the dev database is unreachable."""

import pytest

from src.db_manager import DatabaseConnection, DatabaseError, DBClient


def test_singleton_returns_same_object():
    assert DatabaseConnection() is DatabaseConnection()


def test_dbclient_uses_shared_connection():
    assert DBClient().db is DatabaseConnection()


@pytest.fixture(scope="module")
def db():
    conn = DatabaseConnection()
    try:
        conn.fetch_one("SELECT 1 AS ok")
    except DatabaseError as exc:
        pytest.skip(f"Dev database not available: {exc}")
    return conn


def test_select_one(db):
    assert db.fetch_one("SELECT 1 AS ok") == {"ok": 1}


def test_transaction_rolls_back_on_error(db):
    row = db.fetch_one("SELECT employee_id, city FROM employees ORDER BY employee_id LIMIT 1")
    with pytest.raises(RuntimeError):
        with db.transaction() as cur:
            cur.execute(
                "UPDATE employees SET city = %s WHERE employee_id = %s",
                ("ROLLBACK_TEST", row["employee_id"]),
            )
            raise RuntimeError("force rollback")
    after = db.fetch_one("SELECT city FROM employees WHERE employee_id = %s", (row["employee_id"],))
    assert after["city"] == row["city"]