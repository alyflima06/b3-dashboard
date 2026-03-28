import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date
import rdo.database as db


def _gauge(value: float, max_val: float, title: str, color: str = "#1f77b4") -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        number={"suffix": "%", "font": {"size": 36}},
        title={"text": title, "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color},
            "bgcolor": "white",
            "steps": [
                {"range": [0, 50], "color": "#f8f9fa"},
                {"range": [50, 75], "color": "#e9ecef"},
                {"range": [75, 100], "color": "#dee2e6"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 3},
                "thickness": 0.75,
                "value": max_val,
            },
        },
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def render():
    obra = st.session_state.get("obra_selecionada")
    if not obra:
        st.warning("Selecione uma obra na barra lateral.")
        return

    obra_id = obra["id"]
    kpis = db.get_kpis_obra(obra_id)
    if not kpis:
        st.error("Obra não encontrada.")
        return

    obra_data = kpis["obra"]
    st.title(f"📊 Dashboard — {obra_data['nome']}")

    # Subheader info
    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.caption(f"**Cliente:** {obra_data.get('cliente') or '—'}")
    col_info2.caption(f"**Responsável:** {obra_data.get('responsavel') or '—'}")
    col_info3.caption(f"**Endereço:** {obra_data.get('endereco') or '—'}")

    # Prazo info
    data_inicio = obra_data.get("data_inicio")
    data_prazo = obra_data.get("data_prazo")
    hoje = date.today()
    prazo_info = "—"
    dias_restantes = None
    if data_prazo:
        try:
            dp = date.fromisoformat(str(data_prazo))
            dias_restantes = (dp - hoje).days
            if dias_restantes > 0:
                prazo_info = f"{dias_restantes} dias restantes"
            elif dias_restantes == 0:
                prazo_info = "Prazo: hoje!"
            else:
                prazo_info = f"{abs(dias_restantes)} dias em atraso"
        except Exception:
            prazo_info = str(data_prazo)

    st.divider()

    # ── Linha 1: KPI Cards ────────────────────────────────────────────────────
    st.subheader("Indicadores Principais")
    k1, k2, k3, k4 = st.columns(4)

    # Cost
    gasto = kpis["gasto_aprovado"]
    orcamento = kpis["orcamento"]
    saldo = kpis["saldo"]
    k1.metric(
        "💰 Custo Executado",
        f"R$ {gasto:,.0f}",
        delta=f"Saldo: R$ {saldo:,.0f}",
        delta_color="normal" if saldo >= 0 else "inverse",
    )

    # Prazo
    k2.metric(
        "📅 Prazo",
        str(data_prazo or "—"),
        delta=prazo_info,
        delta_color="normal" if (dias_restantes is None or dias_restantes >= 0) else "inverse",
    )

    # RDOs
    k3.metric(
        "📋 RDOs Aprovados",
        kpis["rdos_aprovados"],
        delta=f"{kpis['rdos_pendentes']} pendentes",
    )

    # Dias trabalhados
    k4.metric(
        "👷 Dias Trabalhados",
        kpis["dias_trabalhados"],
        delta=f"{kpis['rdos_total']} RDOs no total",
    )

    st.divider()

    # ── Linha 2: Gauges ───────────────────────────────────────────────────────
    st.subheader("Execução x Planejado")
    col_gauge1, col_gauge2 = st.columns(2)

    pct_custo = kpis["pct_custo"]
    with col_gauge1:
        gauge_color = "#28a745" if pct_custo <= 80 else ("#ffc107" if pct_custo <= 100 else "#dc3545")
        fig_custo = _gauge(pct_custo, 100, "Orçamento Executado (%)", color=gauge_color)
        st.plotly_chart(fig_custo, use_container_width=True)
        st.caption(f"R$ {gasto:,.2f} de R$ {orcamento:,.2f} orçados")

    pct_exec = kpis["cronograma_executado"]
    pct_prev = kpis["cronograma_previsto"]
    with col_gauge2:
        crono_color = "#28a745" if pct_exec >= pct_prev else ("#ffc107" if pct_exec >= pct_prev * 0.85 else "#dc3545")
        fig_crono = _gauge(pct_exec, pct_prev, "Cronograma Executado (%)", color=crono_color)
        st.plotly_chart(fig_crono, use_container_width=True)
        st.caption(f"Executado: {pct_exec:.1f}% | Previsto para hoje: {pct_prev:.1f}%")

    st.divider()

    # ── Linha 3: Gráficos de detalhe ──────────────────────────────────────────
    col_left, col_right = st.columns(2)

    # Cost evolution chart
    with col_left:
        st.subheader("Evolução de Custos (RDOs Aprovados)")
        custo_por_data = kpis.get("custo_por_data", [])
        if custo_por_data:
            df_custo = pd.DataFrame(custo_por_data)
            df_custo["data_relatorio"] = pd.to_datetime(df_custo["data_relatorio"])
            df_custo = df_custo.sort_values("data_relatorio")
            df_custo["custo_acumulado"] = df_custo["custo_dia"].cumsum()
            fig_ev = go.Figure()
            fig_ev.add_trace(go.Bar(
                x=df_custo["data_relatorio"],
                y=df_custo["custo_dia"],
                name="Custo do dia",
                marker_color="#4e79a7",
                opacity=0.7,
            ))
            fig_ev.add_trace(go.Scatter(
                x=df_custo["data_relatorio"],
                y=df_custo["custo_acumulado"],
                name="Acumulado",
                line=dict(color="#e15759", width=2),
                yaxis="y2",
            ))
            if orcamento > 0:
                fig_ev.add_hline(y=orcamento, line_dash="dash", line_color="red",
                                 annotation_text="Orçamento Total", yref="y2")
            fig_ev.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
                yaxis=dict(title="R$ por dia"),
                yaxis2=dict(title="R$ Acumulado", overlaying="y", side="right"),
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig_ev, use_container_width=True)
        else:
            st.info("Nenhum custo registrado ainda em RDOs aprovados.")

    # Cronograma table
    with col_right:
        st.subheader("Cronograma de Atividades")
        crono = db.get_cronograma(obra_id)
        if crono:
            df_crono = pd.DataFrame(crono)
            # Calculate scheduled % based on today's date
            hoje_str = str(hoje)
            previsto_list = []
            for _, row in df_crono.iterrows():
                try:
                    di = date.fromisoformat(str(row["data_inicio"]))
                    df_end = date.fromisoformat(str(row["data_fim"]))
                    total_dias = (df_end - di).days
                    if total_dias <= 0:
                        pct_p = 100.0 if hoje >= df_end else 0.0
                    elif hoje < di:
                        pct_p = 0.0
                    elif hoje >= df_end:
                        pct_p = 100.0
                    else:
                        pct_p = (hoje - di).days / total_dias * 100
                    previsto_list.append(round(pct_p, 1))
                except Exception:
                    previsto_list.append(0.0)
            df_crono["previsto_%"] = previsto_list
            df_crono["executado_%"] = df_crono["percentual_executado"].round(1)

            def status_icon(row):
                ex = row["executado_%"]
                pr = row["previsto_%"]
                if ex >= pr:
                    return "🟢"
                elif ex >= pr * 0.85:
                    return "🟡"
                else:
                    return "🔴"

            df_crono["status"] = df_crono.apply(status_icon, axis=1)
            display_cols = ["atividade", "data_inicio", "data_fim", "previsto_%", "executado_%", "status"]
            available_cols = [c for c in display_cols if c in df_crono.columns]
            st.dataframe(
                df_crono[available_cols].rename(columns={
                    "atividade": "Atividade",
                    "data_inicio": "Início",
                    "data_fim": "Fim",
                    "previsto_%": "Previsto %",
                    "executado_%": "Executado %",
                    "status": "",
                }),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Cronograma não cadastrado. Acesse Obras > Cronograma para importar via Excel ou cadastrar manualmente.")

    st.divider()

    # ── RDO Status Summary ────────────────────────────────────────────────────
    col_rdos, col_equipe = st.columns(2)

    with col_rdos:
        st.subheader("Resumo de RDOs")
        rdo_data = {
            "Status": ["Aprovados", "Pendentes", "Rascunhos", "Rejeitados"],
            "Qtd.": [
                kpis["rdos_aprovados"],
                kpis["rdos_pendentes"],
                kpis["rdos_rascunhos"],
                kpis["rdos_rejeitados"],
            ],
        }
        df_rdos = pd.DataFrame(rdo_data)
        colors = ["#28a745", "#007bff", "#6c757d", "#dc3545"]
        fig_rdos = px.bar(
            df_rdos, x="Status", y="Qtd.", color="Status",
            color_discrete_sequence=colors,
            text="Qtd.",
        )
        fig_rdos.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        fig_rdos.update_traces(textposition="outside")
        st.plotly_chart(fig_rdos, use_container_width=True)

    with col_equipe:
        st.subheader("Equipe (Total por Função)")
        equipe_resumo = kpis.get("equipe_resumo", [])
        if equipe_resumo:
            df_eq = pd.DataFrame(equipe_resumo)
            fig_eq = px.pie(df_eq, values="total", names="funcao",
                            color_discrete_sequence=px.colors.qualitative.Set3)
            fig_eq.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_eq, use_container_width=True)
        else:
            st.info("Nenhum registro de equipe nos RDOs aprovados.")

    # ── Ocorrências Recentes ──────────────────────────────────────────────────
    st.divider()
    st.subheader("⚠️ Últimas Ocorrências (RDOs Aprovados)")
    ultimas = kpis.get("ultimas_ocorrencias", [])
    if ultimas:
        tipo_emoji = {"Segurança":"🦺","Qualidade":"📐","Prazo":"⏰","Custo":"💰",
                      "Ambiental":"🌿","Interferência":"⚡","Outra":"📝"}
        for oc in ultimas:
            emoji = tipo_emoji.get(oc.get("tipo","Outra"),"📝")
            col_a, col_b = st.columns([1, 4])
            col_a.markdown(f"**RDO #{oc.get('numero_rdo',''):03d}** | {oc.get('data_relatorio','')}")
            col_b.markdown(f"{emoji} **[{oc.get('tipo','—')}]** {oc['descricao']}"
                           + (f"\n> Ação: {oc['acao_tomada']}" if oc.get("acao_tomada") else ""))
    else:
        st.success("Nenhuma ocorrência registrada nos RDOs aprovados.")

    # ── Orçamento Analítico ───────────────────────────────────────────────────
    orcamento_itens = db.get_orcamento_itens(obra_id)
    if orcamento_itens:
        st.divider()
        st.subheader("📑 Orçamento Analítico")
        df_orc = pd.DataFrame(orcamento_itens)
        total_orc = df_orc["valor"].sum()
        fig_orc = px.bar(
            df_orc.sort_values("valor", ascending=True),
            x="valor", y="item",
            orientation="h",
            text="valor",
            labels={"valor": "R$", "item": "Item"},
            color="valor",
            color_continuous_scale="Blues",
        )
        fig_orc.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
        fig_orc.update_layout(height=max(300, len(orcamento_itens)*30), margin=dict(l=10,r=10,t=10,b=10), showlegend=False)
        st.plotly_chart(fig_orc, use_container_width=True)
        st.caption(f"Total orçado (analítico): R$ {total_orc:,.2f}")
