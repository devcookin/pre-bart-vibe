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

# ===== AESTHETICS =====
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(180deg, #0b0e11 0%, #0f1218 100%);
        font-family: 'Inter', sans-serif;
    }
    
    h1 {
        background: linear-gradient(90deg, #00ff9f, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
    }
    
    .stMetric {
        background: rgba(22, 26, 30, 0.75);
        border: 1px solid rgba(0, 255, 159, 0.12);
        border-radius: 14px;
        padding: 12px 16px;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        font-weight: 600;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00ff9f, #00d4ff);
    }
</style>
""", unsafe_allow_html=True)

st.title("🚀 Pre-Bart Vibe Dashboard")
st.markdown("##### Live crypto vibes + meme feedback")
st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

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

def calc_vibe(price, high, low, change_1h, change_24h):
    if high != low:
        range_pos = ((price - low) / (high - low)) * 100
    else:
        range_pos = 50

    # Stricter thresholds
    if range_pos > 90 and change_1h > 1.2:
        score, meme = 95, "🔥 PRE-BART INCOMING! Extreme strength."
    elif range_pos > 82 and change_1h > 0.7:
        score, meme = 85, "🚀 Very strong. Holding near highs."
    elif range_pos > 72 and change_1h > 0.2:
        score, meme = 72, "📈 Solid position, still constructive."
    elif range_pos > 60 and change_1h > -0.3:
        score, meme = 58, "📊 Above mid-range but momentum cooling."
    elif range_pos > 45:
        score, meme = 48, "😐 Mid-range chop. No clear edge."
    elif range_pos > 32 and change_1h < 0:
        score, meme = 35, "⚠️ Losing the mid. Short-term weakness."
    elif range_pos > 18:
        score, meme = 25, "🐻 Sliding toward the lows."
    elif range_pos <= 18:
        score, meme = 12, "💀 Sitting on the lows. Bearish pressure."
    else:
        score, meme = 42, "😐 Mixed signals."

    # Smaller bullish boost + stronger bearish penalty
    if change_24h > 8 and score >= 70:
        score = min(score + 3, 95)
    elif change_24h < -3:
        score = max(score - 10, 8)
    elif change_1h < -1.5:
        score = max(score - 7, 10)

    return score, meme, range_pos

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

# ========== MULTI-COIN VIBE OVERVIEW ==========
st.subheader("🌐 Multi-Coin Vibe Overview")

markets = get_markets()
coin_map = {c["id"]: c for c in markets} if markets else {}

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
            score, meme, _ = calc_vibe(price, high, low, ch1, ch24)
            
            st.markdown(f"**{tick}**")
            st.metric(label="", value=f"${price:,.4f}" if price < 10 else f"${price:,.2f}",
                      delta=f"{ch24:+.2f}%")
            st.progress(score / 100, text=f"Vibe {score}")
            st.caption(meme)
        else:
            st.info(f"{tick}\nLoading...")

st.divider()

# ========== DETAILED VIEW ==========
st.subheader("🎯 Detailed View")

col_a, col_b = st.columns([2, 1])
with col_a:
    selected = st.selectbox("Select Coin", [x[0] for x in COIN_ORDER], index=3)
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

    score, meme, range_pos = calc_vibe(price, high, low, change_1h, change_24h)

    price_text = f"${price:,.4f}" if price < 10 else f"${price:,.2f}"
    st.metric(f"{selected}", price_text, f"{change_24h:+.2f}% (24h)  |  {change_1h:+.2f}% (1h)")

    c1, c2, c3 = st.columns(3)
    c1.metric("24h Volume", f"${volume/1_000_000:,.1f}M")
    c2.metric("Market Cap", f"${market_cap/1_000_000_000:,.2f}B")
    c3.metric("Range Position", f"{range_pos:.0f}% of today's range")

    st.progress(score / 100, text=f"Vibe Score: {score}/100")

    if score >= 80:
        st.success(meme)
    elif score <= 30:
        st.error(meme)
    else:
        st.info(meme)

    # X Links
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
            increasing_line_color="#00ff9f",
            decreasing_line_color="#ff4d6d",
            increasing_fillcolor="#00ff9f",
            decreasing_fillcolor="#ff4d6d",
            name="Price"
        ), row=1, col=1)

        # Key Levels
        fig.add_hline(y=high, line_dash="dot", line_color="rgba(0,255,159,0.6)", 
                      annotation_text="24h High", annotation_position="top left", row=1, col=1)
        fig.add_hline(y=low, line_dash="dot", line_color="rgba(255,77,109,0.6)", 
                      annotation_text="24h Low", annotation_position="bottom left", row=1, col=1)

        if has_volume:
            colors = ["#00ff9f" if row["close"] >= row["open"] else "#ff4d6d" for _, row in df.iterrows()]
            fig.add_trace(go.Bar(
                x=df["time"], y=df["volume"],
                marker_color=colors, opacity=0.65, name="Volume"
            ), row=2, col=1)

        fig.update_layout(
            height=580,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis_rangeslider_visible=False,
            showlegend=False,
            hovermode="x unified"
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")

        st.plotly_chart(fig, use_container_width=True)
        if days == "1":
            st.caption("30-minute candlesticks • Dotted lines = 24h High / Low")
    else:
        st.info("Chart temporarily unavailable.")
else:
    st.warning("Loading coin data...")
