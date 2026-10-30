import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="FinResearch AI | Advanced", page_icon="📊", layout="wide")

# ---------- Styling ----------
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
div[data-testid="stMetric"] {background: rgba(120,120,140,.10); padding: 14px 16px; border-radius: 12px; border: 1px solid rgba(120,120,140,.18);}
.small-muted {font-size: .86rem; color: #9ca3af;}
</style>
""", unsafe_allow_html=True)

st.title("📊 FinResearch AI")
st.caption("Advanced company research • Financial statements • News intelligence • Valuation • Risk analysis")
st.info("Data transparency: this app uses Yahoo Finance through yfinance. It is an independent research prototype, not a guaranteed real-time exchange feed. Verify data and assumptions before making investment decisions.")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("🔎 Research Controls")
    ticker_input = st.text_input("NSE ticker", value="RELIANCE", help="Examples: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC").strip().upper()
    ticker_symbol = ticker_input if "." in ticker_input else f"{ticker_input}.NS"
    chart_period = st.selectbox("Historical period", ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)
    interval_label = st.selectbox("Chart interval", ["5 minutes (recent data)", "15 minutes (recent data)", "30 minutes (recent data)", "1 hour", "1 day"], index=3)
    interval_map = {
        "5 minutes (recent data)": ("5m", "5d"),
        "15 minutes (recent data)": ("15m", "1mo"),
        "30 minutes (recent data)": ("30m", "1mo"),
        "1 hour": ("1h", "730d"),
        "1 day": ("1d", chart_period),
    }
    interval, allowed_period = interval_map[interval_label]
    refresh_seconds = st.selectbox("Auto-refresh dashboard", [30, 60, 120, 300], index=1)
    auto_refresh = st.checkbox("Enable automatic refresh", value=True)
    refresh_now = st.button("🔄 Refresh data now", use_container_width=True)
    st.divider()
    st.caption("Tip: use daily data for longer historical analysis and intraday intervals for recent market activity.")

if auto_refresh:
    st_autorefresh(interval=refresh_seconds * 1000, key="finresearch_auto_refresh")
if refresh_now:
    st.cache_data.clear()
    st.rerun()

# ---------- Data layer ----------
@st.cache_data(ttl=45, show_spinner=False)
def fetch_market_history(symbol, period, interval):
    return yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False, actions=False)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_company_bundle(symbol):
    obj = yf.Ticker(symbol)
    info = {}
    try:
        info = obj.get_info() or {}
    except Exception:
        pass
    statements = {}
    for key, getter in [
        ("Income Statement", lambda: obj.financials),
        ("Balance Sheet", lambda: obj.balance_sheet),
        ("Cash Flow", lambda: obj.cashflow),
    ]:
        try:
            statements[key] = getter()
        except Exception:
            statements[key] = pd.DataFrame()
    try:
        news = obj.news or []
    except Exception:
        news = []
    try:
        recommendations = obj.recommendations
    except Exception:
        recommendations = pd.DataFrame()
    return info, statements, news, recommendations

def fmt_money(value, currency="INR"):
    if value is None or pd.isna(value):
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1e12:
        return f"{sign}₹{v/1e12:.2f}T"
    if v >= 1e9:
        return f"{sign}₹{v/1e7:,.0f} Cr"
    if v >= 1e7:
        return f"{sign}₹{v/1e7:,.2f} Cr"
    return f"{sign}₹{v:,.2f}"

def first_number(frame, candidates):
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    for label in candidates:
        if label in frame.index:
            row = frame.loc[label]
            if isinstance(row, pd.Series):
                vals = row.dropna()
                if len(vals):
                    return float(vals.iloc[0])
    return None

def sentiment_label(text):
    t = (text or "").lower()
    positive = ["growth", "profit rises", "profit up", "beats", "record high", "upgrade", "strong demand", "surge", "wins", "expansion", "positive", "buy rating"]
    negative = ["loss", "profit falls", "profit down", "misses", "downgrade", "probe", "fraud", "debt concern", "weak demand", "decline", "lawsuit", "negative", "sell rating", "cuts outlook"]
    p = sum(word in t for word in positive)
    n = sum(word in t for word in negative)
    if p > n:
        return "Positive"
    if n > p:
        return "Negative"
    return "Neutral"

def to_display_frame(frame):
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()
    out = frame.copy()
    try:
        out.columns = [pd.to_datetime(c).strftime("%d %b %Y") for c in out.columns]
    except Exception:
        pass
    return out

# ---------- Fetch current ticker data ----------
if not ticker_input:
    st.warning("Enter a ticker symbol in the sidebar.")
    st.stop()

try:
    history = fetch_market_history(ticker_symbol, allowed_period, interval)
except Exception as e:
    st.error(f"Could not retrieve price history: {e}")
    st.stop()

if history is None or history.empty or "Close" not in history:
    st.error("No market data was returned for this ticker/interval. Try a common NSE ticker or select a different interval.")
    st.stop()

history = history.dropna(subset=["Close"]).copy()
if history.empty:
    st.error("The data provider returned no valid closing prices.")
    st.stop()

try:
    info, statements, news_items, recommendations = fetch_company_bundle(ticker_symbol)
except Exception:
    info, statements, news_items, recommendations = {}, {}, [], pd.DataFrame()

latest_price = float(history["Close"].iloc[-1])
previous_bar = float(history["Close"].iloc[-2]) if len(history) > 1 else np.nan
bar_change = latest_price - previous_bar if pd.notna(previous_bar) else np.nan
bar_pct = (bar_change / previous_bar * 100) if pd.notna(previous_bar) and previous_bar != 0 else np.nan
market_time = history.index[-1]
retrieved_time = datetime.now().astimezone()
currency = info.get("currency", "INR")
company_name = info.get("longName") or info.get("shortName") or ticker_symbol
sector = info.get("sector", "Not available")
industry = info.get("industry", "Not available")

# ---------- Header and key metrics ----------
st.subheader(f"{company_name}  ·  {ticker_symbol}")
st.caption(f"Sector: {sector} | Industry: {industry} | Exchange data timestamp: {market_time}")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Latest returned price", f"{currency} {latest_price:,.2f}", f"{bar_change:+.2f} ({bar_pct:+.2f}%)" if pd.notna(bar_pct) else None)
m2.metric("Market cap", fmt_money(info.get("marketCap")))
m3.metric("P/E ratio", f"{info.get('trailingPE'):.2f}" if isinstance(info.get("trailingPE"), (int, float)) and pd.notna(info.get("trailingPE")) else "N/A")
m4.metric("52-week high", f"{currency} {info.get('fiftyTwoWeekHigh'):,.2f}" if isinstance(info.get("fiftyTwoWeekHigh"), (int, float)) else "N/A")
m5.metric("52-week low", f"{currency} {info.get('fiftyTwoWeekLow'):,.2f}" if isinstance(info.get("fiftyTwoWeekLow"), (int, float)) else "N/A")
st.caption(f"App retrieved data at {retrieved_time.strftime('%d %b %Y, %I:%M:%S %p %Z')} · Auto-refresh: {'ON' if auto_refresh else 'OFF'} every {refresh_seconds}s")
st.warning("The dashboard refreshes the request, not the exchange. Yahoo Finance data may be delayed, incomplete, or unavailable. The percentage above compares the latest two returned bars, not necessarily today's official change.")

# ---------- Tabs ----------
tabs = st.tabs(["📈 Market", "🏢 Financials", "📰 News Intelligence", "💎 Valuation Lab", "⚠️ Risk Scanner", "🆚 Compare", "📄 Export"])

with tabs[0]:
    left, right = st.columns([2.2, 1])
    with left:
        st.markdown("#### Price history")
        chart = go.Figure()
        chart.add_trace(go.Scatter(x=history.index, y=history["Close"], mode="lines", name="Close"))
        if interval == "1d" and len(history) >= 20:
            ma20 = history["Close"].rolling(20).mean()
            chart.add_trace(go.Scatter(x=history.index, y=ma20, mode="lines", name="20-day average"))
        chart.update_layout(template="plotly_dark", height=430, xaxis_title="Time", yaxis_title=f"Price ({currency})", hovermode="x unified")
        st.plotly_chart(chart, use_container_width=True)
    with right:
        st.markdown("#### Price & volume")
        vol_col = "Volume" if "Volume" in history else None
        if vol_col:
            v = history["Volume"].tail(30)
            st.bar_chart(v, height=200)
        st.write("**Available data points:**", f"{len(history):,}")
        st.write("**Latest bar:**", str(market_time))
        st.write("**52-week range:**", f"{info.get('fiftyTwoWeekLow', 'N/A')} – {info.get('fiftyTwoWeekHigh', 'N/A')}")
        st.write("**Beta:**", info.get("beta", "N/A"))
        st.write("**Dividend yield:**", f"{info.get('dividendYield')*100:.2f}%" if isinstance(info.get("dividendYield"), (int, float)) and pd.notna(info.get("dividendYield")) else "N/A")
    st.markdown("#### Latest market bars")
    show_cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in history.columns]
    st.dataframe(history[show_cols].tail(25), use_container_width=True)

with tabs[1]:
    st.markdown("#### Financial statement explorer")
    statement_choice = st.selectbox("Select statement", ["Income Statement", "Balance Sheet", "Cash Flow"], key="statement_choice")
    statement = statements.get(statement_choice, pd.DataFrame())
    display_statement = to_display_frame(statement)
    if display_statement.empty:
        st.info("Financial statements are not available from the current data source for this ticker.")
    else:
        st.dataframe(display_statement, use_container_width=True)
        st.download_button("Download statement as CSV", display_statement.to_csv().encode("utf-8"), file_name=f"{ticker_input}_{statement_choice.lower().replace(' ', '_')}.csv", mime="text/csv")
    income = statements.get("Income Statement", pd.DataFrame())
    balance = statements.get("Balance Sheet", pd.DataFrame())
    cashflow = statements.get("Cash Flow", pd.DataFrame())
    revenue = first_number(income, ["Total Revenue", "Operating Revenue", "Revenue"])
    net_income = first_number(income, ["Net Income", "Net Income Common Stockholders"])
    total_debt = first_number(balance, ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt"])
    total_equity = first_number(balance, ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"])
    operating_cf = first_number(cashflow, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
    capex = first_number(cashflow, ["Capital Expenditure", "Capital Expenditures"])
    st.markdown("#### Snapshot ratios & indicators")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Latest annual revenue", fmt_money(revenue))
    r2.metric("Latest annual net income", fmt_money(net_income))
    r3.metric("Total debt", fmt_money(total_debt))
    r4.metric("Operating cash flow", fmt_money(operating_cf))
    if revenue and net_income is not None and revenue != 0:
        st.write(f"**Net profit margin (approx.):** {net_income/revenue*100:.2f}%")
    if total_debt is not None and total_equity not in (None, 0):
        st.write(f"**Debt-to-equity (approx.):** {total_debt/total_equity:.2f}x")
    if operating_cf is not None and capex is not None:
        st.write(f"**Free cash flow proxy:** {fmt_money(operating_cf + capex)} (provider sign convention may vary)")
    st.caption("Provider line-item names and coverage vary. Ratios are approximate and should be verified against official filings.")

with tabs[2]:
    st.markdown("#### Company news")
    if not news_items:
        st.info("No news was returned by the current source. News availability varies by ticker.")
    else:
        rows = []
        for item in news_items[:30]:
            content = item.get("content", item) if isinstance(item, dict) else {}
            title = content.get("title", "Untitled")
            summary = content.get("summary", "")
            publisher = content.get("publisher", {})
            if isinstance(publisher, dict):
                publisher = publisher.get("displayName", "Source not supplied")
            canonical = content.get("canonicalUrl", {})
            if isinstance(canonical, dict):
                link = canonical.get("url", "")
            else:
                link = canonical or content.get("link", "")
            pub_date = content.get("pubDate") or content.get("providerPublishTime") or ""
            label = sentiment_label(f"{title} {summary}")
            rows.append({"Headline": title, "Publisher": publisher, "Published": pub_date, "Rule-based label": label, "Summary": summary, "URL": link})
        news_df = pd.DataFrame(rows)
        filter_sentiment = st.multiselect("Filter by headline sentiment (keyword-based)", ["Positive", "Neutral", "Negative"], default=["Positive", "Neutral", "Negative"])
        filtered = news_df[news_df["Rule-based label"].isin(filter_sentiment)]
        for _, row in filtered.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['Headline']}**")
                st.caption(f"{row['Publisher']} · {row['Published']} · Keyword label: {row['Rule-based label']}")
                if row["Summary"]:
                    st.write(row["Summary"])
                if row["URL"]:
                    st.markdown(f"[Read source article]({row['URL']})")
        st.caption("Sentiment labels are simple keyword-based screening, not an AI model or a verified assessment of market impact.")

with tabs[3]:
    st.markdown("#### Discounted cash flow (DCF) scenario model")
    st.caption("A simplified educational model. Review all assumptions; it is not a price target or investment recommendation.")
    cashflow = statements.get("Cash Flow", pd.DataFrame())
    fcf = None
    ocf = first_number(cashflow, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
    capex = first_number(cashflow, ["Capital Expenditure", "Capital Expenditures"])
    if ocf is not None and capex is not None:
        fcf = ocf + capex
    with st.form("dcf_form"):
        d1, d2, d3 = st.columns(3)
        with d1:
            base_fcf = st.number_input("Base-year free cash flow (₹; use same currency units as provider)", value=float(fcf or 0.0), step=100000000.0, format="%.2f")
            growth = st.slider("Annual FCF growth assumption", min_value=-20.0, max_value=30.0, value=8.0, step=0.5) / 100
        with d2:
            discount_rate = st.slider("Discount rate / WACC", min_value=4.0, max_value=25.0, value=12.0, step=0.5) / 100
            terminal_growth = st.slider("Terminal growth", min_value=0.0, max_value=6.0, value=3.0, step=0.5) / 100
        with d3:
            cash = st.number_input("Cash & equivalents (₹; optional)", min_value=0.0, value=float(info.get("totalCash") or 0.0), step=100000000.0, format="%.2f")
            debt = st.number_input("Total debt (₹; optional)", min_value=0.0, value=float(info.get("totalDebt") or 0.0), step=100000000.0, format="%.2f")
        submitted = st.form_submit_button("Calculate DCF")
    if submitted:
        shares = info.get("sharesOutstanding")
        if base_fcf <= 0:
            st.error("Enter a positive base-year free cash flow for this simplified DCF model.")
        elif discount_rate <= terminal_growth:
            st.error("Discount rate must be greater than terminal growth.")
        elif not shares:
            st.error("Share count is unavailable, so per-share value cannot be calculated.")
        else:
            projected = [base_fcf * ((1 + growth) ** year) for year in range(1, 6)]
            pv_explicit = sum(cf / ((1 + discount_rate) ** year) for year, cf in enumerate(projected, start=1))
            terminal_value = projected[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
            pv_terminal = terminal_value / ((1 + discount_rate) ** 5)
            equity_value = pv_explicit + pv_terminal + cash - debt
            per_share = equity_value / shares
            dcf1, dcf2, dcf3 = st.columns(3)
            dcf1.metric("Illustrative equity value", f"₹{equity_value:,.0f}")
            dcf2.metric("Illustrative value per share", f"₹{per_share:,.2f}")
            dcf3.metric("Latest returned price", f"₹{latest_price:,.2f}")
            st.write("**Projected free cash flows:**", ", ".join(f"₹{v:,.0f}" for v in projected))
            st.write(f"**Implied difference vs latest returned price:** {(per_share/latest_price-1)*100:+.2f}%" if latest_price else "N/A")
            st.warning("DCF outputs are highly sensitive to assumptions and data quality. Confirm units, cash flow sign conventions, share count, and filings before interpreting results.")

with tabs[4]:
    st.markdown("#### Financial & market risk screening")
    flags = []
    pe = info.get("trailingPE")
    debt_equity_info = info.get("debtToEquity")
    current_ratio = info.get("currentRatio")
    profit_margin = info.get("profitMargins")
    beta = info.get("beta")
    if isinstance(pe, (int, float)) and pe > 40:
        flags.append(("Valuation", f"Trailing P/E is relatively high at {pe:.1f}x; compare with peers and growth expectations."))
    if isinstance(debt_equity_info, (int, float)) and debt_equity_info > 150:
        flags.append(("Leverage", f"Provider debt/equity value is elevated ({debt_equity_info:.1f}); verify units and industry context."))
    if isinstance(current_ratio, (int, float)) and current_ratio < 1:
        flags.append(("Liquidity", f"Current ratio is below 1 ({current_ratio:.2f}); inspect near-term obligations and cash flows."))
    if isinstance(profit_margin, (int, float)) and profit_margin < 0:
        flags.append(("Profitability", "Provider reports a negative profit margin; check the latest statements and one-off items."))
    if isinstance(beta, (int, float)) and beta > 1.5:
        flags.append(("Market sensitivity", f"Beta is high ({beta:.2f}); historical market sensitivity may be elevated."))
    close = history["Close"].dropna()
    returns = close.pct_change().dropna()
    if len(returns) >= 10:
        annual_factor = 252 if interval == "1d" else 252 * 6.5 * 60 / (5 if interval == "5m" else 15 if interval == "15m" else 30 if interval == "30m" else 60)
        volatility = float(returns.std() * np.sqrt(annual_factor) * 100)
        max_drawdown = float(((close / close.cummax()) - 1).min() * 100)
        q1, q2 = st.columns(2)
        q1.metric("Annualized volatility (rough)", f"{volatility:.2f}%")
        q2.metric("Max drawdown in selected window", f"{max_drawdown:.2f}%")
    if flags:
        for category, message in flags:
            st.warning(f"**{category}:** {message}")
    else:
        st.success("No rule-based warning flags were triggered from the available summary fields. This does not mean the company is risk-free.")
    st.caption("Rules are simple screening heuristics, not audit findings, fraud detection, or personalized financial advice.")

with tabs[5]:
    st.markdown("#### Compare companies")
    compare_input = st.text_input("Other NSE tickers (comma-separated)", value="TCS,INFY", key="compare_tickers")
    compare_symbols = [x.strip().upper() for x in compare_input.split(",") if x.strip()]
    if st.button("Compare companies"):
        compare_rows = []
        for sym in [ticker_input] + compare_symbols[:5]:
            nsym = sym if "." in sym else f"{sym}.NS"
            try:
                ci = yf.Ticker(nsym).get_info() or {}
                compare_rows.append({
                    "Ticker": sym,
                    "Company": ci.get("longName") or ci.get("shortName") or sym,
                    "Sector": ci.get("sector", "N/A"),
                    "Market cap": ci.get("marketCap"),
                    "P/E": ci.get("trailingPE"),
                    "P/B": ci.get("priceToBook"),
                    "ROE": ci.get("returnOnEquity"),
                    "Profit margin": ci.get("profitMargins"),
                    "Debt/equity": ci.get("debtToEquity"),
                    "52-week change": ci.get("52WeekChange"),
                })
            except Exception:
                compare_rows.append({"Ticker": sym, "Company": "Data unavailable"})
        comp = pd.DataFrame(compare_rows)
        st.dataframe(comp, use_container_width=True)
        st.download_button("Download comparison CSV", comp.to_csv(index=False).encode("utf-8"), file_name="company_comparison.csv", mime="text/csv")

with tabs[6]:
    st.markdown("#### Export research data")
    st.write("Download the currently retrieved price bars for offline analysis.")
    csv_data = history.to_csv().encode("utf-8")
    st.download_button("⬇️ Download price history CSV", csv_data, file_name=f"{ticker_input}_{interval}_price_history.csv", mime="text/csv")
    overview = pd.DataFrame([{
        "Ticker": ticker_input,
        "Company": company_name,
        "Sector": sector,
        "Latest returned price": latest_price,
        "Latest bar timestamp": str(market_time),
        "App retrieval timestamp": retrieved_time.isoformat(),
        "Market cap": info.get("marketCap"),
        "Trailing PE": info.get("trailingPE"),
        "Source": "Yahoo Finance via yfinance",
        "Data caveat": "Not guaranteed real-time; verify with official/authorized sources",
    }])
    st.download_button("⬇️ Download research overview CSV", overview.to_csv(index=False).encode("utf-8"), file_name=f"{ticker_input}_research_overview.csv", mime="text/csv")

st.divider()
st.caption("FinResearch AI Advanced • Educational research tool. Market data and financial fields depend on provider coverage. This app does not provide personalized investment advice.")
