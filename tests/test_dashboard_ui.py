from streamlit.testing.v1 import AppTest

from src.managers import AnalyticsManager


def test_dashboard_renders_decision_tabs_with_warehouse_fixture(monkeypatch):
    fixture = {
        "rating_trend_by_year": [
            {"review_year": 2023, "review_count": 90, "avg_rating": 3.2, "avg_score": 72.0},
            {"review_year": 2024, "review_count": 120, "avg_rating": 3.5, "avg_score": 76.0},
        ],
        "attrition_by_department": [
            {"department_name": "Research", "headcount": 80, "leavers": 5, "attrition_rate_pct": 6.25, "avg_job_satisfaction": 3.3, "avg_env_satisfaction": 3.2, "avg_salary_hike_pct": 14.0},
            {"department_name": "Sales", "headcount": 100, "leavers": 18, "attrition_rate_pct": 18.0, "avg_job_satisfaction": 2.0, "avg_env_satisfaction": 2.2, "avg_salary_hike_pct": 11.0},
        ],
        "top_performers_per_department": [
            {"department_name": "Research", "employee_id": 1, "full_name": "Asha Rao", "avg_rating": 4.8, "avg_score": 94.0, "review_count": 5, "dept_rank": 1}
        ],
        "at_risk_watchlist": [
            {"employee_id": 2, "full_name": "Ravi Shah", "department_name": "Sales", "job_role": "Sales Executive", "avg_job_satisfaction": 1.8, "avg_env_satisfaction": 2.0, "avg_rating": 3.1, "review_count": 4}
        ],
        "project_health": [
            {"project_id": 10, "project_name": "Orion", "status": "Active", "department_name": "Sales", "review_count": 7, "avg_rating": 3.0, "avg_job_satisfaction": 2.2, "active_assignments": 8, "avg_allocation_pct": 92.0}
        ],
        "attrition_by_hire_cohort": [
            {"hire_year": 2022, "headcount": 80, "leavers": 8, "attrition_pct": 10.0, "avg_rating": 3.4}
        ],
        "salary_band_attrition": [
            {"salary_band": 1, "band_label": "$2,000 - $4,000", "headcount": 50, "leavers": 9, "attrition_pct": 18.0}
        ],
        "validate_warehouse": {
            "oltp_reviews": 210,
            "fact_reviews": 210,
            "reviews_missing_in_fact": 0,
            "oltp_employees": 180,
            "current_dim_employees": 180,
            "employees_match": True,
            "employees_with_multiple_current_rows": 0,
        },
    }

    monkeypatch.setattr(AnalyticsManager, "__init__", lambda self: None)
    for method, response in fixture.items():
        monkeypatch.setattr(AnalyticsManager, method, lambda self, *args, _response=response, **kwargs: _response)

    dashboard = AppTest.from_file("app/views/5_Analytics_Dashboard.py")
    dashboard.run()

    assert not dashboard.exception
    assert [title.value for title in dashboard.title] == ["Enterprise Employee Analytics"]
    assert [tab.label for tab in dashboard.tabs] == [
        "Overview", "Workforce", "Project health", "Employee history"
    ]
    assert len(dashboard.metric) == 4
    assert len(dashboard.expander) == 4
    assert "dashboard_focus_mode" not in [button.key for button in dashboard.button]
    assert dashboard.sidebar
    assert "Filters" in [heading.value for heading in dashboard.sidebar.subheader]
    assert "Attrition attention threshold" in [slider.label for slider in dashboard.sidebar.slider]

    reset_button = next(button for button in dashboard.button if button.label == "Reset filters")
    reset_button.click()
    dashboard.run()
    assert not dashboard.exception
