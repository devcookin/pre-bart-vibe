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

MODEL_VERSION = "v2.5-breakout"
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

def fill_pending_returns():
    """Improved version: only fills the next pending horizon (shortest first)
    so that 30m / 1h / 4h / 24h get different values."""
    if not supabase: return
    now = datetime.now(timezone.utc)
    last_fill = st.session_state.last_fill_time
    if last_fill and (now - last_fill).total_seconds() < FILL_INTERVAL_SECONDS:
        return

    try:
        result = supabase.table("vibe_snapshots")\
            .select("id, timestamp, coin_id, price, return_30m, return_1h, return_4h, return_24h")\
            .is_("return_24h", "null")\
            .order("timestamp", desc=False)\
            .limit(80)\
            .execute()
        
        rows = result.data or []
        if not rows:
            st.session_state.last_fill_time = now
            return

        coin_ids = list(set(r["coin_id"] for r in rows))
        try:
            r = requests.get(
                "https://pro-api.coingecko.com/api/v3/simple/price",
                headers=HEADERS,
                params={"ids": ",".join(coin_ids), "vs_currencies": "usd"},
                timeout=8
            )
            prices = r.json() if r.status_code == 200 else {}
        except:
            prices = {}

        for row in rows:
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            age = (now - ts).total_seconds()
            original = row["price"]
            current = prices.get(row["coin_id"], {}).get("usd")
            if not current or original <= 0:
                continue

            ret = ((current - original) / original) * 100
            updates = {}

            # Only fill the *next* missing horizon (shortest first)
            if age >= 1800 and row.get("return_30m") is None:
                updates["return_30m"] = round(ret, 4)
            elif age >= 3600 and row.get("return_1h") is None:
                updates["return_1h"] = round(ret, 4)
            elif age >= 14400 and row.get("return_4h") is None:
                updates["return_4h"] = round(ret, 4)
            elif age >= 86400 and row.get("return_24h") is None:
                updates["return_24h"] = round(ret, 4)

            if updates:
                updates["filled_at"] = now.isoformat()
                try:
                    supabase.table("vibe_snapshots").update(updates).eq("id", row["id"]).execute()
                except:
                    pass

        st.session_state.last_fill_time = now
    except:
        pass

@st.cache_data(ttl=300)
def get_bucket_stats(min_n=5):
    if not supabase: return None
    try:
        result = supabase.table("vibe_snapshots")\
            .select("score, return_30m, return_1h, return_4h, return_24h")\
            .not_.is_("return_1h", "null").limit(2000).execute()
        rows = result.data or []
        if not rows: return None
        df = pd.DataFrame(rows)
        
        overall_avg_1h = df["return_1h"].mean() if len(df) > 0 else 0
        
        def bucket(s):
            if s < 20: return "0-19"
            if s < 40: return "20-39"
            if s < 60: return "40-59"
            if s < 70: return "60-69"
            if s < 80: return "70-79"
            if s < 90: return "80-89"
            return "90-100"
        df["bucket"] = df["score"].apply(bucket)
        
        stats = []
        for b in ["0-19","20-39","40-59","60-69","70-79","80-89","90-100"]:
            sub = df[df["bucket"] == b]
            n = len(sub)
            if n < min_n:
                stats.append({"bucket": b, "n": n, "ready": False})
                continue
            
            def avg(col):
                vals = sub[col].dropna()
                return round(vals.mean(), 3) if len(vals) else None
            def win(col):
                vals = sub[col].dropna()
                return round((vals > 0).mean() * 100, 1) if len(vals) else None
            
            avg_1h = avg("return_1h")
            edge = round(avg_1h - overall_avg_1h, 2) if avg_1h is not None else None
            
            stats.append({
                "bucket": b, "n": n, "ready": True,
                "avg_30m": avg("return_30m"), "win_30m": win("return_30m"),
                "avg_1h": avg_1h, "win_1h": win("return_1h"),
                "avg_4h": avg("return_4h"), "win_4h": win("return_4h"),
                "avg_24h": avg("return_24h"), "win_24h": win("return_24h"),
                "edge": edge
            })
        return stats
    except:
        return None

