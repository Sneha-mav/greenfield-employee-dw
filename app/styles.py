def apply_custom_css(theme="Light"):
    import streamlit as st

    # ── Colour tokens ──────────────────────────────────────────────────
    if theme == "Dark":
        bg            = "#0B1120"
        surface       = "#1E293B"
        txt_primary   = "#F8FAFC"
        txt_secondary = "#94A3B8"
        border        = "#334155"
        accent        = "#3B82F6"
        accent_hover  = "#2563EB"
        shadow        = "0 4px 12px rgba(0,0,0,0.45)"
        input_bg      = "#0F172A"
    else:                                   # ← default Light
        bg            = "#F0F4F8"           # very light blue-grey page
        surface       = "#FFFFFF"           # pure white cards / sidebar
        txt_primary   = "#0F172A"           # near-black navy headings
        txt_secondary = "#475569"           # slate-600 labels
        border        = "#CBD5E1"           # slate-300 borders
        accent        = "#2563EB"           # blue-600 buttons / highlights
        accent_hover  = "#1D4ED8"           # blue-700 hover
        shadow        = "0 2px 8px rgba(15,23,42,0.08)"
        input_bg      = "#FFFFFF"

    st.markdown(f"""
        <style>
        /* ── Google Font ───────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* ── Hide Streamlit chrome ─────────────────────────────────── */
        #MainMenu {{visibility: hidden;}}
        footer     {{visibility: hidden;}}
        header     {{visibility: hidden;}}

        /* ── Page background & font ────────────────────────────────── */
        html, body, [data-testid="stAppViewContainer"],
        .stApp, .main .block-container {{
            background-color: {bg} !important;
            color: {txt_primary} !important;
            font-family: 'Inter', system-ui, sans-serif !important;
        }}
        .main .block-container {{
            padding-top: 1.25rem !important;
            padding-bottom: 1.5rem !important;
            max-width: 1400px;
        }}

        /* ── Section block backgrounds (stop Streamlit injecting dark) */
        section[data-testid="stSidebar"],
        div[data-testid="stVerticalBlock"],
        div[data-testid="column"] {{
            background-color: transparent !important;
        }}

        /* ── Typography ────────────────────────────────────────────── */
        h1, h2, h3, h4, h5, h6,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
        .stMarkdown p, label, .stRadio label,
        div[data-testid="stMetricLabel"] p {{
            color: {txt_primary} !important;
            font-family: 'Inter', system-ui, sans-serif !important;
        }}
        h1 {{
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
            margin-bottom: 0.15rem !important;
        }}
        h3 {{
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            color: {txt_primary} !important;
            margin-top: 0.4rem !important;
            margin-bottom: 0.25rem !important;
        }}
        p, li, span {{
            color: {txt_secondary} !important;
        }}

        /* ── KPI metric cards ──────────────────────────────────────── */
        div[data-testid="metric-container"] {{
            background-color: {surface} !important;
            border: 1px solid {border};
            border-top: 3px solid {accent};
            border-radius: 8px;
            padding: 12px 16px !important;
            box-shadow: {shadow};
            transition: transform 0.18s, box-shadow 0.18s;
        }}
        div[data-testid="metric-container"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(37,99,235,0.10);
        }}
        div[data-testid="stMetricValue"] {{
            color: {txt_primary} !important;
            font-size: 1.55rem !important;
            font-weight: 700 !important;
            line-height: 1.2 !important;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {txt_secondary} !important;
            font-size: 0.74rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2px !important;
        }}

        /* ── Expanders ─────────────────────────────────────────────── */
        div[data-testid="stExpander"] {{
            background-color: {surface} !important;
            border: 1px solid {border} !important;
            border-radius: 10px !important;
            box-shadow: {shadow};
            margin-bottom: 14px;
        }}
        div[data-testid="stExpander"] summary p {{
            color: {txt_primary} !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
        }}

        /* ── Forms ─────────────────────────────────────────────────── */
        div[data-testid="stForm"] {{
            background-color: {surface} !important;
            border: 1px solid {border} !important;
            border-radius: 10px !important;
            padding: 24px !important;
            box-shadow: {shadow};
        }}

        /* ── Buttons ───────────────────────────────────────────────── */
        .stButton > button, button[kind="formSubmit"] {{
            background-color: {accent} !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 7px !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            padding: 0.55rem 1.25rem !important;
            transition: background-color 0.18s, transform 0.15s, box-shadow 0.15s;
            box-shadow: 0 2px 6px rgba(37,99,235,0.25) !important;
        }}
        .stButton > button:hover, button[kind="formSubmit"]:hover {{
            background-color: {accent_hover} !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 10px rgba(37,99,235,0.35) !important;
        }}
        .stButton > button:active {{
            transform: translateY(0) !important;
        }}

        /* ── Inputs ────────────────────────────────────────────────── */
        input, textarea, div[data-baseweb="select"] > div {{
            background-color: {input_bg} !important;
            border-color: {border} !important;
            border-radius: 7px !important;
            color: {txt_primary} !important;
        }}

        /* ── DataFrames / tables ───────────────────────────────────── */
        div[data-testid="stDataFrame"],
        div[data-testid="stDataFrameContainer"] {{
            background-color: {surface} !important;
            border: 1px solid {border} !important;
            border-radius: 10px !important;
            overflow: hidden;
            box-shadow: {shadow};
        }}

        /* ── Sidebar ───────────────────────────────────────────────── */
        section[data-testid="stSidebar"] > div:first-child {{
            background-color: {surface} !important;
            border-right: 1px solid {border};
            padding-top: 1.5rem;
        }}
        [data-testid="stSidebarNav"] {{
            display: none !important;
        }}

        /* ── Sidebar brand block ───────────────────────────────────── */
        .sidebar-brand {{
            padding: 0 20px 24px 20px;
            border-bottom: 1px solid {border};
            margin-bottom: 20px;
        }}
        .sidebar-brand-logo {{
            font-size: 2rem;
            font-weight: 800;
            color: {accent};
            line-height: 1;
            margin-bottom: 6px;
        }}
        .sidebar-brand-title {{
            font-size: 1rem;
            font-weight: 700;
            color: {txt_primary} !important;
        }}
        .sidebar-brand-subtitle {{
            font-size: 0.72rem;
            color: {txt_secondary} !important;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-top: 3px;
        }}

        /* ── Info / alert boxes ────────────────────────────────────── */
        div[data-testid="stInfo"] {{
            background-color: #EFF6FF !important;
            border-left: 4px solid {accent} !important;
            color: #1E40AF !important;
            border-radius: 6px;
        }}
        div[data-testid="stSuccess"] {{
            background-color: #F0FDF4 !important;
            border-left: 4px solid #16A34A !important;
            border-radius: 6px;
        }}
        div[data-testid="stWarning"] {{
            background-color: #FFFBEB !important;
            border-left: 4px solid #D97706 !important;
            border-radius: 6px;
        }}
        div[data-testid="stError"] {{
            background-color: #FEF2F2 !important;
            border-left: 4px solid #DC2626 !important;
            border-radius: 6px;
        }}

        /* ── Horizontal rule ───────────────────────────────────────── */
        hr {{
            border: none !important;
            border-top: 1px solid {border} !important;
            margin: 1.2rem 0 !important;
        }}
        </style>
    """, unsafe_allow_html=True)
