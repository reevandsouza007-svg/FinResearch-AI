import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="FinResearch AI",
    page_icon="📈",
    layout="wide",
)

st.title("📈 FinResearch AI")
st.caption("Financial research prototype • Market data is subject to provider limitations")

with st.sidebar:
    st.header("Company Search")
    symbol = st.text_input(
        "NSE ticker",
        value="RELIANCE",
        help="Examples: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK",
    ).strip().upper()
    period = st.selectbox("Chart period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=1)
    interval_options = {
        "1 minute (availability limited)": "1m",
        "5 minutes": "5m",
        "15 minutes": "15m",
        "Daily": "1d",
    }
    interval_label = st.selectbox("Price-data interval", list(interval_options.keys()), index=1)
    interval = interval_options[interval_label]
    refresh_seconds = st.selectbox("Dashboard refresh", [30, 60, 120, 300], index=1)
    st.caption("Refresh reruns the app. A new market price appears only when the data source supplies one.")
    manual_refresh = st.button("🔄 Refresh now", use_container_width=True)

# Automatic rerun; this does not make the provider's data real-time.
st_autorefresh(interval=refresh_seconds * 1000, key="finresearch_refresh")

if manual_refresh:
    st.cache_data.clear()
    st.rerun()

if not symbol:
    st.info("Enter an NSE ticker in the sidebar.")
    st.stop()

ticker = f"{symbol}.NS"

@st.cache_data(ttl=45, show_spinner=False)
def fetch_history(ticker_symbol: str, selected_period: str, selected_interval: str):
    return yf.Ticker(ticker_symbol).history(
        period=selected_period,
        interval=selected_interval,
        auto_adjust=False,
        actions=False,
    )

try:
    with st.spinner(f"Fetching available data for {ticker}..."):
        history = fetch_history(ticker, period, interval)

    if history is None or history.empty or "Close" not in history:
        st.error(
            "No data was returned. Check the NSE ticker, try a different interval, "
            "or try again later. Free data availability can vary."
        )
        st.stop()

    history = history.dropna(subset=["Close"]).copy()
    if history.empty:
        st.error("No valid closing-price values were returned.")
        st.stop()

    latest_price = float(history["Close"].iloc[-1])
    previous_price = float(history["Close"].iloc[-2]) if len(history) >= 2 else None
    if previous_price and previous_price != 0:
        price_change = latest_price - previous_price
        pct_change = (price_change / previous_price) * 100
        change_label = f"{price_change:+.2f} ({pct_change:+.2f}%)"
    else:
        price_change = None
        change_label = None

    latest_market_timestamp = history.index[-1]
    retrieval_time = datetime.now().astimezone()

    c1, c2, c3 = st.columns(3)
    c1.metric("Latest available close / bar price", f"₹{latest_price:,.2f}", change_label)
    c2.metric("Data points loaded", f"{len(history):,}")
    c3.metric("Last bar timestamp", str(latest_market_timestamp))

    st.caption(f"App retrieved data at: {retrieval_time.strftime('%d %b %Y, %I:%M:%S %p %Z')}")
    st.warning(
        "Data notice: this prototype uses Yahoo Finance data through yfinance. "
        "It is not a guaranteed real-time NSE feed; quotes may be delayed, incomplete, "
        "or unavailable. The dashboard refresh interval only refreshes the request. "
        "The price-change metric compares the latest two returned bars, not necessarily "
        "today's change. Do not use this prototype alone to make trading decisions."
    )

    st.subheader(f"{symbol} price chart")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history.index,
            y=history["Close"],
            mode="lines",
            name="Price",
            line=dict(width=2),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=430,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Time",
        yaxis_title="Price (₹)",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Latest returned data")
    display_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in history.columns]
    st.dataframe(history[display_cols].tail(20), use_container_width=True)

    st.subheader("Quick research notes")
    st.write(
        "- This version focuses on fetching and displaying market data.\n"
        "- Financial statements, news analysis, valuation, and AI-generated research "
        "will be added in later versions.\n"
        "- For robust live quotes, connect a provider that explicitly supports real-time "
        "NSE data and follow its licensing and API terms."
    )

except Exception as exc:
    st.error("Could not fetch market data.")
    st.code(str(exc))
    st.info("Try another ticker or interval, wait a little, and refresh.")
