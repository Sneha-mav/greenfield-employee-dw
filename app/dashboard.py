import streamlit as st
import plotly.express as px
import pandas as pd
from db_queries import (
    get_dashboard_data, get_employees, get_projects, get_reviews,
    get_department_breakdown, get_yoy_trend, get_top_performers,
    get_attrition_risk, get_dept_avg_performance, get_departments,
    show_fallback_warning, reset_fallback_flag,
)

# ── Shared Plotly base layout defaults ─────────────────────────────────
BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", size=11, color="#475569"),
)

BLUE_PALETTE = [
    "#2563EB", "#3B82F6", "#60A5FA", "#93C5FD",
    "#1D4ED8", "#0EA5E9", "#0284C7", "#0369A1",
]


def _section(title: str):
    """Render a styled compact section heading."""
    st.markdown(f"### {title}")


def render_dashboard():
    reset_fallback_flag()
    st.markdown("<h1 style='margin-bottom:0px;'>Dashboard Overview</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#64748B;font-size:0.88rem;margin-top:0px;margin-bottom:12px;'>"
        "Enterprise HR Management &amp; Workforce Analytics</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    # Fetch all data first, then emit one banner if fallback was triggered
    data     = get_dashboard_data()
    dept_df  = get_department_breakdown()
    df_proj  = get_projects()
    df_risk  = get_attrition_risk()
    show_fallback_warning()

    # ── KPI row (single compact row on desktop) ────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Active Employees", f"{data['total_employees']:,}")
    k2.metric("Total Departments", data["total_departments"])
    k3.metric("Total Projects", data["total_projects"])
    k4.metric("Average Performance Rating (out of 5)", f"{data['avg_performance']}")

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

    # ── Two-column 2x2 chart grid ──────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        _section("🏢 Active Employees by Department")
        if not dept_df.empty:
            fig = px.pie(
                dept_df, names="Department", values="Count",
                hole=0.52, color_discrete_sequence=BLUE_PALETTE,
            )
            fig.update_traces(
                textposition="inside",
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>"
            )
            fig.update_layout(
                **BASE_LAYOUT,
                height=265,
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.18,
                    xanchor="center",
                    x=0.5,
                    title_text=""
                )
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            st.caption("Distribution of active headcount across organizational departments.")
        else:
            st.info("No employee data available.")

        _section("⚠️ Historical Attrition Risk by Department (%)")
        if not df_risk.empty and "Attrition %" in df_risk.columns:
            fig_a = px.bar(
                df_risk, x="Department", y="Attrition %",
                color="Department",
                color_discrete_sequence=["#2563EB", "#60A5FA", "#EF4444"],
                text_auto=".1f",
                hover_data=["Employees", "Avg Job Satisfaction"],
                labels={"Attrition %": "Attrition Rate (%)", "Department": "Department"}
            )
            fig_a.update_layout(
                **BASE_LAYOUT,
                height=265,
                showlegend=False,
                margin=dict(t=15, b=20, l=45, r=15)
            )
            fig_a.update_traces(textposition="outside")
            st.plotly_chart(fig_a, width="stretch", config={"displayModeBar": False})
            st.caption("Historical employee turnover percentage per department.")
        else:
            st.info("Attrition risk data not yet available (requires OLAP tables to be loaded).")

    with col_r:
        _section("📋 Largest Active Projects")
        if not df_proj.empty and "Assigned Employees" in df_proj.columns:
            active_projects = df_proj[df_proj["Status"] == "Active"] if "Status" in df_proj.columns else df_proj
            plot_df = active_projects if not active_projects.empty else df_proj
            top_projects = plot_df.nlargest(6, "Assigned Employees").sort_values("Assigned Employees", ascending=True)
            fig_p = px.bar(
                top_projects, y="Project Name", x="Assigned Employees",
                orientation="h",
                color="Assigned Employees",
                color_continuous_scale=[[0, "#93C5FD"], [1, "#1D4ED8"]],
                text_auto=True,
                labels={"Assigned Employees": "Assigned Headcount", "Project Name": ""}
            )
            fig_p.update_layout(
                **BASE_LAYOUT,
                height=265,
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(t=15, b=20, l=10, r=20)
            )
            fig_p.update_traces(textposition="inside")
            st.plotly_chart(fig_p, width="stretch", config={"displayModeBar": False})
            st.caption("Top active projects ranked by total assigned employee headcount.")
        else:
            st.info("No project data available.")

        _section("🎯 Project Resource Allocation")
        if not df_proj.empty and "Assigned Employees" in df_proj.columns:
            df_alloc = df_proj.copy()
            df_alloc["Assigned Employees"] = (
                pd.to_numeric(df_alloc["Assigned Employees"], errors="coerce")
                .fillna(0)
                .astype(int)
            )

            # Top 10 projects by assigned headcount (sorted ascending for clean top-down bar ranking)
            top_alloc = df_alloc.nlargest(10, "Assigned Employees").sort_values("Assigned Employees", ascending=True)

            # Calculate real database assignment metrics
            active_mask = (
                df_alloc["Status"].str.strip().str.lower() == "active"
                if "Status" in df_alloc.columns else pd.Series(True, index=df_alloc.index)
            )
            active_assignments = int(df_alloc[active_mask]["Assigned Employees"].sum())
            total_assignments = int(df_alloc["Assigned Employees"].sum())

            # Horizontal Bar Chart for optimal name readability
            fig_alloc = px.bar(
                top_alloc,
                x="Assigned Employees",
                y="Project Name",
                orientation="h",
                text_auto=True,
                labels={
                    "Assigned Employees": "Assigned Employees",
                    "Project Name": "Project Name",
                },
                hover_data={
                    "Assigned Employees": ":,",
                    "Project Name": True,
                    "Department": True if "Department" in top_alloc.columns else False,
                    "Status": True if "Status" in top_alloc.columns else False,
                }
            )
            has_dept_status = "Department" in top_alloc.columns and "Status" in top_alloc.columns
            # Use a solid professional blue
            fig_alloc.update_traces(
                marker_color="#2563EB",
                textposition="inside",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Assigned Employees: <b>%{x:,}</b><br>"
                    "Department: %{customdata[1]}<br>"
                    "Status: %{customdata[2]}<extra></extra>"
                ) if has_dept_status else
                "<b>%{y}</b><br>Assigned Employees: <b>%{x:,}</b><extra></extra>"
            )
            fig_alloc.update_layout(
                **BASE_LAYOUT,
                height=280,
                margin=dict(t=15, b=25, l=10, r=20),
                xaxis=dict(title="Assigned Employee Count", showgrid=True, gridcolor="#F1F5F9", zerolinecolor="#CBD5E1"),
                yaxis=dict(title="", tickfont=dict(size=11, color="#334155")),
            )
            st.plotly_chart(fig_alloc, width="stretch", config={"displayModeBar": False})
            st.caption(
                f"Top 10 projects by employee allocation. "
                f"Active Assignments: **{active_assignments:,}** | Total Tracked: **{total_assignments:,}**"
            )
        else:
            st.info("No project resourcing data available.")


