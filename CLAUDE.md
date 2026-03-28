# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (use venv)
.venv/Scripts/pip install -r requirements.txt

# Run the application
.venv/Scripts/streamlit run app.py
# or
streamlit run app.py
```

There is no test suite, linter, or build step.

## Architecture

A Streamlit dashboard for analyzing B3 (Brazilian Stock Exchange) stocks, built in four layers:

**Data (`data/fetcher.py`)** — Downloads OHLCV data from Yahoo Finance via `yfinance`. Exposes `fetch_all()` (full OHLCV) and `fetch_close()` (closing prices only). Results are cached for 1 hour via `@st.cache_data`. The ticker list is defined here.

**Metrics (`utils/metrics.py`)** — Pure functions that compute financial metrics from a closing price Series: total return, annualized volatility (252 trading days), max drawdown, and Sharpe ratio (using 10.5% CDI as risk-free rate). `compute_all()` aggregates them into a DataFrame.

**Charts (`charts/`)** — One module per chart type, each returning a Plotly figure:
- `price_chart.py` — Multi-stock closing price line chart
- `performance.py` — Normalized performance (% return from period start)
- `volume_chart.py` — Stacked volume bars per stock
- `candlestick.py` — Candlestick + SMA 20/50
- `correlation.py` — Correlation heatmap of daily returns

**UI (`app.py`)** — Streamlit entry point. Renders sidebar (date range, stock selector), fetches and filters data, shows KPI cards, a collapsible metrics table, three tabs (price/performance/volume), per-stock candlestick charts, and a correlation heatmap (only when 2+ stocks are selected).

## Key Conventions

- The fixed analysis period is 2025 (2025-01-01 to 2025-12-31); date range defaults live in `app.py`.
- Yahoo Finance ticker format for B3: append `.SA` suffix (e.g., `PETR4.SA`). This mapping is handled in `data/fetcher.py`.
- All monetary values are in Brazilian Real (R$).
