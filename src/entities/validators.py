"""Small validation helpers shared by the entity classes."""

from datetime import date, datetime
from typing import Any, Optional

from src.db_manager import ValidationError


def require_text(value: Any, name: str) -> str:
    """Return a stripped, non-empty string or raise ValidationError."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is required")
    return value.strip()


def require_int_range(value: Any, name: str, low: int, high: int) -> int:
    """Return value as an int within [low, high] or raise ValidationError."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be a whole number") from None
    if not low <= number <= high:
        raise ValidationError(f"{name} must be between {low} and {high}")
    return number


def require_positive(value: Any, name: str) -> float:
    """Return value as a float greater than 0 or raise ValidationError."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be a number") from None
    if number <= 0:
        raise ValidationError(f"{name} must be greater than 0")
    return number


def to_flag(value: Any, name: str) -> int:
    """Accept None/0/1/True/False and return 0 or 1."""
    if value is None:
        return 0
    if value in (0, 1, True, False):
        return int(value)
    raise ValidationError(f"{name} must be 0 or 1")


def to_date(value: Any, name: str, required: bool = True) -> Optional[date]:
    """Convert a date, datetime or 'YYYY-MM-DD' string to a date."""
    if value is None or value == "":
        if required:
            raise ValidationError(f"{name} is required")
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValidationError(f"{name} must be a date in YYYY-MM-DD format") from None