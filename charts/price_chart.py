import plotly.graph_objects as go
import pandas as pd


def build(close_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for ticker in close_df.columns:
        label = ticker.replace(".SA", "")
        fig.add_trace(
            go.Scatter(
                x=close_df.index,
                y=close_df[ticker],
                mode="lines",
                name=label,
            )
        )
    fig.update_layout(
        title="Evolução do Preço de Fechamento (R$)",
        xaxis_title="Data",
        yaxis_title="Preço (R$)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=480,
    )
    return fig
