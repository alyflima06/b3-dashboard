import streamlit as st
import pandas as pd
from datetime import date, datetime
import rdo.database as db


def _parse_date(val) -> str:
    """Convert various date types to ISO string."""
    if val is None:
        return ""
    if isinstance(val, date):
        return str(val)
    try:
        return str(pd.to_datetime(val).date())
    except Exception:
        return str(val) if val else ""


def _import_excel(obra_id: int):
    st.subheader("📥 Importar Cronograma e Orçamento via Excel")

    with st.expander("📋 Formato esperado do arquivo Excel", expanded=False):
        st.markdown("""
        **Aba `Cronograma`** (obrigatória para importar cronograma):
        | Atividade | Início | Fim | Peso% |
        |---|---|---|---|
        | Fundações | 2025-03-01 | 2025-04-15 | 20 |
        | Estrutura | 2025-04-01 | 2025-06-30 | 30 |

        **Aba `Orçamento`** (obrigatória para importar orçamento analítico):
        | Item | Descrição | Valor |
        |---|---|---|
        | 01 | Fundações | 150000.00 |
        | 02 | Estrutura | 400000.00 |

        Datas aceitas: `AAAA-MM-DD`, `DD/MM/AAAA` ou formato de data do Excel.
        """)

    uploaded = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)",
        type=["xlsx", "xls"],
        key=f"excel_upload_{obra_id}",
    )

    if not uploaded:
        return

    try:
        xl = pd.ExcelFile(uploaded)
        sheet_names_lower = {s.lower(): s for s in xl.sheet_names}

        # ── Import Cronograma ──────────────────────────────────────────────
        crono_sheet = sheet_names_lower.get("cronograma")
        if crono_sheet:
            df_c = xl.parse(crono_sheet)
            df_c.columns = [str(c).strip().lower() for c in df_c.columns]
            col_map = {}
            for col in df_c.columns:
                if "atividade" in col or "ativ" in col:
                    col_map["atividade"] = col
                elif "início" in col or "inicio" in col or "start" in col or "ini" in col:
                    col_map["data_inicio"] = col
                elif "fim" in col or "end" in col or "término" in col or "termino" in col:
                    col_map["data_fim"] = col
                elif "peso" in col or "%" in col or "weight" in col:
                    col_map["peso_percentual"] = col

            if "atividade" not in col_map:
                st.error("Coluna 'Atividade' não encontrada na aba Cronograma.")
            else:
                linhas = []
                for _, row in df_c.iterrows():
                    ativ = str(row.get(col_map["atividade"], "")).strip()
                    if not ativ or ativ.lower() == "nan":
                        continue
                    di = _parse_date(row.get(col_map.get("data_inicio", ""), ""))
                    df_end = _parse_date(row.get(col_map.get("data_fim", ""), ""))
                    peso = float(row.get(col_map.get("peso_percentual", ""), 0) or 0)
                    linhas.append({
                        "atividade": ativ,
                        "data_inicio": di,
                        "data_fim": df_end,
                        "peso_percentual": peso,
                        "percentual_executado": 0.0,
                    })
                if linhas:
                    st.success(f"✅ {len(linhas)} atividades encontradas no cronograma.")
                    preview_df = pd.DataFrame(linhas)[["atividade","data_inicio","data_fim","peso_percentual"]]
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)
                    if st.button("💾 Importar Cronograma", key=f"imp_crono_{obra_id}", type="primary"):
                        db.save_cronograma(obra_id, linhas)
                        st.success("Cronograma importado com sucesso!")
                        st.rerun()
        else:
            st.warning("Aba 'Cronograma' não encontrada no Excel.")

        # ── Import Orçamento ───────────────────────────────────────────────
        orc_sheet = (sheet_names_lower.get("orçamento")
                     or sheet_names_lower.get("orcamento")
                     or sheet_names_lower.get("budget"))
        if orc_sheet:
            df_o = xl.parse(orc_sheet)
            df_o.columns = [str(c).strip().lower() for c in df_o.columns]
            col_item = col_desc = col_valor = None
            for col in df_o.columns:
                if "item" in col or "código" in col or "codigo" in col or "cod" in col:
                    col_item = col
                elif "descri" in col or "nome" in col or "serviço" in col or "servico" in col:
                    col_desc = col
                elif "valor" in col or "custo" in col or "preço" in col or "preco" in col or "r$" in col:
                    col_valor = col

            if not col_valor:
                st.error("Coluna 'Valor' não encontrada na aba Orçamento.")
            else:
                itens = []
                for _, row in df_o.iterrows():
                    item_val = str(row.get(col_item, "")).strip() if col_item else ""
                    desc_val = str(row.get(col_desc, "")).strip() if col_desc else ""
                    valor_val = float(row.get(col_valor, 0) or 0)
                    label = item_val or desc_val
                    if not label or label.lower() == "nan":
                        continue
                    itens.append({"item": label, "descricao": desc_val, "valor": valor_val})
                if itens:
                    st.success(f"✅ {len(itens)} itens encontrados no orçamento.")
                    preview_orc = pd.DataFrame(itens)[["item","descricao","valor"]]
                    preview_orc = preview_orc.copy()
                    preview_orc["valor"] = preview_orc["valor"].apply(lambda v: f"R$ {v:,.2f}")
                    st.dataframe(preview_orc, use_container_width=True, hide_index=True)
                    if st.button("💾 Importar Orçamento", key=f"imp_orc_{obra_id}", type="primary"):
                        db.save_orcamento_itens(obra_id, itens)
                        st.success("Orçamento analítico importado com sucesso!")
                        st.rerun()
        else:
            st.warning("Aba 'Orçamento' (ou 'Orcamento'/'Budget') não encontrada no Excel.")

    except Exception as e:
        st.error(f"Erro ao processar Excel: {e}")


