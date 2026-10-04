"""Shared base for all managers: DB access, small SQL helpers, error handling."""

import functools
from typing import Any, Callable

from src.db_manager import DatabaseError, DBClient, RecordNotFoundError, ValidationError


def handle_errors(action: str) -> Callable:
   

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self: "BaseManager", *args: Any, **kwargs: Any) -> Any:
            try:
                return func(self, *args, **kwargs)
            except (ValidationError, DatabaseError) as exc:
                self.log.warning("Could not %s: %s", action, exc)
                raise
            except Exception as exc:
                self.log.exception("Unexpected error while trying to %s", action)
                raise DatabaseError(f"Could not {action}: {exc}") from exc

        return wrapper

    return decorator


class BaseManager(DBClient):

    def _exists(self, cur: Any, table: str, column: str, value: Any) -> bool:
        cur.execute(f"SELECT 1 FROM {table} WHERE {column} = %s LIMIT 1", (value,))
        return cur.fetchone() is not None

    def _require(self, cur: Any, table: str, column: str, value: Any, label: str) -> None:
        """Raise RecordNotFoundError unless the referenced row exists."""
        if not self._exists(cur, table, column, value):
            raise RecordNotFoundError(f"{label} {value} does not exist")

    def _count(self, cur: Any, table: str, column: str, value: Any) -> int:
        cur.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {column} = %s", (value,))
        return int(cur.fetchone()["n"])

    def _next_id(self, cur: Any, table: str, column: str) -> int:
        """COALESCE(MAX(id), 0) + 1, to be used inside the inserting transaction."""
        cur.execute(f"SELECT COALESCE(MAX({column}), 0) + 1 AS next_id FROM {table}")
        return int(cur.fetchone()["next_id"])

    def _insert(self, cur: Any, table: str, data: dict) -> None:
        columns = ", ".join(data)
        marks = ", ".join(["%s"] * len(data))
        cur.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(data.values()))

    def _update_fields(self, cur: Any, table: str, id_column: str, record_id: Any, values: dict) -> None:
        assignments = ", ".join(f"{column} = %s" for column in values)
        cur.execute(
            f"UPDATE {table} SET {assignments} WHERE {id_column} = %s",
            (*values.values(), record_id),
        )

    def _validated_values(self, entity: Any, fields: dict, allowed: tuple) -> dict:
        """Apply ``fields`` to the entity (running its validation) and return them."""
        if not fields:
            raise ValidationError("No fields to update")
        unknown = set(fields) - set(allowed)
        if unknown:
            raise ValidationError(f"Cannot update field(s): {', '.join(sorted(unknown))}")
        for name, value in fields.items():
            setattr(entity, name, value)
        return {name: getattr(entity, name) for name in fields}