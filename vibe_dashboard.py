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
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ===== FUN + SLEEK CRYPTO AESTHETIC =====
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
        background: rgba(22, 26, 30, 0.7);
        border: 1px solid rgba(0, 255, 159, 0.15);
        border-radius: 16px;
        padding: 16px;
        backdrop-filter: blur(10px);
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 600;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00ff9f, #00d4ff);
    }
    
    .stSelectbox > div > div {
        background-color: #161a1e;
        border: 1px solid #2a2f36;
        border-radius: 12px;
    }
    
    .stSuccess {
        background: rgba(0, 255, 159, 0.1);
        border: 1px solid rgba(0, 255, 159, 0.3);
        border-radius: 12px;
    }
    
    .stError {
        background: rgba(239, 83, 80, 0.1);
        border: 1px solid rgba(239, 83, 80, 0.3);
        border-radius: 12px;
    }
    
    .stInfo {
        background: rgba(88, 166, 255, 0.1);
        border: 1px solid rgba(88, 166, 255, 0.3);
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚀 Pre-Bart Vibe Dashboard")
st.markdown("##### Live crypto vibes + meme feedback")
st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

st.divider()

COINS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Avalanche": "avalanche-2",
    "Dogecoin": "dogecoin",
}

TICKERS = {
    "Bitcoin": "BTC",
    "Ethereum": "ETH",
    "Solana": "SOL",
    "Avalanche": "AVAX",
    "Dogecoin": "DOGE",
}

col_a, col_b = st.columns([2, 1])
with col_a:
    selected = st.selectbox("Select Coin", list(COINS.keys()), index=3)
with col_b:
    timeframe = st.selectbox("Timeframe", ["Last 1 Day (30 min)", "Last 7 Days", "Last 30 Days"])

coin_id = COINS[selected]
ticker = TICKERS[selected]

@st.cache_data(ttl=30)
def get_coin_data(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    return res.json()

@st.cache_data(ttl=60)
def get_market_chart(coin_id, days="1"):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    res = requests.get(url, headers=HEADERS, params=params, timeout=10)
    return res.json()

@st.cache_data(ttl=60)
def get_ohlc(coin_id, days="1"):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": days}
    res = requests.get(url, headers=HEADERS, params=params, timeout=10)
    return res.json()

try:
    data = get_coin_data(coin_id)

    if "market_data" not in data:
        st.warning("Temporary issue with data. Retrying shortly...")
        st.stop()

    market = data["market_data"]

    price = market["current_price"]["usd"]
    change_24h = market.get("price_change_percentage_24h") or 0
    change_1h = market.get("price_change_percentage_1h_in_currency", {}).get("usd") or 0
    high = market["high_24h"]["usd"]
    low = market["low_24h"]["usd"]
    volume = market["total_volume"]["usd"]
    market_cap = market["market_cap"]["usd"]

    if high != low:
        range_position = ((price - low) / (high - low)) * 100
    else:
        range_position = 50

    # Dynamic scoring
    if range_position > 85 and change_1h > 0.8:
        score, meme = 95, "🔥 PRE-BART INCOMING! Price pushing highs with strong momentum."
    elif range_position > 75 and change_1h > 0.3:
        score, meme = 85, "🚀 Holding near the highs. Continuation looking likely."
    elif range_position > 65 and change_1h > -0.3:
        score, meme = 75, "📈 Strong position in the daily range. Still constructive."
    elif range_position > 55:
        score, meme = 65, "📊 Above the middle of the range. Mildly bullish."
    elif range_position > 40 and change_1h > -0.5:
        score, meme = 50, "😐 Mid-range chop. Waiting for direction."
    elif range_position > 30:
        score, meme = 40, "⚠️ Losing strength. Sliding toward support."
    elif range_position > 15 and change_1h < 0:
        score, meme = 28, "🐻 Near the lows of the day. Short-term bearish."
    elif range_position <= 15:
        score, meme = 15, "💀 Sitting on the lows. Full Bart dump pressure."
    else:
        score, meme = 45, "😐 Mixed signals right now."

    if change_24h > 6 and score < 90:
        score = min(score + 5, 95)
    elif change_24h < -4 and score > 20:
        score = max(score - 8, 10)

    price_text = f"${price:,.4f}" if price < 10 else f"${price:,.2f}"
    st.metric(f"{selected}", price_text, f"{change_24h:+.2f}% (24h)  |  {change_1h:+.2f}% (1h)")

    c1, c2, c3 = st.columns(3)
    c1.metric("24h Volume", f"${volume/1_000_000:,.1f}M")
    c2.metric("Market Cap", f"${market_cap/1_000_000_000:,.2f}B")
    c3.metric("Range Position", f"{range_position:.0f}% of today's range")

    st.progress(score / 100, text=f"Vibe Score: {score}/100")

    if score >= 80:
        st.success(meme)
    elif score <= 30:
        st.error(meme)
    else:
        st.info(meme)

    # X Links
    st.divider()
    st.subheader(f"🐦 Latest on X • ${ticker}")

    st.markdown(f"""
    <div style="display:flex; flex-wrap:wrap; gap:10px; margin-bottom: 12px;">
        <a href="https://x.com/search?q=%24{ticker}&src=typed_query&f=live" target="_blank" 
           style="background:linear-gradient(90deg, #1da1f2, #0d8ecf); color:white; padding:9px 18px; border-radius:25px; text-decoration:none; font-weight:600; box-shadow: 0 4px 15px rgba(29,161,242,0.3);">
            ${ticker} Live
        </a>
        <a href="https://x.com/search?q={quote(selected + ' crypto')}&src=typed_query&f=live" target="_blank" 
           style="background:linear-gradient(90deg, #1da1f2, #0d8ecf); color:white; padding:9px 18px; border-radius:25px; text-decoration:none; font-weight:600; box-shadow: 0 4px 15px rgba(29,161,242,0.3);">
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
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            increasing_line_color="#00ff9f",
            decreasing_line_color="#ff4d6d",
            increasing_fillcolor="#00ff9f",
            decreasing_fillcolor="#ff4d6d",
            name="Price"
        ), row=1, col=1)

        if has_volume:
            colors = ["#00ff9f" if row["close"] >= row["open"] else "#ff4d6d" for _, row in df.iterrows()]
            fig.add_trace(go.Bar(
                x=df["time"],
                y=df["volume"],
                marker_color=colors,
                opacity=0.65,
                name="Volume"
            ), row=2, col=1)

        fig.update_layout(
            height=580,
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_rangeslider_visible=False,
            showlegend=False,
            hovermode="x unified"
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")

        st.plotly_chart(fig, use_container_width=True)
        
        if days == "1":
            st.caption("30-minute candlesticks")
    else:
        st.info("Chart temporarily unavailable.")

except Exception as e:
    st.warning("Temporary issue. The app will retry shortly.")
