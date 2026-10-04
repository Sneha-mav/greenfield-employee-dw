"""Design tokens, CSS injection, and chart theme for the entire app.

Single source of truth for all visual constants.
Call inject_css() once per page. Use apply_chart_theme() on every Plotly figure.
"""

import streamlit as st
import plotly.graph_objects as go

# ── Color tokens ──────────────────────────────────────────────────────────────
# Surfaces
COLOR_CANVAS      = "#F7F8FA"
COLOR_SURFACE     = "#FFFFFF"
COLOR_SURFACE_ALT = "#F3F4F6"

# Text
COLOR_TEXT_PRIMARY   = "#111827"
COLOR_TEXT_SECONDARY = "#6B7280"
COLOR_TEXT_MUTED     = "#9CA3AF"

# Borders
COLOR_BORDER = "#D1D5DB"

# Semantic
COLOR_ACCENT   = "#2563EB"
COLOR_POSITIVE = "#059669"
COLOR_WARNING  = "#D97706"
COLOR_NEGATIVE = "#DC2626"
COLOR_NEUTRAL  = "#6B7280"

# Chart palette
CHART_PRIMARY   = "#2563EB"
CHART_SECONDARY = "#64748B"
CHART_TERTIARY  = "#94A3B8"
CHART_POSITIVE  = "#059669"
CHART_WARNING   = "#D97706"
CHART_NEGATIVE  = "#DC2626"
CHART_BG        = "rgba(0,0,0,0)"

# Aliases used by charts.py
PRIMARY  = CHART_PRIMARY
DANGER   = CHART_NEGATIVE
WARNING  = CHART_WARNING
SUCCESS  = CHART_POSITIVE
NEUTRAL  = COLOR_NEUTRAL

# Thresholds
ATTRITION_HIGH   = 15.0
ATTRITION_MEDIUM = 10.0
SATISFACTION_LOW = 2.5

# Chart defaults
CHART_TEMPLATE = "plotly_white"
CHART_HEIGHT   = 400


# ── Helpers ───────────────────────────────────────────────────────────────────

def attrition_color(value: float) -> str:
    """Return semantic hex color for an attrition rate value."""
    if value > ATTRITION_HIGH:
        return CHART_NEGATIVE
    if value > ATTRITION_MEDIUM:
        return CHART_WARNING
    return CHART_POSITIVE


def fmt_number(value, prefix: str = "", suffix: str = "", decimals: int = 1) -> str:
    """Format large numbers with K/M/B abbreviation.

    Examples:
        fmt_number(268308)          -> "268.3K"
        fmt_number(2840000, "$")    -> "$2.8M"
        fmt_number(18.6, suffix="%")-> "18.6%"
    """
    if value is None:
        return "-"
    v = float(value)
    if abs(v) >= 1_000_000_000:
        return f"{prefix}{v / 1_000_000_000:.{decimals}f}B{suffix}"
    if abs(v) >= 1_000_000:
        return f"{prefix}{v / 1_000_000:.{decimals}f}M{suffix}"
    if abs(v) >= 1_000:
        return f"{prefix}{v / 1_000:.{decimals}f}K{suffix}"
    return f"{prefix}{v:.{decimals}f}{suffix}"


