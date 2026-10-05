"""Database layer for the Employee Data Warehouse (Phase 3).
Usage::
    from src.db_manager import DatabaseConnection
    db = DatabaseConnection()                       # always the same object
    rows = db.fetch_all("SELECT * FROM departments WHERE department_id = %s", (1,))
    with db.transaction() as cur:                   # commit on success, rollback on error
        cur.execute("UPDATE employees SET city = %s WHERE employee_id = %s", ("Pune", 7))
Always pass values through ``params`` (%s placeholders), never f-strings.
Do not nest ``transaction()`` blocks; reuse the cursor you were given.
"""
import logging
import os
import threading
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence
from dotenv import load_dotenv
from mysql.connector import Error as MySQLError
from mysql.connector import pooling
logger = logging.getLogger(__name__)
class DatabaseError(Exception):
    """A database operation failed (connection, query, procedure)."""
class RecordNotFoundError(DatabaseError):
    """A record that was expected to exist was not found."""
class ValidationError(Exception):
    """Input failed validation."""
class DatabaseConnection:
    """Thread-safe Singleton that owns a small MySQL connection pool."""
    POOL_SIZE = 10
    _instance: Optional["DatabaseConnection"] = None
    _lock = threading.Lock()
    def __new__(cls) -> "DatabaseConnection":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._pool = None
        return cls._instance
    def _get_pool(self) -> pooling.MySQLConnectionPool:
        """Create the pool on first use, reading settings from .env."""
        with self._lock:
            if self._pool is None:
                load_dotenv()
                try:
                    self._pool = pooling.MySQLConnectionPool(
                        pool_name="dw_pool",
                        pool_size=self.POOL_SIZE,
                        host=os.getenv("DB_HOST", "localhost"),
                        port=int(os.getenv("DB_PORT", "3306")),
                        user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASSWORD"),
                        database=os.getenv("DB_NAME"),
                        autocommit=False,
                    )
                except (MySQLError, ValueError) as exc:
                    logger.error("Could not create connection pool: %s", exc)
                    raise DatabaseError(
                        f"Could not connect to MySQL. Check your .env settings. ({exc})"
                    ) from exc
        return self._pool
    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Yield a dict cursor; commit if the block succeeds, roll back if it raises."""
        pool = self._get_pool()
        try:
            conn = pool.get_connection()
        except MySQLError as exc:
            raise DatabaseError(f"Could not get a database connection: {exc}") from exc
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            yield cursor
            conn.commit()
        except MySQLError as exc:
            conn.rollback()
            logger.error("Database error, rolled back: %s", exc)
            raise DatabaseError(str(exc)) from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()  # returns the connection to the pool
    def fetch_all(self, query: str, params: Optional[Sequence[Any]] = None) -> list:
        """Run a SELECT and return all rows as dicts."""
        with self.transaction() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    def fetch_one(self, query: str, params: Optional[Sequence[Any]] = None) -> Optional[dict]:
        """Run a SELECT and return the first row as a dict, or None."""
        with self.transaction() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def fetch_df(self, query: str, params: Optional[Sequence[Any]] = None):
        """Run a SELECT and return results as a pandas DataFrame."""
        import pandas as pd
        with self.transaction() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return pd.DataFrame(rows)

    def execute(self, query: str, params: Optional[Sequence[Any]] = None) -> int:
        """Run an INSERT/UPDATE/DELETE and return the affected row count."""
        with self.transaction() as cur:
            cur.execute(query, params)
            return cur.rowcount
    def call_procedure(self, name: str, args: Sequence[Any] = ()) -> list:
        """CALL a stored procedure; return a list of its result sets (lists of rows)."""
        with self.transaction() as cur:
            cur.callproc(name, tuple(args))
            return [result.fetchall() for result in cur.stored_results()]
class DBClient:
    """Thin base class for managers: gives them ``self.db`` and ``self.log``."""
    def __init__(self) -> None:
        self.db = DatabaseConnection()
        self.log = logging.getLogger(type(self).__name__)
