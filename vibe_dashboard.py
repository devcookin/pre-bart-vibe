import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from urllib.parse import quote
import json
import os
from supabase import create_client, Client
import streamlit.components.v1 as components
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=120 * 1000, key="datarefresh")
except:
    pass

# ========== SUPABASE ==========
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        pass

MODEL_VERSION = "v2.10-balanced-predictive"
APP_VERSION = "v10.9-balanced-predictive"
MIN_SNAPSHOT_INTERVAL = 300
FILL_INTERVAL_SECONDS = 60

# ========== API KEY ==========
API_KEY = st.secrets.get("COINGECKO_API_KEY")

if not API_KEY:
    st.error("⚠️ CoinGecko API key is missing. Please add it in Streamlit secrets.")
    st.stop()

HEADERS = {"x-cg-pro-api-key": API_KEY}
HISTORY_FILE = "vibe_history.json"

st.set_page_config(
    page_title="Pre-Bart Vibe Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== FIXED DARK THEME ==========
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html {
        color-scheme: dark !important;
        background-color: #0e1117 !important;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background-color: #0e1117 !important;
        color: #fafafa !important;
    }
    
    .block-container {
        max-width: 100% !important;
        padding-top: 0.8rem !important;
        padding-bottom: 1.8rem !important;
        padding-left: 1.4rem !important;
        padding-right: 1.4rem !important;
    }
    
    h1 {
        font-weight: 700 !important;
        letter-spacing: -0.5px;
        color: #ffffff !important;
    }
    
    h2, h3, h4, h5 {
        color: #f0f0f0 !important;
    }
    
    .stMetric {
        background-color: #1a1d24;
        border-radius: 12px;
        padding: 12px 16px;
        border: 1px solid #2a2d35;
        min-height: 110px !important;
        height: 110px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        font-weight: 600;
        color: #ffffff !important;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #a0a0a0 !important;
    }
    
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        background-color: #262730;
        color: #fafafa;
        border: 1px solid #3a3b45;
        transition: all 0.2s ease;
    }
    
    div.stButton > button:hover {
        background-color: #32333d;
        border-color: #4a4b55;
        transform: translateY(-1px);
    }
    
    .live-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(0, 200, 83, 0.15);
        color: #00c853;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
        margin-left: 12px;
    }
    
    .live-dot {
        width: 7px;
        height: 7px;
        background: #00c853;
        border-radius: 50%;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #16181d;
        border: 1px solid #2a2b35 !important;
        border-radius: 12px;
    }
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stSelectbox [data-baseweb="select"] {
        background-color: #1a1d24 !important;
        color: #fafafa !important;
        border-color: #3a3b45 !important;
    }
    
    .stCodeBlock {
        background-color: #1a1d24 !important;
    }
    
    hr {
        margin: 1rem 0 !important;
        border-color: #2a2b35 !important;
    }
    
    .stCaption {
        color: #888 !important;
    }
    
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.6rem !important;
    }

    /* Pre Bart Vibes visual system — lightweight, no extra data calls. */
    .pb-header { padding: 8px 0 4px 0; }
    .pb-title-row { display:flex;align-items:center;gap:12px;flex-wrap:wrap; }
    .pb-logo-mark {
        width:42px;height:42px;border-radius:13px;display:flex;align-items:center;justify-content:center;
        font-size:1.45rem;font-weight:800;letter-spacing:.05em;color:#dffcf4;
        background:linear-gradient(145deg,rgba(20,184,166,.28),rgba(0,230,118,.10));
        border:1px solid rgba(94,234,212,.28);box-shadow:0 8px 26px rgba(20,184,166,.09);
    }
    .pb-title { font-size:2.05rem;line-height:1.08;font-weight:800;letter-spacing:-.045em;color:#fff; }
    .pb-subtitle { margin-top:5px;font-size:.98rem;color:#9298a3;line-height:1.45; }
    .pb-refresh-note { color:#6f7682;font-size:.78rem;margin:1px 0 8px 2px; }

    .pb-vibe-hero {
        position:relative;overflow:hidden;border:1px solid #292f38;border-radius:18px;padding:22px 24px;
        background:linear-gradient(135deg,#11161d 0%,#0e1117 64%,color-mix(in srgb,var(--accent) 7%,#0e1117) 100%);
        margin:5px 0 10px 0;display:flex;justify-content:space-between;align-items:center;gap:22px;flex-wrap:wrap;
        box-shadow:0 12px 34px rgba(0,0,0,.16);
    }
    .pb-vibe-hero:before {
        content:"";position:absolute;width:250px;height:250px;border-radius:50%;right:-110px;top:-140px;
        background:var(--accent);opacity:.055;filter:blur(18px);pointer-events:none;
    }
    .pb-vibe-main,.pb-price-panel { position:relative;z-index:1; }
    .pb-eyebrow { font-size:.72rem;color:#858c97;text-transform:uppercase;letter-spacing:.095em;font-weight:650; }
    .pb-score-line { display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:6px; }
    .pb-score-number { font-size:3.1rem;font-weight:850;line-height:.95;letter-spacing:-.055em;color:#fff; }
    .pb-score-denom { font-size:1rem;color:#7f8793;margin-right:2px; }
    .pb-status-pill { display:inline-flex;align-items:center;padding:5px 10px;border-radius:999px;border:1px solid;font-size:.72rem;font-weight:850;letter-spacing:.07em;text-transform:uppercase; }
    .pb-signal-row { display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:11px;font-size:.83rem;color:#aab0ba; }
    .pb-dot-sep { color:#424851; }.pb-updated { color:#777f8a; }
    .pb-context-copy { font-size:.93rem;color:#d5d9df;font-weight:600;margin-top:12px; }
    .pb-meme-line { font-size:.82rem;color:#8f96a1;margin-top:5px; }
    .pb-price-panel { min-width:185px;text-align:right;padding-left:22px;border-left:1px solid #252a32; }
    .pb-price-value { margin-top:5px;font-size:1.6rem;font-weight:780;color:#fff;letter-spacing:-.025em; }
    .pb-price-change { font-size:.84rem;margin-top:4px;font-weight:620; }.pb-price-change span { color:#4f5660;padding:0 4px; }
    .pb-score-track { background:#252a31;border-radius:999px;overflow:hidden;margin:7px 1px 11px 1px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.025); }

    .pb-metrics-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:9px;margin:10px 0 14px 0; }
    .pb-mini-card { border:1px solid #282e37;border-radius:13px;padding:11px 13px;background:linear-gradient(180deg,#141922,#11151b);min-height:62px; }
    .pb-mini-label { font-size:.71rem;color:#838a95;display:flex;align-items:center;gap:6px; }.pb-mini-label span { color:#69727e;font-size:.8rem; }
    .pb-mini-value { font-size:1.02rem;font-weight:750;color:#f7f8fa;margin-top:4px;letter-spacing:-.015em; }

    .pb-section-head { margin:22px 0 9px 0;display:flex;justify-content:space-between;align-items:flex-end;gap:12px; }
    .pb-section-title { font-size:1.18rem;font-weight:780;color:#f4f5f7;letter-spacing:-.025em; }
    .pb-section-sub { margin-top:3px;font-size:.78rem;color:#737b86; }
    .pb-global-pill { font-size:.58rem;font-weight:850;letter-spacing:.08em;color:#5eead4;border:1px solid rgba(94,234,212,.25);background:rgba(20,184,166,.09);padding:3px 6px;border-radius:999px;vertical-align:middle;margin-left:5px; }

    /* Keep expanders and dataframes quiet so the hero signal remains primary. */
    [data-testid="stExpander"] { border-color:#292f37 !important;border-radius:12px !important;overflow:hidden; }
    [data-testid="stDataFrame"] { border-radius:12px;overflow:hidden; }

    /* Desktop compatibility: BaseWeb select dropdowns/popovers are rendered
       outside the selectbox container, so force them to the app's dark palette
       on all viewport sizes. This fixes Windows/Chrome light-theme fallbacks. */
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [role="listbox"],
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"] > div {
        background: #1a1d24 !important;
        color: #fafafa !important;
        border-color: #3a3b45 !important;
        color-scheme: dark !important;
    }

    [role="option"],
    [role="option"] *,
    [data-baseweb="menu"] li,
    [data-baseweb="menu"] li * {
        color: #fafafa !important;
        -webkit-text-fill-color: #fafafa !important;
        background-color: transparent !important;
        opacity: 1 !important;
    }

    [role="option"]:hover,
    [data-baseweb="menu"] li:hover {
        background: #222731 !important;
    }

    [role="option"][aria-selected="true"] {
        background: #262a33 !important;
        color: #ffffff !important;
    }

    .stSelectbox [data-baseweb="select"],
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] svg,
    [data-baseweb="select"] [data-testid="stMarkdownContainer"],
    [data-baseweb="select"] div,
    [data-baseweb="select"] span {
        color: #fafafa !important;
        -webkit-text-fill-color: #fafafa !important;
        fill: #fafafa !important;
        opacity: 1 !important;
        color-scheme: dark !important;
    }

    .stTextInput input,
    .stTextInput input::placeholder,
    [data-baseweb="input"] input {
        color: #fafafa !important;
        -webkit-text-fill-color: #fafafa !important;
        caret-color: #fafafa !important;
        opacity: 1 !important;
        color-scheme: dark !important;
    }

    /* Windows/Chrome hardening: Streamlit can inherit a light foreground palette
       for native widget/card labels even while the app surface is dark. Keep
       secondary labels readable without making them compete with primary values. */
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span,
    .stTextInput label,
    .stSelectbox label {
        color: #c3c9d2 !important;
        -webkit-text-fill-color: #c3c9d2 !important;
        opacity: 1 !important;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] span {
        color: #b8c0cb !important;
        -webkit-text-fill-color: #b8c0cb !important;
        opacity: 1 !important;
    }

    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        opacity: 1 !important;
    }

    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    .stCaption,
    .stCaption p {
        color: #a7aeb8 !important;
        -webkit-text-fill-color: #a7aeb8 !important;
        opacity: 1 !important;
    }

    /* Force Glide Data Grid (st.dataframe) onto the same dark palette on desktop.
       The table is canvas-based, so these theme variables are more reliable than
       styling th/td selectors alone. */
    [data-testid="stDataFrame"],
    [data-testid="stDataFrame"] > div {
        background-color: #0e1117 !important;
        color: #fafafa !important;
        color-scheme: dark !important;
        --gdg-bg-cell: #0e1117;
        --gdg-bg-cell-medium: #141922;
        --gdg-bg-header: #1a1d24;
        --gdg-bg-header-has-focus: #1f242d;
        --gdg-bg-header-hovered: #232933;
        --gdg-text-dark: #fafafa;
        --gdg-text-medium: #c2c8d0;
        --gdg-text-light: #969eaa;
        --gdg-border-color: #2a2d35;
        --gdg-horizontal-border-color: #2a2d35;
        --gdg-accent-color: #14b8a6;
        --gdg-accent-light: rgba(20,184,166,.15);
    }

    @media (max-width: 768px) {
        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background-color: #0e1117 !important;
            color: #fafafa !important;
        }

        .block-container,
        [data-testid="stMainBlockContainer"] {
            background-color: #0e1117 !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        .pb-title { font-size:1.65rem; }
        .pb-subtitle { font-size:.88rem; }
        .pb-logo-mark { width:37px;height:37px;border-radius:11px; }
        .pb-vibe-hero { padding:17px 17px;border-radius:15px;gap:15px; }
        .pb-score-number { font-size:2.7rem; }
        .pb-price-panel { width:100%;min-width:0;text-align:left;padding:13px 0 0 0;border-left:0;border-top:1px solid #252a32; }
        .pb-metrics-grid { grid-template-columns:repeat(2,minmax(0,1fr));gap:7px; }
        .pb-mini-card { padding:10px 11px;min-height:58px; }
        .pb-section-head { margin-top:18px; }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #16181d !important;
            border-color: #2a2b35 !important;
            box-shadow: none !important;
        }

        .stMetric {
            background-color: #1a1d24 !important;
            border-color: #2a2d35 !important;
            box-shadow: none !important;
        }

        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stSelectbox [data-baseweb="select"] {
            background-color: #1a1d24 !important;
            color: #fafafa !important;
        }

        /* Mobile Safari/Chrome can partially apply a light component theme even
           when the page itself is dark. Force the foreground/background colors
           on Streamlit widgets without changing layout or app logic. */
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] span,
        label,
        .stTextInput label,
        .stSelectbox label {
            color: #f0f0f0 !important;
            -webkit-text-fill-color: #f0f0f0 !important;
            opacity: 1 !important;
        }

        .stTextInput input,
        .stTextInput input::placeholder,
        [data-baseweb="input"] input {
            color: #fafafa !important;
            -webkit-text-fill-color: #fafafa !important;
            caret-color: #fafafa !important;
            opacity: 1 !important;
        }

        .stSelectbox [data-baseweb="select"],
        .stSelectbox [data-baseweb="select"] > div,
        .stSelectbox [data-baseweb="select"] span,
        .stSelectbox [data-baseweb="select"] svg {
            color: #fafafa !important;
            -webkit-text-fill-color: #fafafa !important;
            fill: #fafafa !important;
            opacity: 1 !important;
        }

        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricLabel"] span {
            color: #a0a0a0 !important;
            -webkit-text-fill-color: #a0a0a0 !important;
            opacity: 1 !important;
        }

        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
        }

        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p,
        .stCaption,
        .stCaption p {
            color: #9a9a9a !important;
            -webkit-text-fill-color: #9a9a9a !important;
            opacity: 1 !important;
        }

        [data-testid="stExpander"] details,
        [data-testid="stExpander"] summary {
            background-color: #0e1117 !important;
            color: #f0f0f0 !important;
            border-color: #2a2d35 !important;
        }

        [data-testid="stExpander"] summary *,
        [data-testid="stExpander"] details * {
            color: inherit;
        }

        [data-testid="stCodeBlock"],
        [data-testid="stCodeBlock"] pre,
        [data-testid="stCodeBlock"] code,
        .stCodeBlock,
        .stCodeBlock pre,
        .stCodeBlock code {
            background-color: #1a1d24 !important;
            color: #fafafa !important;
            -webkit-text-fill-color: #fafafa !important;
            border-color: #2a2d35 !important;
        }

        div.stButton > button,
        div.stButton > button * {
            color: #fafafa !important;
            -webkit-text-fill-color: #fafafa !important;
        }

        /* Dataframe host surface. Styled cells retain their own green/orange
           backgrounds; this forces the unstyled base/header surface dark. */
        [data-testid="stDataFrame"],
        [data-testid="stDataFrame"] > div {
            background-color: #0e1117 !important;
            color: #fafafa !important;
            --gdg-bg-cell: #0e1117;
            --gdg-bg-header: #1a1d24;
            --gdg-text-dark: #fafafa;
            --gdg-text-medium: #b8b8b8;
            --gdg-border-color: #2a2d35;
        }

        /* BaseWeb select menus are rendered in a portal outside .stSelectbox.
           Target the portal itself so iOS cannot fall back to light-theme text/menu colors. */
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"],
        [data-baseweb="popover"] > div,
        [data-baseweb="menu"] > div {
            background: #1a1d24 !important;
            color: #fafafa !important;
        }

        [role="option"],
        [role="option"] *,
        [data-baseweb="menu"] li,
        [data-baseweb="menu"] li * {
            color: #fafafa !important;
            -webkit-text-fill-color: #fafafa !important;
        }

        [role="option"][aria-selected="true"] {
            background: #262a33 !important;
        }

        /* Current selected value lives inside BaseWeb's value container on iOS. */
        [data-baseweb="select"] [data-testid="stMarkdownContainer"],
        [data-baseweb="select"] div,
        [data-baseweb="select"] span {
            color: #fafafa !important;
            -webkit-text-fill-color: #fafafa !important;
            opacity: 1 !important;
        }
    }

    /* v9.15 signal-language + sidebar polish */
    :root {
        --pb-strong:#22c55e; --pb-positive:#14b8a6; --pb-neutral:#f59e0b;
        --pb-negative:#ef5350; --pb-muted:#8b93a1; --pb-card:#12171e; --pb-border:#2a3039;
    }
    .pb-side-card { border:1px solid var(--pb-border);border-radius:14px;padding:15px 16px;background:linear-gradient(180deg,#131820,#10141a);margin-bottom:10px; }
    .pb-side-title { font-size:.78rem;color:#9098a5;text-transform:uppercase;letter-spacing:.075em;font-weight:750;margin-bottom:11px; }
    .pb-bias-value { font-size:1.15rem;font-weight:780;letter-spacing:-.02em; }
    .pb-side-sub { color:#8e96a3;font-size:.76rem;margin-top:5px; }
    .pb-extreme-row { display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 0; }
    .pb-extreme-row + .pb-extreme-row { border-top:1px solid #252b33; }
    .pb-extreme-name { display:flex;align-items:center;gap:8px;font-weight:720; }
    .pb-score-chip { min-width:38px;text-align:center;padding:3px 8px;border-radius:999px;font-size:.76rem;font-weight:800;border:1px solid; }
    .pb-mover-head,.pb-mover-row { display:grid;grid-template-columns:1fr auto;align-items:center;gap:8px; }
    .pb-mover-head { color:#7f8794;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;margin:12px 0 4px; }
    .pb-mover-row { padding:4px 0;font-size:.82rem; }
    .pb-mover-symbol { font-weight:720;color:#f3f5f7; }
    .pb-confidence { display:inline-flex;align-items:center;gap:5px;padding:2px 7px;border-radius:999px;font-size:.68rem;font-weight:750;border:1px solid #343b45;color:#aab1bc;background:#171c23; }
    .pb-definition { color:#8d95a1;font-size:.76rem;line-height:1.5; }

    /* Top Movers uses the same card language as Market Bias / Strongest-Weakest. */
    .pb-movers-card { padding-bottom:13px; }
    .pb-mover-tabs {
        display:grid;grid-template-columns:1fr 1fr;gap:3px;
        background:#0d1117;border:1px solid #303741;border-radius:10px;
        padding:3px;margin:1px 0 13px 0;max-width:190px;
    }
    .pb-mover-tabs input { position:absolute;opacity:0;pointer-events:none; }
    .pb-mover-tabs label {
        display:flex;align-items:center;justify-content:center;
        min-width:0;padding:6px 12px;border-radius:7px;
        color:#929aa7;font-size:.76rem;font-weight:760;
        line-height:1;white-space:nowrap;cursor:pointer;
        transition:background .15s ease,color .15s ease;
    }
    .pb-mover-tabs label:hover { color:#f3f5f7; }
    #pb-movers-1h:checked + label,
    #pb-movers-24h:checked + label { background:#252c35;color:#f7f8fa; }
    .pb-movers-panel { display:none; }
    .pb-movers-card:has(#pb-movers-1h:checked) .pb-movers-panel-1h { display:block; }
    .pb-movers-card:has(#pb-movers-24h:checked) .pb-movers-panel-24h { display:block; }
    .pb-mover-section + .pb-mover-section { margin-top:13px; }
    .pb-mover-head { margin:0 0 5px 0; }

    @media (max-width: 768px) {
        .pb-side-card { padding:13px 14px;margin-bottom:8px; }
        .pb-side-title { margin-bottom:8px; }
        .pb-mover-row { padding:5px 0; }
        .pb-mover-tabs { max-width:100%;margin-bottom:11px; }
        .pb-mover-tabs label { padding:7px 10px;font-size:.78rem; }
    }

    /* v10 — Setup Intelligence */
    .pb-intel-grid {
        display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:12px 0 10px 0;
    }
    .pb-intel-card {
        border:1px solid #29313b;border-radius:14px;padding:13px 14px;
        background:linear-gradient(180deg,#141a22,#10151b);min-height:92px;
    }
    .pb-intel-kicker { font-size:.68rem;color:#7e8794;text-transform:uppercase;letter-spacing:.075em;font-weight:800; }
    .pb-intel-value { font-size:1.18rem;font-weight:820;color:#f5f7fa;letter-spacing:-.025em;margin-top:7px; }
    .pb-intel-sub { color:#8f98a5;font-size:.74rem;line-height:1.45;margin-top:4px; }
    .pb-setup-shell {
        border:1px solid #29313b;border-radius:15px;background:linear-gradient(145deg,#131922,#10151b);
        padding:15px 16px;margin:9px 0 13px 0;
    }
    .pb-setup-top { display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap; }
    .pb-setup-title { font-size:.82rem;color:#8e97a3;text-transform:uppercase;letter-spacing:.075em;font-weight:800; }
    .pb-setup-state { font-size:1.22rem;font-weight:840;letter-spacing:-.025em;margin-top:4px; }
    .pb-setup-pill { display:inline-flex;align-items:center;border:1px solid;padding:4px 9px;border-radius:999px;font-size:.68rem;font-weight:850;letter-spacing:.055em;text-transform:uppercase; }
    .pb-analog-grid { display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:13px; }
    .pb-analog-stat { background:#0f141a;border:1px solid #252c35;border-radius:11px;padding:9px 10px; }
    .pb-analog-label { color:#79828e;font-size:.64rem;text-transform:uppercase;letter-spacing:.06em;font-weight:760; }
    .pb-analog-value { color:#f5f7fa;font-size:.94rem;font-weight:800;margin-top:3px; }
    .pb-lead-note { margin-top:10px;color:#9ba4b0;font-size:.75rem;line-height:1.5; }
    .pb-lead-dot { display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:6px;vertical-align:1px; }

    @media (max-width: 900px) {
        .pb-intel-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .pb-analog-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    }
    @media (max-width: 520px) {
        .pb-intel-grid { grid-template-columns:1fr 1fr;gap:7px; }
        .pb-intel-card { padding:11px 12px;min-height:84px; }
        .pb-intel-value { font-size:1.02rem; }
        .pb-setup-shell { padding:13px; }
        .pb-analog-grid { grid-template-columns:1fr 1fr;gap:7px; }
    }

</style>
""", unsafe_allow_html=True)

# ========== SESSION STATE ==========
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "selected_coin" not in st.session_state:
    st.session_state.selected_coin = "Bitcoin"
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if "search_coin" not in st.session_state:
    st.session_state.search_coin = None
if "show_count" not in st.session_state:
    st.session_state.show_count = "Top 5"
if "last_snapshot_time" not in st.session_state:
    st.session_state.last_snapshot_time = {}
if "last_fill_time" not in st.session_state:
    st.session_state.last_fill_time = None
if "movers_tf" not in st.session_state:
    st.session_state.movers_tf = "1h"
if "quick_filter" not in st.session_state:
    st.session_state.quick_filter = "All"

# ========== HISTORY (Supabase) ==========
def load_history():
    if not supabase:
        return {}
    try:
        result = supabase.table("vibe_score_history")\
            .select("coin_id, timestamp, score")\
            .order("timestamp", desc=True)\
            .limit(2000)\
            .execute()
        
        rows = result.data or []
        history = {}
        for row in rows:
            cid = row["coin_id"]
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            score = row["score"]
            if cid not in history:
                history[cid] = []
            history[cid].append((ts, score))
        
        for cid in history:
            history[cid] = sorted(history[cid], key=lambda x: x[0])[-150:]
        return history
    except:
        return {}

def load_coin_history(cid: str, limit: int = 150):
    """Load recent persisted history for one coin.

    The global history loader is intentionally capped for startup speed. If a
    coin's rows fall outside that global window after a restart, this targeted
    loader restores that coin's chart without fetching the whole table.
    """
    if not supabase or not cid:
        return []
    try:
        result = supabase.table("vibe_score_history")\
            .select("coin_id, timestamp, score")\
            .eq("coin_id", cid)\
            .order("timestamp", desc=True)\
            .limit(limit)\
            .execute()

        rows = result.data or []
        entries = []
        for row in rows:
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            entries.append((ts, row["score"]))
        return sorted(entries, key=lambda x: x[0])[-limit:]
    except Exception:
        return []

def ensure_coin_history_loaded(cid: str, history_dict):
    """Hydrate a coin's history from Supabase when the session has too little.

    This fixes the case where load_history()'s global 2,000-row window does not
    include the selected coin. Existing in-session points are merged and kept.
    """
    existing = history_dict.get(cid, [])
    if len(existing) >= 2:
        return history_dict

    persisted = load_coin_history(cid, limit=150)
    if not persisted:
        return history_dict

    combined = persisted + existing
    deduped = {}
    for ts, score in combined:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        deduped[ts.isoformat()] = (ts, score)

    history_dict[cid] = sorted(deduped.values(), key=lambda x: x[0])[-150:]
    return history_dict

def save_history_point(cid: str, score: int):
    if not supabase:
        return
    try:
        supabase.table("vibe_score_history").insert({
            "coin_id": cid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "score": int(score)
        }).execute()
    except:
        pass

def update_history(cid, score, history_dict):
    now = datetime.now(timezone.utc)
    if cid not in history_dict:
        history_dict[cid] = []
    
    entries = history_dict[cid]
    should_add = False
    
    if not entries:
        should_add = True
    else:
        last_time, last_score = entries[-1]
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        if score != last_score or (now - last_time) > timedelta(minutes=2):
            should_add = True
    
    if should_add:
        entries.append((now, score))
        history_dict[cid] = entries[-150:]
        save_history_point(cid, score)
    
    return history_dict

if "score_history" not in st.session_state:
    st.session_state.score_history = load_history()

# ========== SUPABASE SNAPSHOTS ==========
def save_vibe_snapshot(coin_id, symbol, price, score, label, change_24h, range_pos, vs_btc, prev_score, sub_signals):
    if not supabase: return
    now = datetime.now(timezone.utc)
    last_time = st.session_state.last_snapshot_time.get(coin_id)
    if last_time and (now - last_time).total_seconds() < MIN_SNAPSHOT_INTERVAL:
        return
    direction = None
    if prev_score is not None:
        if score > prev_score + 2: direction = "rising"
        elif score < prev_score - 2: direction = "falling"
        else: direction = "flat"
    data = {
        "timestamp": now.isoformat(), "coin_id": coin_id, "symbol": symbol,
        "price": float(price), "score": int(score), "label": label,
        "change_24h": float(change_24h) if change_24h is not None else None,
        "range_pos": float(range_pos) if range_pos is not None else None,
        "vs_btc": float(vs_btc) if vs_btc is not None else None,
        "prev_score": int(prev_score) if prev_score is not None else None,
        "direction": direction, "sub_signals": sub_signals, "model_version": MODEL_VERSION,
    }
    try:
        supabase.table("vibe_snapshots").insert(data).execute()
        st.session_state.last_snapshot_time[coin_id] = now
    except:
        pass

def save_vibe_snapshots_batch(snapshot_rows):
    """Insert all due top-coin snapshots in one Supabase request.

    This preserves the existing 5-minute snapshot cadence while avoiding up to
    30 separate network round-trips during a collection cycle.
    """
    if not supabase or not snapshot_rows:
        return
    try:
        supabase.table("vibe_snapshots").insert([row["data"] for row in snapshot_rows]).execute()
        for row in snapshot_rows:
            st.session_state.last_snapshot_time[row["coin_id"]] = row["timestamp"]
    except:
        # Fall back to the original per-coin insert behavior so collection is
        # never lost just because a batch request fails.
        for row in snapshot_rows:
            try:
                supabase.table("vibe_snapshots").insert(row["data"]).execute()
                st.session_state.last_snapshot_time[row["coin_id"]] = row["timestamp"]
            except:
                pass

def queue_vibe_snapshot(snapshot_rows, coin_id, symbol, price, score, label, change_24h, range_pos, vs_btc, prev_score, sub_signals):
    """Queue a snapshot only when the same interval rules as save_vibe_snapshot allow it."""
    if not supabase:
        return
    now = datetime.now(timezone.utc)
    last_time = st.session_state.last_snapshot_time.get(coin_id)
    if last_time and (now - last_time).total_seconds() < MIN_SNAPSHOT_INTERVAL:
        return
    direction = None
    if prev_score is not None:
        if score > prev_score + 2:
            direction = "rising"
        elif score < prev_score - 2:
            direction = "falling"
        else:
            direction = "flat"
    data = {
        "timestamp": now.isoformat(), "coin_id": coin_id, "symbol": symbol,
        "price": float(price), "score": int(score), "label": label,
        "change_24h": float(change_24h) if change_24h is not None else None,
        "range_pos": float(range_pos) if range_pos is not None else None,
        "vs_btc": float(vs_btc) if vs_btc is not None else None,
        "prev_score": int(prev_score) if prev_score is not None else None,
        "direction": direction, "sub_signals": sub_signals, "model_version": MODEL_VERSION,
    }
    snapshot_rows.append({"coin_id": coin_id, "timestamp": now, "data": data})

def fill_pending_returns():
    """Fill each forward-return horizon from snapshots near its own maturity time.

    Each horizon is queried independently. This prevents the 24h-null backlog from
    crowding 30m snapshots out of a shared LIMIT window (the cause of blank 30m stats).
    """
    if not supabase:
        return

    now = datetime.now(timezone.utc)
    last_fill = st.session_state.last_fill_time
    if last_fill and (now - last_fill).total_seconds() < FILL_INTERVAL_SECONDS:
        return

    horizons = [
        ("return_30m", 30 * 60, 12 * 60),
        ("return_1h", 60 * 60, 15 * 60),
        ("return_4h", 4 * 60 * 60, 30 * 60),
        ("return_24h", 24 * 60 * 60, 90 * 60),
    ]

    try:
        # Pull only snapshots that are currently inside each horizon's valid fill
        # window. A single shared query cannot do this safely because 24h-null rows
        # vastly outnumber the snapshots eligible for the 30m window.
        eligible = {}
        for col, target_age, max_late in horizons:
            oldest = (now - timedelta(seconds=target_age + max_late)).isoformat()
            newest = (now - timedelta(seconds=target_age)).isoformat()
            try:
                result = supabase.table("vibe_snapshots")\
                    .select("id, timestamp, coin_id, price, return_30m, return_1h, return_4h, return_24h")\
                    .eq("model_version", MODEL_VERSION)\
                    .is_(col, "null")\
                    .gte("timestamp", oldest)\
                    .lte("timestamp", newest)\
                    .order("timestamp", desc=False)\
                    .limit(1000)\
                    .execute()
                for row in (result.data or []):
                    eligible[row["id"]] = row
            except Exception:
                continue

        rows = list(eligible.values())
        if not rows:
            st.session_state.last_fill_time = now
            return

        coin_ids = list({r["coin_id"] for r in rows})
        try:
            r = requests.get(
                "https://pro-api.coingecko.com/api/v3/simple/price",
                headers=HEADERS,
                params={"ids": ",".join(coin_ids), "vs_currencies": "usd"},
                timeout=8,
            )
            prices = r.json() if r.status_code == 200 else {}
        except Exception:
            prices = {}

        for row in rows:
            try:
                ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                age = (now - ts).total_seconds()
                original = float(row["price"])
                current = prices.get(row["coin_id"], {}).get("usd")
                if current is None or original <= 0:
                    continue

                ret = ((float(current) - original) / original) * 100
                updates = {}
                for col, target_age, max_late in horizons:
                    if row.get(col) is None and target_age <= age <= target_age + max_late:
                        updates[col] = round(ret, 4)

                if updates:
                    updates["filled_at"] = now.isoformat()
                    try:
                        supabase.table("vibe_snapshots").update(updates).eq("id", row["id"]).execute()
                    except Exception:
                        pass
            except Exception:
                continue

        # Bucket stats are cached separately; clear them so newly matured returns
        # can appear immediately instead of waiting up to five more minutes.
        try:
            get_bucket_stats.clear()
        except Exception:
            pass
        st.session_state.last_fill_time = now
    except Exception:
        pass

@st.cache_data(ttl=300)
def get_bucket_stats(min_n=5):
    """Cumulative bucket stats for the current model version.

    Uses paginated Supabase reads so historical observations never fall out of a
    rolling LIMIT window. Each horizon is still queried independently so sparse
    30m/1h/4h/24h maturity does not interfere with the others.
    """
    if not supabase:
        return None

    bucket_order = ["0-19", "20-39", "40-59", "60-69", "70-79", "80-89", "90-100"]

    def bucket(score):
        if score < 20: return "0-19"
        if score < 40: return "20-39"
        if score < 60: return "40-59"
        if score < 70: return "60-69"
        if score < 80: return "70-79"
        if score < 90: return "80-89"
        return "90-100"

    def paged_rows(columns, extra_filter=None, page_size=1000):
        """Read all matching rows in bounded pages.

        This avoids a single huge response while keeping cumulative statistics
        exact for the current model version.
        """
        rows = []
        offset = 0
        while True:
            q = (
                supabase.table("vibe_snapshots")
                .select(columns)
                .eq("model_version", MODEL_VERSION)
                .order("timestamp", desc=False)
                .range(offset, offset + page_size - 1)
            )
            if extra_filter is not None:
                q = extra_filter(q)
            result = q.execute()
            batch = result.data or []
            rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
        return rows

    try:
        # All-time count for the CURRENT model version.
        count_rows = paged_rows("score,timestamp")
        if not count_rows:
            return None

        count_df = pd.DataFrame(count_rows)
        count_df["bucket"] = count_df["score"].apply(bucket)
        counts = count_df["bucket"].value_counts().to_dict()

        # All completed observations for each forward horizon, independently paged.
        horizon_frames = {}
        for col in ["return_30m", "return_1h", "return_4h", "return_24h"]:
            try:
                rows = paged_rows(
                    f"score,{col},timestamp",
                    extra_filter=lambda q, c=col: q.not_.is_(c, "null"),
                )
                if rows:
                    hdf = pd.DataFrame(rows)
                    hdf["bucket"] = hdf["score"].apply(bucket)
                    horizon_frames[col] = hdf
                else:
                    horizon_frames[col] = pd.DataFrame(columns=["score", col, "timestamp", "bucket"])
            except Exception:
                horizon_frames[col] = pd.DataFrame(columns=["score", col, "timestamp", "bucket"])

        one_hour = horizon_frames["return_1h"]
        overall_avg_1h = one_hour["return_1h"].mean() if not one_hour.empty else 0

        def horizon_metric(bucket_name, col, metric):
            hdf = horizon_frames[col]
            if hdf.empty:
                return None
            vals = hdf.loc[hdf["bucket"] == bucket_name, col].dropna()
            if len(vals) == 0:
                return None
            if metric == "avg":
                return round(vals.mean(), 3)
            if metric == "median":
                # Keep the stored precision here. Rounding before display can turn a
                # tiny positive/negative median into a misleading 0.00%.
                return float(vals.median())
            if metric == "avg_win":
                winners = vals[vals > 0]
                return round(winners.mean(), 3) if len(winners) else None
            if metric == "avg_loss":
                losers = vals[vals < 0]
                return round(losers.mean(), 3) if len(losers) else None
            return round((vals > 0).mean() * 100, 1)

        stats = []
        for b in bucket_order:
            n = int(counts.get(b, 0))
            if n < min_n:
                stats.append({
                    "bucket": b,
                    "n": n,
                    "ready": False,
                    "n_30m": int((horizon_frames["return_30m"]["bucket"] == b).sum()),
                    "n_1h": int((horizon_frames["return_1h"]["bucket"] == b).sum()),
                    "n_4h": int((horizon_frames["return_4h"]["bucket"] == b).sum()),
                    "n_24h": int((horizon_frames["return_24h"]["bucket"] == b).sum()),
                })
                continue

            avg_1h = horizon_metric(b, "return_1h", "avg")
            edge = round(avg_1h - overall_avg_1h, 2) if avg_1h is not None else None

            stats.append({
                "bucket": b,
                "n": n,
                "ready": True,
                "n_30m": int((horizon_frames["return_30m"]["bucket"] == b).sum()),
                "n_1h": int((horizon_frames["return_1h"]["bucket"] == b).sum()),
                "n_4h": int((horizon_frames["return_4h"]["bucket"] == b).sum()),
                "n_24h": int((horizon_frames["return_24h"]["bucket"] == b).sum()),
                "avg_30m": horizon_metric(b, "return_30m", "avg"),
                "win_30m": horizon_metric(b, "return_30m", "win"),
                "avg_1h": avg_1h,
                "median_1h": horizon_metric(b, "return_1h", "median"),
                "avg_win_1h": horizon_metric(b, "return_1h", "avg_win"),
                "avg_loss_1h": horizon_metric(b, "return_1h", "avg_loss"),
                "win_1h": horizon_metric(b, "return_1h", "win"),
                "avg_4h": horizon_metric(b, "return_4h", "avg"),
                "win_4h": horizon_metric(b, "return_4h", "win"),
                "avg_24h": horizon_metric(b, "return_24h", "avg"),
                "win_24h": horizon_metric(b, "return_24h", "win"),
                "edge": edge,
            })

        return stats
    except Exception:
        return None

@st.cache_data(ttl=180)
def get_coin_performance(coin_id, min_n=15):
    if not supabase: return None
    try:
        result = supabase.table("vibe_snapshots")\
            .select("score, return_1h, return_4h")\
            .eq("coin_id", coin_id)\
            .eq("model_version", MODEL_VERSION)\
            .not_.is_("return_1h", "null").limit(500).execute()
        rows = result.data or []
        if len(rows) < min_n:
            return {"n": len(rows), "ready": False}
        df = pd.DataFrame(rows)
        return {
            "n": len(df), "ready": True,
            "avg_1h": round(df["return_1h"].mean(), 3),
            "win_1h": round((df["return_1h"] > 0).mean() * 100, 1),
            "avg_4h": round(df["return_4h"].dropna().mean(), 3) if df["return_4h"].notna().any() else None,
            "win_4h": round((df["return_4h"].dropna() > 0).mean() * 100, 1) if df["return_4h"].notna().any() else None
        }
    except:
        return None

@st.cache_data(ttl=180)
def get_vibe_price_history(coin_id, limit=150):
    """Recent paired Vibe/price snapshots for a simple relationship chart."""
    if not supabase or not coin_id:
        return []
    try:
        result = supabase.table("vibe_snapshots")\
            .select("timestamp,price,score")\
            .eq("coin_id", coin_id)\
            .eq("model_version", MODEL_VERSION)\
            .order("timestamp", desc=True)\
            .limit(limit)\
            .execute()
        rows = result.data or []
        return sorted(rows, key=lambda r: r.get("timestamp", ""))
    except Exception:
        return []

@st.cache_data(ttl=300)
def get_setup_history(coin_id, limit=1200):
    """Load a bounded recent snapshot history for setup/transition analytics.

    This is intentionally per-coin and cached so v10 can study Vibe transitions
    without turning every page load into a full-database scan.
    """
    if not supabase or not coin_id:
        return []
    try:
        result = supabase.table("vibe_snapshots")\
            .select("timestamp,price,score,prev_score,return_30m,return_1h,return_4h")\
            .eq("coin_id", coin_id)\
            .eq("model_version", MODEL_VERSION)\
            .order("timestamp", desc=True)\
            .limit(limit)\
            .execute()
        return sorted(result.data or [], key=lambda r: r.get("timestamp", ""))
    except Exception:
        return []

def _score_bucket(score):
    if score is None:
        return None
    score = float(score)
    if score < 20: return "0-19"
    if score < 40: return "20-39"
    if score < 60: return "40-59"
    if score < 70: return "60-69"
    if score < 80: return "70-79"
    if score < 90: return "80-89"
    return "90-100"

def _velocity_state(delta):
    if delta is None or pd.isna(delta): return "Unknown"
    if delta >= 8: return "Surging"
    if delta >= 3: return "Improving"
    if delta <= -8: return "Fading fast"
    if delta <= -3: return "Weakening"
    return "Stable"

def _price_state(delta):
    if delta is None or pd.isna(delta): return "Unknown"
    if delta <= -0.50: return "Price lagging"
    if delta < 0.50: return "Price flat"
    if delta < 1.50: return "Price moving"
    return "Price extended"

def _prior_series(df, minutes, tolerance_minutes):
    scores, prices = [], []
    times = list(df["time"])
    score_vals = list(df["score"])
    price_vals = list(df["price"])
    for i, t in enumerate(times):
        target = t - pd.Timedelta(minutes=minutes)
        # nearest historical reading to the target, never using a future row
        candidates = []
        for j in range(max(0, i-30), i):
            diff = abs((times[j] - target).total_seconds())
            if diff <= tolerance_minutes * 60:
                candidates.append((diff, j))
        if candidates:
            _, j = min(candidates, key=lambda x: x[0])
            scores.append(score_vals[j]); prices.append(price_vals[j])
        else:
            scores.append(None); prices.append(None)
    return scores, prices

def build_setup_analytics(rows, current_score, current_price):
    """Derive Vibe velocity, price response, transition behavior and historical analogs."""
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if df.empty:
        return None
    df["time"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for col in ["price","score","prev_score","return_30m","return_1h","return_4h"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["time","price","score"]).sort_values("time").reset_index(drop=True)
    if df.empty:
        return None

    # Append a synthetic now-row so current Vibe/price is measured against persisted history.
    now_row = {c: None for c in df.columns}
    now_row.update({"time": pd.Timestamp.now(tz="UTC"), "price": float(current_price), "score": float(current_score)})
    df = pd.concat([df, pd.DataFrame([now_row])], ignore_index=True)

    p30_score, p30_price = _prior_series(df, 30, 12)
    p60_score, p60_price = _prior_series(df, 60, 20)
    df["prior_score_30m"] = p30_score
    df["prior_price_30m"] = p30_price
    df["prior_score_1h"] = p60_score
    df["prior_price_1h"] = p60_price
    df["dv_30m"] = df["score"] - pd.to_numeric(df["prior_score_30m"], errors="coerce")
    df["dv_1h"] = df["score"] - pd.to_numeric(df["prior_score_1h"], errors="coerce")
    df["px_30m"] = (df["price"] / pd.to_numeric(df["prior_price_30m"], errors="coerce") - 1.0) * 100
    df["px_1h"] = (df["price"] / pd.to_numeric(df["prior_price_1h"], errors="coerce") - 1.0) * 100
    df["bucket"] = df["score"].apply(_score_bucket)
    df["velocity_state"] = df["dv_30m"].apply(_velocity_state)
    df["price_state"] = df["px_30m"].apply(_price_state)

    cur = df.iloc[-1]
    dv30 = None if pd.isna(cur["dv_30m"]) else float(cur["dv_30m"])
    dv1h = None if pd.isna(cur["dv_1h"]) else float(cur["dv_1h"])
    px30 = None if pd.isna(cur["px_30m"]) else float(cur["px_30m"])
    px1h = None if pd.isna(cur["px_1h"]) else float(cur["px_1h"])
    velocity = _velocity_state(dv30)
    pstate = _price_state(px30)

    if dv30 is None:
        setup_state, setup_color = "Building data", "#8b93a1"
    elif dv30 <= -5:
        setup_state, setup_color = "Cooling", "#ef5350"
    elif current_score >= 75 and px30 is not None and px30 >= 1.50:
        setup_state, setup_color = "Extended", "#f59e0b"
    elif dv30 >= 6 and (px30 is None or px30 <= 0.50):
        setup_state, setup_color = "Emerging", "#22c55e"
    elif dv30 >= 3:
        setup_state, setup_color = "Strengthening", "#14b8a6"
    elif current_score >= 70:
        setup_state, setup_color = "Confirmed", "#14b8a6"
    else:
        setup_state, setup_color = "Balanced", "#f59e0b"

    if dv30 is not None and px30 is not None and dv30 >= 5 and px30 <= 0.35:
        lead_label, lead_color = "Positive lead candidate", "#22c55e"
    elif dv30 is not None and px30 is not None and dv30 <= -5 and px30 >= -0.35:
        lead_label, lead_color = "Negative lead candidate", "#ef5350"
    elif dv30 is not None and px30 is not None and ((dv30 > 1 and px30 > 0.25) or (dv30 < -1 and px30 < -0.25)):
        lead_label, lead_color = "Confirming price", "#14b8a6"
    else:
        lead_label, lead_color = "No clear divergence", "#8b93a1"

    hist = df.iloc[:-1].copy()
    current_bucket = _score_bucket(current_score)
    current_vel = _velocity_state(dv30)
    current_px_state = _price_state(px30)

    # Most specific analog set first; relax only if the sample is too small.
    analog = hist[(hist["bucket"] == current_bucket) & (hist["velocity_state"] == current_vel) & (hist["price_state"] == current_px_state)]
    match_basis = "same score band + Vibe velocity + price response"
    if analog["return_1h"].notna().sum() < 15:
        analog = hist[(hist["bucket"] == current_bucket) & (hist["velocity_state"] == current_vel)]
        match_basis = "same score band + Vibe velocity"
    if analog["return_1h"].notna().sum() < 15:
        analog = hist[hist["bucket"] == current_bucket]
        match_basis = "same score band"

    def stats_for(col):
        vals = pd.to_numeric(analog[col], errors="coerce").dropna() if col in analog.columns else pd.Series(dtype=float)
        if len(vals) == 0:
            return {"n":0,"avg":None,"median":None,"win":None,"avg_win":None,"avg_loss":None}
        wins = vals[vals > 0]; losses = vals[vals < 0]
        return {
            "n": int(len(vals)), "avg": float(vals.mean()), "median": float(vals.median()),
            "win": float((vals > 0).mean()*100),
            "avg_win": float(wins.mean()) if len(wins) else None,
            "avg_loss": float(losses.mean()) if len(losses) else None,
        }

    # Cross-bucket transition study, using the immediate persisted previous score.
    trans = hist.dropna(subset=["prev_score"]).copy()
    trans["from_bucket"] = trans["prev_score"].apply(_score_bucket)
    trans["to_bucket"] = trans["score"].apply(_score_bucket)
    trans = trans[trans["from_bucket"] != trans["to_bucket"]]
    trans_rows = []
    if not trans.empty:
        trans["transition"] = trans["from_bucket"] + " → " + trans["to_bucket"]
        for name, grp in trans.groupby("transition"):
            vals = pd.to_numeric(grp["return_1h"], errors="coerce").dropna()
            if len(vals):
                trans_rows.append({
                    "Transition": name, "n": int(len(vals)),
                    "Avg 1h": float(vals.mean()), "Median 1h": float(vals.median()),
                    "Win 1h": float((vals > 0).mean()*100),
                })
        trans_rows = sorted(trans_rows, key=lambda r: r["n"], reverse=True)[:12]

    return {
        "frame": df, "dv30": dv30, "dv1h": dv1h, "px30": px30, "px1h": px1h,
        "velocity": velocity, "price_state": pstate, "setup_state": setup_state,
        "setup_color": setup_color, "lead_label": lead_label, "lead_color": lead_color,
        "analog_30m": stats_for("return_30m"), "analog_1h": stats_for("return_1h"),
        "analog_4h": stats_for("return_4h"), "match_basis": match_basis,
        "transitions": trans_rows,
    }

def sample_strength(n):
    """Plain-language sample maturity; descriptive rather than statistical certainty."""
    if n is None or n < 15:
        return "Early", "#8b93a1"
    if n < 50:
        return "Building", "#f59e0b"
    if n < 200:
        return "Moderate", "#14b8a6"
    return "Strong", "#22c55e"

# ========== HELPERS ==========
@st.cache_data(ttl=45)
def get_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        d = r.json()["data"][0]
        return int(d["value"]), d["value_classification"]
    except:
        return None, None

@st.cache_data(ttl=120)
def get_global():
    try:
        r = requests.get("https://pro-api.coingecko.com/api/v3/global", headers=HEADERS, timeout=10)
        return r.json()["data"]
    except:
        return None

# Stablecoins are intentionally excluded from the Top Coins overview.
# We filter them BEFORE OHLC/Vibe processing so they do not consume candle
# requests, scoring work, or snapshot rows. Search still supports them normally.
STABLECOIN_IDS = {
    "tether", "usd-coin", "dai", "ethena-usde", "usds",
    "first-digital-usd", "paypal-usd", "true-usd", "frax", "usdd",
    "gemini-dollar", "liquity-usd", "pax-dollar", "ripple-usd",
    "global-dollar", "world-liberty-financial-usd", "usual-usd",
    "crvusd", "gho", "usd0",
}

STABLECOIN_SYMBOLS = {
    "USDT", "USDC", "DAI", "USDE", "USDS", "FDUSD", "PYUSD",
    "TUSD", "FRAX", "USDD", "GUSD", "LUSD", "USDP", "RLUSD",
    "USDG", "USD1", "USD0", "CRVUSD", "GHO",
}

def is_stablecoin(coin):
    cid = str(coin.get("id", "")).lower()
    symbol = str(coin.get("symbol", "")).upper()
    return cid in STABLECOIN_IDS or symbol in STABLECOIN_SYMBOLS

@st.cache_data(ttl=120)
def get_top_coins(limit=30):
    try:
        r = requests.get("https://pro-api.coingecko.com/api/v3/coins/markets", headers=HEADERS,
            params={"vs_currency":"usd","order":"market_cap_desc","per_page":limit,"page":1,
                    "sparkline":False,"price_change_percentage":"1h,24h"}, timeout=12)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=300)
def get_ohlc(coin_id, days="1"):
    try:
        r = requests.get(f"https://pro-api.coingecko.com/api/v3/coins/{coin_id}/ohlc", headers=HEADERS,
            params={"vs_currency":"usd","days":days}, timeout=10)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=300)
def get_ohlc_batch(coin_ids, days="1"):
    """Fetch OHLC for many coins concurrently.

    Call count is unchanged; wall-clock load time is lower because a handful of
    CoinGecko requests run in parallel instead of all 30 running serially.
    """
    ids = list(coin_ids)
    if not ids:
        return {}

    def _fetch(cid):
        try:
            r = requests.get(
                f"https://pro-api.coingecko.com/api/v3/coins/{cid}/ohlc",
                headers=HEADERS,
                params={"vs_currency":"usd","days":days},
                timeout=10
            )
            return cid, (r.json() if r.status_code == 200 else [])
        except:
            return cid, []

    results = {}
    # A modest worker count speeds cold loads without creating an excessive API burst.
    with ThreadPoolExecutor(max_workers=min(4, len(ids))) as executor:
        futures = [executor.submit(_fetch, cid) for cid in ids]
        for future in as_completed(futures):
            cid, data = future.result()
            results[cid] = data
    return results

@st.cache_data(ttl=300)
def get_market_chart(coin_id, days="1"):
    try:
        r = requests.get(f"https://pro-api.coingecko.com/api/v3/coins/{coin_id}/market_chart", headers=HEADERS,
            params={"vs_currency":"usd","days":days}, timeout=10)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

@st.cache_data(ttl=300)
def search_coins(query):
    if not query or len(query) < 2: return []
    try:
        r = requests.get("https://pro-api.coingecko.com/api/v3/search", headers=HEADERS, params={"query":query}, timeout=8)
        return r.json().get("coins", [])[:10]
    except:
        return []

def analyze_candles(ohlc_data):
    if not isinstance(ohlc_data, list) or len(ohlc_data) < 4: return 0.0
    df = pd.DataFrame(ohlc_data[-8:], columns=["timestamp","open","high","low","close"])
    quality = 0.0
    for _, row in df.iterrows():
        body = abs(row["close"] - row["open"])
        upper_wick = row["high"] - max(row["open"], row["close"])
        lower_wick = min(row["open"], row["close"]) - row["low"]
        full_range = row["high"] - row["low"]
        if full_range == 0: continue
        close_pos = (row["close"] - row["low"]) / full_range
        if close_pos > 0.70 and row["close"] > row["open"]: quality += 0.35
        elif close_pos < 0.30: quality -= 0.25
        if upper_wick > body * 1.5 and upper_wick / full_range > 0.40: quality -= 0.40
        if lower_wick > body * 1.2 and lower_wick / full_range > 0.30: quality += 0.25
    lows, highs, closes = df["low"].values, df["high"].values, df["close"].values
    if len(lows) >= 4:
        if lows[-1] > lows[-2] > lows[-3]: quality += 0.70
        elif lows[-1] > lows[-2]: quality += 0.35
        elif lows[-1] < lows[-2] < lows[-3]: quality -= 0.45
    if len(highs) >= 3 and highs[-1] > highs[-2] > highs[-3]: quality += 0.40
    if len(closes) >= 3 and closes[-1] > closes[-2] > closes[-3]: quality += 0.45
    elif len(closes) >= 2 and closes[-1] < closes[-2]: quality -= 0.20

    # Recovery recognition: a strong latest close after choppy/weak candles should
    # soften stale rejection pressure without being treated as a breakout.
    last = df.iloc[-1]
    last_range = last["high"] - last["low"]
    if last_range > 0:
        last_close_pos = (last["close"] - last["low"]) / last_range
        last_body = abs(last["close"] - last["open"])
        last_lower_wick = min(last["open"], last["close"]) - last["low"]
        if last["close"] > last["open"] and last_close_pos >= 0.65:
            quality += 0.35
            if last_lower_wick > last_body * 0.8 and last_lower_wick / last_range >= 0.25:
                quality += 0.15

    return max(min(quality, 1.8), -1.5)

def calc_vibe(price, high, low, change_1h, change_24h, fg_value=None, btc_change=None, candle_quality=0, coin_id=None):
    """Balanced Vibe calibration.

    v2.9 keeps the restrained breakout logic while making negative candle structure
    asymmetric and recognizing genuine short-term recovery. No new API inputs are
    required; this is purely a weighting/calibration change.
    """
    if high != low:
        range_pos = ((price - low) / (high - low)) * 100
    else:
        range_pos = 50.0

    reasons = []
    base = 56.0

    # Positive structure can earn its full reward, while negative candle quality is
    # intentionally less powerful. Crypto naturally wicks/chops, so rejection alone
    # should not drag an otherwise neutral setup deeply bearish.
    structure_boost = candle_quality * (8.0 if candle_quality >= 0 else 4.5)
    base += structure_boost
    if candle_quality > 1.0: reasons.append("Excellent bullish structure")
    elif candle_quality > 0.5: reasons.append("Solid constructive structure")
    elif candle_quality > 0.15: reasons.append("Mildly positive structure")
    elif candle_quality < -0.7:
        # Only call structure outright weak when another live signal confirms it.
        vs_btc_now = (change_24h - btc_change) if btc_change is not None else 0.0
        if change_1h < -0.4 or range_pos < 25 or vs_btc_now < -1.5:
            reasons.append("Weak structure / rejection")
        else:
            reasons.append("Mixed structure / attempted recovery")
    elif candle_quality < -0.25: reasons.append("Mixed structure")

    # Non-linear range positioning: the middle 40-60% is mostly neutral, while
    # genuine upper/lower-range positioning matters progressively more.
    if range_pos >= 100:
        # Keep rewarding genuine breaks above the measured range, but ramp the
        # contribution gradually so a single threshold crossing cannot make Vibe jump.
        range_effect = 5.0 + min(range_pos - 100, 30) * 0.12
    elif range_pos >= 80:
        range_effect = 3.0 + (range_pos - 80) * 0.10       # +3.0 to +5.0
    elif range_pos >= 60:
        range_effect = 0.6 + (range_pos - 60) * 0.12      # +0.6 to +3.0
    elif range_pos >= 40:
        range_effect = (range_pos - 50) * 0.04            # -0.4 to +0.4
    elif range_pos >= 20:
        range_effect = -0.4 - (40 - range_pos) * 0.09     # -0.4 to -2.2
    else:
        range_effect = -2.2 - (20 - range_pos) * 0.09     # -2.2 to -4.0
    base += range_effect

    if range_pos > 88: reasons.append("Near top of daily range")
    elif range_pos > 72: reasons.append("Upper half of range")
    elif range_pos < 18: reasons.append("Building from lows" if candle_quality > 0.15 else "Near bottom of range")
    elif range_pos < 32: reasons.append("Lower half of range")

    # Keep short-term momentum important, but reduce the chance that one fast
    # candle alone pushes a merely decent setup into the mid/high 70s.
    base += change_1h * 2.9
    if change_1h > 2.0: reasons.append("Very strong 1h momentum")
    elif change_1h > 0.7: reasons.append("Strong 1h momentum")
    elif change_1h > 0.2: reasons.append("Positive 1h")
    elif change_1h < -1.5: reasons.append("Strong negative 1h")
    elif change_1h < -0.4: reasons.append("Mild negative 1h")

    # 24h performance remains useful context without overpowering current setup.
    base += change_24h * 0.38

    # Relative strength remains meaningful for alts. BTC cannot outperform itself,
    # so give Bitcoin a small absolute-momentum contribution instead of forcing this
    # component to zero during broad-market breakouts.
    if coin_id == "bitcoin":
        btc_abs_effect = max(min(change_24h * 0.25, 2.5), -2.0)
        base += btc_abs_effect
        if change_24h > 4.0: reasons.append("Strong BTC market momentum")
    elif btc_change is not None:
        vs_btc = change_24h - btc_change
        base += vs_btc * 0.62
        if vs_btc > 3.5: reasons.append("Clearly outperforming BTC")
        elif vs_btc > 1.2: reasons.append("Outperforming BTC")
        elif vs_btc < -3.5: reasons.append("Lagging BTC")

    # Keep market context small so Vibe remains primarily coin-specific.
    if fg_value is not None:
        if fg_value < 25: base -= 1.25
        elif fg_value > 75: base += 1.0

    # Predictive breakout credit is continuous rather than threshold-driven.
    # This preserves early-move sensitivity while avoiding abrupt 5-10 point jumps
    # when price barely crosses a hard range-position level.
    if range_pos >= 80 and change_1h >= 0.35 and candle_quality > 0.0:
        pos_factor = min(max((range_pos - 80) / 30.0, 0.0), 1.0)
        mom_factor = min(max((change_1h - 0.35) / 1.15, 0.0), 1.0)
        structure_factor = min(max(candle_quality / 0.75, 0.0), 1.0)
        breakout_bonus = 1.0 + (1.5 * pos_factor) + (1.5 * mom_factor) + (0.75 * structure_factor)
        base += breakout_bonus

        if breakout_bonus >= 4.0:
            reasons.append("Strong confirmed breakout")
        elif breakout_bonus >= 2.5:
            reasons.append("Clear breakout in progress")
        elif breakout_bonus >= 1.6:
            reasons.append("Breaking higher with momentum")
        else:
            reasons.append("Pushing into breakout territory")

    # Small rejection penalty only when price is high in the range AND structure
    # is clearly deteriorating. This avoids making the model overly bearish.
    if range_pos >= 80 and candle_quality < -0.25:
        base -= 0.75
        reasons.append("Upper-range rejection risk")

    score = max(min(int(round(base)), 98), 16)
    if score >= 90: meme = "🔥 Explosive strength + clear breakout"
    elif score >= 80: meme = "🚀 Strong structure + solid momentum"
    elif score >= 70: meme = "📈 Constructive structure, building strength"
    elif score >= 60: meme = "👍 Decent structure, mild positive bias"
    elif score >= 50: meme = "😐 Mixed signals, no clear direction"
    elif score >= 40: meme = "⚠️ Weakening structure, caution"
    elif score >= 30: meme = "📉 Short-term weakness dominating"
    else: meme = "💀 Heavy selling pressure / poor structure"
    return score, meme, range_pos, reasons

def colored_progress(score: int, height: int = 10):
    if score >= 80: color = "linear-gradient(90deg, #34d399, #00e676)"
    elif score >= 60: color = "linear-gradient(90deg, #5eead4, #14b8a6)"
    elif score >= 40: color = "linear-gradient(90deg, #fde047, #f59e0b)"
    else: color = "linear-gradient(90deg, #fb7185, #ef4444)"
    return f"""
    <div class="pb-score-track" style="height:{height}px;">
        <div style="width:{score}%;height:100%;background:{color};border-radius:999px;"></div>
    </div>
    """

def make_sparkline(history, height=190):
    """Vibe history with a fixed 0-100 scale and subtle interpretation bands."""
    if not history or len(history) < 2:
        return None

    times = [h[0] for h in history]
    scores = [h[1] for h in history]
    line_color = "#00e676" if scores[-1] >= 80 else "#14b8a6" if scores[-1] >= 60 else "#f59e0b" if scores[-1] >= 40 else "#ef4444"

    fig = go.Figure()

    # Very subtle score zones: Weak / Neutral / Constructive / Strong.
    bands = [
        (0, 40, "rgba(239,68,68,0.040)"),
        (40, 60, "rgba(245,158,11,0.035)"),
        (60, 80, "rgba(20,184,166,0.035)"),
        (80, 100, "rgba(0,230,118,0.045)"),
    ]
    for y0, y1, color in bands:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, line_width=0, layer="below")

    for y in (40, 60, 80):
        fig.add_hline(y=y, line_width=1, line_dash="dot", line_color="rgba(160,160,160,0.18)")

    fig.add_trace(go.Scatter(
        x=times, y=scores, mode="lines",
        line=dict(color=line_color, width=2.6),
        fill="tozeroy",
        fillcolor="rgba(0,230,118,0.09)" if scores[-1] >= 80 else "rgba(20,184,166,0.08)" if scores[-1] >= 60 else "rgba(245,158,11,0.07)" if scores[-1] >= 40 else "rgba(239,68,68,0.08)",
        hovertemplate="Vibe %{y:.0f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=[times[-1]], y=[scores[-1]], mode="markers+text",
        marker=dict(size=9, color=line_color, line=dict(width=2, color="#0e1117")),
        text=[f"  {scores[-1]:.0f}"], textposition="middle right",
        textfont=dict(size=11, color=line_color), hoverinfo="skip"
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=42, r=42, t=8, b=22),
        xaxis=dict(showgrid=False, showticklabels=True, tickfont=dict(size=10, color="#8b8f98"), zeroline=False),
        yaxis=dict(
            showgrid=False, showticklabels=True, zeroline=False, range=[0, 100],
            tickmode="array", tickvals=[0, 20, 40, 60, 80, 100],
            tickfont=dict(size=10, color="#8b8f98")
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hovermode="x unified"
    )
    return fig

def get_score_arrow(cid, current_score):
    hist = st.session_state.score_history.get(cid, [])
    if len(hist) < 2:
        return ""
    prev = hist[-2][1]
    if current_score > prev:
        return ' <span style="color:#00c853;font-weight:800;">↑</span>'
    elif current_score < prev:
        return ' <span style="color:#ff5252;font-weight:800;">↓</span>'
    return ""

def get_direction(cid, current_score):
    hist = st.session_state.score_history.get(cid, [])
    if len(hist) < 2:
        return "→ Flat"
    prev = hist[-2][1]
    if current_score > prev + 1:
        return "↑ Rising"
    elif current_score < prev - 1:
        return "↓ Falling"
    return "→ Flat"

@st.cache_data(ttl=120)
def get_single_coin_market(cid):
    try:
        r = requests.get(
            "https://pro-api.coingecko.com/api/v3/coins/markets",
            headers=HEADERS,
            params={"vs_currency":"usd","ids":cid,"price_change_percentage":"1h,24h"},
            timeout=8
        )
        if r.status_code != 200:
            return []
        return r.json()
    except:
        return []

def fetch_single_coin_vibe(cid, btc_change, fg_value):
    try:
        data = get_single_coin_market(cid)
        if not data: return None
        c = data[0]
        price = c["current_price"]
        high, low = c["high_24h"], c["low_24h"]
        ch1 = c.get("price_change_percentage_1h_in_currency") or 0
        ch24 = c.get("price_change_percentage_24h") or 0
        ohlc = top_ohlc_map.get(cid) if cid in top_ohlc_map else get_ohlc(cid, "1")
        cq = analyze_candles(ohlc)
        score, meme, range_pos, reasons = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, cq, cid)
        st.session_state.score_history = update_history(cid, score, st.session_state.score_history)
        return {
            "name": c["name"], "cid": cid, "tick": c["symbol"].upper(),
            "price": price, "ch24": ch24, "ch1": ch1, "score": score, "meme": meme,
            "image_url": c.get("image", ""), "candle_quality": cq,
            "range_pos": range_pos, "reasons": reasons,
            "history": st.session_state.score_history.get(cid, []),
            "prev_score": st.session_state.score_history.get(cid, [[None, None]])[-2][1] if len(st.session_state.score_history.get(cid, [])) >= 2 else None
        }
    except:
        return None

# ========== HEADER ==========
col_title, col_refresh = st.columns([6, 1])

with col_title:
    st.markdown("""
    <div class="pb-header">
        <div class="pb-title-row">
            <div class="pb-logo-mark">🚀</div>
            <div>
                <div class="pb-title">Pre Bart Vibes</div>
                <div class="pb-subtitle">Real-time market vibes for the coins that matter most.</div>
            </div>
            <span class="live-badge"><span class="live-dot"></span> LIVE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_refresh:
    st.write("")
    st.write("")
    if st.button("↻ Refresh", use_container_width=True):
        # Rerun the UI without destroying expensive CoinGecko caches.
        # Cached market data refreshes automatically according to each function's TTL.
        st.session_state.last_refresh = datetime.now()
        st.rerun()

st.markdown(f'<div class="pb-refresh-note">Last refreshed {st.session_state.last_refresh.strftime('%H:%M:%S')}</div>', unsafe_allow_html=True)

# ========== MARKET CONTEXT ==========
fg_value, fg_label = get_fear_greed()
global_data = get_global()

ctx1, ctx2, ctx3, ctx4 = st.columns(4)
with ctx1:
    st.metric("Fear & Greed", f"{fg_value} {'🟢' if fg_value and fg_value >= 55 else '🟡' if fg_value and fg_value >= 40 else '🔴'}" if fg_value else "—", fg_label)
with ctx2:
    st.metric("BTC Dominance", f"{global_data['market_cap_percentage'].get('btc', 0):.1f}%" if global_data else "—")
with ctx3:
    st.metric("Total Crypto MCap", f"${global_data['total_market_cap']['usd']/1e12:.2f}T" if global_data else "—")
with ctx4:
    st.metric("Market 24h", f"{global_data.get('market_cap_change_percentage_24h_usd', 0):+.2f}%" if global_data else "—")

st.divider()
fill_pending_returns()

# ========== TOP COINS ==========
# Fetch a slightly wider market-cap list in the same single CoinGecko request,
# remove stablecoins, then keep the first 30 non-stablecoins. OHLC/Vibe work is
# still performed for only 30 coins, so stablecoins do not create extra OHLC calls.
top_market_coins = get_top_coins(40)
top_coins = [c for c in top_market_coins if not is_stablecoin(c)][:30]
if not top_coins:
    st.error("Could not load top coins.")
    st.stop()

COIN_ORDER = []
coin_map = {}
for c in top_coins:
    name, cid, tick = c["name"], c["id"], c["symbol"].upper()
    COIN_ORDER.append((name, cid, tick))
    coin_map[cid] = c

btc_change = next((c.get("price_change_percentage_24h") or 0 for c in top_coins if c["id"] == "bitcoin"), 0)

# Fetch the 1-day OHLC inputs concurrently. This keeps every coin's Vibe
# calculation and snapshot collection intact while cutting cold-load latency.
top_ohlc_map = get_ohlc_batch(tuple(cid for _, cid, _ in COIN_ORDER), "1")

vibe_data = []
pending_snapshot_rows = []
for name, cid, tick in COIN_ORDER:
    c = coin_map.get(cid)
    if not c: continue
    price = c["current_price"]
    high, low = c["high_24h"], c["low_24h"]
    ch1 = c.get("price_change_percentage_1h_in_currency") or 0
    ch24 = c.get("price_change_percentage_24h") or 0
    image_url = c.get("image", "")
    ohlc = top_ohlc_map.get(cid) or get_ohlc(cid, "1")
    cq = analyze_candles(ohlc)
    score, meme, range_pos, reasons = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, cq, cid)
    st.session_state.score_history = update_history(cid, score, st.session_state.score_history)
    hist = st.session_state.score_history.get(cid, [])
    prev_score = hist[-2][1] if len(hist) >= 2 else None
    if prev_score is not None:
        if score >= 80 and prev_score < 80: st.toast(f"{tick} Vibe crossed 80!", icon="🔥")
        elif score >= 70 and prev_score < 70: st.toast(f"{tick} Vibe crossed 70!", icon="🚀")
        elif score <= 30 and prev_score > 30: st.toast(f"{tick} Vibe dropped below 30", icon="🐻")
        elif score <= 40 and prev_score > 40: st.toast(f"{tick} Vibe dropped below 40", icon="⚠️")
    vs_btc_val = ch24 - btc_change
    queue_vibe_snapshot(
        pending_snapshot_rows, cid, tick, price, score, meme, ch24, range_pos, vs_btc_val, prev_score,
        {
            "reasons": reasons, "candle_quality": cq, "change_1h": ch1,
            "change_24h": ch24, "range_pos": range_pos, "vs_btc": vs_btc_val,
            "score_delta": (score - prev_score) if prev_score is not None else None,
            "app_version": APP_VERSION,
        }
    )
    vibe_data.append({
        "name": name, "cid": cid, "tick": tick, "price": price, "ch24": ch24, "ch1": ch1,
        "score": score, "meme": meme, "image_url": image_url, "candle_quality": cq,
        "range_pos": range_pos, "reasons": reasons, "history": st.session_state.score_history.get(cid, []),
        "prev_score": prev_score
    })

# One Supabase insert per collection cycle instead of one insert per coin.
save_vibe_snapshots_batch(pending_snapshot_rows)

vibe_data_sorted = sorted(vibe_data, key=lambda x: x["score"], reverse=True)

avg_vibe = sum(v["score"] for v in vibe_data) / len(vibe_data) if vibe_data else 50

# Market Bias now reflects the aggregate Vibe Score only.
# Funding rates/Open Interest were removed to reduce unnecessary external data calls.
# Keep the aggregate label deliberately conservative around the midpoint.
# A market averaging in the high-50s is mixed/neutral, not a bullish regime.
if avg_vibe >= 75:
    bias, bias_color = "Strongly Bullish", "#22c55e"
elif avg_vibe >= 65:
    bias, bias_color = "Mildly Bullish", "#14b8a6"
elif avg_vibe <= 35:
    bias, bias_color = "Strongly Bearish", "#ef5350"
elif avg_vibe <= 45:
    bias, bias_color = "Mildly Bearish", "#fb7185"
else:
    bias, bias_color = "Neutral / Mixed", "#f59e0b"

strongest = vibe_data_sorted[0] if vibe_data_sorted else None
weakest = vibe_data_sorted[-1] if vibe_data_sorted else None

# ========== MAIN + SIDE PANEL ==========
main_col, side_col = st.columns([4.2, 1], gap="medium")

with main_col:
    st.subheader("🌐 Multi-Coin Vibe Overview")

    f1, f2 = st.columns([2, 2])
    with f1:
        filter_opt = st.selectbox(
            "Quick Filter",
            ["All", "Vibe ≥ 70", "Vibe ≥ 60", "Vibe ≤ 40", "Rising", "Falling", "Watchlist Only"],
            index=["All", "Vibe ≥ 70", "Vibe ≥ 60", "Vibe ≤ 40", "Rising", "Falling", "Watchlist Only"].index(st.session_state.quick_filter)
            if st.session_state.quick_filter in ["All", "Vibe ≥ 70", "Vibe ≥ 60", "Vibe ≤ 40", "Rising", "Falling", "Watchlist Only"] else 0
        )
        st.session_state.quick_filter = filter_opt
    with f2:
        show_option = st.selectbox(
            "Show", 
            ["Top 5", "Top 10", "Top 15", "All"],
            index=["Top 5","Top 10","Top 15","All"].index(st.session_state.show_count) 
            if st.session_state.show_count in ["Top 5","Top 10","Top 15","All"] else 0
        )
        st.session_state.show_count = show_option

    filtered = vibe_data_sorted.copy()
    if filter_opt == "Vibe ≥ 70":
        filtered = [v for v in filtered if v["score"] >= 70]
    elif filter_opt == "Vibe ≥ 60":
        filtered = [v for v in filtered if v["score"] >= 60]
    elif filter_opt == "Vibe ≤ 40":
        filtered = [v for v in filtered if v["score"] <= 40]
    elif filter_opt == "Rising":
        filtered = [v for v in filtered if v.get("prev_score") is not None and v["score"] > v["prev_score"]]
    elif filter_opt == "Falling":
        filtered = [v for v in filtered if v.get("prev_score") is not None and v["score"] < v["prev_score"]]
    elif filter_opt == "Watchlist Only":
        filtered = [v for v in filtered if v["cid"] in st.session_state.watchlist]

    if show_option == "Top 5":
        display_data = filtered[:5]
    elif show_option == "Top 10":
        display_data = filtered[:10]
    elif show_option == "Top 15":
        display_data = filtered[:15]
    else:
        display_data = filtered

    st.caption(f"Showing {len(display_data)} of {len(filtered)} coins")

    # ===== WATCHLIST =====
    if st.session_state.watchlist:
        st.markdown("##### ⭐ Your Watchlist")
        watch_items = []
        for cid in st.session_state.watchlist:
            item = next((v for v in vibe_data if v["cid"] == cid), None)
            if item is None:
                item = fetch_single_coin_vibe(cid, btc_change, fg_value)
            if item:
                watch_items.append(item)
        
        watch_items = sorted(watch_items, key=lambda x: x["score"], reverse=True)
        
        if watch_items:
            cols = st.columns(3)
            for i, item in enumerate(watch_items):
                with cols[i % 3]:
                    with st.container(border=True):
                        if item["image_url"]:
                            st.image(item["image_url"], width=24)
                        st.markdown(f"**{item['tick']}**")
                        
                        price_str = f"${item['price']:,.0f}" if item["price"] >= 1000 else f"${item['price']:,.2f}" if item["price"] >= 1 else f"${item['price']:.4f}"
                        st.markdown(f"<div style='font-size:1.2rem;font-weight:700;height:26px;line-height:26px;overflow:hidden;'>{price_str}</div>", unsafe_allow_html=True)
                        
                        arrow = get_score_arrow(item["cid"], item["score"])
                        ch_color = "#00c853" if item["ch24"] >= 0 else "#ff5252"
                        st.markdown(
                            f"<div style='font-size:12.5px;height:20px;line-height:20px;overflow:hidden;'>"
                            f"<span style='color:{ch_color};font-weight:600'>{item['ch24']:+.2f}%</span> • Vibe {item['score']}{arrow}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        
                        if len(item.get("history", [])) >= 3:
                            fig = make_sparkline(item["history"], height=70)
                            if fig:
                                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                        else:
                            st.markdown("<div style='height:70px;'></div>", unsafe_allow_html=True)
                        
                        vs_btc = item["ch24"] - btc_change
                        direction = get_direction(item["cid"], item["score"])
                        st.markdown(
                            f"<div style='font-size:11px;color:#888;height:32px;line-height:1.3;overflow:hidden;'>"
                            f"Range {item['range_pos']:.0f}% · vsBTC {vs_btc:+.1f}% · CQ {item['candle_quality']:+.1f}<br>"
                            f"1h {item['ch1']:+.2f}% · {direction}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        
                        st.markdown(colored_progress(item["score"], height=6), unsafe_allow_html=True)
                        
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("View", key=f"watch_view_{item['cid']}", use_container_width=True):
                                st.session_state.selected_coin = item["name"]
                                st.session_state.search_coin = item["cid"]
                                st.rerun()
                        with b2:
                            if st.button("Unpin", key=f"unpin_{item['cid']}", use_container_width=True):
                                st.session_state.watchlist.remove(item["cid"])
                                st.rerun()
        st.divider()

    # ===== MAIN GRID =====
    if not display_data:
        st.info("No coins match this filter right now.")
    else:
        for row_start in range(0, len(display_data), 5):
            cols = st.columns(5)
            for i, item in enumerate(display_data[row_start:row_start+5]):
                with cols[i]:
                    with st.container(border=True):
                        if item["image_url"]:
                            st.image(item["image_url"], width=24)
                        else:
                            st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
                        
                        st.markdown(f"**{item['tick']}**")
                        
                        price_str = f"${item['price']:,.0f}" if item["price"]>=1000 else f"${item['price']:,.2f}" if item["price"]>=1 else f"${item['price']:.4f}"
                        st.markdown(f"<div style='font-size:1.15rem;font-weight:600;height:26px;line-height:26px;overflow:hidden;'>{price_str}</div>", unsafe_allow_html=True)
                        
                        arrow = get_score_arrow(item["cid"], item["score"])
                        st.markdown(
                            f"<div style='font-size:12px;color:#888;height:18px;line-height:18px;overflow:hidden;'>"
                            f"{item['ch24']:+.2f}% • Vibe {item['score']}{arrow}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        
                        st.markdown(colored_progress(item["score"], height=7), unsafe_allow_html=True)
                        
                        st.markdown(
                            f"<div style='height:36px;font-size:12px;color:#888;line-height:1.25;overflow:hidden;'>"
                            f"{item['meme']}</div>",
                            unsafe_allow_html=True
                        )
                        
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("View", key=f"btn_{item['cid']}", use_container_width=True):
                                st.session_state.selected_coin = item["name"]
                                st.session_state.search_coin = None
                                st.rerun()
                        with b2:
                            is_watched = item["cid"] in st.session_state.watchlist
                            label = "★" if is_watched else "☆"
                            if st.button(label, key=f"watch_{item['cid']}", use_container_width=True):
                                if is_watched:
                                    st.session_state.watchlist.remove(item["cid"])
                                else:
                                    st.session_state.watchlist.append(item["cid"])
                                st.rerun()

with side_col:
    st.markdown("### ⚡ Market Pulse")

    st.markdown(f"""
    <div class="pb-side-card">
      <div class="pb-side-title">Market Bias</div>
      <div class="pb-bias-value" style="color:{bias_color};">● <span style="color:#f5f7fa">{bias}</span></div>
      <div class="pb-side-sub">Avg Vibe {avg_vibe:.1f} · bullish bias begins at 65</div>
    </div>
    """, unsafe_allow_html=True)

    if strongest and weakest:
        strong_color = "#22c55e" if strongest["score"] >= 80 else "#14b8a6" if strongest["score"] >= 60 else "#f59e0b"
        weak_color = "#ef5350" if weakest["score"] < 40 else "#f59e0b" if weakest["score"] < 60 else "#14b8a6"
        st.markdown(f"""
        <div class="pb-side-card">
          <div class="pb-side-title">Strongest / Weakest</div>
          <div class="pb-extreme-row"><div class="pb-extreme-name"><span style="color:#22c55e">▲</span>{strongest['tick']}</div><span class="pb-score-chip" style="color:{strong_color};border-color:{strong_color}55;background:{strong_color}12">{strongest['score']}</span></div>
          <div class="pb-extreme-row"><div class="pb-extreme-name"><span style="color:#ef5350">▼</span>{weakest['tick']}</div><span class="pb-score-chip" style="color:{weak_color};border-color:{weak_color}55;background:{weak_color}12">{weakest['score']}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # Top Movers: self-contained UI card so it exactly matches the two cards above.
    # Both timeframes are already present in vibe_data, so switching tabs is client-side
    # presentation only and adds no API calls or Streamlit reruns.
    def _mover_panel(metric_key, panel_class):
        gainers = sorted(vibe_data, key=lambda x: x[metric_key], reverse=True)[:3]
        losers = sorted(vibe_data, key=lambda x: x[metric_key])[:3]
        gain_rows = "".join(
            f'<div class="pb-mover-row"><span class="pb-mover-symbol">{m["tick"]}</span>'
            f'<span style="color:#22c55e;font-weight:700">{m[metric_key]:+.2f}%</span></div>'
            for m in gainers
        )
        loss_rows = "".join(
            f'<div class="pb-mover-row"><span class="pb-mover-symbol">{m["tick"]}</span>'
            f'<span style="color:#ef5350;font-weight:700">{m[metric_key]:+.2f}%</span></div>'
            for m in losers
        )
        return (
            f'<div class="pb-movers-panel {panel_class}">'
            '<div class="pb-mover-section">'
            '<div class="pb-mover-head"><span>Gainers</span><span>Move</span></div>'
            + gain_rows +
            '</div>'
            '<div class="pb-mover-section">'
            '<div class="pb-mover-head"><span>Losers</span><span>Move</span></div>'
            + loss_rows +
            '</div>'
            '</div>'
        )

    movers_1h = _mover_panel("ch1", "pb-movers-panel-1h")
    movers_24h = _mover_panel("ch24", "pb-movers-panel-24h")

    movers_html = (
        '<div class="pb-side-card pb-movers-card">'
        '<div class="pb-side-title">Top Movers</div>'
        '<div class="pb-mover-tabs">'
        '<input type="radio" name="pb-movers-tf" id="pb-movers-1h" checked>'
        '<label for="pb-movers-1h">1h</label>'
        '<input type="radio" name="pb-movers-tf" id="pb-movers-24h">'
        '<label for="pb-movers-24h">24h</label>'
        '</div>'
        + movers_1h
        + movers_24h
        + '</div>'
    )
    st.markdown(movers_html, unsafe_allow_html=True)


st.divider()

# ========== DETAILED VIEW ==========
st.subheader("🎯 Detailed View")
st.markdown("##### Search any coin on CoinGecko")

search_query = st.text_input("Type coin name or symbol", placeholder="e.g. Avalanche, PEPE, WIF, BONK...", key="detail_search")
if search_query and len(search_query.strip()) >= 2:
    results = search_coins(search_query.strip())
    if results:
        options = {f"{c['name']} ({c['symbol'].upper()})": c["id"] for c in results}
        chosen = st.selectbox("Select from results", list(options.keys()), key="search_results_select")
        selected_id = options[chosen]
        if st.session_state.search_coin != selected_id:
            st.session_state.search_coin = selected_id
            st.session_state.selected_coin = chosen.split(" (")[0]
            st.rerun()
    else:
        st.info("No coins found.")
else:
    st.caption("Type at least 2 characters to search")

if st.session_state.search_coin:
    single = get_single_coin_market(st.session_state.search_coin)
    if single:
        c = single[0]
        name, cid, tick = c["name"], c["id"], c["symbol"].upper()
        price, high, low = c["current_price"], c["high_24h"], c["low_24h"]
        ch1 = c.get("price_change_percentage_1h_in_currency") or 0
        ch24 = c.get("price_change_percentage_24h") or 0
        ohlc = top_ohlc_map.get(cid) if cid in top_ohlc_map else get_ohlc(cid, "1")
        cq = analyze_candles(ohlc)
        score, meme, range_pos, reasons = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, cq, cid)
        volume, market_cap = c["total_volume"], c["market_cap"]
        image_url = c.get("image", "")
        st.session_state.score_history = ensure_coin_history_loaded(cid, st.session_state.score_history)
        st.session_state.score_history = update_history(cid, score, st.session_state.score_history)
        history = st.session_state.score_history.get(cid, [])
        prev_score = history[-2][1] if len(history) >= 2 else None
        save_vibe_snapshot(
            cid, tick, price, score, meme, ch24, range_pos, ch24-btc_change, prev_score,
            {
                "reasons": reasons, "candle_quality": cq, "change_1h": ch1,
                "change_24h": ch24, "range_pos": range_pos, "vs_btc": ch24-btc_change,
                "score_delta": (score - prev_score) if prev_score is not None else None,
                "app_version": APP_VERSION,
            }
        )
    else:
        st.warning("Could not load coin data.")
        st.stop()
else:
    item = next((v for v in vibe_data if v["name"] == st.session_state.selected_coin), vibe_data[0] if vibe_data else None)
    if not item:
        st.info("Search for a coin or click View on a card.")
        st.stop()
    name, cid, tick = item["name"], item["cid"], item["tick"]
    price, ch24, ch1 = item["price"], item["ch24"], item["ch1"]
    score, meme = item["score"], item["meme"]
    range_pos, cq, reasons = item["range_pos"], item["candle_quality"], item["reasons"]
    st.session_state.score_history = ensure_coin_history_loaded(cid, st.session_state.score_history)
    history = st.session_state.score_history.get(cid, item["history"])
    c = coin_map.get(cid, {})
    volume = c.get("total_volume", 0)
    market_cap = c.get("market_cap", 0)
    high = c.get("high_24h", price)
    low = c.get("low_24h", price)
    image_url = item["image_url"]

vs_btc = ch24 - (btc_change or 0)
price_text = f"${price:,.4f}" if price < 10 else f"${price:,.2f}"
arrow = get_score_arrow(cid, score)

def vibe_band(score):
    if score >= 80:
        return "Strong", "#00e676"
    if score >= 60:
        return "Constructive", "#14b8a6"
    if score >= 40:
        return "Neutral", "#f59e0b"
    return "Weak", "#ef4444"

band_label, band_color = vibe_band(score)

def vibe_context_copy(score, direction):
    if score >= 80:
        return "Strong market conditions are holding." if "Weakening" not in direction else "Strong conditions remain, but momentum is cooling."
    if score >= 60:
        return "Market setup is strengthening." if "Improving" in direction else "Constructive conditions with room for confirmation."
    if score >= 40:
        return "Mixed conditions — patience may offer a cleaner setup."
    return "Weak conditions are dominating right now."

def get_one_hour_vibe_context(history, current_score):
    """Return the score change over roughly one hour using already-collected history."""
    if not history:
        return None, "→ Stable", "#8f949e"

    now = datetime.now(timezone.utc)
    target = now - timedelta(hours=1)
    normalized = []
    for ts, hist_score in history:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        normalized.append((ts, hist_score))

    # Use the reading closest to one hour ago, but only when it is reasonably
    # close to that horizon. This avoids presenting a misleading 1h change.
    closest_ts, closest_score = min(normalized, key=lambda x: abs((x[0] - target).total_seconds()))
    if abs((closest_ts - target).total_seconds()) > 20 * 60:
        delta = None
    else:
        delta = int(current_score) - int(closest_score)

    # Direction uses the recent trajectory when a clean 1h comparison exists.
    if delta is not None:
        if delta >= 3:
            return delta, "↑ Improving", "#00c853"
        if delta <= -3:
            return delta, "↓ Weakening", "#ff5252"
        return delta, "→ Stable", "#8f949e"

    # Fall back to the last two readings if one hour of history is unavailable.
    if len(normalized) >= 2:
        recent_delta = int(current_score) - int(normalized[-2][1])
        if recent_delta >= 2:
            return None, "↑ Improving", "#00c853"
        if recent_delta <= -2:
            return None, "↓ Weakening", "#ff5252"
    return None, "→ Stable", "#8f949e"

def format_updated_age(history):
    if not history:
        return "Updated now"
    ts = history[-1][0]
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    seconds = max(0, int((datetime.now(timezone.utc) - ts).total_seconds()))
    if seconds < 60:
        return "Updated just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"Updated {minutes}m ago"
    hours = minutes // 60
    return f"Updated {hours}h ago"

vibe_1h_delta, vibe_direction, vibe_direction_color = get_one_hour_vibe_context(history, score)
vibe_delta_text = f"{vibe_1h_delta:+d} over 1h" if vibe_1h_delta is not None else "1h change building"
updated_text = format_updated_age(history)
context_copy = vibe_context_copy(score, vibe_direction)

# The Vibe Score is the product's primary signal, so make it the visual anchor.
st.markdown(
    f"""
    <div class="pb-vibe-hero" style="--accent:{band_color};">
      <div class="pb-vibe-main">
        <div class="pb-eyebrow">{name} · {tick}</div>
        <div class="pb-score-line">
          <span class="pb-score-number">{score}</span>
          <span class="pb-score-denom">/ 100</span>
          <span class="pb-status-pill" style="border-color:{band_color}66;background:{band_color}18;color:{band_color};">{band_label}</span>{arrow}
        </div>
        <div class="pb-signal-row">
          <span style="color:{vibe_direction_color};font-weight:750;">{vibe_direction}</span>
          <span class="pb-dot-sep">·</span>
          <span>{vibe_delta_text}</span>
          <span class="pb-dot-sep">·</span>
          <span class="pb-updated">{updated_text}</span>
        </div>
        <div class="pb-context-copy">{context_copy}</div>
      </div>
      <div class="pb-price-panel">
        <div class="pb-eyebrow">Price</div>
        <div class="pb-price-value">{price_text}</div>
        <div class="pb-price-change" style="color:{'#00e676' if ch24 >= 0 else '#ef4444'};">{ch24:+.2f}% 24h <span>·</span> {ch1:+.2f}% 1h</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(colored_progress(score, height=9), unsafe_allow_html=True)

# Compact supporting metrics instead of five equally heavy cards.
st.markdown(
    f"""
    <div class="pb-metrics-grid">
      <div class="pb-mini-card"><div class="pb-mini-label"><span>◫</span> 24h Volume</div><div class="pb-mini-value">${volume/1_000_000:,.1f}M</div></div>
      <div class="pb-mini-card"><div class="pb-mini-label"><span>↕</span> Range Position</div><div class="pb-mini-value">{range_pos:.0f}%</div></div>
      <div class="pb-mini-card"><div class="pb-mini-label"><span>↗</span> vs BTC · 24h</div><div class="pb-mini-value" style="color:{'#00e676' if vs_btc >= 0 else '#ef4444'};">{vs_btc:+.2f}%</div></div>
      <div class="pb-mini-card"><div class="pb-mini-label"><span>◈</span> Market Cap</div><div class="pb-mini-value">${market_cap/1_000_000_000:,.2f}B</div></div>
    </div>
    """,
    unsafe_allow_html=True
)

# Keep the watchlist action directly beneath the supporting metrics row,
# visually anchored under the left-most 24h Volume card.
is_watched = cid in st.session_state.watchlist
_watch_col, _watch_spacer = st.columns([1, 3])
with _watch_col:
    if st.button("★ Remove from Watchlist" if is_watched else "☆ Add to Watchlist", key="detail_watch", use_container_width=True):
        if is_watched:
            st.session_state.watchlist.remove(cid)
        else:
            st.session_state.watchlist.append(cid)
        st.rerun()

# v10: separate "current strength" from "entry/setup context".
setup_rows = get_setup_history(cid, limit=1200)
setup = build_setup_analytics(setup_rows, score, price) if setup_rows else None

def _fmt_delta(val, suffix=""):
    return "—" if val is None else f"{val:+.1f}{suffix}"

def _fmt_price_delta(val):
    """Keep tiny price responses visible instead of rounding them into +0.0/-0.0."""
    if val is None or pd.isna(val):
        return "—"
    val = float(val)
    # Extra precision near zero is useful for lead/lag research.
    if abs(val) < 0.10:
        return f"{val:+.3f}%"
    return f"{val:+.2f}%"

st.markdown(
    """<div class="pb-section-head"><div><div class="pb-section-title">Setup Intelligence <span class="pb-global-pill">V10</span></div>
    <div class="pb-section-sub">Separates current market strength from early-move context and historical analogs</div></div></div>""",
    unsafe_allow_html=True
)

if setup:
    dv30_color = "#22c55e" if (setup["dv30"] or 0) >= 3 else "#ef5350" if (setup["dv30"] or 0) <= -3 else "#f59e0b"
    px30_color = "#22c55e" if (setup["px30"] or 0) > 0.35 else "#ef5350" if (setup["px30"] or 0) < -0.35 else "#f59e0b"
    st.markdown(f"""
    <div class="pb-intel-grid">
      <div class="pb-intel-card"><div class="pb-intel-kicker">Current Strength</div><div class="pb-intel-value" style="color:{band_color}">{score} · {band_label}</div><div class="pb-intel-sub">Absolute Vibe describes the market state now.</div></div>
      <div class="pb-intel-card"><div class="pb-intel-kicker">Vibe Velocity</div><div class="pb-intel-value" style="color:{dv30_color}">{_fmt_delta(setup['dv30'])} / 30m</div><div class="pb-intel-sub">{_fmt_delta(setup['dv1h'])} over 1h · {setup['velocity']}</div></div>
      <div class="pb-intel-card"><div class="pb-intel-kicker">Price Response</div><div class="pb-intel-value" style="color:{px30_color}">{_fmt_price_delta(setup['px30'])} / 30m</div><div class="pb-intel-sub">{_fmt_price_delta(setup['px1h'])} over 1h · {setup['price_state']}</div></div>
      <div class="pb-intel-card"><div class="pb-intel-kicker">Lead / Divergence</div><div class="pb-intel-value" style="color:{setup['lead_color']};font-size:1.02rem">{setup['lead_label']}</div><div class="pb-intel-sub">Looks for Vibe changing before price meaningfully follows.</div></div>
    </div>
    """, unsafe_allow_html=True)

else:
    st.caption("Setup Intelligence will populate as this coin builds persisted Vibe + price history.")

# Keep secondary analytics available without competing with the core score.
with st.expander("Score details", expanded=False):
    d1, d2 = st.columns(2)
    d1.metric("Candle Quality", f"{cq:+.1f}")
    d2.metric("24h High / Low", f"${high:,.4f}" if high < 10 else f"${high:,.2f}", f"Low ${low:,.4f}" if low < 10 else f"Low ${low:,.2f}")

    perf = get_coin_performance(cid)
    if perf and perf.get("ready"):
        strength_label, _ = sample_strength(perf["n"])
        st.caption(f"Historical 1h win rate: **{perf['win_1h']}%** · Avg 1h return: **{perf['avg_1h']:+.2f}%** · n = {perf['n']} · Sample: **{strength_label}**")
    else:
        st.caption("Historical performance is still collecting for this coin.")

with st.expander("🤔 Why this score?", expanded=False):
    if reasons:
        for r in reasons:
            st.write(f"• {r}")
    else:
        st.caption("No additional score drivers available for this reading.")

# Vibe + price relationship — v10 adds lead-candidate markers without changing the score.
vp_rows = get_vibe_price_history(cid, limit=150)
if len(vp_rows) >= 3:
    vp = pd.DataFrame(vp_rows)
    vp["time"] = pd.to_datetime(vp["timestamp"], utc=True, errors="coerce")
    vp["price"] = pd.to_numeric(vp["price"], errors="coerce")
    vp["score"] = pd.to_numeric(vp["score"], errors="coerce")
    vp = vp.dropna(subset=["time", "price", "score"]).sort_values("time")
    if len(vp) >= 3:
        st.markdown("""
        <div class="pb-section-head"><div><div class="pb-section-title">Vibe + Price History</div><div class="pb-section-sub">See when Vibe leads, confirms, or diverges from price</div></div></div>
        """, unsafe_allow_html=True)
        rel_fig = make_subplots(specs=[[{"secondary_y": True}]])
        rel_fig.add_trace(go.Scatter(x=vp["time"], y=vp["price"], name="Price", mode="lines", line=dict(color="#cbd5e1", width=2.0)), secondary_y=False)
        rel_fig.add_trace(go.Scatter(x=vp["time"], y=vp["score"], name="Vibe", mode="lines", line=dict(color="#14b8a6", width=2.6)), secondary_y=True)

        # Mark recent positive lead candidates from the richer setup history.
        if setup and isinstance(setup.get("frame"), pd.DataFrame):
            sf = setup["frame"].iloc[:-1].copy()
            leads = sf[(sf["dv_30m"] >= 5) & (sf["px_30m"] <= 0.35)].tail(12)
            if not leads.empty:
                rel_fig.add_trace(go.Scatter(
                    x=leads["time"], y=leads["score"], name="Lead candidate", mode="markers",
                    marker=dict(symbol="diamond", size=7, color="#22c55e", line=dict(width=1,color="#0e1117")),
                    hovertemplate="Potential lead setup<br>Vibe %{y:.0f}<extra></extra>"
                ), secondary_y=True)

        rel_fig.add_hrect(y0=65, y1=100, fillcolor="rgba(20,184,166,.032)", line_width=0, secondary_y=True)
        rel_fig.add_hrect(y0=0, y1=45, fillcolor="rgba(239,83,80,.026)", line_width=0, secondary_y=True)
        rel_fig.update_yaxes(title_text="Price", showgrid=True, gridcolor="rgba(148,163,184,.08)", tickfont=dict(color="#9aa3af", size=10), secondary_y=False)
        rel_fig.update_yaxes(title_text="Vibe", range=[0,100], showgrid=False, tickfont=dict(color="#14b8a6", size=10), secondary_y=True)
        rel_fig.update_xaxes(showgrid=False, tickfont=dict(color="#8b93a1", size=10))
        rel_fig.update_layout(height=300, template="plotly_dark", margin=dict(l=8,r=8,t=10,b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)))
        st.plotly_chart(rel_fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
        st.caption("Green diamonds flag moments when Vibe strengthens before price catches up — potential early-move signals.")


# ========== SHARE SECTION ==========
st.markdown("""
<div class="pb-section-head"><div><div class="pb-section-title">Share this vibe</div><div class="pb-section-sub">Share the current market read</div></div></div>
""", unsafe_allow_html=True)

# Keep the original concise, score-dependent language for the clipboard/X share text.
share_text = (
    f"{tick} Vibe Score: {score}/100 – {meme}\n"
    f"{ch24:+.2f}% 24h | Range {range_pos:.0f}%\n"
    f"https://prebartvibes.xyz"
)
share_text_js = json.dumps(share_text)
share_change_color = "#34d399" if ch24 >= 0 else "#fb7185"

components.html(f"""
<!DOCTYPE html>
<html>
<head>
<style>
    * {{ box-sizing: border-box; }}
    html, body {{
        margin: 0;
        padding: 0;
        background: transparent;
        color: #f7f8fa;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .share-shell {{
        width: min(100%, 720px);
    }}
    .share-card {{
        position: relative;
        overflow: hidden;
        border: 1px solid #2a3039;
        border-radius: 16px;
        background: linear-gradient(145deg, #151a22 0%, #11151b 58%, #0f1419 100%);
        padding: 18px 19px 15px;
        box-shadow: 0 12px 30px rgba(0,0,0,.18);
    }}
    .share-card:before {{
        content: "";
        position: absolute;
        width: 190px;
        height: 190px;
        border-radius: 50%;
        right: -78px;
        top: -105px;
        background: {band_color};
        opacity: .055;
        filter: blur(10px);
        pointer-events: none;
    }}
    .top {{
        position: relative;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 18px;
    }}
    .coin-kicker {{
        color: #7f8792;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: .09em;
        text-transform: uppercase;
    }}
    .coin {{
        margin-top: 4px;
        font-size: 22px;
        line-height: 1.1;
        font-weight: 800;
        letter-spacing: -.03em;
        color: #ffffff;
    }}
    .score-wrap {{ text-align: right; white-space: nowrap; }}
    .score {{
        font-size: 27px;
        font-weight: 850;
        line-height: 1;
        letter-spacing: -.045em;
        color: #ffffff;
    }}
    .denom {{ color: #737b86; font-size: 12px; font-weight: 650; }}
    .pill {{
        display: inline-flex;
        margin-top: 7px;
        padding: 4px 8px;
        border-radius: 999px;
        border: 1px solid {band_color}66;
        background: {band_color}16;
        color: {band_color};
        font-size: 9.5px;
        line-height: 1;
        font-weight: 850;
        letter-spacing: .075em;
        text-transform: uppercase;
    }}
    .insight {{
        position: relative;
        margin-top: 17px;
        color: #d9dde3;
        font-size: 14px;
        line-height: 1.45;
        font-weight: 650;
    }}
    .metrics {{
        position: relative;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 9px;
        margin-top: 15px;
    }}
    .metric {{
        border: 1px solid #282e37;
        border-radius: 11px;
        background: rgba(13,17,23,.52);
        padding: 9px 11px;
    }}
    .label {{
        color: #747c87;
        font-size: 9.5px;
        font-weight: 750;
        letter-spacing: .07em;
        text-transform: uppercase;
    }}
    .value {{ margin-top: 3px; color: #f7f8fa; font-size: 15px; font-weight: 800; }}
    .footer {{
        position: relative;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-top: 13px;
        padding-top: 12px;
        border-top: 1px solid #252b33;
    }}
    .domain {{ color: #737b86; font-size: 11.5px; font-weight: 650; }}
    button {{
        appearance: none;
        border: 1px solid #33404c;
        border-radius: 10px;
        background: #18212a;
        color: #ecf2f5;
        padding: 8px 13px;
        font: inherit;
        font-size: 11.5px;
        font-weight: 750;
        cursor: pointer;
        transition: background .15s ease, border-color .15s ease, transform .15s ease;
    }}
    button:hover {{ background: #202b35; border-color: #42515e; transform: translateY(-1px); }}
    button:active {{ transform: translateY(0); }}
    @media (max-width: 760px) {{
        .share-shell {{ width: 100%; }}
    }}
    @media (max-width: 520px) {{
        .share-card {{ padding: 15px 15px 13px; border-radius: 14px; }}
        .coin {{ font-size: 19px; }}
        .score {{ font-size: 24px; }}
        .insight {{ font-size: 13px; margin-top: 14px; }}
        .metrics {{ gap: 7px; margin-top: 12px; }}
        .metric {{ padding: 8px 9px; }}
        .footer {{ margin-top: 11px; padding-top: 10px; }}
    }}
</style>
</head>
<body>
<div class="share-shell">
<div class="share-card">
    <div class="top">
        <div>
            <div class="coin-kicker">Current Vibe</div>
            <div class="coin">{tick}</div>
        </div>
        <div class="score-wrap">
            <div><span class="score">{score}</span> <span class="denom">/ 100</span></div>
            <div class="pill">{band_label}</div>
        </div>
    </div>

    <div class="insight">{meme}</div>

    <div class="metrics">
        <div class="metric">
            <div class="label">24h change</div>
            <div class="value" style="color:{share_change_color};">{ch24:+.2f}%</div>
        </div>
        <div class="metric">
            <div class="label">Range position</div>
            <div class="value">{range_pos:.0f}%</div>
        </div>
    </div>

    <div class="footer">
        <div class="domain">prebartvibes.xyz</div>
        <button id="copyBtn" type="button">Copy</button>
    </div>
</div>
</div>

<script>
    const btn = document.getElementById('copyBtn');
    const textToCopy = {share_text_js};
    const defaultLabel = 'Copy';

    async function copyShareText() {{
        try {{
            await navigator.clipboard.writeText(textToCopy);
        }} catch (err) {{
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }}
        btn.textContent = 'Copied ✓';
        setTimeout(() => btn.textContent = defaultLabel, 1800);
    }}

    btn.addEventListener('click', copyShareText);
</script>
</body>
</html>
""", height=250, scrolling=False)

st.markdown(f"""
<div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:10px 0 6px 0;">
    <span style="color:#737a85;font-size:12.5px;font-weight:600;">On X:</span>
    <a href="https://x.com/search?q=%24{tick}&src=typed_query&f=live" target="_blank"
       style="background:#151a21;border:1px solid #2b313a;color:#d7dbe1;padding:6px 11px;border-radius:16px;text-decoration:none;font-weight:650;font-size:12.5px;">𝕏 ${tick}</a>
</div>
""", unsafe_allow_html=True)

st.divider()
st.markdown(f"""
<div class="pb-section-head"><div><div class="pb-section-title">{name} · Chart</div><div class="pb-section-sub">Price action and volume context</div></div></div>
""", unsafe_allow_html=True)

# Keep the chart control with the chart it actually controls.
col_time, _ = st.columns([1.15, 2.85])
with col_time:
    timeframe = st.selectbox(
        "Timeframe",
        ["Last 1 Day (30 min)", "Last 7 Days", "Last 30 Days"],
        key="detail_chart_timeframe",
    )

days = "1" if "1 Day" in timeframe else "7" if "7 Days" in timeframe else "30"
ohlc_data = top_ohlc_map.get(cid) if days == "1" and cid in top_ohlc_map else get_ohlc(cid, days)
volume_data = get_market_chart(cid, days)
if isinstance(ohlc_data, list) and len(ohlc_data) > 0:
    df = pd.DataFrame(ohlc_data, columns=["timestamp","open","high","low","close"])
    df["time"] = pd.to_datetime(df["timestamp"], unit="ms")
    has_volume = False
    if "total_volumes" in volume_data:
        vol_df = pd.DataFrame(volume_data["total_volumes"], columns=["timestamp","volume"])
        vol_df["time"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
        df = pd.merge_asof(df.sort_values("time"), vol_df.sort_values("time"), on="time", direction="nearest")
        has_volume = True

    # Cleaner terminal-style proportions: price stays primary, volume becomes context.
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.015,
        row_heights=[0.82, 0.18]
    )
    fig.add_trace(go.Candlestick(
        x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#22c55e", decreasing_line_color="#ef5350",
        increasing_fillcolor="#22c55e", decreasing_fillcolor="#ef5350",
        whiskerwidth=0.35, name="Price"
    ), row=1, col=1)

    # High/low guides remain useful, but are intentionally quieter than price.
    fig.add_hline(
        y=high, line_dash="dot", line_width=1, line_color="rgba(34,197,94,0.48)",
        annotation_text="24h High", annotation_position="top right",
        annotation_font=dict(size=11, color="rgba(210,220,214,0.82)"), row=1, col=1
    )
    fig.add_hline(
        y=low, line_dash="dot", line_width=1, line_color="rgba(239,83,80,0.48)",
        annotation_text="24h Low", annotation_position="bottom right",
        annotation_font=dict(size=11, color="rgba(220,210,210,0.82)"), row=1, col=1
    )

    if has_volume:
        colors = [
            "rgba(34,197,94,0.52)" if r["close"] >= r["open"] else "rgba(239,83,80,0.52)"
            for _, r in df.iterrows()
        ]
        fig.add_trace(
            go.Bar(x=df["time"], y=df["volume"], marker_color=colors, name="Volume", hoverinfo="skip"),
            row=2, col=1
        )

    grid = "rgba(148,163,184,0.10)"
    axis_font = dict(size=11, color="rgba(203,213,225,0.72)")
    fig.update_xaxes(
        showgrid=False, zeroline=False, showline=False,
        tickfont=axis_font, ticks="", fixedrange=True
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=grid, gridwidth=1, zeroline=False,
        showline=False, tickfont=axis_font, ticks="", side="right", fixedrange=True, row=1, col=1
    )
    fig.update_yaxes(
        showgrid=False, zeroline=False, showline=False,
        tickfont=dict(size=10, color="rgba(148,163,184,0.55)"), ticks="", side="right", fixedrange=True, row=2, col=1
    )
    fig.update_layout(
        height=500,
        template="plotly_dark",
        margin=dict(l=6, r=8, t=8, b=4),
        xaxis_rangeslider_visible=False,
        showlegend=False,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#171b22", bordercolor="#303641", font_size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.16,
        dragmode=False,
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "scrollZoom": False,
            "doubleClick": False,
            "responsive": True,
        },
    )
else:
    st.info("Chart temporarily unavailable.")

st.divider()
st.markdown("""
<div class="pb-section-head"><div><div class="pb-section-title">Vibe Performance <span class="pb-global-pill">GLOBAL</span></div><div class="pb-section-sub">How similar scores performed historically across tracked coins</div></div></div>
""", unsafe_allow_html=True)
st.caption("Historical forward returns grouped by the Vibe Score shown at the time of each snapshot.")

def _fmt_median_return(val):
    """Keep the distribution table visually clean at two decimals."""
    if val is None or pd.isna(val):
        return "—"
    val = float(val)
    # Anything that rounds to zero at the displayed precision should simply read 0.00%.
    if abs(val) < 0.005:
        return "0.00%"
    return f"{val:+.2f}%"

bucket_stats = get_bucket_stats(min_n=5)
if bucket_stats:
    table_data = []
    for s in bucket_stats:
        if not s["ready"]:
            table_data.append({
                "Bucket": s["bucket"], "n": s["n"], "Sample": sample_strength(0)[0],
                "Avg 30m": "—", "Win 30m": "—", "Avg 1h": "—", "Median 1h": "—",
                "Avg Winner": "—", "Avg Loser": "—", "Win 1h": "—", "Edge (1h)": "—",
                "Avg 4h": "—", "Win 4h": "—", "Avg 24h": "—", "Win 24h": "—"
            })
        else:
            table_data.append({
                "Bucket": s["bucket"],
                "n": s["n"],
                "Sample": sample_strength(s.get("n_1h", 0))[0],
                "Avg 30m": f"{s['avg_30m']:+.2f}%" if s['avg_30m'] is not None else "—",
                "Win 30m": f"{s['win_30m']}%" if s['win_30m'] is not None else "—",
                "Avg 1h": f"{s['avg_1h']:+.2f}%" if s['avg_1h'] is not None else "—",
                "Median 1h": _fmt_median_return(s.get("median_1h")),
                "Avg Winner": f"{s['avg_win_1h']:+.2f}%" if s.get('avg_win_1h') is not None else "—",
                "Avg Loser": f"{s['avg_loss_1h']:+.2f}%" if s.get('avg_loss_1h') is not None else "—",
                "Win 1h": f"{s['win_1h']}%" if s['win_1h'] is not None else "—",
                "Edge (1h)": f"{s['edge']:+.2f}%" if s.get('edge') is not None else "—",
                "Avg 4h": f"{s['avg_4h']:+.2f}%" if s['avg_4h'] is not None else "—",
                "Win 4h": f"{s['win_4h']}%" if s['win_4h'] is not None else "—",
                "Avg 24h": f"{s['avg_24h']:+.2f}%" if s['avg_24h'] is not None else "—",
                "Win 24h": f"{s['win_24h']}%" if s['win_24h'] is not None else "—",
            })

    df_display = pd.DataFrame(table_data)

    def style_win(val):
        if val == "—": return ""
        try:
            num = float(str(val).replace("%", ""))
            if num >= 70: return "background-color: #1b5e20; color: white; font-weight: 600"
            elif num >= 55: return "background-color: #0f766e; color: white"
            elif num >= 45: return "background-color: #f9a825; color: black"
            else: return "background-color: #c62828; color: white"
        except: return ""

    def style_avg(val):
        if val == "—": return ""
        try:
            num = float(str(val).replace("%", "").replace("+", ""))
            if num >= 4: return "background-color: #1b5e20; color: white; font-weight: 600"
            elif num >= 1.5: return "background-color: #2e7d32; color: white"
            elif num >= 0: return "background-color: #f9a825; color: black"
            elif num > -1.5: return "background-color: #ef6c00; color: white"
            else: return "background-color: #c62828; color: white"
        except: return ""

    def style_edge(val):
        if val == "—": return ""
        try:
            num = float(str(val).replace("%", "").replace("+", ""))
            if num >= 1.0: return "background-color: #1b5e20; color: white; font-weight: 700"
            elif num >= 0.25: return "background-color: #0f766e; color: white; font-weight: 600"
            elif num > -0.25: return "background-color: #f9a825; color: black"
            elif num > -1.0: return "background-color: #ef6c00; color: white"
            else: return "background-color: #c62828; color: white"
        except: return ""

    def style_table(df, compact=False):
        styler = df.style.set_properties(**{
            "background-color": "#0e1117", "color": "#fafafa", "border-color": "#2a2d35"
        }).set_table_styles([
            {"selector": "th", "props": [("background-color", "#1a1d24"), ("color", "#b8b8b8"), ("border-color", "#2a2d35")]},
            {"selector": "td", "props": [("border-color", "#2a2d35")]},
        ])
        win_cols = [c for c in df.columns if c.startswith("Win ")]
        avg_cols = [c for c in df.columns if c.startswith("Avg ")]
        median_cols = [c for c in df.columns if c.startswith("Median ")]
        if win_cols:
            styler = styler.map(style_win, subset=win_cols)
        if avg_cols:
            styler = styler.map(style_avg, subset=avg_cols)
        if median_cols:
            styler = styler.map(style_avg, subset=median_cols)
        if "Edge (1h)" in df.columns:
            styler = styler.map(style_edge, subset=["Edge (1h)"])
        return styler

    with st.expander("Show all timeframes", expanded=False):
        st.markdown(
            '<div class="pb-definition"><b>What this tells you:</b> this is the main Vibe Performance study. '
            'Pick a score band and see what price historically did 30 minutes, 1 hour, 4 hours, and 24 hours later. '
            'Higher Vibe does <i>not</i> automatically mean better future returns — that is exactly what this table is testing.</div>',
            unsafe_allow_html=True
        )
        st.caption("Quick read: Avg = average forward return · Win = % of outcomes above 0% · Edge = how that bucket did versus the tracked market.")
        full_cols = ["Bucket","n","Sample","Avg 30m","Win 30m","Avg 1h","Win 1h","Edge (1h)","Avg 4h","Win 4h","Avg 24h","Win 24h"]
        st.dataframe(style_table(df_display[full_cols]), use_container_width=True, hide_index=True)
        st.caption("n counts cumulative Vibe snapshots for the current model version. Sample describes how mature the completed 1h outcome set is.")


    st.caption("Performance colors: green/teal = stronger historical outcome · yellow = mixed/near neutral · orange/red = weaker historical outcome. Historical results are descriptive, not guarantees.")
else:
    st.info("Collecting performance data…")

# Methodology and disclaimer are available when wanted, but stay out of the primary flow.
with st.expander("About the Vibe Score & data disclaimer", expanded=False):
    st.markdown(
        """
        **Vibe Score** is Pre Bart Vibes' 0–100 market-strength rating. In v10, Vibe remains a description of current market conditions rather than being presented as a direct entry probability.

        **Setup Intelligence** studies Vibe velocity, price response, bucket transitions, and historically similar observations to separate current strength from early-move context. Comparable-set statistics are descriptive and can change as the dataset grows.

        **Historical performance** is based on tracked observations collected by Pre Bart Vibes. It is descriptive, not a prediction, and sample sizes can vary substantially by score bucket and timeframe.

        Crypto markets are volatile. Vibe Scores and historical statistics are informational tools, not financial advice or guarantees of future returns.
        """
    )

st.divider()

# Minimal footer: legitimacy and navigation without another large card.
st.markdown(
    """
    <div style="
        display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;
        padding:2px 2px 18px 2px;color:#818792;font-size:.86rem;
    ">
      <div>Pre Bart Vibes · Market context, simplified.</div>
      <div>
        <a href="mailto:contact@prebartvibes.xyz" style="color:#aeb4bd;text-decoration:none;font-weight:650;">Contact</a>
        <span style="padding:0 8px;color:#4b5059;">·</span>
        <a href="mailto:contact@prebartvibes.xyz" style="color:#8f949e;text-decoration:none;">contact@prebartvibes.xyz</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

