import plotly.graph_objects as go
import pandas as pd
import numpy as np


def build(close_df: pd.DataFrame) -> go.Figure:
    returns = close_df.pct_change().dropna()
    labels = [c.replace(".SA", "") for c in returns.columns]
    corr = returns.corr().values

    # Anotações com valores
    text = [[f"{corr[i][j]:.2f}" for j in range(len(labels))] for i in range(len(labels))]

    fig = go.Figure(
        go.Heatmap(
            z=corr,
            x=labels,
            y=labels,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=14),
            hovertemplate="%{y} × %{x}: %{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Correlação dos Retornos Diários (2025)",
        height=420,
    )
    return fig
