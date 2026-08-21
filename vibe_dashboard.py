import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from urllib.parse import quote

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=45 * 1000, key="datarefresh")
except:
    pass

API_KEY = "CG-h61Dg6UoB2gVfCSUJQDj4dLa"
HEADERS = {"x-cg-demo-api-key": API_KEY}

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
    st.session_state.selected_coin = "Avalanche"
if "last_score" not in st.session_state:
    st.session_state.last_score = None
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if "score_history" not in st.session_state:
    st.session_state.score_history = {}
if "search_coin" not in st.session_state:
    st.session_state.search_coin = None

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

@st.cache_data(ttl=30)
def get_markets(ids_str):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ids_str,
        "price_change_percentage": "1h,24h"
    }
    r = requests.get(url, headers=HEADERS, params=params, timeout=12)
    return r.json() if r.status_code == 200 else []

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
        return r.json().get("coins", [])[:8]
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
    base = 55
    structure_boost = candle_quality * 11
    base += structure_boost
    if candle_quality > 0.8:
        reasons.append("Clean higher-lows + strong closes (bullish structure)")
    elif candle_quality > 0.35:
        reasons.append("Constructive recent candles / structure")
    elif candle_quality < -0.6:
        reasons.append("Lower-lows or heavy rejection showing")
    elif candle_quality < -0.2:
        reasons.append("Mixed / weak recent candle structure")
    if range_pos > 85:
        base += 6
        reasons.append("Price near the top of the daily range")
    elif range_pos > 70:
        base += 4
        reasons.append("Upper half of the range")
    elif range_pos < 20:
        if candle_quality > 0.15:
            base += 4
            reasons.append("Building from the bottom of the range (accumulation feel)")
        else:
            base -= 5
            reasons.append("Sitting near the bottom of the range")
    elif range_pos < 35:
        if candle_quality > 0.1:
            base += 2
        else:
            base -= 3
            reasons.append("Lower half of the range")
    if change_1h > 1.3:
        base += 13
        reasons.append("Strong positive 1h momentum")
    elif change_1h > 0.5:
        base += 9
        reasons.append("Positive 1h momentum")
    elif change_1h > 0.1:
        base += 5
        reasons.append("Slightly positive 1h")
    elif change_1h > -0.5:
        base += 0
    elif change_1h > -1.2:
        base -= 5
        reasons.append("Mild negative 1h")
    else:
        base -= 10
        reasons.append("Strong negative 1h momentum")
    if change_24h > 5:
        base += 4
    elif change_24h > 2:
        base += 2
    elif change_24h < -5:
        base -= 4
    elif change_24h < -2:
        base -= 2
    if btc_change is not None:
        vs_btc = change_24h - btc_change
        if vs_btc > 3:
            base += 4
            reasons.append("Outperforming BTC on the day")
        elif vs_btc < -3:
            base -= 3
            reasons.append("Lagging BTC on the day")
    if fg_value is not None:
        if fg_value < 25:
            base -= 2
        elif fg_value > 70:
            base += 1
    score = max(min(int(round(base)), 92), 14)
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
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=scores, mode="lines",
        line=dict(color="#00c853" if scores[-1] >= 60 else "#ff5252", width=2),
        fill="tozeroy", fillcolor="rgba(0,200,83,0.15)" if scores[-1] >= 60 else "rgba(255,82,82,0.15)"
    ))
    fig.update_layout(
        height=80, margin=dict(l=0, r=0, t=5, b=5),
        xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0, 100]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
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

st.caption(f"Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')}")

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

# ========== COIN LIST + SEARCH ==========
COIN_ORDER = [
    ("Bitcoin", "bitcoin", "BTC"),
    ("Ethereum", "ethereum", "ETH"),
    ("Solana", "solana", "SOL"),
    ("Avalanche", "avalanche-2", "AVAX"),
    ("Dogecoin", "dogecoin", "DOGE"),
    ("Chainlink", "chainlink", "LINK"),
    ("Sui", "sui", "SUI"),
    ("Render", "render-token", "RENDER"),
    ("NEAR", "near", "NEAR"),
    ("Aptos", "aptos", "APT"),
    ("dogwifhat", "dogwifcoin", "WIF"),
    ("Pepe", "pepe", "PEPE"),
    ("Bonk", "bonk", "BONK"),
]

ids_str = ",".join([c[1] for c in COIN_ORDER])
markets = get_markets(ids_str)
coin_map = {c["id"]: c for c in markets} if markets else {}

btc_change = coin_map.get("bitcoin", {}).get("price_change_percentage_24h") or 0

# Search
st.subheader("🔍 Search any coin")
search_query = st.text_input("Type coin name or symbol", placeholder="e.g. PEPE, SUI, WIF, BONK...")
search_results = search_coins(search_query) if search_query else []

