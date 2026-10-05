"""Pure transformations used by the analytics dashboard."""

import pandas as pd


def latest_period_metrics(trend: pd.DataFrame) -> dict:
    """Return the newest trend values and comparable prior-period deltas."""
    if trend.empty:
        return {
            "year": None,
            "avg_rating": 0.0,
            "rating_delta": None,
            "avg_score": 0.0,
            "score_delta": None,
            "review_count": 0,
        }

    ordered = trend.sort_values("review_year").reset_index(drop=True)
    latest = ordered.iloc[-1]
    previous = ordered.iloc[-2] if len(ordered) > 1 else None
    return {
        "year": int(latest["review_year"]),
        "avg_rating": float(latest["avg_rating"]),
        "rating_delta": (
            round(float(latest["avg_rating"]) - float(previous["avg_rating"]), 2)
            if previous is not None
            else None
        ),
        "avg_score": float(latest["avg_score"]),
        "score_delta": (
            round(float(latest["avg_score"]) - float(previous["avg_score"]), 2)
            if previous is not None
            else None
        ),
        "review_count": int(latest["review_count"]),
    }


def build_department_scorecard(
    departments: pd.DataFrame, attention_threshold: float = 15.0
) -> pd.DataFrame:
    """Rank departments by an explainable workforce-health score."""
    if departments.empty:
        return departments.copy()

    scorecard = departments.copy()
    scorecard["attrition_rate_pct"] = scorecard["attrition_rate_pct"].astype(float)
    scorecard["avg_job_satisfaction"] = scorecard["avg_job_satisfaction"].astype(float)
    scorecard["health_score"] = (
        scorecard["attrition_rate_pct"]
        + (4.0 - scorecard["avg_job_satisfaction"]) * 5.0
    ).round(1)
    scorecard["health_status"] = scorecard.apply(
        lambda row: (
            "High attention"
            if row["attrition_rate_pct"] >= attention_threshold
            or row["avg_job_satisfaction"] < 2.5
            else "Healthy"
        ),
        axis=1,
    )
    return scorecard.sort_values(
        ["health_score", "attrition_rate_pct"], ascending=False
    ).reset_index(drop=True)


def normalize_view_settings(
    settings: dict, departments: list[str], project_statuses: list[str], focus_views: list[str]
) -> dict:
    """Return safe dashboard preferences after source data changes."""
    department = settings.get("department", "All")
    project_status = settings.get("project_status", "All")
    focus_view = settings.get("focus_view", focus_views[0])
    retention_threshold = float(settings.get("retention_threshold", 2.0))
    attrition_threshold = float(settings.get("attrition_threshold", 15.0))
    return {
        "department": department if department in departments else "All",
        "project_status": project_status if project_status in project_statuses else "All",
        "focus_view": focus_view if focus_view in focus_views else focus_views[0],
        "retention_threshold": min(3.0, max(1.0, retention_threshold)),
        "attrition_threshold": min(30.0, max(5.0, attrition_threshold)),
    }


def filter_frame(
    frame: pd.DataFrame, department: str = "All", project_status: str = "All"
) -> pd.DataFrame:
    """Apply available dashboard dimensions without assuming every dataset has both."""
    if frame.empty:
        return frame.copy()
    filtered = frame.copy()
    if department != "All" and "department_name" in filtered.columns:
        filtered = filtered[filtered["department_name"] == department]
    if project_status != "All" and "status" in filtered.columns:
        filtered = filtered[filtered["status"] == project_status]
    return filtered.copy()


def project_health_status(
    average_allocation_pct: float, average_rating: float, average_satisfaction: float
) -> str:
    """Classify project attention level using workload and employee signals."""
    return "High attention" if project_attention_reasons(
        average_allocation_pct, average_rating, average_satisfaction
    ) != "Healthy" else "Healthy"


def project_attention_reasons(
    average_allocation_pct: float, average_rating: float, average_satisfaction: float
) -> str:
    """Return the transparent internal thresholds that require project review."""
    reasons = []
    if float(average_allocation_pct) >= 90:
        reasons.append("Allocation ≥90%")
    if float(average_rating) < 3.2:
        reasons.append("Rating <3.2")
    if float(average_satisfaction) < 2.5:
        reasons.append("Satisfaction <2.5")
    return "; ".join(reasons) if reasons else "Healthy"
