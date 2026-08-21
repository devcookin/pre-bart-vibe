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

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=45 * 1000, key="datarefresh")
except:
    pass

# ========== SUPABASE ==========
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.warning(f"Supabase connection issue: {e}")

MODEL_VERSION = "v2.1-breakout"
MIN_SNAPSHOT_INTERVAL = 120  # seconds between snapshots for the same coin

API_KEY = "CG-h61Dg6UoB2gVfCSUJQDj4dLa"
HEADERS = {"x-cg-demo-api-key": API_KEY}

HISTORY_FILE = "vibe_history.json"

st.set_page_config(
    page_title="Pre-Bart Vibe Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
    h1 { font-weight: 700 !important; }
    .stMetric { border-radius: 14px; padding: 12px 16px; }
    div[data-testid="stMetricValue"] { font-size: 1.45rem !important; font-weight: 600; }
    div.stButton > button { width: 100%; border-radius: 10px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ========== SESSION STATE ==========
if "selected_coin" not in st.session_state:
    st.session_state.selected_coin = "Bitcoin"
if "last_score" not in st.session_state:
    st.session_state.last_score = None
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if "search_coin" not in st.session_state:
    st.session_state.search_coin = None
if "show_count" not in st.session_state:
    st.session_state.show_count = "Top 10"
if "last_snapshot_time" not in st.session_state:
    st.session_state.last_snapshot_time = {}

# ========== PERSISTENT HISTORY (sparkline) ==========
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                for cid in data:
                    data[cid] = [(datetime.fromisoformat(t), s) for t, s in data[cid]]
                return data
        except:
            return {}
    return {}

def save_history(history):
    try:
        serializable = {}
        for cid, entries in history.items():
            serializable[cid] = [(t.isoformat(), s) for t, s in entries]
        with open(HISTORY_FILE, "w") as f:
            json.dump(serializable, f)
    except:
        pass

def update_history(cid, score, history_dict):
    now = datetime.now()
    if cid not in history_dict:
        history_dict[cid] = []
    
    entries = history_dict[cid]
    
    should_add = False
    if not entries:
        should_add = True
    else:
        last_time, last_score = entries[-1]
        if score != last_score or (now - last_time) > timedelta(minutes=2):
            should_add = True
    
    if should_add:
        entries.append((now, score))
        history_dict[cid] = entries[-150:]
        save_history(history_dict)
    
    return history_dict

if "score_history" not in st.session_state:
    st.session_state.score_history = load_history()

# ========== SUPABASE SNAPSHOT FUNCTIONS ==========
def save_vibe_snapshot(coin_id, symbol, price, score, label, change_24h, range_pos, vs_btc, prev_score, sub_signals):
    if not supabase:
        return
    
    now = datetime.now(timezone.utc)
    last_time = st.session_state.last_snapshot_time.get(coin_id)
    
    # Throttle
    if last_time and (now - last_time).total_seconds() < MIN_SNAPSHOT_INTERVAL:
        if prev_score is not None and score == prev_score:
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
        "timestamp": now.isoformat(),
        "coin_id": coin_id,
        "symbol": symbol,
        "price": float(price),
        "score": int(score),
        "label": label,
        "change_24h": float(change_24h) if change_24h is not None else None,
        "range_pos": float(range_pos) if range_pos is not None else None,
        "vs_btc": float(vs_btc) if vs_btc is not None else None,
        "prev_score": int(prev_score) if prev_score is not None else None,
        "direction": direction,
        "sub_signals": sub_signals,
        "model_version": MODEL_VERSION,
        "return_30m": None,
        "return_1h": None,
        "return_4h": None,
        "return_24h": None,
        "filled_at": None
    }
    
    try:
        supabase.table("vibe_snapshots").insert(data).execute()
        st.session_state.last_snapshot_time[coin_id] = now
    except Exception as e:
        # Silent fail so the app doesn't break
        pass

def fill_pending_returns():
    """Fill returns for snapshots that are old enough"""
    if not supabase:
        return
    
    try:
        # Get snapshots that still need returns
        result = supabase.table("vibe_snapshots")\
            .select("id, timestamp, coin_id, price, return_30m, return_1h, return_4h, return_24h")\
            .is_("return_24h", "null")\
            .order("timestamp", desc=False)\
            .limit(100)\
            .execute()
        
        rows = result.data or []
        now = datetime.now(timezone.utc)
        
        for row in rows:
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            age_seconds = (now - ts).total_seconds()
            original_price = row["price"]
            
            # We need current price for this coin
            # For simplicity we use a quick markets call only when needed
            # (In production you could cache prices)
            try:
                r = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    headers=HEADERS,
                    params={"ids": row["coin_id"], "vs_currencies": "usd"},
                    timeout=8
                )
                if r.status_code != 200:
                    continue
                current_price = r.json().get(row["coin_id"], {}).get("usd")
                if not current_price or original_price <= 0:
                    continue
                
                ret = ((current_price - original_price) / original_price) * 100
                updates = {}
                
                if age_seconds >= 30 * 60 and row["return_30m"] is None:
                    updates["return_30m"] = round(ret, 4)
                if age_seconds >= 60 * 60 and row["return_1h"] is None:
                    updates["return_1h"] = round(ret, 4)
                if age_seconds >= 4 * 60 * 60 and row["return_4h"] is None:
                    updates["return_4h"] = round(ret, 4)
                if age_seconds >= 24 * 60 * 60 and row["return_24h"] is None:
                    updates["return_24h"] = round(ret, 4)
                
                if updates:
                    updates["filled_at"] = now.isoformat()
                    supabase.table("vibe_snapshots").update(updates).eq("id", row["id"]).execute()
            except:
                continue
    except Exception:
        pass

