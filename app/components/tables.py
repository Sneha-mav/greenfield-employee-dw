"""Styled st.dataframe wrappers — one function per table type.

Pages call these instead of st.dataframe directly so column config
and display logic stays in one place.
"""

import pandas as pd
import streamlit as st


def records_to_frame(records) -> pd.DataFrame:
    """Normalize manager results so table components accept lists or DataFrames."""
    if records is None:
        return pd.DataFrame()
    if isinstance(records, pd.DataFrame):
        return records.copy()
    return pd.DataFrame(records)


def top_performers_table(df: pd.DataFrame, dept_filter: str = "All") -> None:
    if df.empty:
        st.info("No performers found for the selected filters.")
        return

    display = df.copy()
    if dept_filter != "All":
        display = display[display["department_name"] == dept_filter]

    if display.empty:
        st.info(f"No top performers found for **{dept_filter}**.")
        return

    st.dataframe(
        display,
        column_config={
            "dept_rank":       st.column_config.NumberColumn("Rank",        format="%d"),
            "avg_rating":      st.column_config.NumberColumn("Avg Rating",  format="%.2f / 5"),
            "avg_score":       st.column_config.NumberColumn("Avg Score",   format="%.1f"),
            "review_count":    st.column_config.NumberColumn("Reviews"),
            "full_name":       st.column_config.TextColumn("Employee"),
            "department_name": st.column_config.TextColumn("Department"),
        },
        use_container_width=True,
        hide_index=True,
    )


def watchlist_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No employees meet the current retention-review threshold.")
        return

    st.dataframe(
        df,
        column_config={
            "employee_id":          st.column_config.NumberColumn("ID"),
            "full_name":            st.column_config.TextColumn("Employee"),
            "department_name":      st.column_config.TextColumn("Department"),
            "job_role":             st.column_config.TextColumn("Role"),
            "avg_job_satisfaction": st.column_config.ProgressColumn(
                "Avg Satisfaction", min_value=0, max_value=4, format="%.2f"
            ),
            "avg_env_satisfaction": st.column_config.ProgressColumn(
                "Env Satisfaction", min_value=0, max_value=4, format="%.2f"
            ),
            "avg_rating":           st.column_config.NumberColumn(
                "Avg Rating", format="%.2f / 5"
            ),
            "review_count":         st.column_config.NumberColumn("Reviews"),
        },
        use_container_width=True,
        hide_index=True,
    )


def bottleneck_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.success("No project bottlenecks detected.")
        return

    st.dataframe(
        df,
        column_config={
            "bottleneck_rank":     st.column_config.NumberColumn("Risk Rank", format="%d"),
            "project_name":        st.column_config.TextColumn("Project"),
            "status":              st.column_config.TextColumn("Status"),
            "review_count":        st.column_config.NumberColumn("Reviews"),
            "avg_rating":          st.column_config.NumberColumn("Avg Rating", format="%.2f"),
            "avg_job_satisfaction":st.column_config.ProgressColumn(
                "Avg Satisfaction", min_value=0, max_value=4, format="%.2f"
            ),
        },
        use_container_width=True,
        hide_index=True,
    )


def scd2_history_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No history found for this employee.")
        return

    st.dataframe(
        df,
        column_config={
            "version_num":     st.column_config.NumberColumn("Version"),
            "department_name": st.column_config.TextColumn("Department"),
            "job_role":        st.column_config.TextColumn("Job Role"),
            "job_level":       st.column_config.NumberColumn("Level"),
            "monthly_income":  st.column_config.NumberColumn("Monthly Income", format="%d"),
            "start_date":      st.column_config.DateColumn("Effective From"),
            "end_date":        st.column_config.TextColumn("Effective To"),
            "is_current":      st.column_config.CheckboxColumn("Current"),
        },
        use_container_width=True,
        hide_index=True,
    )


def assignments_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No assignments found for this project.")
        return

    st.dataframe(
        df,
        column_config={
            "assignment_id":   st.column_config.NumberColumn("ID"),
            "employee_id":     st.column_config.NumberColumn("Emp ID"),
            "employee_name":   st.column_config.TextColumn("Employee"),
            "role_on_project": st.column_config.TextColumn("Role"),
            "allocation_pct":  st.column_config.ProgressColumn(
                "Allocation", min_value=0, max_value=100, format="%d%%"
            ),
            "start_date":      st.column_config.DateColumn("Start"),
            "end_date":        st.column_config.DateColumn("End"),
        },
        use_container_width=True,
        hide_index=True,
    )


def employee_reviews_table(df: pd.DataFrame) -> None:
    display = records_to_frame(df)
    if display.empty:
        st.info("No reviews found for this employee.")
        return

    st.dataframe(
        display,
        column_config={
            "review_id":              st.column_config.NumberColumn("ID"),
            "review_date":            st.column_config.DateColumn("Date"),
            "performance_rating":     st.column_config.NumberColumn("Rating (1-5)"),
            "review_score":           st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%.0f"
            ),
            "job_satisfaction":       st.column_config.NumberColumn("Job Sat."),
            "environment_satisfaction": st.column_config.NumberColumn("Env Sat."),
            "salary_hike_pct":        st.column_config.NumberColumn("Hike %", format="%.1f%%"),
        },
        use_container_width=True,
        hide_index=True,
    )
