"""
ui.py
------------------------------------------------------------------
Small design-system layer for CrowdFlow AI.

Keeping all styling / reusable visual components in one place means
app.py stays focused on layout & data-wiring, and the look of the
app can be tuned from a single file.
------------------------------------------------------------------
"""
import streamlit as st

# ---------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------
PRIMARY = "#00E676"      # calm / low congestion
WARNING = "#FF9100"      # high congestion
DANGER = "#FF1744"       # critical congestion
INFO = "#29B6F6"         # neutral accent
BG = "#0B0E14"
CARD_BG = "#151A23"
CARD_BG_ALT = "#1B2230"
BORDER = "#262E3D"
TEXT = "#F5F7FA"
TEXT_MUTED = "#8B93A7"

STATUS_COLORS = {
    "green": PRIMARY,
    "yellow": "#FFEA00",
    "orange": WARNING,
    "red": DANGER,
}

STATUS_LABELS = {
    "green": "Low",
    "yellow": "Medium",
    "orange": "High",
    "red": "Critical",
}


def inject_css():
    """Injects the app-wide stylesheet. Call once near the top of app.py."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        .stApp {{
            background: radial-gradient(circle at 15% 0%, #101623 0%, {BG} 45%) fixed;
            color: {TEXT};
        }}

        section[data-testid="stSidebar"] {{
            background: #0A0D13;
            border-right: 1px solid {BORDER};
        }}

        /* Hide default streamlit chrome clutter */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}

        h1, h2, h3, h4 {{
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }}

        /* ---------- Header ---------- */
        .app-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 2px 18px 2px;
            border-bottom: 1px solid {BORDER};
            margin-bottom: 18px;
        }}
        .app-header .title-block .eyebrow {{
            color: {TEXT_MUTED};
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 2px;
        }}
        .app-header .title-block h1 {{
            font-size: 1.7rem;
            margin: 0;
        }}
        .live-pill {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 6px 14px;
            border-radius: 999px;
            background: {CARD_BG};
            border: 1px solid {BORDER};
            font-size: 0.82rem;
            font-weight: 600;
            color: {TEXT_MUTED};
        }}
        .live-dot {{
            width: 8px; height: 8px; border-radius: 50%;
            background: {PRIMARY};
            box-shadow: 0 0 0 0 rgba(0,230,118,0.6);
            animation: pulse 1.8s infinite;
        }}
        .live-dot.paused {{ background: {TEXT_MUTED}; animation: none; }}
        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(0,230,118,0.55); }}
            70% {{ box-shadow: 0 0 0 8px rgba(0,230,118,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(0,230,118,0); }}
        }}

        /* ---------- KPI cards ---------- */
        .kpi-card {{
            background: linear-gradient(160deg, {CARD_BG} 0%, {CARD_BG_ALT} 100%);
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 16px 18px;
            height: 100%;
        }}
        .kpi-card .kpi-label {{
            color: {TEXT_MUTED};
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
            margin-bottom: 6px;
        }}
        .kpi-card .kpi-value {{
            font-size: 1.65rem;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            color: {TEXT};
        }}
        .kpi-card .kpi-sub {{
            font-size: 0.78rem;
            color: {TEXT_MUTED};
            margin-top: 4px;
        }}

        /* ---------- Generic panel ---------- */
        .panel {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 18px 18px 8px 18px;
            margin-bottom: 14px;
        }}

        /* ---------- Badges ---------- */
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }}

        /* ---------- Alert banner ---------- */
        .alert-banner {{
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 10px;
            border-left: 4px solid;
            font-size: 0.9rem;
        }}
        .alert-critical {{ background: {DANGER}14; border-color: {DANGER}; }}
        .alert-warning  {{ background: {WARNING}14; border-color: {WARNING}; }}
        .alert-ok       {{ background: {PRIMARY}14; border-color: {PRIMARY}; }}

        /* ---------- Route step chips ---------- */
        .route-chip {{
            display: inline-flex;
            align-items: center;
            background: {CARD_BG_ALT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 0.82rem;
            margin: 2px;
        }}
        .route-arrow {{ color: {TEXT_MUTED}; margin: 0 2px; }}

        /* Streamlit tab polish */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: {CARD_BG};
            border-radius: 10px 10px 0 0;
            border: 1px solid {BORDER};
            border-bottom: none;
            padding: 8px 16px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def app_header(title: str, eyebrow: str, live: bool = False):
    dot_cls = "live-dot" if live else "live-dot paused"
    label = "LIVE" if live else "PAUSED"
    st.markdown(
        f"""
        <div class="app-header">
            <div class="title-block">
                <div class="eyebrow">{eyebrow}</div>
                <h1>{title}</h1>
            </div>
            <div class="live-pill"><span class="{dot_cls}"></span>{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card_html(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """


def render_kpi_row(items):
    """items: list of dicts with keys label, value, sub (optional)"""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            st.markdown(kpi_card_html(**item), unsafe_allow_html=True)


def status_badge(color_key: str) -> str:
    hex_color = STATUS_COLORS.get(color_key, TEXT_MUTED)
    label = STATUS_LABELS.get(color_key, "Unknown")
    return (
        f'<span class="badge" style="background:{hex_color}22;'
        f'color:{hex_color};border:1px solid {hex_color}55;">{label}</span>'
    )


def alert_banner(message: str, level: str = "ok"):
    cls = {"critical": "alert-critical", "warning": "alert-warning", "ok": "alert-ok"}.get(level, "alert-ok")
    icon = {"critical": "🔴", "warning": "🟠", "ok": "🟢"}.get(level, "🟢")
    st.markdown(f'<div class="alert-banner {cls}">{icon}&nbsp; {message}</div>', unsafe_allow_html=True)
