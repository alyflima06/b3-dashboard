import streamlit as st
from datetime import date

from data.fetcher import fetch_all, fetch_close, TICKERS, TICKER_LABELS, START_DATE, END_DATE
from utils import metrics as m
from charts import price_chart, performance, volume_chart, candlestick, correlation

st.set_page_config(
    page_title="Análise de Ações B3 — 2025",
    page_icon="📈",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Configurações")
    start = st.date_input("Data inicial", value=date(2025, 1, 2), min_value=date(2025, 1, 1), max_value=date(2025, 12, 31))
    end   = st.date_input("Data final",   value=date(2025, 12, 31), min_value=date(2025, 1, 1), max_value=date(2025, 12, 31))
    selected = st.multiselect(
        "Ações exibidas",
        options=TICKERS,
        default=TICKERS,
        format_func=lambda t: TICKER_LABELS[t],
    )
    if not selected:
        st.warning("Selecione ao menos uma ação.")
        st.stop()
    st.caption("Dados via Yahoo Finance (B3). Cache de 1 hora.")

# ── Carregamento de dados ─────────────────────────────────────────────────────
with st.spinner("Carregando dados do mercado..."):
    all_data = fetch_all(str(start), str(end))
    close_df = fetch_close(str(start), str(end))

# Filtrar pelas ações selecionadas
all_data  = {t: df for t, df in all_data.items() if t in selected}
close_df  = close_df[[t for t in selected if t in close_df.columns]]

if close_df.empty:
    st.error("Não foi possível carregar dados. Verifique sua conexão e tente novamente.")
    st.stop()

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.title("📈 Análise de Ações — B3 2025")
st.caption(f"Período: {start} → {end}  |  Ações: {', '.join(TICKER_LABELS[t] for t in selected)}")

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.subheader("Resumo de Performance")
cols = st.columns(len(selected))
for col, ticker in zip(cols, selected):
    s = close_df[ticker].dropna()
    ret = m.total_return(s)
    delta_color = "normal"
    col.metric(
        label=TICKER_LABELS[ticker],
        value=f"R$ {s.iloc[-1]:.2f}" if not s.empty else "—",
        delta=f"{ret:+.2f}%" if ret == ret else "—",
        delta_color=delta_color,
    )

# ── Tabela de métricas ────────────────────────────────────────────────────────
with st.expander("Ver métricas detalhadas"):
    metrics_df = m.compute_all(close_df)
    st.dataframe(metrics_df, use_container_width=True)

# ── Gráficos principais ───────────────────────────────────────────────────────
st.subheader("Gráficos Comparativos")
tab1, tab2, tab3 = st.tabs(["Preço (R$)", "Performance (%)", "Volume"])

with tab1:
    st.plotly_chart(price_chart.build(close_df), use_container_width=True)

with tab2:
    st.plotly_chart(performance.build(close_df), use_container_width=True)

with tab3:
    st.plotly_chart(volume_chart.build(all_data), use_container_width=True)

# ── Candlestick individual ────────────────────────────────────────────────────
st.subheader("Análise Individual — Candlestick")
chosen = st.selectbox(
    "Selecione a ação",
    options=selected,
    format_func=lambda t: TICKER_LABELS[t],
)
if chosen in all_data:
    st.plotly_chart(
        candlestick.build(all_data[chosen], TICKER_LABELS[chosen]),
        use_container_width=True,
    )

# ── Correlação ────────────────────────────────────────────────────────────────
if len(selected) >= 2:
    st.subheader("Correlação dos Retornos Diários")
    st.plotly_chart(correlation.build(close_df), use_container_width=True)
    st.caption(
        "Correlação 1.0 = movimentos idênticos | 0.0 = independentes | -1.0 = opostos. "
        "IVVB11 tende a ter baixa correlação com ações domésticas em períodos de volatilidade cambial."
    )
