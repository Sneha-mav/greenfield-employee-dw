# Dashboard design rationale

The dashboard uses native Streamlit layout primitives where possible: four `st.metric` cards for the executive snapshot, `st.tabs` for distinct decision questions, `st.columns` for the two-chart overview, `st.sidebar` for persistent slicers, and `st.expander` for secondary tables. This follows Streamlit's documented layout model and avoids fragile layout workarounds.

| Decision | Why it fits the HR use case | Evidence |
|---|---|---|
| Four equal KPI cards | Supports a fast executive scan without making one metric look more important due to different card sizing. | [Streamlit `st.metric`](https://docs.streamlit.io/develop/api-reference/data/st.metric) |
| Sidebar filters; top HR navigation | Keeps filters persistent while avoiding a technical, vertically stacked page menu. | [Streamlit layouts and containers](https://docs.streamlit.io/develop/concepts/design/layouts-and-containers) |
| Line plus review-volume bars | A line shows the performance trend over time; the bars explain the volume supporting each period. | [Plotly line charts](https://plotly.com/python/line-charts/) |
| Horizontal department attrition bars | Department names remain readable and the attention threshold can be displayed as a visible reference line. | [Plotly bar charts](https://plotly.com/python/bar-charts/) |
| Workforce and project scatter plots | Makes trade-offs visible: department satisfaction versus attrition, and project satisfaction versus performance, with bubble size for workload. | [Plotly basic charts](https://plotly.com/python/basic-charts/) |
| Expanders for tables and detailed checks | Preserves every analytical capability without turning the default screen into a long report. | [Streamlit layouts and containers](https://docs.streamlit.io/develop/concepts/design/layouts-and-containers) |

The retention queue is explicitly a threshold-based review list, not an AI attrition prediction. The dashboard uses amber/red only for configured attention signals and keeps the default palette blue/neutral/green.
