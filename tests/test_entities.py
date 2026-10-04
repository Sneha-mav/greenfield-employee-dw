"""Unit tests for the entity classes. No database needed."""

from datetime import date

import pytest

from src.db_manager import ValidationError
from src.entities.employee import Employee
from src.entities.project import Project
from src.entities.review import Review


def make_employee(**overrides) -> Employee:
    data = dict(
        first_name="Asha", last_name="Verma", email="asha@example.com",
        hire_date="2020-01-15", department_id=1, job_role_id=2,
        job_level=3, monthly_income=5000,
    )
    data.update(overrides)
    return Employee(**data)


# ----- Employee ---------------------------------------------------------------
def test_valid_employee():
    emp = make_employee()
    assert emp.full_name == "Asha Verma"
    assert emp.is_active is True
    assert emp.hire_date == date(2020, 1, 15)


@pytest.mark.parametrize("field,value", [
    ("job_level", 0), ("job_level", 6), ("monthly_income", 0), ("monthly_income", -5),
    ("email", "no-at-sign"), ("email", "@missing-local"), ("first_name", "  "),
    ("hire_date", "15/01/2020"), ("over_time", 2),
])
def test_invalid_employee_values(field, value):
    with pytest.raises(ValidationError):
        make_employee(**{field: value})


def test_employee_setter_validates():
    emp = make_employee()
    with pytest.raises(ValidationError):
        emp.job_level = 9
    assert emp.job_level == 3


def test_terminated_employee_is_not_active():
    assert make_employee(attrition=1).is_active is False


def test_employee_round_trip():
    row = {
        "employee_id": 7, "first_name": "Asha", "last_name": "Verma",
        "email": "asha@example.com", "gender": "Female", "age": 30,
        "marital_status": "Single", "city": "Pune", "education_field": "Engineering",
        "hire_date": date(2020, 1, 15), "department_id": 1, "job_role_id": 2,
        "job_level": 3, "monthly_income": 5000, "over_time": 0, "attrition": 0,
        "years_at_company": 4,
    }
    assert Employee.from_row(row).to_dict() == row


def test_employee_from_row_missing_fields():
    with pytest.raises(ValidationError):
        Employee.from_row({"employee_id": 1})


# ----- Project ----------------------------------------------------------------
def test_valid_project():
    project = Project(project_name="Atlas", department_id=1, start_date="2024-01-01")
    assert project.is_open is True
    assert Project(project_name="Old", department_id=1, status="Completed").is_open is False


def test_project_invalid_status_and_dates():
    with pytest.raises(ValidationError):
        Project(project_name="Atlas", department_id=1, status="Cancelled")
    with pytest.raises(ValidationError):
        Project(project_name="Atlas", department_id=1, start_date="2024-05-01", end_date="2024-01-01")


def test_project_round_trip():
    row = {
        "project_id": 3, "project_name": "Atlas", "department_id": 1, "status": "On Hold",
        "start_date": date(2024, 1, 1), "end_date": None,
    }
    assert Project.from_row(row).to_dict() == row


# ----- Review -----------------------------------------------------------------
def test_valid_review_and_high_performer():
    assert Review(employee_id=1, review_date="2024-06-01", performance_rating=5).is_high_performer
    assert not Review(employee_id=1, review_date="2024-06-01", performance_rating=3).is_high_performer


@pytest.mark.parametrize("rating", [0, 6, "abc", None])
def test_review_invalid_rating(rating):
    with pytest.raises(ValidationError):
        Review(employee_id=1, review_date="2024-06-01", performance_rating=rating)


def test_review_round_trip():
    row = {
        "review_id": 9, "employee_id": 1, "project_id": None, "review_date": date(2024, 6, 1),
        "performance_rating": 4, "review_score": 3.5, "job_satisfaction": 3,
        "environment_satisfaction": 2, "salary_hike_pct": 11.0,
    }
    assert Review.from_row(row).to_dict() == row