"""All Plotly chart builder functions.

Every function accepts a pandas DataFrame and returns a plotly Figure.
No Streamlit calls here — pages call st.plotly_chart(fig, config=_CFG).
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.components.theme import (
    apply_chart_theme,
    attrition_color,
    CHART_BG, CHART_HEIGHT, CHART_TEMPLATE,
    CHART_PRIMARY, CHART_SECONDARY,
    CHART_POSITIVE, CHART_WARNING, CHART_NEGATIVE,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_BORDER, COLOR_SURFACE_ALT,
    PRIMARY, DANGER, WARNING, SUCCESS, NEUTRAL,
    ATTRITION_HIGH, SATISFACTION_LOW,
)

# Suppress Plotly toolbar on all charts
_CFG = {"displayModeBar": False}


def yoy_trend_line(df: pd.DataFrame) -> go.Figure:
    """Avg rating per year with YoY delta annotations and review volume bars."""
    if df.empty:
        return go.Figure()

    # Determine trend direction for semantic line color
    first_rating = float(df.iloc[0]["avg_rating"])
    last_rating  = float(df.iloc[-1]["avg_rating"])
    if last_rating > first_rating:
        _line_color = CHART_POSITIVE
    elif last_rating < first_rating:
        _line_color = CHART_NEGATIVE
    else:
        _line_color = CHART_PRIMARY

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=df["review_year"],
            y=df["review_count"],
            name="Review Count",
            marker_color="rgba(100,116,139,0.35)",
            hovertemplate="%{y:,} reviews<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=df["review_year"],
            y=df["avg_rating"].apply(float),
            mode="lines+markers",
            name="Avg Rating",
            line=dict(color=_line_color, width=2.5),
            marker=dict(size=8, color=_line_color),
            hovertemplate="Year %{x}<br>Avg Rating: %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.update_yaxes(title_text="Avg Rating", secondary_y=False, range=[1, 5.8])
    fig.update_yaxes(title_text="Review Count", secondary_y=True, showgrid=False)
    fig.update_xaxes(tickformat="d")
    apply_chart_theme(fig, "Performance rating trend")
    fig.add_hline(
        y=3.0,
        line_dash="dot",
        line_color=CHART_WARNING,
        opacity=0.45,
        annotation_text="Midpoint 3.0",
        annotation_position="bottom right",
        annotation_font=dict(color=CHART_WARNING, size=10),
    )
    return fig


def attrition_by_dept_bar(
    df: pd.DataFrame, attention_threshold: float = ATTRITION_HIGH
) -> go.Figure:
    """Readable department columns with a configurable attention threshold."""
    if df.empty:
        return go.Figure()

    df = df.sort_values("attrition_rate_pct", ascending=False).copy()
    colors = [attrition_color(float(v)) for v in df["attrition_rate_pct"]]

    fig = go.Figure(
        go.Bar(
            x=df["department_name"],
            y=df["attrition_rate_pct"].apply(float),
            marker_color=colors,
            text=df["attrition_rate_pct"].apply(lambda v: f"{float(v):.1f}%"),
            textposition="outside",
            textfont=dict(size=11, color=COLOR_TEXT_PRIMARY),
            customdata=df[["headcount", "leavers"]].values,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Attrition: %{y:.1f}%<br>"
                "Headcount: %{customdata[0]:,}<br>"
                "Leavers: %{customdata[1]:,}"
                "<extra></extra>"
            ),
        )
    )
    fig.add_hline(
        y=attention_threshold,
        line_dash="dash",
        line_color=CHART_WARNING,
        opacity=0.85,
    )
    fig.add_annotation(
        x=1,
        y=attention_threshold,
        xref="paper",
        yref="y",
        text=f"Attention threshold · {attention_threshold:.0f}%",
        showarrow=False,
        xanchor="right",
        font=dict(color=CHART_WARNING, size=10),
        bgcolor="rgba(255, 247, 237, 0.96)",
        bordercolor=CHART_WARNING,
        borderwidth=1,
        borderpad=3,
    )
    maximum = max(float(df["attrition_rate_pct"].max()), float(attention_threshold))
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Attrition %", range=[0, maximum * 1.28])
    apply_chart_theme(fig, "Attrition rate by department")
    fig.update_layout(margin=dict(l=0, r=8, t=66, b=0))
    # Add legend key for attrition risk colours
    for _label, _color in [
        ("Low  <10%",       CHART_POSITIVE),
        ("Moderate 10–15%", CHART_WARNING),
        ("High  >15%",      CHART_NEGATIVE),
    ]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=10, color=_color, symbol="square"),
            name=_label,
            showlegend=True,
        ))
    fig.update_layout(legend=dict(title_text="Attrition risk", x=1.0, xanchor="right", y=1.0))
    return fig


def satisfaction_by_dept_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: avg job satisfaction per department."""
    if df.empty or "avg_job_satisfaction" not in df.columns:
        return go.Figure()

    df = df.sort_values("avg_job_satisfaction", ascending=True).copy()
    colors = [
        CHART_NEGATIVE if float(v) < SATISFACTION_LOW - 0.5
        else CHART_WARNING if float(v) < SATISFACTION_LOW
        else CHART_POSITIVE
        for v in df["avg_job_satisfaction"]
    ]

    fig = go.Figure(
        go.Bar(
            x=df["avg_job_satisfaction"].apply(float),
            y=df["department_name"],
            orientation="h",
            marker_color=colors,
            text=df["avg_job_satisfaction"].apply(lambda v: f"{float(v):.2f}"),
            textposition="outside",
            textfont=dict(size=11, color=COLOR_TEXT_SECONDARY),
            hovertemplate="<b>%{y}</b><br>Avg Satisfaction: %{x:.2f} / 4<extra></extra>",
        )
    )
    fig.add_vline(
        x=SATISFACTION_LOW,
        line_dash="dash",
        line_color=CHART_WARNING,
        opacity=0.6,
        annotation_text="Threshold",
        annotation_font=dict(color=CHART_WARNING, size=10),
    )
    fig.update_xaxes(title_text="Avg Job Satisfaction (1-4)", range=[0, 4.6])
    fig.update_yaxes(title_text="")
    apply_chart_theme(fig, "Job Satisfaction by Department")
    return fig