def render_analytics():
    reset_fallback_flag()
    st.markdown("<h1 style='margin-bottom:0px;'>Workforce Analytics</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#64748B;font-size:0.88rem;margin-top:0px;margin-bottom:12px;'>"
        "Performance evaluations, longitudinal trends, and department talent rankings.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Filters (compact row) ──────────────────────────────────────────
    _section("🔍 Filters")
    f1, f2 = st.columns(2)
    dept_options = ["All"] + get_departments()
    dept_filter  = f1.selectbox("Department", dept_options, key="analytics_dept")
    year_options = ["All"] + [str(y) for y in range(2025, 2019, -1)]
    year_filter  = f2.selectbox("Review Year", year_options, key="analytics_year")

    selected_dept = None if dept_filter == "All" else dept_filter
    selected_year = None if year_filter == "All" else int(year_filter)

    # Fetch all data after filters are read, then single banner
    df_dept_perf = get_dept_avg_performance(department=selected_dept, year=selected_year)
    df_yoy       = get_yoy_trend()
    df_top       = get_top_performers(department=selected_dept)
    show_fallback_warning()

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

    # ── Two-column chart row ───────────────────────────────────────────
    col_a1, col_a2 = st.columns(2)

    with col_a1:
        _section("📊 Departmental Performance Averages")
        if not df_dept_perf.empty:
            avg = df_dept_perf.groupby("Department")["Rating"].mean().reset_index()
            fig_d = px.bar(
                avg, x="Department", y="Rating",
                color="Department", color_discrete_sequence=BLUE_PALETTE,
                text_auto=".2f",
                labels={"Rating": "Avg Rating (1-5)", "Department": "Department"}
            )
            fig_d.update_layout(
                **BASE_LAYOUT,
                height=265,
                yaxis=dict(range=[0, 5]),
                showlegend=False,
                margin=dict(t=15, b=20, l=45, r=15)
            )
            fig_d.update_traces(textposition="outside")
            st.plotly_chart(fig_d, width="stretch", config={"displayModeBar": False})
            st.caption("Average rating achieved across departments for selected filters.")
        else:
            st.warning("No performance records match the selected filters.")

    with col_a2:
        _section("📈 Historical Performance Rating Trajectory")
        if not df_yoy.empty and "Avg Rating" in df_yoy.columns:
            extra = ["Reviews"] if "Reviews" in df_yoy.columns else []
            fig_yoy = px.line(
                df_yoy, x="Year", y="Avg Rating", markers=True,
                color_discrete_sequence=["#2563EB"],
                labels={"Avg Rating": "Avg Rating (1-5)", "Year": "Review Year"},
                custom_data=extra,
            )
            if extra:
                fig_yoy.update_traces(
                    hovertemplate="%{x}<br>Avg Rating: %{y:.2f}<br>Reviews: %{customdata[0]:,}"
                )
            fig_yoy.update_layout(
                **BASE_LAYOUT,
                height=265,
                yaxis=dict(range=[1, 5]),
                margin=dict(t=15, b=20, l=45, r=15)
            )
            st.plotly_chart(fig_yoy, width="stretch", config={"displayModeBar": False})
            st.caption("Longitudinal performance rating trajectory across review cycles.")
        else:
            st.info("Year-over-year data not available.")

    # ── Top performers (DENSE_RANK via OLAP) ───────────────────────────
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    _section("🏆 Top Performers by Department")
    st.caption("Ranked by average review score via SQL DENSE_RANK() in fact_performance_reviews (minimum 3 reviews required).")
    if not df_top.empty:
        display_cols = [c for c in ["Department", "Name", "Avg Score", "Rating", "Rank", "Reviews"]
                        if c in df_top.columns]
        st.dataframe(
            df_top[display_cols].style.format(
                {"Rank": "{:.0f}", "Avg Score": "{:.2f}", "Rating": "{:.2f}"}
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No qualifying performers found (each employee needs ≥ 3 reviews).")
