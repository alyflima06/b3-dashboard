import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data.fetcher import TICKER_LABELS


def build(all_data: dict) -> go.Figure:
    tickers = list(all_data.keys())
    n = len(tickers)
    fig = make_subplots(
        rows=n,
        cols=1,
        shared_xaxes=True,
        subplot_titles=[TICKER_LABELS.get(t, t) for t in tickers],
        vertical_spacing=0.05,
    )

    for i, ticker in enumerate(tickers, start=1):
        df = all_data[ticker]
        if "Volume" not in df.columns:
            continue
        label = TICKER_LABELS.get(ticker, ticker)
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                name=label,
                showlegend=False,
            ),
            row=i,
            col=1,
        )

    fig.update_layout(
        title="Volume Negociado por Ação",
        height=200 * n,
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Volume")
    return fig
