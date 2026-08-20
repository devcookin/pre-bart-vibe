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
    .stProgress > div > div > div > div { background: linear-gradient(90deg, #00c853, #00b0ff); }
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
def get_markets():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin,ethereum,solana,avalanche-2,dogecoin",
        "price_change_percentage": "1h,24h"
    }
    r = requests.get(url, headers=HEADERS, params=params, timeout=12)
    return r.json()

@st.cache_data(ttl=60)
def get_ohlc(coin_id, days="1"):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": days}
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    return r.json()

@st.cache_data(ttl=60)
def get_market_chart(coin_id, days="1"):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    return r.json()

def analyze_candles(ohlc_data):
    if not isinstance(ohlc_data, list) or len(ohlc_data) < 3:
        return 0
    df = pd.DataFrame(ohlc_data[-5:], columns=["timestamp", "open", "high", "low", "close"])
    quality = 0
    for _, row in df.iterrows():
        body = abs(row["close"] - row["open"])
        upper_wick = row["high"] - max(row["open"], row["close"])
        full_range = row["high"] - row["low"]
        if full_range == 0: continue
        if upper_wick > body * 1.6 and upper_wick / full_range > 0.45:
            quality -= 0.6
        close_position = (row["close"] - row["low"]) / full_range
        if close_position > 0.78 and row["close"] > row["open"]:
            quality += 0.5
        elif close_position < 0.30:
            quality -= 0.3
    lows = df["low"].values
    if len(lows) >= 3 and lows[-1] > lows[-2] > lows[-3]:
        quality += 0.7
    elif len(lows) >= 2 and lows[-1] < lows[-2]:
        quality -= 0.4
    return max(min(quality, 1.4), -1.4)

def calc_vibe(price, high, low, change_1h, change_24h, fg_value=None, btc_change=None, candle_quality=0):
    if high != low:
        range_pos = ((price - low) / (high - low)) * 100
    else:
        range_pos = 50

    reasons = []

    # More balanced thresholds
    if (range_pos > 83 and change_1h > 0.8 and change_24h > 2.5 and 
        (fg_value is None or fg_value >= 40) and (btc_change is None or btc_change > -1.5)):
        score = 86
        meme = "🔥 Strong multi-timeframe alignment."
        reasons.append("Price near top of range + strong momentum")
    elif range_pos > 75 and change_1h > 0.4 and change_24h > 1.0:
        score = 76
        meme = "🚀 Higher highs forming + good momentum."
        reasons.append("Holding high in the range with positive momentum")
    elif range_pos > 65 and change_1h > 0.0:
        score = 68
        meme = "📈 Reclaiming structure / defending higher."
        reasons.append("Above mid-range with positive short-term momentum")
    elif range_pos > 52 and change_1h > -0.6:
        score = 58
        meme = "📊 Holding mid-range. Waiting for confirmation."
        reasons.append("Price is holding the middle of the daily range")
    elif range_pos > 40:
        score = 49
        meme = "😐 Neutral zone. No clear edge yet."
        reasons.append("Price is in no-man's land")
    elif range_pos > 25 and change_1h < 0:
        score = 37
        meme = "⚠️ Losing short-term structure."
        reasons.append("Sliding lower in the range")
    elif range_pos > 12:
        score = 26
        meme = "🐻 Below key short-term levels."
        reasons.append("Price is in the lower part of the daily range")
    else:
        score = 14
        meme = "💀 Weak. Sitting on the lows."
        reasons.append("Price is near the daily lows")

    # Milder candle quality impact
    score += candle_quality * 2.8
    if candle_quality > 0.4:
        reasons.append("Recent candles show clean strength / higher lows")
    elif candle_quality < -0.4:
        reasons.append("Recent candles show some rejection")

    # Milder penalties
    if change_1h < -2.0:
        score -= 6
        reasons.append("Sharp negative 1h momentum")
    if change_24h < -5:
        score -= 7
        reasons.append("Significant 24h weakness")
    if fg_value is not None and fg_value < 25:
        score -= 4
        reasons.append("Market is in Extreme Fear")

    score = max(min(int(score), 94), 10)

    if score >= 82:
        meme = "🔥 High conviction – momentum + candles aligned."
    elif score >= 70:
        meme = "🚀 Structure improving with decent candle quality."
    elif score >= 58:
        meme = "📈 Holding structure, needs a bit more confirmation."
    elif score <= 28:
        meme = "💀 Weak location + soft candles."

    return score, meme, range_pos, reasons

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
        btc_dom = global_data["market_cap_percentage"].get("btc", 0)
        st.metric("BTC Dominance", f"{btc_dom:.1f}%")
    else:
        st.metric("BTC Dominance", "—")
with ctx3:
    if global_data:
        mcap = global_data["total_market_cap"]["usd"] / 1e12
        st.metric("Total Crypto MCap", f"${mcap:.2f}T")
    else:
        st.metric("Total Crypto MCap", "—")
with ctx4:
    if global_data:
        chg = global_data.get("market_cap_change_percentage_24h_usd", 0)
        st.metric("Market 24h", f"{chg:+.2f}%")
    else:
        st.metric("Market 24h", "—")

st.divider()

# ========== MULTI-COIN OVERVIEW ==========
st.subheader("🌐 Multi-Coin Vibe Overview")
st.caption("Click “View” on any coin to open the detailed view")

markets = get_markets()
coin_map = {c["id"]: c for c in markets} if markets else {}

btc_change = None
if "bitcoin" in coin_map:
    btc_change = coin_map["bitcoin"].get("price_change_percentage_24h") or 0

COIN_ORDER = [
    ("Bitcoin", "bitcoin", "BTC"),
    ("Ethereum", "ethereum", "ETH"),
    ("Solana", "solana", "SOL"),
    ("Avalanche", "avalanche-2", "AVAX"),
    ("Dogecoin", "dogecoin", "DOGE"),
]

cols = st.columns(5)
for i, (name, cid, tick) in enumerate(COIN_ORDER):
    with cols[i]:
        c = coin_map.get(cid)
        if c:
            price = c["current_price"]
            high = c["high_24h"]
            low = c["low_24h"]
            ch1 = c.get("price_change_percentage_1h_in_currency") or 0
            ch24 = c.get("price_change_percentage_24h") or 0
            image_url = c.get("image", "")
            score, meme, _, _ = calc_vibe(price, high, low, ch1, ch24, fg_value, btc_change, 0)

            if image_url:
                st.image(image_url, width=32)
            st.markdown(f"**{tick}**")
            price_str = f"${price:,.2f}" if price >= 1 else f"${price:.4f}"
            st.markdown(f"### {price_str}")
            st.caption(f"{ch24:+.2f}% • Vibe {score}")
            st.progress(score / 100)
            st.caption(meme)
            if st.button("View", key=f"btn_{cid}", use_container_width=True):
                st.session_state.selected_coin = name
                st.rerun()
        else:
            st.info(f"{tick}\nLoading...")

st.divider()

# ========== DETAILED VIEW ==========
st.subheader("🎯 Detailed View")

selected = st.session_state.selected_coin

col_a, col_b = st.columns([2, 1])
with col_a:
    selected = st.selectbox("Select Coin", [x[0] for x in COIN_ORDER], 
                            index=[x[0] for x in COIN_ORDER].index(selected))
    st.session_state.selected_coin = selected
with col_b:
    timeframe = st.selectbox("Timeframe", ["Last 1 Day (30 min)", "Last 7 Days", "Last 30 Days"])

name_to_id = {x[0]: x[1] for x in COIN_ORDER}
name_to_tick = {x[0]: x[2] for x in COIN_ORDER}
coin_id = name_to_id[selected]
ticker = name_to_tick[selected]

c = coin_map.get(coin_id)
if c:
    price = c["current_price"]
    change_24h = c.get("price_change_percentage_24h") or 0
    change_1h = c.get("price_change_percentage_1h_in_currency") or 0
    high = c["high_24h"]
    low = c["low_24h"]
    volume = c["total_volume"]
    market_cap = c["market_cap"]

    ohlc_1d = get_ohlc(coin_id, "1")
    candle_quality = analyze_candles(ohlc_1d)

    score, meme, range_pos, reasons = calc_vibe(price, high, low, change_1h, change_24h, fg_value, btc_change, candle_quality)

    # Alerts
    if st.session_state.last_score is not None:
        if score >= 70 and st.session_state.last_score < 70:
            st.toast(f"🚀 {ticker} Vibe crossed 70!", icon="🚀")
        elif score <= 30 and st.session_state.last_score > 30:
            st.toast(f"🐻 {ticker} Vibe dropped below 30", icon="🐻")
    st.session_state.last_score = score

    vs_btc = change_24h - (btc_change or 0)

    price_text = f"${price:,.4f}" if price < 10 else f"${price:,.2f}"
    st.metric(f"{selected}", price_text, f"{change_24h:+.2f}% (24h)  |  {change_1h:+.2f}% (1h)")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("24h Volume", f"${volume/1_000_000:,.1f}M")
    c2.metric("Market Cap", f"${market_cap/1_000_000_000:,.2f}B")
    c3.metric("Range Position", f"{range_pos:.0f}%")
    c4.metric("Candle Quality", f"{candle_quality:+.1f}")
    c5.metric("vs BTC (24h)", f"{vs_btc:+.2f}%")

    st.progress(score / 100, text=f"Vibe Score: {score}/100")

    if score >= 80:
        st.success(meme)
    elif score <= 30:
        st.error(meme)
    else:
        st.info(meme)

    with st.expander("🤔 Why this score?"):
        for r in reasons:
            st.write(f"• {r}")

    share_text = f"{ticker} Vibe Score: {score}/100 – {meme}\nhttps://prebartvibes.streamlit.app/"
    st.text_area("📋 Share this vibe (copy the text below)", share_text, height=80)

    st.markdown(f"""
    <div style="display:flex; flex-wrap:wrap; gap:10px; margin: 12px 0;">
        <a href="https://x.com/search?q=%24{ticker}&src=typed_query&f=live" target="_blank" 
           style="background:linear-gradient(90deg, #1da1f2, #0d8ecf); color:white; padding:8px 16px; border-radius:20px; text-decoration:none; font-weight:600;">
            ${ticker} Live
        </a>
        <a href="https://x.com/search?q={quote(selected + ' crypto')}&src=typed_query&f=live" target="_blank" 
           style="background:linear-gradient(90deg, #1da1f2, #0d8ecf); color:white; padding:8px 16px; border-radius:20px; text-decoration:none; font-weight:600;">
            {selected} Crypto
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.subheader(f"{selected} • {timeframe}")

    if "1 Day" in timeframe:
        days = "1"
    elif "7 Days" in timeframe:
        days = "7"
    else:
        days = "30"

    ohlc_data = get_ohlc(coin_id, days)
    volume_data = get_market_chart(coin_id, days)

    if isinstance(ohlc_data, list) and len(ohlc_data) > 0:
        df = pd.DataFrame(ohlc_data, columns=["timestamp", "open", "high", "low", "close"])
        df["time"] = pd.to_datetime(df["timestamp"], unit="ms")

        has_volume = False
        if "total_volumes" in volume_data:
            vol_df = pd.DataFrame(volume_data["total_volumes"], columns=["timestamp", "volume"])
            vol_df["time"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
            df = df.sort_values("time")
            vol_df = vol_df.sort_values("time")
            df = pd.merge_asof(df, vol_df, on="time", direction="nearest")
            has_volume = True

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            vertical_spacing=0.03, row_heights=[0.72, 0.28])

        fig.add_trace(go.Candlestick(
            x=df["time"],
            open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            increasing_line_color="#00c853",
            decreasing_line_color="#ff5252",
            increasing_fillcolor="#00c853",
            decreasing_fillcolor="#ff5252",
            name="Price"
        ), row=1, col=1)

        fig.add_hline(y=high, line_dash="dot", line_color="rgba(0,200,83,0.6)", 
                      annotation_text="24h High", annotation_position="top left", row=1, col=1)
        fig.add_hline(y=low, line_dash="dot", line_color="rgba(255,82,82,0.6)", 
                      annotation_text="24h Low", annotation_position="bottom left", row=1, col=1)

        if has_volume:
            colors = ["#00c853" if row["close"] >= row["open"] else "#ff5252" for _, row in df.iterrows()]
            fig.add_trace(go.Bar(
                x=df["time"], y=df["volume"],
                marker_color=colors, opacity=0.65, name="Volume"
            ), row=2, col=1)

        fig.update_layout(
            height=580,
            template="plotly_white",
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis_rangeslider_visible=False,
            showlegend=False,
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)
        if days == "1":
            st.caption("30-minute candlesticks • Dotted lines = 24h High / Low")
    else:
        st.info("Chart temporarily unavailable.")
else:
    st.warning("Loading coin data...")