def salary_vs_attrition_scatter(df: pd.DataFrame) -> go.Figure:
    """Bubble chart: salary hike % vs attrition rate, sized by headcount."""
    if df.empty or "avg_salary_hike_pct" not in df.columns:
        return go.Figure()

    plot_df = df.copy()
    plot_df["attrition_rate_pct"]  = plot_df["attrition_rate_pct"].apply(float)
    plot_df["avg_salary_hike_pct"] = plot_df["avg_salary_hike_pct"].apply(float)
    plot_df["headcount"]           = plot_df["headcount"].apply(int)

    fig = px.scatter(
        plot_df,
        x="avg_salary_hike_pct",
        y="attrition_rate_pct",
        size="headcount",
        color="attrition_rate_pct",
        text="department_name",
        color_continuous_scale=[CHART_POSITIVE, CHART_WARNING, CHART_NEGATIVE],
        size_max=48,
        template=CHART_TEMPLATE,
        height=CHART_HEIGHT,
        labels={
            "avg_salary_hike_pct": "Avg Salary Hike %",
            "attrition_rate_pct":  "Attrition %",
            "headcount":           "Headcount",
        },
        hover_data={"headcount": True, "department_name": False},
    )
    fig.update_traces(textposition="top center", textfont=dict(size=10))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=0, r=8, t=44, b=0),
        coloraxis_showscale=False,
    )
    apply_chart_theme(fig, "Salary Hike vs. Attrition")
    return fig


def cohort_attrition_bar(df: pd.DataFrame) -> go.Figure:
    """Bar + dotted line: attrition rate and avg rating by hire year cohort."""
    if df.empty:
        return go.Figure()

    plot_df = df.copy()
    plot_df["attrition_pct"] = plot_df["attrition_pct"].apply(float)
    plot_df["avg_rating"]    = plot_df["avg_rating"].apply(float)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    colors = [attrition_color(v) for v in plot_df["attrition_pct"]]
    fig.add_trace(
        go.Bar(
            x=plot_df["hire_year"],
            y=plot_df["attrition_pct"],
            name="Attrition %",
            marker_color=colors,
            hovertemplate="Cohort %{x}<br>Attrition: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["hire_year"],
            y=plot_df["avg_rating"],
            mode="lines+markers",
            name="Avg Rating",
            line=dict(color=CHART_PRIMARY, width=2, dash="dot"),
            marker=dict(size=6),
            hovertemplate="Cohort %{x}<br>Avg Rating: %{y:.2f}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="Attrition %", secondary_y=False)
    fig.update_yaxes(title_text="Avg Rating",  secondary_y=True, range=[1, 5])
    fig.update_xaxes(tickformat="d")
    apply_chart_theme(fig, "Attrition by Hire Year Cohort")
    # Add legend key for attrition risk colours
    for _label, _color in [
        ("Low  <10%",       CHART_POSITIVE),
        ("Moderate 10–15%", CHART_WARNING),
        ("High  >15%",      CHART_NEGATIVE),
    ]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=10, color=_color, symbol="square"),
            name=_label,
            showlegend=True,
        ))
    return fig