def get_bucket_stats(min_n=25):
    """Global performance by score bucket"""
    if not supabase:
        return None
    
    try:
        result = supabase.table("vibe_snapshots")\
            .select("score, return_30m, return_1h, return_4h, return_24h")\
            .not_.is_("return_1h", "null")\
            .execute()
        
        rows = result.data or []
        if not rows:
            return None
        
        df = pd.DataFrame(rows)
        
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
        for b in ["0-19", "20-39", "40-59", "60-69", "70-79", "80-89", "90-100"]:
            sub = df[df["bucket"] == b]
            n = len(sub)
            if n < min_n:
                stats.append({"bucket": b, "n": n, "ready": False})
                continue
            
            def safe_avg(col):
                vals = sub[col].dropna()
                return round(vals.mean(), 3) if len(vals) > 0 else None
            
            def safe_win(col):
                vals = sub[col].dropna()
                if len(vals) == 0:
                    return None
                return round((vals > 0).mean() * 100, 1)
            
            stats.append({
                "bucket": b,
                "n": n,
                "ready": True,
                "avg_30m": safe_avg("return_30m"),
                "win_30m": safe_win("return_30m"),
                "avg_1h": safe_avg("return_1h"),
                "win_1h": safe_win("return_1h"),
                "avg_4h": safe_avg("return_4h"),
                "win_4h": safe_win("return_4h"),
                "avg_24h": safe_avg("return_24h"),
                "win_24h": safe_win("return_24h"),
            })
        return stats
    except Exception:
        return None

def get_coin_performance(coin_id, min_n=20):
    if not supabase:
        return None
    try:
        result = supabase.table("vibe_snapshots")\
            .select("score, return_1h, return_4h")\
            .eq("coin_id", coin_id)\
            .not_.is_("return_1h", "null")\
            .execute()
        
        rows = result.data or []
        if len(rows) < min_n:
            return {"n": len(rows), "ready": False}
        
        df = pd.DataFrame(rows)
        high = df[df["score"] >= 70]
        
        def stats(sub):
            if len(sub) == 0:
                return None, None
            avg = round(sub["return_1h"].mean(), 3)
            win = round((sub["return_1h"] > 0).mean() * 100, 1)
            return avg, win
        
        avg1, win1 = stats(df)
        avg4 = round(df["return_4h"].dropna().mean(), 3) if df["return_4h"].notna().any() else None
        win4 = round((df["return_4h"].dropna() > 0).mean() * 100, 1) if df["return_4h"].notna().any() else None
        
        return {
            "n": len(df),
            "ready": True,
            "avg_1h": avg1,
            "win_1h": win1,
            "avg_4h": avg4,
            "win_4h": win4,
            "high_n": len(high),
            "high_avg_1h": round(high["return_1h"].mean(), 3) if len(high) > 5 else None,
            "high_win_1h": round((high["return_1h"] > 0).mean() * 100, 1) if len(high) > 5 else None,
        }
    except Exception:
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

@st.cache_data(ttl=45)
def get_global():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", headers=HEADERS, timeout=10)
        return r.json()["data"]
    except:
        return None

@st.cache_data(ttl=60)
def get_top_coins(limit=20):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "1h,24h"
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

@st.cache_data(ttl=60)
def get_ohlc(coin_id, days="1"):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": days}
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    return r.json() if r.status_code == 200 else []

@st.cache_data(ttl=60)
def get_market_chart(coin_id, days="1"):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    return r.json() if r.status_code == 200 else {}

@st.cache_data(ttl=120)
def search_coins(query):
    if not query or len(query) < 2:
        return []
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search", headers=HEADERS, params={"query": query}, timeout=8)
        return r.json().get("coins", [])[:10]
    except:
        return []

def analyze_candles(ohlc_data):
    if not isinstance(ohlc_data, list) or len(ohlc_data) < 4:
        return 0.0
    df = pd.DataFrame(ohlc_data[-8:], columns=["timestamp", "open", "high", "low", "close"])
    quality = 0.0
    for _, row in df.iterrows():
        body = abs(row["close"] - row["open"])
        upper_wick = row["high"] - max(row["open"], row["close"])
        lower_wick = min(row["open"], row["close"]) - row["low"]
        full_range = row["high"] - row["low"]
        if full_range == 0: continue
        close_pos = (row["close"] - row["low"]) / full_range
        if close_pos > 0.70 and row["close"] > row["open"]:
            quality += 0.35
        elif close_pos < 0.30:
            quality -= 0.25
        if upper_wick > body * 1.5 and upper_wick / full_range > 0.40:
            quality -= 0.40
        if lower_wick > body * 1.2 and lower_wick / full_range > 0.30:
            quality += 0.25
    lows = df["low"].values
    highs = df["high"].values
    closes = df["close"].values
    if len(lows) >= 4:
        if lows[-1] > lows[-2] > lows[-3]: quality += 0.70
        elif lows[-1] > lows[-2]: quality += 0.35
        elif lows[-1] < lows[-2] < lows[-3]: quality -= 0.45
    if len(highs) >= 3 and highs[-1] > highs[-2] > highs[-3]:
        quality += 0.40
    if len(closes) >= 3 and closes[-1] > closes[-2] > closes[-3]:
        quality += 0.45
    elif len(closes) >= 2 and closes[-1] < closes[-2]:
        quality -= 0.20
    return max(min(quality, 1.8), -1.5)

def calc_vibe(price, high, low, change_1h, change_24h, fg_value=None, btc_change=None, candle_quality=0):
    if high != low:
        range_pos = ((price - low) / (high - low)) * 100
    else:
        range_pos = 50.0
    reasons = []
    
    base = 54.0
    
    structure_boost = candle_quality * 10.5
    base += structure_boost
    if candle_quality > 1.0:
        reasons.append("Excellent bullish structure")
    elif candle_quality > 0.5:
        reasons.append("Solid constructive structure")
    elif candle_quality > 0.15:
        reasons.append("Mildly positive structure")
    elif candle_quality < -0.7:
        reasons.append("Weak structure / rejection")
    elif candle_quality < -0.25:
        reasons.append("Mixed structure")

    base += (range_pos - 50) * 0.14
    if range_pos > 88:
        reasons.append("Near top of daily range")
    elif range_pos > 72:
        reasons.append("Upper half of range")
    elif range_pos < 18:
        if candle_quality > 0.15:
            reasons.append("Building from lows")
        else:
            reasons.append("Near bottom of range")
    elif range_pos < 32:
        reasons.append("Lower half of range")

    base += change_1h * 3.8
    if change_1h > 2.0:
        reasons.append("Very strong 1h momentum")
    elif change_1h > 0.7:
        reasons.append("Strong 1h momentum")
    elif change_1h > 0.2:
        reasons.append("Positive 1h")
    elif change_1h < -1.5:
        reasons.append("Strong negative 1h")
    elif change_1h < -0.4:
        reasons.append("Mild negative 1h")

    base += change_24h * 0.45

    if btc_change is not None:
        vs_btc = change_24h - btc_change
        base += vs_btc * 0.75
        if vs_btc > 3.5:
            reasons.append("Clearly outperforming BTC")
        elif vs_btc > 1.2:
            reasons.append("Outperforming BTC")
        elif vs_btc < -3.5:
            reasons.append("Lagging BTC")

    if fg_value is not None:
        if fg_value < 25:
            base -= 1.5
        elif fg_value > 75:
            base += 1.0

    # Breakout boost
    if range_pos >= 87 and change_1h >= 0.6 and candle_quality > 0.15:
        base += 5
        reasons.append("Clear breakout in progress")
    elif range_pos >= 82 and change_1h >= 1.0:
        base += 3.5
        reasons.append("Breaking higher with momentum")
    elif range_pos >= 78 and change_1h >= 0.4 and candle_quality > 0.3:
        base += 2
        reasons.append("Pushing into breakout territory")

    score = max(min(int(round(base)), 92), 16)
    
    if score >= 80:
        meme = "🔥 Strong structure + momentum"
    elif score >= 68:
        meme = "🚀 Constructive structure"
    elif score >= 55:
        meme = "📈 Structure okay, mixed short-term"
    elif score >= 42:
        meme = "😐 Mixed signals"
    elif score >= 28:
        meme = "⚠️ Short-term weakness"
    else:
        meme = "💀 Weak structure"
    
    return score, meme, range_pos, reasons

def colored_progress(score: int, height: int = 12):
    if score >= 75:
        color = "linear-gradient(90deg, #00e676, #00c853)"
    elif score >= 60:
        color = "linear-gradient(90deg, #69f0ae, #00e676)"
    elif score >= 45:
        color = "linear-gradient(90deg, #ffd600, #ffab00)"
    else:
        color = "linear-gradient(90deg, #ff5252, #d50000)"
    return f"""
    <div style="background:#e0e0e0;border-radius:10px;height:{height}px;overflow:hidden;margin:6px 0 10px 0;">
        <div style="width:{score}%;height:100%;background:{color};border-radius:10px;transition:width 0.5s ease;"></div>
    </div>
    """

def make_sparkline(history):
    if not history or len(history) < 2:
        return None
    times = [h[0] for h in history]
    scores = [h[1] for h in history]
    
    min_score = min(scores)
    max_score = max(scores)
    padding = max(4, (max_score - min_score) * 0.25)
    y_min = max(0, min_score - padding)
    y_max = min(100, max_score + padding)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=scores,
        mode="lines+markers",
        line=dict(color="#00c853" if scores[-1] >= 60 else "#ff5252", width=3),
        marker=dict(size=5),
        fill="tozeroy",
        fillcolor="rgba(0,200,83,0.12)" if scores[-1] >= 60 else "rgba(255,82,82,0.12)"
    ))
    fig.update_layout(
        height=160,
        margin=dict(l=0, r=10, t=10, b=30),
        xaxis=dict(showgrid=False, showticklabels=True, tickformat="%H:%M"),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(0,0,0,0.06)",
            range=[y_min, y_max],
            title="Vibe"
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )
    return fig

# ========== HEADER ==========
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.title("🚀 Pre-Bart Vibe Dashboard")
    st.markdown("##### Live crypto vibes + meme feedback")
with col_refresh:
    st.write("")
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.session_state.last_refresh = datetime.now()
        st.rerun()

st.caption(f"Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')} • Model: {MODEL_VERSION}")

# ========== MARKET CONTEXT ==========
fg_value, fg_label = get_fear_greed()
global_data = get_global()

ctx1, ctx2, ctx3, ctx4 = st.columns(4)
with ctx1:
    if fg_value is not None:
        color = "🟢" if fg_value >= 55 else "🟡" if fg_value >= 40 else "🔴"
        st.metric("Fear & Greed", f"{fg_value} {color}", fg_label)
    else:
        st.metric("Fear & Greed", "—")
with ctx2:
    if global_data:
        st.metric("BTC Dominance", f"{global_data['market_cap_percentage'].get('btc', 0):.1f}%")
    else:
        st.metric("BTC Dominance", "—")
with ctx3:
    if global_data:
        st.metric("Total Crypto MCap", f"${global_data['total_market_cap']['usd']/1e12:.2f}T")
    else:
        st.metric("Total Crypto MCap", "—")
with ctx4:
    if global_data:
        st.metric("Market 24h", f"{global_data.get('market_cap_change_percentage_24h_usd', 0):+.2f}%")
    else:
        st.metric("Market 24h", "—")

st.divider()

# ========== FILL PENDING RETURNS ==========
fill_pending_returns()

# ========== LIVE TOP COINS ==========
top_coins = get_top_coins(20)

if not top_coins:
    st.error("Could not load top coins. Please try refreshing.")
    st.stop()

COIN_ORDER = []
coin_map = {}
for c in top_coins:
    name = c["name"]
    cid = c["id"]
    tick = c["symbol"].upper()
    COIN_ORDER.append((name, cid, tick))
    coin_map[cid] = c

btc_change = next((c.get("price_change_percentage_24h") or 0 for c in top_coins if c["id"] == "bitcoin"), 0)

# ========== PRE-CALCULATE VIBES ==========
vibe_data = []
for name, cid, tick in COIN_ORDER:
    c = coin_map.get(cid)
    if not c:
        continue
    price = c["current_price"]
    high = c["high_24h"]
    low = c["low_24h"]
    ch1 = c.get("price_change_percentage_1h_in_currency") or 0
    ch24 = c.get("price_change_percentage_24h") or 0
    image_url = c.get("image", "")
    ohlc = get_ohlc(cid, "1")
    cq = analyze_candles(ohlc)
    score, meme, range_pos, reasons = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, cq)

    st.session_state.score_history = update_history(cid, score, st.session_state.score_history)

    # Previous score from history
    hist = st.session_state.score_history.get(cid, [])
    prev_score = hist[-2][1] if len(hist) >= 2 else None

    # Save snapshot
    vs_btc_val = ch24 - btc_change
    save_vibe_snapshot(
        coin_id=cid,
        symbol=tick,
        price=price,
        score=score,
        label=meme,
        change_24h=ch24,
        range_pos=range_pos,
        vs_btc=vs_btc_val,
        prev_score=prev_score,
        sub_signals={"reasons": reasons, "candle_quality": cq}
    )

    vibe_data.append({
        "name": name, "cid": cid, "tick": tick, "price": price, "ch24": ch24, "ch1": ch1,
        "score": score, "meme": meme, "image_url": image_url, "candle_quality": cq,
        "range_pos": range_pos, "reasons": reasons,
        "history": st.session_state.score_history.get(cid, [])
    })

vibe_data_sorted = sorted(vibe_data, key=lambda x: x["score"], reverse=True)

# ========== MULTI-COIN CARDS ==========
st.subheader("🌐 Multi-Coin Vibe Overview")
st.caption("Live Top 20 by market cap • Sorted by current vibe score")

col_filter, _ = st.columns([2, 4])
with col_filter:
    show_option = st.selectbox(
        "Show",
        ["Top 5", "Top 10", "Top 15", "All"],
        index=["Top 5", "Top 10", "Top 15", "All"].index(st.session_state.show_count)
        if st.session_state.show_count in ["Top 5", "Top 10", "Top 15", "All"] else 1
    )
    st.session_state.show_count = show_option

if show_option == "Top 5":
    display_data = vibe_data_sorted[:5]
elif show_option == "Top 10":
    display_data = vibe_data_sorted[:10]
elif show_option == "Top 15":
    display_data = vibe_data_sorted[:15]
else:
    display_data = vibe_data_sorted

st.caption(f"Showing {len(display_data)} coins")

for row_start in range(0, len(display_data), 5):
    cols = st.columns(5)
    for i, item in enumerate(display_data[row_start:row_start+5]):
        with cols[i]:
            with st.container(border=True):
                if item["image_url"]:
                    st.image(item["image_url"], width=28)
                else:
                    st.markdown("<div style='height:28px; margin-bottom:4px;'></div>", unsafe_allow_html=True)

                st.markdown(f"**{item['tick']}**")
                
                if item["price"] >= 1000:
                    price_str = f"${item['price']:,.0f}"
                elif item["price"] >= 1:
                    price_str = f"${item['price']:,.2f}"
                else:
                    price_str = f"${item['price']:.4f}"
                
                st.markdown(
                    f"<div style='font-size:1.25rem; font-weight:600; height:30px; line-height:30px; overflow:hidden;'>{price_str}</div>",
                    unsafe_allow_html=True
                )
                st.caption(f"{item['ch24']:+.2f}% • Vibe {item['score']}")
                
                st.markdown(colored_progress(item["score"], height=10), unsafe_allow_html=True)
                
                st.markdown(
                    f"""
                    <div style="
                        height: 42px;
                        min-height: 42px;
                        max-height: 42px;
                        font-size: 13px;
                        color: #888;
                        line-height: 1.3;
                        overflow: hidden;
                        margin-bottom: 8px;
                    ">{item['meme']}</div>
                    """,
                    unsafe_allow_html=True
                )
                
                if st.button("View", key=f"btn_{item['cid']}", use_container_width=True):
                    st.session_state.selected_coin = item["name"]
                    st.session_state.search_coin = None
                    st.rerun()

st.divider()

# ========== DETAILED VIEW ==========
st.subheader("🎯 Detailed View")

st.markdown("##### Search any coin on CoinGecko")

search_query = st.text_input(
    "Type coin name or symbol",
    placeholder="e.g. Avalanche, PEPE, WIF, BONK, INJ...",
    key="detail_search"
)

if search_query and len(search_query.strip()) >= 2:
    results = search_coins(search_query.strip())
    
    if results:
        options = {f"{c['name']} ({c['symbol'].upper()})": c["id"] for c in results}
        
        chosen = st.selectbox(
            "Select from results",
            list(options.keys()),
            key="search_results_select"
        )
        
        selected_id = options[chosen]
        if st.session_state.search_coin != selected_id:
            st.session_state.search_coin = selected_id
            st.session_state.selected_coin = chosen.split(" (")[0]
            st.rerun()
    else:
        st.info("No coins found. Try a different search.")
else:
    st.caption("Type at least 2 characters to search")

col_time, _ = st.columns([1, 3])
with col_time:
    timeframe = st.selectbox("Timeframe", ["Last 1 Day (30 min)", "Last 7 Days", "Last 30 Days"])

# ========== LOAD DATA ==========
if st.session_state.search_coin:
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            headers=HEADERS,
            params={"vs_currency": "usd", "ids": st.session_state.search_coin, "price_change_percentage": "1h,24h"},
            timeout=10
        )
        single = r.json() if r.status_code == 200 else []
    except:
        single = []

    if single:
        c = single[0]
        name = c["name"]
        cid = c["id"]
        tick = c["symbol"].upper()
        price = c["current_price"]
        high = c["high_24h"]
        low = c["low_24h"]
        ch1 = c.get("price_change_percentage_1h_in_currency") or 0
        ch24 = c.get("price_change_percentage_24h") or 0
        ohlc = get_ohlc(cid, "1")
        cq = analyze_candles(ohlc)
        score, meme, range_pos, reasons = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, cq)
        volume = c["total_volume"]
        market_cap = c["market_cap"]
        image_url = c.get("image", "")
        st.session_state.score_history = update_history(cid, score, st.session_state.score_history)
        history = st.session_state.score_history.get(cid, [])
        
        prev_score = history[-2][1] if len(history) >= 2 else None
        vs_btc_val = ch24 - btc_change
        save_vibe_snapshot(cid, tick, price, score, meme, ch24, range_pos, vs_btc_val, prev_score, {"reasons": reasons, "candle_quality": cq})
    else:
        st.warning("Could not load coin data.")
        st.stop()
else:
    item = next((v for v in vibe_data if v["name"] == st.session_state.selected_coin), vibe_data[0] if vibe_data else None)
    if not item:
        st.info("Search for a coin above or click View on a card to see details.")
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

# Alerts
if st.session_state.last_score is not None:
    if score >= 70 and st.session_state.last_score < 70:
        st.toast(f"🚀 {tick} Vibe crossed 70!", icon="🚀")
    elif score <= 30 and st.session_state.last_score > 30:
        st.toast(f"🐻 {tick} Vibe dropped below 30", icon="🐻")
st.session_state.last_score = score

vs_btc = ch24 - (btc_change or 0)
price_text = f"${price:,.4f}" if price < 10 else f"${price:,.2f}"
st.metric(f"{name}", price_text, f"{ch24:+.2f}% (24h)  |  {ch1:+.2f}% (1h)")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("24h Volume", f"${volume/1_000_000:,.1f}M")
c2.metric("Market Cap", f"${market_cap/1_000_000_000:,.2f}B")
c3.metric("Range Position", f"{range_pos:.0f}%")
c4.metric("Candle Quality", f"{cq:+.1f}")
c5.metric("vs BTC (24h)", f"{vs_btc:+.2f}%")

# Current Vibe + Performance Summary
st.markdown(f"**Vibe Score: {score}/100**")
st.markdown(colored_progress(score, height=14), unsafe_allow_html=True)

# Live performance summary
perf = get_coin_performance(cid)
if perf and perf.get("ready"):
    st.caption(f"Historical 1h win rate: **{perf['win_1h']}%** • Avg 1h return: **{perf['avg_1h']:+.2f}%** • n = {perf['n']}")
else:
    st.caption("Collecting performance data — not enough observations yet.")

if score >= 80:
    st.success(meme)
elif score <= 30:
    st.error(meme)
else:
    st.info(meme)

st.markdown("##### Vibe Score History")
if history and len(history) >= 2:
    fig = make_sparkline(history)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(f"Showing last {len(history)} readings • Persistent across most restarts")
else:
    st.info("History will start building after a few more refreshes...")

with st.expander("🤔 Why this score?"):
    for r in reasons:
        st.write(f"• {r}")

# Share Card
st.markdown("### 📤 Share this vibe")
share_html = f"""
<div style="
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 16px;
    padding: 24px;
    color: white;
    font-family: Inter, sans-serif;
    max-width: 420px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <img src="{image_url}" width="36" style="border-radius:50%;">
        <div>
            <div style="font-weight:700;font-size:1.2rem;">{tick}</div>
            <div style="opacity:0.7;font-size:0.85rem;">{name}</div>
        </div>
    </div>
    <div style="font-size:2.2rem;font-weight:700;margin:8px 0;">{score}/100</div>
    <div style="font-size:1.05rem;margin-bottom:12px;">{meme}</div>
    <div style="opacity:0.8;font-size:0.9rem;">
        {ch24:+.2f}% 24h • Range {range_pos:.0f}%
    </div>
    <div style="margin-top:16px;font-size:0.8rem;opacity:0.6;">
        Pre-Bart Vibe Dashboard • prebartvibes.streamlit.app
    </div>
</div>
"""
st.markdown(share_html, unsafe_allow_html=True)
st.caption("Screenshot the card above or copy the text below")

share_text = f"{tick} Vibe Score: {score}/100 – {meme}\n{ch24:+.2f}% 24h | Range {range_pos:.0f}%\nhttps://prebartvibes.streamlit.app/"
st.code(share_text, language=None)

st.markdown(f"""
<div style="display:flex;flex-wrap:wrap;gap:10px;margin:12px 0;">
    <a href="https://x.com/search?q=%24{tick}&src=typed_query&f=live" target="_blank"
       style="background:linear-gradient(90deg,#1da1f2,#0d8ecf);color:white;padding:8px 16px;border-radius:20px;text-decoration:none;font-weight:600;">
        ${tick} Live
    </a>
    <a href="https://x.com/search?q={quote(name + ' crypto')}&src=typed_query&f=live" target="_blank"
       style="background:linear-gradient(90deg,#1da1f2,#0d8ecf);color:white;padding:8px 16px;border-radius:20px;text-decoration:none;font-weight:600;">
        {name} Crypto
    </a>
</div>
""", unsafe_allow_html=True)

# Chart
st.divider()
st.subheader(f"{name} • Chart")

days = "1"
if "7 Days" in timeframe:
    days = "7"
elif "30 Days" in timeframe:
    days = "30"

ohlc_data = get_ohlc(cid, days)
volume_data = get_market_chart(cid, days)

if isinstance(ohlc_data, list) and len(ohlc_data) > 0:
    df = pd.DataFrame(ohlc_data, columns=["timestamp", "open", "high", "low", "close"])
    df["time"] = pd.to_datetime(df["timestamp"], unit="ms")
    has_volume = False
    if "total_volumes" in volume_data:
        vol_df = pd.DataFrame(volume_data["total_volumes"], columns=["timestamp", "volume"])
        vol_df["time"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
        df = pd.merge_asof(df.sort_values("time"), vol_df.sort_values("time"), on="time", direction="nearest")
        has_volume = True

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.72, 0.28])
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
    fig.update_layout(height=520, template="plotly_white", margin=dict(l=0,r=0,t=20,b=0),
                      xaxis_rangeslider_visible=False, showlegend=False, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    if days == "1":
        st.caption("30-minute candles (best available on free API)")
else:
    st.info("Chart temporarily unavailable.")

# ========== VIBE PERFORMANCE SECTION ==========
st.divider()
st.subheader("📊 Vibe Performance")
st.caption("Historical forward returns by Vibe Score bucket • Only shows when enough data exists")

bucket_stats = get_bucket_stats(min_n=20)

if bucket_stats:
    # Create a nice table
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
                "Avg 4h": "—",
                "Win 4h": "—",
                "Avg 24h": "—",
                "Win 24h": "—",
            })
        else:
            table_data.append({
                "Bucket": s["bucket"],
                "n": s["n"],
                "Avg 30m": f"{s['avg_30m']:+.2f}%" if s['avg_30m'] is not None else "—",
                "Win 30m": f"{s['win_30m']}%" if s['win_30m'] is not None else "—",
                "Avg 1h": f"{s['avg_1h']:+.2f}%" if s['avg_1h'] is not None else "—",
                "Win 1h": f"{s['win_1h']}%" if s['win_1h'] is not None else "—",
                "Avg 4h": f"{s['avg_4h']:+.2f}%" if s['avg_4h'] is not None else "—",
                "Win 4h": f"{s['win_4h']}%" if s['win_4h'] is not None else "—",
                "Avg 24h": f"{s['avg_24h']:+.2f}%" if s['avg_24h'] is not None else "—",
                "Win 24h": f"{s['win_24h']}%" if s['win_24h'] is not None else "—",
            })
    
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
    st.caption("Win rate = % of times the future return was positive. Data only appears after sufficient observations.")
else:
    st.info("Collecting performance data… Check back in a few hours once more snapshots have matured.")
