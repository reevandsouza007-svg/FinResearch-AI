# FinResearch AI — Advanced

A multi-tab Streamlit financial research prototype with market charts, financial statements, news screening, a simplified DCF model, risk heuristics, company comparison, and CSV exports.

## Deploy to Streamlit Community Cloud
1. Upload `app.py`, `requirements.txt`, and `README.md` to your GitHub repository root.
2. In Streamlit Community Cloud, choose the repository and branch `main`.
3. Set **Main file path** to `app.py`.
4. Deploy.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Included modules
- Market overview and interactive price chart
- Auto-refresh and manual refresh
- Company information and available financial statements
- News list with simple keyword-based sentiment labels
- Simplified, assumption-driven five-year DCF scenario calculator
- Rule-based risk flags and rough historical volatility/drawdown
- Peer comparison and CSV exports

## Data and calculation caveats
- Market data and company information come from Yahoo Finance through `yfinance`; availability and update frequency vary by symbol and interval.
- Dashboard refresh does not guarantee a new quote. This is **not a guaranteed real-time NSE feed**.
- Financial statement line items may be missing or named differently across companies.
- News sentiment uses simple keyword rules; it is not an AI model.
- DCF results are illustrative and sensitive to assumptions, input units, cash-flow sign conventions, and provider data quality.
- This is an educational research prototype, not investment advice. Verify information with official company filings and authorized market-data providers.