def apply_chart_theme(fig: go.Figure, title: str = "", height: int = CHART_HEIGHT) -> go.Figure:
    """Apply consistent chart theme. Call on every Plotly figure before returning."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=13, color=COLOR_TEXT_PRIMARY, family="Inter, system-ui, sans-serif"),
            x=0,
            xanchor="left",
        ),
        height=height,
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=COLOR_TEXT_SECONDARY),
        margin=dict(l=0, r=8, t=44, b=0),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(size=11, color=COLOR_TEXT_SECONDARY),
        ),
        hoverlabel=dict(
            bgcolor="#1F2937",
            font=dict(color="#F9FAFB", size=12, family="Inter, system-ui, sans-serif"),
            bordercolor="rgba(0,0,0,0)",
        ),
    )
    fig.update_xaxes(
        gridcolor=COLOR_SURFACE_ALT,
        gridwidth=1,
        linecolor=COLOR_BORDER,
        tickfont=dict(size=11, color=COLOR_TEXT_SECONDARY),
        title_font=dict(size=11, color=COLOR_TEXT_SECONDARY),
        zeroline=False,
    )
    fig.update_yaxes(
        gridcolor=COLOR_SURFACE_ALT,
        gridwidth=1,
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(size=11, color=COLOR_TEXT_SECONDARY),
        title_font=dict(size=11, color=COLOR_TEXT_SECONDARY),
        zeroline=False,
    )
    return fig


def inject_css() -> None:
    """Inject global CSS. Called once per page on every Streamlit rerun."""
    st.markdown(
        f"""
        <style>
        /* ── Page ───────────────────────────────────────────────────── */
        [data-testid="stAppViewContainer"] > .main {{
            background-color: {COLOR_CANVAS};
        }}
        [data-testid="stMainBlockContainer"] {{
            padding-top: 1.25rem;
        }}

        /* ── KPI cards ──────────────────────────────────────────────── */
        .metric-card {{
            background: {COLOR_SURFACE};
            border: 1px solid {COLOR_BORDER};
            box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.05);
            border-radius: 6px;
            padding: 14px 16px;
            min-height: 84px;
        }}
        .metric-label {{
            font-size: 0.7rem;
            font-weight: 500;
            color: {COLOR_TEXT_MUTED};
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 1.625rem;
            font-weight: 700;
            color: {COLOR_TEXT_PRIMARY};
            line-height: 1.2;
        }}
        .metric-delta-up      {{ color: {COLOR_POSITIVE}; font-size: 0.8rem; margin-top: 3px; }}
        .metric-delta-down    {{ color: {COLOR_NEGATIVE}; font-size: 0.8rem; margin-top: 3px; }}
        .metric-delta-neutral {{ color: {COLOR_NEUTRAL};  font-size: 0.8rem; margin-top: 3px; }}

        /* ── Section headers ─────────────────────────────────────────── */
        .section-header {{
            font-size: 0.8rem;
            font-weight: 600;
            color: {COLOR_TEXT_SECONDARY};
            text-transform: uppercase;
            letter-spacing: 0.08em;
            border-left: 3px solid {COLOR_ACCENT};
            padding-left: 10px;
            margin: 24px 0 12px 0;
        }}

        /* ── Sidebar ─────────────────────────────────────────────────── */
        [data-testid="stSidebar"][aria-expanded="true"] {{
            background: {COLOR_SURFACE};
            border-right: 1px solid {COLOR_BORDER};
            min-width: 248px !important;
            max-width: 248px !important;
        }}
        [data-testid="stSidebar"][aria-expanded="false"] {{
            min-width: 0 !important;
            max-width: 0 !important;
        }}
        [data-testid="stMainBlockContainer"] {{
            max-width: none !important;
            width: 100%;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {{
            border-radius: 6px;
            padding: 4px 6px;
            transition: background-color 120ms ease, color 120ms ease;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
            background: {COLOR_SURFACE_ALT};
            color: {COLOR_ACCENT};
        }}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: 0.4rem;
        }}

        /* ── Streamlit metric widget (native) ───────────────────────── */
        [data-testid="stMetric"] {{
            background: {COLOR_SURFACE};
            border: 1px solid {COLOR_BORDER};
            box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.05);
            border-radius: 8px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 112px;
            padding: 14px 16px;
        }}
        [data-testid="stMetricLabel"] {{
            align-items: flex-start;
            color: {COLOR_TEXT_SECONDARY};
            line-height: 1.25;
            min-height: 2.5rem;
        }}
        [data-testid="stMetricValue"] {{
            color: {COLOR_TEXT_PRIMARY};
            font-variant-numeric: tabular-nums;
            line-height: 1.1;
        }}
        /* ── Dashboard boards ───────────────────────────────────────── */
        [data-testid="stPlotlyChart"],
        [data-testid="stDataFrame"] {{
            background: {COLOR_SURFACE};
            border: 1px solid {COLOR_BORDER};
            box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.05);
            border-radius: 8px;
            box-sizing: border-box;
        }}
        [data-testid="stPlotlyChart"] {{
            padding: 4px 8px 0;
        }}
        [data-testid="stExpander"] {{
            border: 1px solid {COLOR_BORDER};
            border-radius: 8px;
            background: {COLOR_SURFACE};
        }}
        [data-testid="stForm"] {{
            border: 1px solid {COLOR_BORDER};
            border-radius: 8px;
            background: {COLOR_SURFACE};
            padding: 1rem;
        }}
        @media (max-width: 900px) {{
            [data-testid="stMetric"] {{
                min-height: 104px;
            }}
        }}
        /* ── Input widget borders ───────────────────────────── */
        [data-baseweb="input"] > div,
        [data-baseweb="base-input"] > div {{
            border: 1.5px solid {COLOR_BORDER} !important;
            border-radius: 6px !important;
            transition: border-color 0.15s ease;
        }}
        [data-baseweb="input"]:focus-within > div,
        [data-baseweb="base-input"]:focus-within > div {{
            border-color: {COLOR_ACCENT} !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
        }}
        [data-baseweb="select"] > div:first-child {{
            border: 1.5px solid {COLOR_BORDER} !important;
            border-radius: 6px !important;
            transition: border-color 0.15s ease;
        }}
        [data-baseweb="select"]:focus-within > div:first-child {{
            border-color: {COLOR_ACCENT} !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
        }}
        /* Date input */
        [data-testid="stDateInput"] [data-baseweb="input"] > div {{
            border: 1.5px solid {COLOR_BORDER} !important;
            border-radius: 6px !important;
        }}
        /* Number input */
        [data-testid="stNumberInput"] [data-baseweb="input"] > div {{
            border: 1.5px solid {COLOR_BORDER} !important;
            border-radius: 6px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str) -> None:
    """Render a styled section heading."""
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
