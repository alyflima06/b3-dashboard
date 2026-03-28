import plotly.graph_objects as go
import pandas as pd


def build(close_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Linha de referência em 0%
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    for ticker in close_df.columns:
        s = close_df[ticker].dropna()
        if s.empty:
            continue
        perf = (s / s.iloc[0] - 1) * 100
        label = ticker.replace(".SA", "")
        last_val = perf.iloc[-1]
        color = "green" if last_val >= 0 else "red"
        fig.add_trace(
            go.Scatter(
                x=perf.index,
                y=perf,
                mode="lines",
                name=f"{label} ({last_val:+.1f}%)",
                line=dict(color=color if len(close_df.columns) == 1 else None),
            )
        )

    fig.update_layout(
        title="Performance Comparativa (base 0% em 01/01/2025)",
        xaxis_title="Data",
        yaxis_title="Retorno (%)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=480,
    )
    return fig
