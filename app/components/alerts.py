"""Insight callouts — rendered below relevant charts.

Rules:
- Keep messages to one sentence of factual data.
- Use warning/error only for actionable conditions.
- Use info/success only when the positive result is analytically meaningful.
- No emoji prefixes — colour coding carries the severity signal.
"""

import pandas as pd
import streamlit as st

from app.components.theme import ATTRITION_HIGH


def attrition_insight(df: pd.DataFrame) -> None:
    if df.empty or "attrition_rate_pct" not in df.columns:
        return
    worst = df.sort_values("attrition_rate_pct", ascending=False).iloc[0]
    avg   = df["attrition_rate_pct"].mean()
    level = "error" if worst["attrition_rate_pct"] > ATTRITION_HIGH else "warning"
    getattr(st, level)(
        f"**{worst['department_name']}** has the highest attrition at "
        f"**{worst['attrition_rate_pct']:.1f}%** (company avg {avg:.1f}%)."
    )


def yoy_insight(df: pd.DataFrame) -> None:
    if df.empty or "avg_rating" not in df.columns:
        return
    latest = df.sort_values("review_year").iloc[-1]
    delta  = latest.get("change_vs_prev_year")
    if delta is None or pd.isna(delta):
        return
    year   = int(latest["review_year"])
    rating = float(latest["avg_rating"])
    if delta >= 0:
        st.success(
            f"Performance improved by **+{delta:.2f}** in **{year}** (avg rating {rating:.2f})."
        )
    else:
        st.warning(
            f"Performance declined by **{delta:.2f}** in **{year}** (avg rating {rating:.2f})."
        )


def watchlist_insight(df: pd.DataFrame) -> None:
    if df.empty:
        return
    count     = len(df)
    depts     = df["department_name"].value_counts()
    top_dept  = depts.index[0]
    top_count = int(depts.iloc[0])
    st.warning(
        f"**{count} employee{'s' if count > 1 else ''}** below satisfaction threshold. "
        f"**{top_dept}** accounts for {top_count}."
    )


def bottleneck_insight(df: pd.DataFrame) -> None:
    if df.empty:
        return
    worst = df.sort_values("bottleneck_rank").iloc[0]
    st.warning(
        f"**{worst['project_name']}** is the highest-risk project — "
        f"avg rating {worst['avg_rating']:.2f}, avg satisfaction {worst['avg_job_satisfaction']:.2f}."
    )


def cohort_insight(df: pd.DataFrame) -> None:
    if df.empty:
        return
    worst = df.sort_values("attrition_pct", ascending=False).iloc[0]
    best  = df.sort_values("attrition_pct").iloc[0]
    st.info(
        f"Highest attrition cohort: **{int(worst['hire_year'])}** ({worst['attrition_pct']:.1f}%). "
        f"Lowest: **{int(best['hire_year'])}** ({best['attrition_pct']:.1f}%)."
    )


def salary_band_insight(df: pd.DataFrame) -> None:
    if df.empty:
        return
    lowest  = df.sort_values("salary_band").iloc[0]
    highest = df.sort_values("salary_band").iloc[-1]
    st.info(
        f"Lowest salary band ({lowest['band_label']}): **{lowest['attrition_pct']:.1f}%** attrition. "
        f"Highest band ({highest['band_label']}): **{highest['attrition_pct']:.1f}%**."
    )
