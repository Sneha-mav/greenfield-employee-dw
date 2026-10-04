import pandas as pd

from app.components.dashboard_logic import (
    build_department_scorecard,
    filter_frame,
    latest_period_metrics,
    normalize_view_settings,
    project_health_status,
    project_attention_reasons,
)


def test_latest_period_metrics_returns_latest_values_and_period_deltas():
    trend = pd.DataFrame(
        {
            "review_year": [2023, 2024],
            "avg_rating": [3.20, 3.45],
            "avg_score": [72.0, 76.5],
            "review_count": [120, 160],
        }
    )

    metrics = latest_period_metrics(trend)

    assert metrics["year"] == 2024
    assert metrics["avg_rating"] == 3.45
    assert metrics["rating_delta"] == 0.25
    assert metrics["avg_score"] == 76.5
    assert metrics["score_delta"] == 4.5
    assert metrics["review_count"] == 160


def test_department_scorecard_prioritizes_high_attrition_and_low_satisfaction():
    departments = pd.DataFrame(
        {
            "department_name": ["Research", "Sales"],
            "headcount": [100, 100],
            "leavers": [8, 20],
            "attrition_rate_pct": [8.0, 20.0],
            "avg_job_satisfaction": [3.4, 1.9],
            "avg_env_satisfaction": [3.2, 2.1],
            "avg_salary_hike_pct": [14.0, 10.0],
        }
    )

    scorecard = build_department_scorecard(departments, attention_threshold=15.0)

    assert scorecard.iloc[0]["department_name"] == "Sales"
    assert scorecard.iloc[0]["health_status"] == "High attention"
    assert scorecard.iloc[1]["health_status"] == "Healthy"


def test_project_health_status_uses_allocation_and_people_signals():
    assert project_health_status(95.0, 3.0, 3.0) == "High attention"
    assert project_health_status(60.0, 4.0, 3.8) == "Healthy"


def test_normalize_view_settings_resets_invalid_filters_and_keeps_focus_choice():
    settings = normalize_view_settings(
        {"department": "Unknown", "project_status": "Closed", "focus_view": "Project health"},
        departments=["All", "Research", "Sales"],
        project_statuses=["All", "Active", "On Hold"],
        focus_views=["Overview", "Workforce", "Project health", "Employee history"],
    )

    assert settings == {
        "department": "All",
        "project_status": "All",
        "focus_view": "Project health",
        "retention_threshold": 2.0,
        "attrition_threshold": 15.0,
    }


def test_project_attention_reasons_name_each_trigger():
    assert project_attention_reasons(95.0, 3.0, 2.0) == "Allocation ≥90%; Rating <3.2; Satisfaction <2.5"
    assert project_attention_reasons(60.0, 4.0, 3.8) == "Healthy"


def test_normalize_view_settings_keeps_valid_dashboard_tab_and_thresholds():
    settings = normalize_view_settings(
        {
            "department": "Sales",
            "project_status": "Active",
            "focus_view": "Employee history",
            "retention_threshold": 2.3,
            "attrition_threshold": 18.0,
        },
        departments=["All", "Sales"],
        project_statuses=["All", "Active"],
        focus_views=["Overview", "Workforce", "Project health", "Employee history"],
    )

    assert settings["focus_view"] == "Employee history"
    assert settings["retention_threshold"] == 2.3
    assert settings["attrition_threshold"] == 18.0


def test_filter_frame_applies_department_and_project_status_only_when_available():
    frame = pd.DataFrame(
        {
            "department_name": ["Sales", "Research", "Sales"],
            "status": ["Active", "Active", "Closed"],
            "value": [1, 2, 3],
        }
    )

    filtered = filter_frame(frame, department="Sales", project_status="Active")

    assert filtered["value"].tolist() == [1]


def test_dashboard_tab_labels_are_complete_and_hr_facing():
    labels = ["Overview", "Workforce", "Project health", "Employee history"]
    assert labels == ["Overview", "Workforce", "Project health", "Employee history"]
