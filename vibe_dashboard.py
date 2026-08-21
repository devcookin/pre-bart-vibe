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
    if not isinstance(ohlc_data, list) or len(ohlc_data) < 4:
        return 0.0

    df = pd.DataFrame(ohlc_data[-8:], columns=["timestamp", "open", "high", "low", "close"])
    quality = 0.0

    for _, row in df.iterrows():
        body = abs(row["close"] - row["open"])
        upper_wick = row["high"] - max(row["open"], row["close"])
        lower_wick = min(row["open"], row["close"]) - row["low"]
        full_range = row["high"] - row["low"]
        if full_range == 0:
            continue

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
        if lows[-1] > lows[-2] > lows[-3]:
            quality += 0.70
        elif lows[-1] > lows[-2]:
            quality += 0.35
        elif lows[-1] < lows[-2] < lows[-3]:
            quality -= 0.45

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
    <div style="
        background: #e0e0e0;
        border-radius: 10px;
        height: {height}px;
        overflow: hidden;
        margin: 6px 0 10px 0;
    ">
        <div style="
            width: {score}%;
            height: 100%;
            background: {color};
            border-radius: 10px;
            transition: width 0.5s ease;
        "></div>
    </div>
    """


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

# ========== DATA PREP ==========
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

# Pre-calculate all scores for cards + leaderboard
vibe_data = []
for name, cid, tick in COIN_ORDER:
    c = coin_map.get(cid)
    if c:
        price = c["current_price"]
        high = c["high_24h"]
        low = c["low_24h"]
        ch1 = c.get("price_change_percentage_1h_in_currency") or 0
        ch24 = c.get("price_change_percentage_24h") or 0
        image_url = c.get("image", "")

        ohlc = get_ohlc(cid, "1")
        candle_quality = analyze_candles(ohlc)

        score, meme, range_pos, reasons = calc_vibe(
            price, high, low, ch1, ch24, fg_value, btc_change, candle_quality
        )

        vibe_data.append({
            "name": name,
            "cid": cid,
            "tick": tick,
            "price": price,
            "ch24": ch24,
            "ch1": ch1,
            "score": score,
            "meme": meme,
            "image_url": image_url,
            "candle_quality": candle_quality,
            "range_pos": range_pos,
            "reasons": reasons
        })

# Sort for leaderboard
vibe_data_sorted = sorted(vibe_data, key=lambda x: x["score"], reverse=True)

# ========== MULTI-COIN OVERVIEW (CARDS) ==========
st.subheader("🌐 Multi-Coin Vibe Overview")
st.caption("Click “View” on any coin to open the detailed view")

cols = st.columns(5)
for i, item in enumerate(vibe_data):
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
                f"<div style='font-size:1.35rem; font-weight:600; height:32px; line-height:32px; overflow:hidden;'>{price_str}</div>",
                unsafe_allow_html=True
            )
            st.caption(f"{item['ch24']:+.2f}% • Vibe {item['score']}")
            
            st.markdown(colored_progress(item["score"], height=10), unsafe_allow_html=True)
            
            st.markdown(
                f"""
                <div style="
                    height: 44px;
                    min-height: 44px;
                    max-height: 44px;
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
                st.rerun()

st.divider()

# ========== VIBE LEADERBOARD ==========
st.subheader("🏆 Vibe Leaderboard")
st.caption("Live ranking by current vibe score")

leaderboard_rows = []
for rank, item in enumerate(vibe_data_sorted, 1):
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
    leaderboard_rows.append({
        "Rank": medal,
        "Coin": item["tick"],
        "Price": f"${item['price']:,.2f}" if item["price"] >= 1 else f"${item['price']:.4f}",
        "24h": f"{item['ch24']:+.2f}%",
        "Vibe": item["score"],
        "Status": item["meme"]
    })

df_leader = pd.DataFrame(leaderboard_rows)
st.dataframe(
    df_leader,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.TextColumn("Rank", width="small"),
        "Coin": st.column_config.TextColumn("Coin", width="small"),
        "Price": st.column_config.TextColumn("Price", width="medium"),
        "24h": st.column_config.TextColumn("24h", width="small"),
        "Vibe": st.column_config.ProgressColumn("Vibe", min_value=0, max_value=100, format="%d"),
        "Status": st.column_config.TextColumn("Status", width="large"),
    }
)

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
    timeframe = st.selectbox("Timeframe", [
        "Last 1 Day (30 min)", 
        "Last 7 Days", 
        "Last 30 Days"
    ])

name_to_id = {x[0]: x[1] for x in COIN_ORDER}
name_to_tick = {x[0]: x[2] for x in COIN_ORDER}
coin_id = name_to_id[selected]
ticker = name_to_tick[selected]

# Find the pre-calculated data for the selected coin
selected_item = next((item for item in vibe_data if item["name"] == selected), None)

if selected_item:
    price = selected_item["price"]
    change_24h = selected_item["ch24"]
    change_1h = selected_item["ch1"]
    score = selected_item["score"]
    meme = selected_item["meme"]
    range_pos = selected_item["range_pos"]
    candle_quality = selected_item["candle_quality"]
    reasons = selected_item["reasons"]

    c = coin_map.get(coin_id)
    volume = c["total_volume"] if c else 0
    market_cap = c["market_cap"] if c else 0
    high = c["high_24h"] if c else price
    low = c["low_24h"] if c else price

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

    st.markdown(f"**Vibe Score: {score}/100**")
    st.markdown(colored_progress(score, height=14), unsafe_allow_html=True)

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
    st.text_area("📋 Share this vibe (select + copy)", share_text, height=70, disabled=True)

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
            st.caption("30-minute candles (best available on free API)")
    else:
        st.info("Chart temporarily unavailable.")
else:
    st.warning("Loading coin data...")
