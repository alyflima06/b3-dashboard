import streamlit as st
import yfinance as yf
import pandas as pd

TICKERS = ["PETR4.SA", "ITSA4.SA", "CMIG3.SA", "BBSE3.SA", "IVVB11.SA"]
TICKER_LABELS = {
    "PETR4.SA": "PETR4",
    "ITSA4.SA": "ITSA4",
    "CMIG3.SA": "CMIG3",
    "BBSE3.SA": "BBSE3",
    "IVVB11.SA": "IVVB11",
}
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"


@st.cache_data(ttl=3600)
def fetch_all(start: str = START_DATE, end: str = END_DATE) -> dict[str, pd.DataFrame]:
    """Retorna um dict {ticker: DataFrame com OHLCV} para todos os tickers."""
    result = {}
    for ticker in TICKERS:
        try:
            df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
            # Achatar MultiIndex se existir (yfinance >= 0.2.x pode retornar MultiIndex)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(how="all").ffill()
            if "Volume" in df.columns:
                df["Volume"] = df["Volume"].replace(0, float("nan"))
            if df.empty or len(df) < 5:
                st.warning(f"Dados insuficientes para {ticker}.")
                continue
            result[ticker] = df
        except Exception as e:
            st.warning(f"Não foi possível carregar dados para {ticker}: {e}")

    return result


@st.cache_data(ttl=3600)
def fetch_close(start: str = START_DATE, end: str = END_DATE) -> pd.DataFrame:
    """Retorna DataFrame com apenas os preços de fechamento de todos os tickers."""
    data = fetch_all(start, end)
    close = pd.DataFrame({t: df["Close"] for t, df in data.items()})
    return close
