"""Small validation helpers shared by the entity classes."""

import re
from datetime import date, datetime
from typing import Any, Optional

from src.db_manager import ValidationError


def require_text(value: Any, name: str) -> str:
    """Return a stripped, non-empty string or raise ValidationError."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is required")
    return value.strip()


def require_name(value: Any, name: str) -> str:
    """Validate a person name field.

    Rules:
    - Must be a non-empty string
    - Must not contain digits (e.g. 'John123')
    - Allowed characters: letters (including Unicode), spaces, hyphens, apostrophes, dots
    - Leading/trailing whitespace is stripped
    """
    text = require_text(value, name)

    if re.search(r"\d", text):
        raise ValidationError(f"{name} must not contain numbers")

    if not re.match(r"^[^\W\d_][\w\s\-'.]*$", text, re.UNICODE):
        raise ValidationError(
            f"{name} contains unsupported characters. "
            "Only letters, spaces, hyphens, apostrophes and dots are allowed."
        )

    return text


def require_city(value: Any, name: str = "city") -> Optional[str]:
    """Validate an optional city name.

    None or a blank string means "no city" and returns None. Otherwise the
    same rules as person names apply: letters, spaces, hyphens, apostrophes
    and dots only, and no digits (so '12345' or 'Pune1' are rejected).
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return require_name(value, name)


def require_project_name(value: Any, name: str = "project_name") -> str:
    """Validate a project name: must contain at least one letter.

    Allows 'Atlas', 'Project 7', 'A1'; rejects '123', '2024-01'.
    """
    text = require_text(value, name)
    if not any(ch.isalpha() for ch in text):
        raise ValidationError(
            f"{name} must contain at least one letter "
            "(e.g. 'Atlas' or 'Project 7'), not only numbers or symbols"
        )
    return text


def require_email(value: Any, name: str = "email") -> str:
    """Validate an email address.

    Rules:
    - Must be non-empty
    - Must match standard email format: local@domain.tld
    - Local part and domain must both be non-empty
    - Domain must contain at least one dot
    """
    text = require_text(value, name)

    pattern = r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-.]+$"
    if not re.match(pattern, text):
        raise ValidationError(
            f"{name} is not a valid email address. Expected format: user@example.com"
        )

    return text


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
