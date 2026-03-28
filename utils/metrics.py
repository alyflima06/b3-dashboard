import numpy as np
import pandas as pd


def total_return(series: pd.Series) -> float:
    """Retorno total percentual da série de preços."""
    s = series.dropna()
    if len(s) < 2:
        return float("nan")
    return (s.iloc[-1] / s.iloc[0] - 1) * 100


def annualized_volatility(series: pd.Series) -> float:
    """Volatilidade anualizada (%) dos retornos diários."""
    s = series.dropna()
    daily_returns = s.pct_change().dropna()
    if len(daily_returns) < 2:
        return float("nan")
    return daily_returns.std() * np.sqrt(252) * 100


def max_drawdown(series: pd.Series) -> float:
    """Máximo drawdown (%) da série de preços."""
    s = series.dropna()
    if len(s) < 2:
        return float("nan")
    rolling_max = s.cummax()
    drawdown = (s - rolling_max) / rolling_max * 100
    return drawdown.min()


def sharpe_ratio(series: pd.Series, risk_free: float = 0.105) -> float:
    """Sharpe simplificado usando CDI anual como taxa livre de risco."""
    s = series.dropna()
    daily_returns = s.pct_change().dropna()
    if len(daily_returns) < 2:
        return float("nan")
    ann_return = (s.iloc[-1] / s.iloc[0]) ** (252 / len(s)) - 1
    ann_vol = daily_returns.std() * np.sqrt(252)
    if ann_vol == 0:
        return float("nan")
    return (ann_return - risk_free) / ann_vol


def compute_all(close_df: pd.DataFrame) -> pd.DataFrame:
    """Retorna DataFrame com métricas para cada ação."""
    rows = []
    for ticker in close_df.columns:
        s = close_df[ticker].dropna()
        rows.append(
            {
                "Ação": ticker.replace(".SA", ""),
                "Retorno Total (%)": round(total_return(s), 2),
                "Volatilidade Anual (%)": round(annualized_volatility(s), 2),
                "Max Drawdown (%)": round(max_drawdown(s), 2),
                "Sharpe": round(sharpe_ratio(s), 2),
            }
        )
    return pd.DataFrame(rows).set_index("Ação")
