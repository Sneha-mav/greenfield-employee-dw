"""Executive analytics dashboard backed by the OLAP star schema."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components import charts, tables
from app.components.charts import PLOTLY_CONFIG
from app.components.dashboard_logic import (
    build_department_scorecard,
    filter_frame,
    latest_period_metrics,
    project_attention_reasons,
    project_health_status,
)
from app.components.theme import (
    CHART_NEGATIVE,
    CHART_POSITIVE,
    CHART_SECONDARY,
    CHART_WARNING,
    apply_chart_theme,
    fmt_number,
    inject_css,
)
from src.db_manager import DatabaseError
from src.managers import AnalyticsManager

inject_css()
TAB_NAMES = ["Overview", "Workforce", "Project health", "Employee history"]


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_data(satisfaction_threshold: float, min_reviews: int) -> dict:
    analytics = AnalyticsManager()
    return {
        "trend": pd.DataFrame(analytics.rating_trend_by_year()),
        "attrition": pd.DataFrame(analytics.attrition_by_department()),
        "performers": pd.DataFrame(
            analytics.top_performers_per_department(top_n=5, min_reviews=min_reviews)
        ),
        "watchlist": pd.DataFrame(
            analytics.at_risk_watchlist(max_satisfaction=satisfaction_threshold, limit=100)
        ),
        "projects": pd.DataFrame(analytics.project_health(min_reviews=min_reviews)),
        "cohort": pd.DataFrame(analytics.attrition_by_hire_cohort()),
        "salary_band": pd.DataFrame(analytics.salary_band_attrition()),
    }


def filter_department(frame: pd.DataFrame, department: str) -> pd.DataFrame:
    if frame.empty or department == "All" or "department_name" not in frame.columns:
        return frame.copy()
    return frame[frame["department_name"] == department].copy()


def render_overview(scope: dict) -> None:
    left, right = st.columns((1.35, 1))
    with left:
        if scope["trend"].empty:
            st.info("No reviews match the selected period.")
        else:
            st.plotly_chart(
                charts.yoy_trend_line(scope["trend"]),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
    with right:
        if scope["attrition"].empty:
            st.info("No current workforce data matches this department.")
        else:
            st.plotly_chart(
                charts.attrition_by_dept_bar(
                    scope["attrition"], scope["attrition_threshold"]
                ),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
    with st.expander("Department scorecard"):
        if scope["scorecard"].empty:
            st.info("No current workforce data matches this department.")
        else:
            st.dataframe(
                scope["scorecard"],
                column_config={
                    "attrition_rate_pct": st.column_config.NumberColumn("Attrition", format="%.1f%%"),
                    "avg_job_satisfaction": st.column_config.NumberColumn("Satisfaction", format="%.2f / 4"),
                    "health_score": st.column_config.NumberColumn("Attention score", format="%.1f"),
                },
                height=260,
                use_container_width=True,
                hide_index=True,
            )


def render_workforce(scope: dict) -> None:
    left, right = st.columns(2)
    with left:
        attrition = scope["attrition"]
        if attrition.empty:
            st.info("No current workforce data matches this department.")
        else:
            figure = px.scatter(
                attrition,
                x="avg_job_satisfaction",
                y="attrition_rate_pct",
                size="headcount",
                color="attrition_rate_pct",
                text="department_name",
                color_continuous_scale=[CHART_POSITIVE, CHART_WARNING, CHART_NEGATIVE],
                labels={
                    "avg_job_satisfaction": "Job satisfaction (1–4)",
                    "attrition_rate_pct": "Attrition (%)",
                    "headcount": "Headcount",
                },
                size_max=48,
            )
            figure.update_traces(textposition="top center")
            figure.update_layout(coloraxis_showscale=False)
            apply_chart_theme(figure, "Workforce risk by department")
            st.plotly_chart(figure, use_container_width=True, config=PLOTLY_CONFIG)
    with right:
        if scope["cohort"].empty:
            st.info("No current hire-cohort data is available.")
        else:
            st.plotly_chart(
                charts.cohort_attrition_bar(scope["cohort"]),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
    with st.expander("Salary-band attrition"):
        if scope["salary_band"].empty:
            st.info("No current salary-band data is available.")
        else:
            st.plotly_chart(
                charts.salary_band_attrition_bar(scope["salary_band"]),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
    with st.expander("Retention review queue"):
        tables.watchlist_table(scope["watchlist"])
        if not scope["watchlist"].empty:
            st.download_button(
                "Download CSV",
                scope["watchlist"].to_csv(index=False).encode("utf-8"),
                file_name="retention_review_queue.csv",
                mime="text/csv",
            )


def render_project_health(scope: dict) -> None:
    projects = scope["projects"]
    if projects.empty:
        st.info("No projects meet the selected criteria.")
        return
    project_frame = projects.copy()
    project_frame["attention_status"] = project_frame.apply(
        lambda row: project_health_status(
            row["avg_allocation_pct"], row["avg_rating"], row["avg_job_satisfaction"]
        ),
        axis=1,
    )
    project_frame["why_flagged"] = project_frame.apply(
        lambda row: project_attention_reasons(
            row["avg_allocation_pct"], row["avg_rating"], row["avg_job_satisfaction"]
        ),
        axis=1,
    )
    plot_frame = project_frame.sort_values("avg_allocation_pct", ascending=True)
    figure = px.bar(
        plot_frame,
        x="avg_allocation_pct",
        y="project_name",
        color="attention_status",
        orientation="h",
        text="avg_allocation_pct",
        hover_name="project_name",
        hover_data=["department_name", "avg_rating", "avg_job_satisfaction", "active_assignments", "review_count", "status", "why_flagged"],
        color_discrete_map={
            "High attention": CHART_NEGATIVE,
            "Healthy": CHART_POSITIVE,
            "On Hold": "#0EA5E9",
        },
        labels={
            "avg_allocation_pct": "Average allocation (%)",
            "project_name": "",
        },
    )
    figure.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
    figure.add_vline(x=90, line_dash="dash", line_color=CHART_WARNING, opacity=0.85)
    figure.update_xaxes(range=[0, 105])
    apply_chart_theme(figure, "Project health — workload & status")
    figure.update_layout(legend_title_text="Health status")
    st.plotly_chart(figure, use_container_width=True, config=PLOTLY_CONFIG)
    with st.expander("Project details"):
        st.dataframe(
            project_frame.sort_values(["attention_status", "avg_rating", "avg_job_satisfaction"]),
            column_config={
                "project_name": "Project",
                "department_name": "Department",
                "avg_rating": st.column_config.NumberColumn("Rating", format="%.2f / 5"),
                "avg_job_satisfaction": st.column_config.NumberColumn("Satisfaction", format="%.2f / 4"),
                "avg_allocation_pct": st.column_config.NumberColumn("Allocation", format="%.1f%%"),
                "active_assignments": st.column_config.NumberColumn("Assignments"),
                "review_count": st.column_config.NumberColumn("Reviews"),
                "attention_status": "Status",
                "why_flagged": "Why flagged",
            },
            height=360,
            use_container_width=True,
            hide_index=True,
        )


def render_employee_history(scope: dict) -> None:
    st.subheader("Top performers")
    tables.top_performers_table(scope["performers"])
    st.divider()
    st.subheader("Employee history")
    employee_id = st.number_input("Employee ID", min_value=1, step=1, key="dashboard_history_id")
    if st.button("View history", key="dashboard_history_load"):
        try:
            history = AnalyticsManager().get_employee_scd2_history(int(employee_id))
            if not history:
                st.info(f"No history found for employee {employee_id}.")
            else:
                frame = pd.DataFrame(history)
                tables.scd2_history_table(frame)
                st.plotly_chart(
                    charts.scd2_gantt(frame, str(frame.iloc[0]["full_name"])),
                    use_container_width=True,
                    config=PLOTLY_CONFIG,
                )
        except DatabaseError as exc:
            st.error(str(exc))
    


for key, value in {
    "filter_department": "All",
    "filter_project_status": "All",
    "filter_satisfaction_threshold": 2.0,
    "filter_attrition_threshold": 15.0,
    "filter_min_reviews": 3,
}.items():
    st.session_state.setdefault(key, value)

with st.spinner("Loading analytics…"):
    try:
        data = load_dashboard_data(
            st.session_state.filter_satisfaction_threshold,
            st.session_state.filter_min_reviews,
        )
    except DatabaseError as exc:
        st.error(f"Analytics are unavailable: {exc}")
        st.stop()

trend = data["trend"]
attrition = data["attrition"]
departments = ["All"] + sorted(attrition["department_name"].dropna().unique().tolist()) if not attrition.empty else ["All"]
project_statuses = ["All"] + sorted(data["projects"]["status"].dropna().unique().tolist()) if not data["projects"].empty else ["All"]
years = sorted(trend["review_year"].astype(int).unique().tolist()) if not trend.empty else []


def reset_dashboard_filters(year_values: list[int]) -> None:
    """Reset widget values before Streamlit instantiates them on the next run."""
    st.session_state.update(
        filter_department="All",
        filter_project_status="All",
        filter_satisfaction_threshold=2.0,
        filter_attrition_threshold=15.0,
        filter_min_reviews=3,
    )
    if year_values:
        st.session_state.filter_years = (year_values[0], year_values[-1])


with st.sidebar:
    st.divider()
    st.subheader("Filters")
    st.selectbox("Department", departments, key="filter_department")
    if years:
        st.select_slider("Review years", years, value=(years[0], years[-1]), key="filter_years")
    st.selectbox("Project status", project_statuses, key="filter_project_status")
    st.slider("Minimum reviews", 3, 20, key="filter_min_reviews")
    st.slider("Retention review threshold", 1.0, 3.0, step=0.1, key="filter_satisfaction_threshold")
    st.slider("Attrition attention threshold", 5.0, 30.0, step=1.0, key="filter_attrition_threshold")
    st.button(
        "Reset filters",
        use_container_width=True,
        on_click=reset_dashboard_filters,
        args=(years,),
    )
    if st.button("Refresh data", use_container_width=True):
        load_dashboard_data.clear()
        st.rerun()

selected_years = st.session_state.get("filter_years", (years[0], years[-1]) if years else (None, None))
trend_view = trend[trend["review_year"].between(*selected_years)].copy() if years else trend.copy()
attrition_view = filter_frame(attrition, department=st.session_state.filter_department)
performers_view = filter_frame(data["performers"], department=st.session_state.filter_department)
watchlist_view = filter_frame(data["watchlist"], department=st.session_state.filter_department)
projects_view = filter_frame(
    data["projects"],
    department=st.session_state.filter_department,
    project_status=st.session_state.filter_project_status,
)

st.title("Enterprise Employee Analytics")

latest = latest_period_metrics(trend_view)
headcount = int(attrition_view["headcount"].sum()) if not attrition_view.empty else 0
leavers = int(attrition_view["leavers"].sum()) if not attrition_view.empty else 0
metrics = st.columns(4, gap="small")
metrics[0].metric("Active employees", fmt_number(max(0, headcount - leavers), decimals=0))
metrics[1].metric("Attrition", f"{(100 * leavers / headcount) if headcount else 0:.1f}%")
metrics[2].metric("Performance rating", f"{latest['avg_rating']:.2f} / 5")
metrics[3].metric("Retention flags", str(len(watchlist_view)))

scope = {
    "trend": trend_view,
    "attrition": attrition_view,
    "performers": performers_view,
    "watchlist": watchlist_view,
    "projects": projects_view,
    "cohort": data["cohort"],
    "salary_band": data["salary_band"],
    "scorecard": build_department_scorecard(
        attrition_view, st.session_state.filter_attrition_threshold
    ),
    "attrition_threshold": st.session_state.filter_attrition_threshold,
}

overview, workforce, projects, history = st.tabs(TAB_NAMES)
with overview:
    render_overview(scope)
with workforce:
    render_workforce(scope)
with projects:
    render_project_health(scope)
with history:
    render_employee_history(scope)