@st.cache_data(ttl=180)
def get_coin_performance(coin_id, min_n=15):
    if not supabase: return None
    try:
        result = supabase.table("vibe_snapshots")\
            .select("score, return_1h, return_4h")\
            .eq("coin_id", coin_id).not_.is_("return_1h", "null").limit(500).execute()
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

@st.cache_data(ttl=60)
def get_funding_rates():
    rates = {}
    try:
        r = requests.get("https://xoomar.com/api/markets/funding-rates", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            data = r.json().get("data", [])
            for item in data:
                base = item.get("baseAsset", "").upper()
                exchange = item.get("exchange", "").lower()
                if base in ["BTC", "ETH", "SOL", "BNB", "XRP"] and base not in rates:
                    if exchange in ["bybit", "binance"]:
                        rate = float(item.get("fundingRate", 0)) * 100
                        rates[base] = rate
    except:
        pass
    return rates

@st.cache_data(ttl=60)
def get_open_interest_delta():
    results = {}
    try:
        r = requests.get("https://xoomar.com/api/markets/funding-rates", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            data = r.json().get("data", [])
            for item in data:
                base = item.get("baseAsset", "").upper()
                exchange = item.get("exchange", "").lower()
                if base in ["BTC", "ETH", "SOL", "BNB"] and exchange == "bybit":
                    oi_val = item.get("openInterestValue") or item.get("openInterest")
                    if oi_val is not None:
                        results[base] = {"oi_usd": float(oi_val), "change_usd": 0.0, "change_pct": 0.0}
    except:
        pass
    for sym in ["BTC", "ETH", "SOL", "BNB"]:
        if sym not in results:
            results[sym] = {"oi_usd": 0.0, "change_usd": 0.0, "change_pct": 0.0}
    return results

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
    return max(min(quality, 1.8), -1.5)

def calc_vibe(price, high, low, change_1h, change_24h, fg_value=None, btc_change=None, candle_quality=0):
    if high != low:
        range_pos = ((price - low) / (high - low)) * 100
    else:
        range_pos = 50.0
    reasons = []
    base = 54.0
    structure_boost = candle_quality * 9.0
    base += structure_boost
    if candle_quality > 1.0: reasons.append("Excellent bullish structure")
    elif candle_quality > 0.5: reasons.append("Solid constructive structure")
    elif candle_quality > 0.15: reasons.append("Mildly positive structure")
    elif candle_quality < -0.7: reasons.append("Weak structure / rejection")
    elif candle_quality < -0.25: reasons.append("Mixed structure")
    base += (range_pos - 50) * 0.14
    if range_pos > 88: reasons.append("Near top of daily range")
    elif range_pos > 72: reasons.append("Upper half of range")
    elif range_pos < 18: reasons.append("Building from lows" if candle_quality > 0.15 else "Near bottom of range")
    elif range_pos < 32: reasons.append("Lower half of range")
    base += change_1h * 3.3
    if change_1h > 2.0: reasons.append("Very strong 1h momentum")
    elif change_1h > 0.7: reasons.append("Strong 1h momentum")
    elif change_1h > 0.2: reasons.append("Positive 1h")
    elif change_1h < -1.5: reasons.append("Strong negative 1h")
    elif change_1h < -0.4: reasons.append("Mild negative 1h")
    base += change_24h * 0.45
    if btc_change is not None:
        vs_btc = change_24h - btc_change
        base += vs_btc * 0.75
        if vs_btc > 3.5: reasons.append("Clearly outperforming BTC")
        elif vs_btc > 1.2: reasons.append("Outperforming BTC")
        elif vs_btc < -3.5: reasons.append("Lagging BTC")
    if fg_value is not None:
        if fg_value < 25: base -= 1.5
        elif fg_value > 75: base += 1.0
    if range_pos >= 95 and change_1h >= 0.5 and candle_quality > 0.15:
        base += 5
        reasons.append("Clear breakout in progress")
    elif range_pos >= 88 and change_1h >= 0.9:
        base += 3.5
        reasons.append("Breaking higher with momentum")
    elif range_pos >= 80 and change_1h >= 0.4 and candle_quality > 0.25:
        base += 2
        reasons.append("Pushing into breakout territory")
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
    if score >= 75: color = "linear-gradient(90deg, #00e676, #00c853)"
    elif score >= 60: color = "linear-gradient(90deg, #69f0ae, #00e676)"
    elif score >= 45: color = "linear-gradient(90deg, #ffd600, #ffab00)"
    else: color = "linear-gradient(90deg, #ff5252, #d50000)"
    return f"""
    <div style="background:#2a2d35;border-radius:10px;height:{height}px;overflow:hidden;margin:6px 0 8px 0;">
        <div style="width:{score}%;height:100%;background:{color};border-radius:10px;"></div>
    </div>
    """

def make_sparkline(history, height=80):
    if not history or len(history) < 2: return None
    times = [h[0] for h in history]
    scores = [h[1] for h in history]
    min_score, max_score = min(scores), max(scores)
    padding = max(3, (max_score - min_score) * 0.2)
    y_min = max(0, min_score - padding)
    y_max = min(100, max_score + padding)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=scores, mode="lines",
        line=dict(color="#00c853" if scores[-1] >= 60 else "#ff5252", width=2.2),
        fill="tozeroy",
        fillcolor="rgba(0,200,83,0.15)" if scores[-1] >= 60 else "rgba(255,82,82,0.15)"
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=2, b=2),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[y_min, y_max]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False
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
        ohlc = get_ohlc(cid, "1")
        cq = analyze_candles(ohlc)
        score, meme, range_pos, reasons = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, cq)
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
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
        <h1 style="margin: 0; padding: 0;">🚀 Pre-Bart Vibe Dashboard</h1>
        <span class="live-badge"><span class="live-dot"></span> LIVE</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="font-size: 1.08rem; color: #a0a0a0; margin-bottom: 4px; line-height: 1.5;">
        Live strength & structure scores for the market’s top coins.<br>
        Spot momentum early, catch weakness, and stay ahead of the noise.
    </div>
    """, unsafe_allow_html=True)

with col_refresh:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        # Rerun the UI without destroying expensive CoinGecko caches.
        # Cached market data refreshes automatically according to each function's TTL.
        st.session_state.last_refresh = datetime.now()
        st.rerun()

st.caption(f"Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')}  •  Model: {MODEL_VERSION}")

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
top_coins = get_top_coins(30)
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

vibe_data = []
for name, cid, tick in COIN_ORDER:
    c = coin_map.get(cid)
    if not c: continue
    price = c["current_price"]
    high, low = c["high_24h"], c["low_24h"]
    ch1 = c.get("price_change_percentage_1h_in_currency") or 0
    ch24 = c.get("price_change_percentage_24h") or 0
    image_url = c.get("image", "")
    ohlc = get_ohlc(cid, "1")
    cq = analyze_candles(ohlc)
    score, meme, range_pos, reasons = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, cq)
    st.session_state.score_history = update_history(cid, score, st.session_state.score_history)
    hist = st.session_state.score_history.get(cid, [])
    prev_score = hist[-2][1] if len(hist) >= 2 else None
    if prev_score is not None:
        if score >= 80 and prev_score < 80: st.toast(f"{tick} Vibe crossed 80!", icon="🔥")
        elif score >= 70 and prev_score < 70: st.toast(f"{tick} Vibe crossed 70!", icon="🚀")
        elif score <= 30 and prev_score > 30: st.toast(f"{tick} Vibe dropped below 30", icon="🐻")
        elif score <= 40 and prev_score > 40: st.toast(f"{tick} Vibe dropped below 40", icon="⚠️")
    vs_btc_val = ch24 - btc_change
    save_vibe_snapshot(cid, tick, price, score, meme, ch24, range_pos, vs_btc_val, prev_score, {"reasons": reasons, "candle_quality": cq})
    vibe_data.append({
        "name": name, "cid": cid, "tick": tick, "price": price, "ch24": ch24, "ch1": ch1,
        "score": score, "meme": meme, "image_url": image_url, "candle_quality": cq,
        "range_pos": range_pos, "reasons": reasons, "history": st.session_state.score_history.get(cid, []),
        "prev_score": prev_score
    })

vibe_data_sorted = sorted(vibe_data, key=lambda x: x["score"], reverse=True)

avg_vibe = sum(v["score"] for v in vibe_data) / len(vibe_data) if vibe_data else 50
funding = get_funding_rates()
avg_funding = sum(funding.values()) / len(funding) if funding else 0

if avg_vibe >= 65 and avg_funding >= 0.01:
    bias = "🟢 Strongly Bullish"
elif avg_vibe >= 58 or avg_funding > 0.005:
    bias = "🟢 Mildly Bullish"
elif avg_vibe <= 42 and avg_funding < -0.005:
    bias = "🔴 Mildly Bearish"
elif avg_vibe <= 38:
    bias = "🔴 Strongly Bearish"
else:
    bias = "🟡 Neutral"

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
    
    with st.container(border=True):
        st.markdown("**📊 Market Bias**")
        st.markdown(f"<div style='font-size:1.15rem;font-weight:600;margin:6px 0;'>{bias}</div>", unsafe_allow_html=True)
        st.caption(f"Avg Vibe: {avg_vibe:.1f} • Avg Funding: {avg_funding:+.4f}%")
    
    with st.container(border=True):
        st.markdown("**🏆 Strongest / Weakest**")
        if strongest: st.markdown(f"🔥 **{strongest['tick']}** {strongest['score']}")
        if weakest: st.markdown(f"💀 **{weakest['tick']}** {weakest['score']}")
    
    with st.container(border=True):
        st.markdown("**🔥 Top Movers**")
        tf = st.radio("Timeframe", ["1h", "24h"], horizontal=True, key="movers_tf_radio", label_visibility="collapsed")
        st.session_state.movers_tf = tf
        key = "ch1" if tf == "1h" else "ch24"

        gainers = sorted(vibe_data, key=lambda x: x[key], reverse=True)[:3]
        losers = sorted(vibe_data, key=lambda x: x[key])[:3]

        st.caption("Gainers")
        for m in gainers:
            ch = m[key]
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-size:13px;padding:2px 0;'>"
                f"<span><b>{m['tick']}</b></span>"
                f"<span style='color:#00c853;font-weight:600'>{ch:+.2f}%</span></div>",
                unsafe_allow_html=True
            )

        st.caption("Losers")
        for m in losers:
            ch = m[key]
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-size:13px;padding:2px 0;'>"
                f"<span><b>{m['tick']}</b></span>"
                f"<span style='color:#ff5252;font-weight:600'>{ch:+.2f}%</span></div>",
                unsafe_allow_html=True
            )
    
    with st.container(border=True):
        st.markdown("**💰 Funding Rates**")
        st.caption("Xoomar • Bybit/Binance")
        if funding:
            for sym in ["BTC", "ETH", "SOL", "BNB", "XRP"]:
                if sym in funding:
                    rate = funding[sym]
                    color = "#00c853" if rate >= 0 else "#ff5252"
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;font-size:13px;padding:2px 0;'>"
                        f"<span>{sym}</span>"
                        f"<span style='color:{color};font-weight:600'>{rate:+.4f}%</span></div>",
                        unsafe_allow_html=True
                    )
        else:
            st.caption("Loading…")
    
    with st.container(border=True):
        st.markdown("**📊 Open Interest**")
        st.caption("Xoomar • current value")
        oi_data = get_open_interest_delta()
        if oi_data:
            for sym in ["BTC", "ETH", "SOL", "BNB"]:
                if sym in oi_data:
                    d = oi_data[sym]
                    oi_usd = d["oi_usd"]
                    oi_str = f"${oi_usd/1e9:.2f}B" if oi_usd >= 1e9 else f"${oi_usd/1e6:.0f}M" if oi_usd >= 1e6 else f"${oi_usd/1e3:.0f}K"
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;font-size:13px;padding:2px 0;'>"
                        f"<span>{sym}</span>"
                        f"<span style='font-weight:600'>{oi_str}</span></div>",
                        unsafe_allow_html=True
                    )
        else:
            st.caption("Loading…")

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

col_time, _ = st.columns([1, 3])
with col_time:
    timeframe = st.selectbox("Timeframe", ["Last 1 Day (30 min)", "Last 7 Days", "Last 30 Days"])

if st.session_state.search_coin:
    single = get_single_coin_market(st.session_state.search_coin)
    if single:
        c = single[0]
        name, cid, tick = c["name"], c["id"], c["symbol"].upper()
        price, high, low = c["current_price"], c["high_24h"], c["low_24h"]
        ch1 = c.get("price_change_percentage_1h_in_currency") or 0
        ch24 = c.get("price_change_percentage_24h") or 0
        ohlc = get_ohlc(cid, "1")
        cq = analyze_candles(ohlc)
        score, meme, range_pos, reasons = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, cq)
        volume, market_cap = c["total_volume"], c["market_cap"]
        image_url = c.get("image", "")
        st.session_state.score_history = update_history(cid, score, st.session_state.score_history)
        history = st.session_state.score_history.get(cid, [])
        prev_score = history[-2][1] if len(history) >= 2 else None
        save_vibe_snapshot(cid, tick, price, score, meme, ch24, range_pos, ch24-btc_change, prev_score, {"reasons":reasons,"candle_quality":cq})
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
    history = item["history"]
    c = coin_map.get(cid, {})
    volume = c.get("total_volume", 0)
    market_cap = c.get("market_cap", 0)
    high = c.get("high_24h", price)
    low = c.get("low_24h", price)
    image_url = item["image_url"]

vs_btc = ch24 - (btc_change or 0)
price_text = f"${price:,.4f}" if price < 10 else f"${price:,.2f}"
st.metric(f"{name}", price_text, f"{ch24:+.2f}% (24h)  |  {ch1:+.2f}% (1h)")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("24h Volume", f"${volume/1_000_000:,.1f}M")
c2.metric("Market Cap", f"${market_cap/1_000_000_000:,.2f}B")
c3.metric("Range Position", f"{range_pos:.0f}%")
c4.metric("Candle Quality", f"{cq:+.1f}")
c5.metric("vs BTC (24h)", f"{vs_btc:+.2f}%")

arrow = get_score_arrow(cid, score)
st.markdown(f"**Vibe Score: {score}/100{arrow}**", unsafe_allow_html=True)
st.markdown(colored_progress(score, height=12), unsafe_allow_html=True)

is_watched = cid in st.session_state.watchlist
if st.button("★ Remove from Watchlist" if is_watched else "☆ Add to Watchlist", key="detail_watch"):
    if is_watched:
        st.session_state.watchlist.remove(cid)
    else:
        st.session_state.watchlist.append(cid)
    st.rerun()

perf = get_coin_performance(cid)
if perf and perf.get("ready"):
    st.caption(f"Historical 1h win rate: **{perf['win_1h']}%** • Avg 1h return: **{perf['avg_1h']:+.2f}%** • n = {perf['n']}")

if score >= 80: st.success(meme)
elif score <= 30: st.error(meme)
else: st.info(meme)

st.markdown("##### Vibe Score History")
if history and len(history) >= 2:
    fig = make_sparkline(history, height=140)
    if fig: st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(f"Showing last {len(history)} readings")
else:
    st.info("History will start building after a few more refreshes...")

with st.expander("🤔 Why this score?"):
    for r in reasons: st.write(f"• {r}")

# ========== SHARE SECTION ==========
st.markdown("### 📤 Share this vibe")

share_text = (
    f"{tick} Vibe Score: {score}/100 – {meme}\n"
    f"{ch24:+.2f}% 24h | Range {range_pos:.0f}%\n"
    f"https://prebartvibes.xyz"
)

st.code(share_text, language=None)

components.html(f"""
<div style="margin-top:6px;">
    <button id="copyBtn" style="
        background: linear-gradient(90deg, #1da1f2, #0d8ecf);
        color: white;
        border: none;
        padding: 9px 18px;
        border-radius: 20px;
        font-weight: 600;
        cursor: pointer;
        font-size: 13.5px;
        font-family: Inter, sans-serif;
    ">
        📋 Copy to Clipboard
    </button>
</div>

<script>
    const btn = document.getElementById('copyBtn');
    const textToCopy = `{share_text}`;

    btn.addEventListener('click', async () => {{
        try {{
            await navigator.clipboard.writeText(textToCopy);
            btn.innerText = '✅ Copied!';
            setTimeout(() => btn.innerText = '📋 Copy to Clipboard', 2000);
        }} catch (err) {{
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            btn.innerText = '✅ Copied!';
            setTimeout(() => btn.innerText = '📋 Copy to Clipboard', 2000);
        }}
    }});
</script>
""", height=55)

st.markdown(f"""
<div style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 6px 0;">
    <a href="https://x.com/search?q=%24{tick}&src=typed_query&f=live" target="_blank"
       style="background:linear-gradient(90deg,#1da1f2,#0d8ecf);color:white;padding:7px 14px;border-radius:18px;text-decoration:none;font-weight:600;font-size:13px;">${tick} Live</a>
    <a href="https://x.com/search?q={quote(name + ' crypto')}&src=typed_query&f=live" target="_blank"
       style="background:linear-gradient(90deg,#1da1f2,#0d8ecf);color:white;padding:7px 14px;border-radius:18px;text-decoration:none;font-weight:600;font-size:13px;">{name} Crypto</a>
</div>
""", unsafe_allow_html=True)

st.divider()
st.subheader(f"{name} • Chart")
days = "1" if "1 Day" in timeframe else "7" if "7 Days" in timeframe else "30"
ohlc_data = get_ohlc(cid, days)
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
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72,0.28])
    fig.add_trace(go.Candlestick(
        x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00c853", decreasing_line_color="#ff5252",
        increasing_fillcolor="#00c853", decreasing_fillcolor="#ff5252", name="Price"
    ), row=1, col=1)
    fig.add_hline(y=high, line_dash="dot", line_color="rgba(0,200,83,0.6)", annotation_text="24h High", row=1, col=1)
    fig.add_hline(y=low, line_dash="dot", line_color="rgba(255,82,82,0.6)", annotation_text="24h Low", row=1, col=1)
    if has_volume:
        colors = ["#00c853" if r["close"] >= r["open"] else "#ff5252" for _, r in df.iterrows()]
        fig.add_trace(go.Bar(x=df["time"], y=df["volume"], marker_color=colors, opacity=0.65, name="Volume"), row=2, col=1)
    fig.update_layout(
        height=480, 
        template="plotly_dark",
        margin=dict(l=0,r=0,t=15,b=0),
        xaxis_rangeslider_visible=False, 
        showlegend=False, 
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Chart temporarily unavailable.")

st.divider()
st.subheader("📊 Vibe Performance (Global)")
st.caption("Historical forward returns across **all tracked coins**.")

bucket_stats = get_bucket_stats(min_n=5)
if bucket_stats:
    table_data = []
    for s in bucket_stats:
        if not s["ready"]:
            table_data.append({
                "Bucket": s["bucket"],
                "n": s["n"],
                "Avg 30m": "—",
                "Win 30m": "—",
                "Avg 1h": "—",
                "Win 1h": "—",
                "Edge (1h)": "—",
                "Avg 4h": "—",
                "Win 4h": "—",
                "Avg 24h": "—",
                "Win 24h": "—"
            })
        else:
            table_data.append({
                "Bucket": s["bucket"],
                "n": s["n"],
                "Avg 30m": f"{s['avg_30m']:+.2f}%" if s['avg_30m'] is not None else "—",
                "Win 30m": f"{s['win_30m']}%" if s['win_30m'] is not None else "—",
                "Avg 1h": f"{s['avg_1h']:+.2f}%" if s['avg_1h'] is not None else "—",
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
            if num >= 85: return "background-color: #1b5e20; color: white; font-weight: 600"
            elif num >= 70: return "background-color: #2e7d32; color: white"
            elif num >= 55: return "background-color: #f9a825; color: black"
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
            if num >= 5: return "background-color: #1b5e20; color: white; font-weight: 700"
            elif num >= 2: return "background-color: #2e7d32; color: white; font-weight: 600"
            elif num >= 0: return "background-color: #f9a825; color: black"
            elif num > -2: return "background-color: #ef6c00; color: white"
            else: return "background-color: #c62828; color: white"
        except: return ""
    
    styler = df_display.style\
        .map(style_win, subset=["Win 30m", "Win 1h", "Win 4h", "Win 24h"])\
        .map(style_avg, subset=["Avg 30m", "Avg 1h", "Avg 4h", "Avg 24h"])\
        .map(style_edge, subset=["Edge (1h)"])
    
    st.dataframe(styler, use_container_width=True, hide_index=True)
    
    st.caption("""
    **Edge (1h)** = How much better (or worse) this Vibe bucket performed compared to the average coin in the next 1 hour.  
    Positive Edge = this score range historically beat the market.
    """)
else:
    st.info("Collecting performance data…")
