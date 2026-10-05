"""KPI metric cards — reusable across any page.

Usage::

    from app.components.kpi_cards import KPIMetric, render_kpi_row

    render_kpi_row([
        KPIMetric("Attrition Rate", "18.4%", delta="+2.1pp", delta_positive=False),
        KPIMetric("Avg Rating",     "3.42",  delta="+0.12 YoY", delta_positive=True),
    ])
"""

from dataclasses import dataclass
from typing import Optional
import streamlit as st


@dataclass
class KPIMetric:
    label: str
    value: str
    delta: Optional[str] = None
    delta_positive: Optional[bool] = None


def render_kpi_row(metrics: list, cols: int = 0) -> None:
    """Render a responsive row of styled KPI cards."""
    n = cols if cols > 0 else len(metrics)
    columns = st.columns(n)
    for i, m in enumerate(metrics):
        with columns[i % n]:
            if m.delta_positive is True:
                delta_class = "metric-delta-up"
            elif m.delta_positive is False:
                delta_class = "metric-delta-down"
            else:
                delta_class = "metric-delta-neutral"

            delta_html = (
                f'<div class="{delta_class}">{m.delta}</div>' if m.delta else ""
            )
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">{m.label}</div>'
                f'<div class="metric-value">{m.value}</div>'
                f'{delta_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
