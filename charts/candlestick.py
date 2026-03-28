import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def build(df: pd.DataFrame, ticker_label: str) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker_label} — Candlestick", "Volume"),
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker_label,
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    # SMA 20
    sma20 = df["Close"].rolling(20).mean()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=sma20,
            mode="lines",
            name="SMA 20",
            line=dict(color="orange", width=1.2),
        ),
        row=1,
        col=1,
    )

    # SMA 50
    sma50 = df["Close"].rolling(50).mean()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=sma50,
            mode="lines",
            name="SMA 50",
            line=dict(color="blue", width=1.2, dash="dot"),
        ),
        row=1,
        col=1,
    )

    # Volume com cor baseada na direção do candle
    colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            marker_color=colors,
            name="Volume",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Preço (R$)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig
