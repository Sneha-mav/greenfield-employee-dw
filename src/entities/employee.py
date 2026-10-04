"""Employee entity: attributes, validation and behaviour for one employee."""

from datetime import date
from typing import Any, Optional

from src.db_manager import ValidationError
from src.entities.validators import (
    require_int_range,
    require_positive,
    require_text,
    to_date,
    to_flag,
)


class Employee:
    """An employee row from the OLTP ``employees`` table.
    """

    FIELDS = (
        "employee_id", "first_name", "last_name", "email", "gender", "age",
        "marital_status", "city", "education_field", "hire_date",
        "department_id", "job_role_id", "job_level", "monthly_income",
        "over_time", "attrition", "years_at_company",
    )

    def __init__(
        self,
        first_name: str,
        last_name: str,
        email: str,
        hire_date: Any,
        department_id: int,
        job_role_id: int,
        job_level: int,
        monthly_income: float,
        employee_id: Optional[int] = None,
        gender: Optional[str] = None,
        age: Optional[int] = None,
        marital_status: Optional[str] = None,
        city: Optional[str] = None,
        education_field: Optional[str] = None,
        over_time: int = 0,
        attrition: int = 0,
        years_at_company: Optional[int] = None,
    ) -> None:
        self.employee_id = employee_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.hire_date = hire_date
        self.department_id = department_id
        self.job_role_id = job_role_id
        self.job_level = job_level
        self.monthly_income = monthly_income
        self.gender = gender
        self.age = age
        self.marital_status = marital_status
        self.city = city
        self.education_field = education_field
        self.over_time = over_time
        self.attrition = attrition
        self.years_at_company = years_at_company

    # ----- validated properties ---------------------------------------------
    @property
    def first_name(self) -> str:
        return self._first_name

    @first_name.setter
    def first_name(self, value: str) -> None:
        self._first_name = require_text(value, "first_name")

    @property
    def last_name(self) -> str:
        return self._last_name

    @last_name.setter
    def last_name(self, value: str) -> None:
        self._last_name = require_text(value, "last_name")

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        text = require_text(value, "email")
        local, _, domain = text.partition("@")
        if not local or not domain:
            raise ValidationError("email must contain '@' with text on both sides")
        self._email = text

    @property
    def hire_date(self) -> date:
        return self._hire_date

    @hire_date.setter
    def hire_date(self, value: Any) -> None:
        self._hire_date = to_date(value, "hire_date")

    @property
    def job_level(self) -> int:
        return self._job_level

    @job_level.setter
    def job_level(self, value: int) -> None:
        self._job_level = require_int_range(value, "job_level", 1, 5)

    @property
    def monthly_income(self) -> float:
        return self._monthly_income

    @monthly_income.setter
    def monthly_income(self, value: float) -> None:
        self._monthly_income = require_positive(value, "monthly_income")

    @property
    def over_time(self) -> int:
        return self._over_time

    @over_time.setter
    def over_time(self, value: Any) -> None:
        self._over_time = to_flag(value, "over_time")

    @property
    def attrition(self) -> int:
        return self._attrition

    @attrition.setter
    def attrition(self, value: Any) -> None:
        self._attrition = to_flag(value, "attrition")

    # ----- behaviour ----------------------------------------------------------
    @property
    def full_name(self) -> str:
        """First and last name joined."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self) -> bool:
        """True while the employee has not left (attrition = 0)."""
        return self.attrition == 0

    # ----- conversion ---------------------------------------------------------
    @classmethod
    def from_row(cls, row: dict) -> "Employee":
        """Build an Employee from a database row (extra keys are ignored)."""
        data = {f: row[f] for f in cls.FIELDS if f in row}
        try:
            return cls(**data)
        except TypeError as exc:
            raise ValidationError(f"Row is missing required employee fields: {exc}") from exc

    def to_dict(self) -> dict:
        """Return all table columns as a dict (dates stay as date objects)."""
        return {f: getattr(self, f) for f in self.FIELDS}

    def __repr__(self) -> str:
        return f"Employee(id={self.employee_id}, name={self.full_name!r})"