def salary_band_attrition_bar(df: pd.DataFrame) -> go.Figure:
    """Bar chart: attrition rate per salary quintile (NTILE 5)."""
    if df.empty:
        return go.Figure()

    plot_df = df.copy()
    plot_df["attrition_pct"] = plot_df["attrition_pct"].apply(float)

    colors = [attrition_color(v) for v in plot_df["attrition_pct"]]
    fig = go.Figure(
        go.Bar(
            x=plot_df["band_label"],
            y=plot_df["attrition_pct"],
            marker_color=colors,
            text=plot_df["attrition_pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            textfont=dict(size=11, color=COLOR_TEXT_SECONDARY),
            customdata=plot_df[["headcount", "leavers"]].values,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Attrition: %{y:.1f}%<br>"
                "Headcount: %{customdata[0]:,}<br>"
                "Leavers: %{customdata[1]:,}"
                "<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(title_text="Salary Band")
    fig.update_yaxes(title_text="Attrition %")
    apply_chart_theme(fig, "Attrition by Salary Band (NTILE 5)")
    return fig


def scd2_gantt(df: pd.DataFrame, emp_name: str) -> go.Figure:
    """Gantt timeline: one bar per recorded employee history entry."""
    if df.empty:
        return go.Figure()

    now = pd.Timestamp.now()
    df = df.copy()
    df["version_label"] = df["version_num"].apply(lambda n: f"Version {n}")
    df["end_display"]   = df["end_date"].apply(
        lambda d: now if str(d) >= "9999-01-01" else pd.Timestamp(str(d))
    )
    df["start_display"] = pd.to_datetime(df["start_date"].astype(str))
    df["income_fmt"]    = df["monthly_income"].apply(lambda v: f"${float(v):,.0f}")

    fig = px.timeline(
        df,
        x_start="start_display",
        x_end="end_display",
        y="version_label",
        color="department_name",
        color_discrete_sequence=[
            "#2563EB", "#059669", "#D97706", "#DC2626", "#7C3AED",
            "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
        ],
        hover_data={
            "job_role":     True,
            "job_level":    True,
            "income_fmt":   True,
            "start_display": False,
            "end_display":   False,
        },
        template=CHART_TEMPLATE,
        height=max(200, 80 + 60 * len(df)),
        labels={"department_name": "Department", "income_fmt": "Income"},
    )
    fig.update_yaxes(autorange="reversed", title_text="")
    fig.update_xaxes(title_text="")
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=0, r=8, t=44, b=0),
        legend_title="Department",
    )
    apply_chart_theme(fig, f"Employee history — {emp_name}")
    return fig


def bottleneck_scatter(df: pd.DataFrame) -> go.Figure:
    """Scatter: avg rating vs satisfaction per project, sized by review count."""
    if df.empty:
        return go.Figure()

    plot_df = df.copy()
    plot_df["avg_rating"]          = plot_df["avg_rating"].apply(float)
    plot_df["avg_job_satisfaction"] = plot_df["avg_job_satisfaction"].apply(float)

    fig = px.scatter(
        plot_df,
        x="avg_job_satisfaction",
        y="avg_rating",
        size="review_count",
        color="bottleneck_rank",
        text="project_name",
        color_continuous_scale=[CHART_NEGATIVE, CHART_WARNING, CHART_POSITIVE],
        template=CHART_TEMPLATE,
        height=CHART_HEIGHT,
        labels={
            "avg_job_satisfaction": "Avg Job Satisfaction",
            "avg_rating":           "Avg Rating",
            "review_count":         "Reviews",
            "bottleneck_rank":      "Risk Rank",
        },
    )
    fig.update_traces(textposition="top center", textfont=dict(size=10))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=0, r=8, t=44, b=0),
        coloraxis_showscale=False,
    )
    apply_chart_theme(fig, "Project Health — Lower Left = Highest Risk")
    return fig


# Public config dict for st.plotly_chart calls
PLOTLY_CONFIG = _CFG
