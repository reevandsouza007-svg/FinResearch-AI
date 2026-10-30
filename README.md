# FinResearch AI

A Streamlit financial-research prototype for viewing available NSE stock-price history.

## Features
- Search by NSE ticker (examples: `RELIANCE`, `TCS`, `INFY`, `HDFCBANK`)
- Select a chart period and data interval
- Automatic dashboard reruns and manual refresh
- Interactive Plotly price chart
- Displays the latest returned bar timestamp and app retrieval time
- Clear notice about free-data limitations

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud
1. Upload `app.py`, `requirements.txt`, and `README.md` to a GitHub repository.
2. In Streamlit Community Cloud, create an app from that repository.
3. Set the main file path to `app.py`.

## Data limitations
This prototype uses Yahoo Finance through `yfinance`. Availability and update frequency can vary, and data is **not guaranteed to be real-time**. Refreshing the dashboard does not guarantee that the provider has supplied a newer price. For production/live trading use, use a provider that explicitly offers real-time NSE data and comply with its terms. This app is for research/education, not investment advice.