if search_results:
    options = {f"{c['name']} ({c['symbol'].upper()})": c["id"] for c in search_results}
    chosen = st.selectbox("Select from results", list(options.keys()))
    if st.button("Load this coin’s vibe", type="primary"):
        st.session_state.search_coin = options[chosen]
        st.session_state.selected_coin = chosen.split(" (")[0]
        st.rerun()

st.divider()

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

    if cid not in st.session_state.score_history:
        st.session_state.score_history[cid] = []
    st.session_state.score_history[cid].append((datetime.now(), score))
    st.session_state.score_history[cid] = st.session_state.score_history[cid][-20:]

    vibe_data.append({
        "name": name, "cid": cid, "tick": tick, "price": price, "ch24": ch24, "ch1": ch1,
        "score": score, "meme": meme, "image_url": image_url, "candle_quality": cq,
        "range_pos": range_pos, "reasons": reasons, "history": st.session_state.score_history[cid]
    })

vibe_data_sorted = sorted(vibe_data, key=lambda x: x["score"], reverse=True)

# ========== LEADERBOARD WITH ICONS ==========
st.subheader("🏆 Vibe Leaderboard")
st.caption("Sorted by current vibe score")

# Build custom HTML table with icons
html = """
<style>
.leaderboard-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 15px;
}
.leaderboard-table th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid #ddd;
    color: #555;
    font-weight: 600;
}
.leaderboard-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #eee;
    vertical-align: middle;
}
.coin-cell {
    display: flex;
    align-items: center;
    gap: 10px;
}
.coin-cell img {
    width: 24px;
    height: 24px;
    border-radius: 50%;
}
</style>
<table class="leaderboard-table">
    <thead>
        <tr>
            <th>Rank</th>
            <th>Coin</th>
            <th>Price</th>
            <th>24h</th>
            <th>Vibe</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
"""

for rank, item in enumerate(vibe_data_sorted, 1):
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
    price_str = f"${item['price']:,.2f}" if item['price'] >= 1 else f"${item['price']:.4f}"
    ch24_str = f"{item['ch24']:+.2f}%"
    
    # Simple colored vibe bar
    if item['score'] >= 75:
        bar_color = "#00c853"
    elif item['score'] >= 60:
        bar_color = "#69f0ae"
    elif item['score'] >= 45:
        bar_color = "#ffab00"
    else:
        bar_color = "#ff5252"
    
    html += f"""
    <tr>
        <td style="font-weight:600;">{medal}</td>
        <td>
            <div class="coin-cell">
                <img src="{item['image_url']}" alt="{item['tick']}">
                <strong>{item['tick']}</strong>
            </div>
        </td>
        <td>{price_str}</td>
        <td>{ch24_str}</td>
        <td>
            <div style="display:flex;align-items:center;gap:8px;">
                <div style="background:#eee;width:80px;height:8px;border-radius:4px;overflow:hidden;">
                    <div style="width:{item['score']}%;height:100%;background:{bar_color};"></div>
                </div>
                <span style="font-weight:600;">{item['score']}</span>
            </div>
        </td>
        <td style="color:#666;">{item['meme']}</td>
    </tr>
    """

html += """
    </tbody>
</table>
"""

st.markdown(html, unsafe_allow_html=True)

st.divider()

# ========== DETAILED VIEW ==========
st.subheader("🎯 Detailed View")

if st.session_state.search_coin:
    single = get_markets(st.session_state.search_coin)
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
        history = st.session_state.score_history.get(cid, [])
    else:
        st.warning("Could not load searched coin.")
        st.stop()
else:
    selected = st.session_state.selected_coin
    col_a, col_b = st.columns([2, 1])
    with col_a:
        selected = st.selectbox("Select Coin", [x[0] for x in COIN_ORDER],
                                index=[x[0] for x in COIN_ORDER].index(selected) if selected in [x[0] for x in COIN_ORDER] else 0)
        st.session_state.selected_coin = selected
    with col_b:
        timeframe = st.selectbox("Timeframe", ["Last 1 Day (30 min)", "Last 7 Days", "Last 30 Days"])

    item = next((v for v in vibe_data if v["name"] == selected), None)
    if not item:
        st.warning("Loading...")
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

st.markdown(f"**Vibe Score: {score}/100**")
st.markdown(colored_progress(score, height=14), unsafe_allow_html=True)

if score >= 80:
    st.success(meme)
elif score <= 30:
    st.error(meme)
else:
    st.info(meme)

if history and len(history) >= 2:
    st.caption("Vibe score history")
    fig = make_sparkline(history)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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
if "timeframe" in locals():
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