def _cronograma_manual(obra_id: int):
    st.subheader("📅 Cronograma de Atividades")
    st.caption("Edite o cronograma diretamente ou importe via Excel acima.")

    crono = db.get_cronograma(obra_id)
    if crono:
        df_crono = pd.DataFrame(crono)[["atividade","data_inicio","data_fim","peso_percentual","percentual_executado"]]
    else:
        df_crono = pd.DataFrame(columns=["atividade","data_inicio","data_fim","peso_percentual","percentual_executado"])

    edited = st.data_editor(
        df_crono,
        column_config={
            "atividade": st.column_config.TextColumn("Atividade", width="large"),
            "data_inicio": st.column_config.TextColumn("Início (AAAA-MM-DD)"),
            "data_fim": st.column_config.TextColumn("Fim (AAAA-MM-DD)"),
            "peso_percentual": st.column_config.NumberColumn("Peso %", min_value=0, max_value=100, step=1, format="%.0f"),
            "percentual_executado": st.column_config.NumberColumn("Executado %", min_value=0, max_value=100, step=1, format="%.0f", disabled=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        key=f"crono_editor_{obra_id}",
    )

    if st.button("💾 Salvar Cronograma", key=f"save_crono_{obra_id}", type="primary"):
        linhas = edited.to_dict("records")
        crono_map = {c["atividade"]: c.get("percentual_executado", 0) for c in crono}
        for ln in linhas:
            if ln.get("atividade") in crono_map:
                ln["percentual_executado"] = crono_map[ln["atividade"]]
        db.save_cronograma(obra_id, linhas)
        st.success("Cronograma salvo!")
        st.rerun()

    if not edited.empty and "peso_percentual" in edited.columns:
        total_peso = float(edited["peso_percentual"].fillna(0).sum())
        if abs(total_peso - 100) > 0.1:
            st.warning(f"A soma dos pesos é {total_peso:.1f}% (idealmente deve ser 100%).")
        else:
            st.success(f"Soma dos pesos: {total_peso:.1f}% ✓")


def _orcamento_manual(obra_id: int):
    st.subheader("📑 Orçamento Analítico")
    st.caption("Itens de custo do orçamento da obra. Edite diretamente ou importe via Excel acima.")

    itens = db.get_orcamento_itens(obra_id)
    if itens:
        df_orc = pd.DataFrame(itens)[["item","descricao","valor"]]
    else:
        df_orc = pd.DataFrame(columns=["item","descricao","valor"])

    edited_orc = st.data_editor(
        df_orc,
        column_config={
            "item": st.column_config.TextColumn("Item / Código"),
            "descricao": st.column_config.TextColumn("Descrição", width="large"),
            "valor": st.column_config.NumberColumn("Valor (R$)", min_value=0, format="R$ %.2f"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key=f"orc_editor_{obra_id}",
    )

    if st.button("💾 Salvar Orçamento", key=f"save_orc_{obra_id}", type="primary"):
        db.save_orcamento_itens(obra_id, edited_orc.to_dict("records"))
        st.success("Orçamento analítico salvo!")
        st.rerun()

    if not edited_orc.empty and "valor" in edited_orc.columns:
        total = float(edited_orc["valor"].fillna(0).sum())
        st.metric("Total Orçamento Analítico", f"R$ {total:,.2f}")


def render():
    st.title("🏗️ Gerenciamento de Obras")

    obras = db.get_all_obras()

    # ── Listagem ──────────────────────────────────────────────────────────────
    st.subheader("Obras Cadastradas")

    if not obras:
        st.info("Nenhuma obra cadastrada ainda.")
    else:
        for o in obras:
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 2, 1])
                ativo_badge = "🟢 Ativa" if o["ativo"] else "🔴 Arquivada"
                prazo_txt = f"Prazo: {o.get('data_prazo') or '—'}"
                col1.markdown(
                    f"**{o['nome']}**  \n"
                    f"{ativo_badge} &nbsp;|&nbsp; Cliente: {o.get('cliente') or '—'}  \n"
                    f"{prazo_txt} | Resp.: {o.get('responsavel') or '—'}"
                )
                col2.markdown(
                    f"Orçamento: **R$ {o['orcamento']:,.2f}**  \n"
                    f"Gasto (aprovado): R$ {o['gasto_aprovado']:,.2f}  \n"
                    f"RDOs: {o['total_rdos']}"
                )
                with col3:
                    if o["ativo"]:
                        if st.button("✏️ Editar", key=f"edit_obra_{o['id']}", help="Editar", use_container_width=True):
                            st.session_state[f"editing_obra_{o['id']}"] = True
                            st.rerun()
                        if st.button("📊 KPIs", key=f"dash_obra_{o['id']}", help="Ver Dashboard", use_container_width=True):
                            st.session_state["obra_selecionada"] = dict(o)
                            st.session_state["obra_selecionada_nome"] = o["nome"]
                            st.session_state["page"] = "dashboard"
                            st.rerun()
                        if st.button("📦 Arquivar", key=f"arch_{o['id']}", use_container_width=True):
                            db.archive_obra(o["id"])
                            st.success(f"Obra '{o['nome']}' arquivada.")
                            st.rerun()
                    else:
                        if st.button("♻️ Reativar", key=f"react_{o['id']}", use_container_width=True):
                            db.reactivate_obra(o["id"])
                            st.success(f"Obra '{o['nome']}' reativada.")
                            st.rerun()

                # Inline edit + management tabs
                if st.session_state.get(f"editing_obra_{o['id']}"):
                    with st.form(key=f"form_edit_obra_{o['id']}"):
                        st.markdown("**Editar Obra**")
                        c1, c2 = st.columns(2)
                        nome_e = c1.text_input("Nome", value=o["nome"])
                        cliente_e = c2.text_input("Cliente", value=o.get("cliente") or "")
                        end_e = st.text_input("Endereço", value=o.get("endereco") or "")
                        resp_e = st.text_input("Responsável / Coordenador", value=o.get("responsavel") or "")
                        c3, c4, c5 = st.columns(3)
                        orc_e = c3.number_input("Orçamento (R$)", value=float(o.get("orcamento") or 0),
                                                min_value=0.0, step=1000.0, format="%.2f")
                        di_val = None
                        dp_val = None
                        try:
                            if o.get("data_inicio"):
                                di_val = date.fromisoformat(str(o["data_inicio"]))
                        except Exception:
                            pass
                        try:
                            if o.get("data_prazo"):
                                dp_val = date.fromisoformat(str(o["data_prazo"]))
                        except Exception:
                            pass
                        di_e = c4.date_input("Data Início", value=di_val or date.today(), key=f"di_{o['id']}")
                        dp_e = c5.date_input("Data Prazo", value=dp_val or date.today(), key=f"dp_{o['id']}")
                        s1, s2 = st.columns(2)
                        if s1.form_submit_button("💾 Salvar", type="primary"):
                            if nome_e.strip():
                                db.update_obra(
                                    o["id"], nome_e.strip(), end_e.strip(),
                                    cliente_e.strip(), orc_e,
                                    data_inicio=str(di_e), data_prazo=str(dp_e),
                                    responsavel=resp_e.strip()
                                )
                                st.session_state.pop(f"editing_obra_{o['id']}", None)
                                st.success("Obra atualizada.")
                                st.rerun()
                            else:
                                st.error("Nome é obrigatório.")
                        if s2.form_submit_button("Cancelar"):
                            st.session_state.pop(f"editing_obra_{o['id']}", None)
                            st.rerun()

                    st.divider()
                    tabs = st.tabs(["📥 Importar Excel", "📅 Cronograma Manual", "📑 Orçamento Manual"])
                    with tabs[0]:
                        _import_excel(o["id"])
                    with tabs[1]:
                        _cronograma_manual(o["id"])
                    with tabs[2]:
                        _orcamento_manual(o["id"])

    st.divider()

    # ── Nova Obra ─────────────────────────────────────────────────────────────
    st.subheader("➕ Nova Obra")
    with st.form("form_nova_obra"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome da obra *")
        cliente = c2.text_input("Cliente")
        endereco = st.text_input("Endereço")
        responsavel = st.text_input("Responsável / Coordenador")
        c3, c4, c5 = st.columns(3)
        orcamento = c3.number_input("Orçamento Total (R$)", min_value=0.0, step=1000.0,
                                    format="%.2f", value=0.0)
        data_inicio = c4.date_input("Data de Início", value=date.today(), key="nova_obra_di")
        data_prazo_input = c5.date_input("Data de Prazo", value=date.today(), key="nova_obra_dp")
        submitted = st.form_submit_button("Criar Obra", type="primary")

    if submitted:
        if not nome.strip():
            st.error("O nome da obra é obrigatório.")
        else:
            db.create_obra(
                nome.strip(), endereco.strip(), cliente.strip(), orcamento,
                data_inicio=str(data_inicio), data_prazo=str(data_prazo_input),
                responsavel=responsavel.strip()
            )
            st.success(f"Obra '{nome.strip()}' criada com sucesso!")
            st.rerun()
