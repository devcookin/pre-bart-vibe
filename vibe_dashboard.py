import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Pre-Bart Vibe Dashboard",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for a cleaner dark look
st.markdown("""
<style>
    .stApp {
        background-color: #0b0e11;
    }
    .stMetric {
        background-color: #161a1e;
        padding: 12px;
        border-radius: 10px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚀 Pre-Bart Vibe Dashboard")
st.markdown("##### Live crypto vibes + meme feedback")
st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

st.divider()

COINS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Avalanche": "avalanche-2",
    "Dogecoin": "dogecoin",
}

col_a, col_b = st.columns([2, 1])
with col_a:
    selected = st.selectbox("Select Coin", list(COINS.keys()), index=3)
with col_b:
    timeframe = st.selectbox("Timeframe", ["Last 1 Day (~5 min)", "Last 7 Days", "Last 30 Days"])

coin_id = COINS[selected]

if st.button("⚡ Get Live Vibe", use_container_width=True, type="primary"):
    with st.spinner("Loading market data..."):
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            res = requests.get(url, timeout=12)
            data = res.json()
            market = data["market_data"]

            price = market["current_price"]["usd"]
            change = market.get("price_change_percentage_24h") or 0
            high = market["high_24h"]["usd"]
            low = market["low_24h"]["usd"]
            volume = market["total_volume"]["usd"]
            market_cap = market["market_cap"]["usd"]

            # Vibe logic
            if change > 8:
                score, meme, color = 95, "🔥 PRE-BART INCOMING! Vertical pump detected.", "green"
            elif change > 4:
                score, meme, color = 80, "🚀 Strong upward vibes. Looking spicy.", "green"
            elif change > 1.5:
                score, meme, color = 65, "📈 Mild bullish vibes. Quietly heating up.", "blue"
            elif change > -1.5:
                score, meme, color = 45, "😐 Sideways vibes. Waiting for a catalyst.", "gray"
            elif change > -5:
                score, meme, color = 30, "🐻 Mild bearish pressure.", "orange"
            else:
                score, meme, color = 15, "💀 Full Bart dump energy.", "red"

            # Price display
            price_text = f"${price:,.4f}" if price < 10 else f"${price:,.2f}"
            st.metric(f"{selected}", price_text, f"{change:+.2f}% (24h)")

            c1, c2, c3 = st.columns(3)
            c1.metric("24h Volume", f"${volume/1_000_000:,.1f}M")
            c2.metric("Market Cap", f"${market_cap/1_000_000_000:,.2f}B")
            c3.metric("24h Range", f"${low:,.2f} – ${high:,.2f}")

            st.progress(score / 100, text=f"Vibe Score: {score}/100")
            
            if color == "green":
                st.success(meme)
            elif color == "red":
                st.error(meme)
            else:
                st.info(meme)

            st.divider()
            st.subheader(f"{selected} • {timeframe}")

            if timeframe == "Last 1 Day (~5 min)":
                chart_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                params = {"vs_currency": "usd", "days": "1"}
                chart_res = requests.get(chart_url, params=params, timeout=12)
                chart_data = chart_res.json()

                if "prices" in chart_data and "total_volumes" in chart_data:
                    prices = chart_data["prices"]
                    volumes = chart_data["total_volumes"]

                    df = pd.DataFrame(prices, columns=["timestamp", "price"])
                    df["volume"] = [v[1] for v in volumes]
                    df["time"] = pd.to_datetime(df["timestamp"], unit="ms")

                    price_min = df["price"].min()
                    price_max = df["price"].max()
                    padding = (price_max - price_min) * 0.12
                    y_min = price_min - padding
                    y_max = price_max + padding

                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                        vertical_spacing=0.02, row_heights=[0.75, 0.25])

                    fig.add_trace(go.Scatter(
                        x=df["time"], y=df["price"],
                        mode="lines", line=dict(color="#00ff9f", width=2.2),
                        fill="tozeroy", fillcolor="rgba(0,255,159,0.08)",
                        name="Price"
                    ), row=1, col=1)

                    fig.add_trace(go.Bar(
                        x=df["time"], y=df["volume"],
                        marker_color="rgba(88, 166, 255, 0.5)", name="Volume"
                    ), row=2, col=1)

                    fig.update_layout(
                        height=560,
                        template="plotly_dark",
                        paper_bgcolor="#0b0e11",
                        plot_bgcolor="#0b0e11",
                        margin=dict(l=0, r=0, t=10, b=0),
                        showlegend=False,
                        hovermode="x unified"
                    )
                    fig.update_yaxes(range=[y_min, y_max], row=1, col=1)
                    fig.update_xaxes(showgrid=True, gridcolor="#1c2128", zeroline=False)
                    fig.update_yaxes(showgrid=True, gridcolor="#1c2128", zeroline=False)

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Chart data temporarily unavailable.")

            else:
                days = "7" if "7" in timeframe else "30"
                ohlc_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
                params = {"vs_currency": "usd", "days": days}
                ohlc_res = requests.get(ohlc_url, params=params, timeout=12)
                ohlc_data = ohlc_res.json()

                if isinstance(ohlc_data, list) and len(ohlc_data) > 0:
                    df = pd.DataFrame(ohlc_data, columns=["timestamp", "open", "high", "low", "close"])
                    df["time"] = pd.to_datetime(df["timestamp"], unit="ms")

                    fig = go.Figure(data=[go.Candlestick(
                        x=df["time"],
                        open=df["open"], high=df["high"],
                        low=df["low"], close=df["close"],
                        increasing_line_color="#26a69a",
                        decreasing_line_color="#ef5350",
                        increasing_fillcolor="#26a69a",
                        decreasing_fillcolor="#ef5350"
                    )])

                    fig.update_layout(
                        height=520,
                        template="plotly_dark",
                        paper_bgcolor="#0b0e11",
                        plot_bgcolor="#0b0e11",
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_rangeslider_visible=False,
                        hovermode="x unified"
                    )
                    fig.update_xaxes(showgrid=True, gridcolor="#1c2128")
                    fig.update_yaxes(showgrid=True, gridcolor="#1c2128")

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Candlestick data temporarily unavailable.")

        except Exception as e:
            st.error("Data temporarily unavailable. Please wait 30–60 seconds and try again.")
else:
    st.info("Select a coin and timeframe, then click **Get Live Vibe**.")