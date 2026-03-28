import streamlit as st
import pandas as pd
from datetime import date
import rdo.database as db

CLIMA_OPTIONS = ["Ensolarado", "Parcialmente Nublado", "Nublado", "Garoa", "Chuvoso", "Tempestade", "Não Observado"]
TIPO_OCORRENCIA = ["Segurança", "Qualidade", "Prazo", "Custo", "Ambiental", "Interferência", "Outra"]
STATUS_EQ = ["ativo", "parado", "saindo"]
STATUS_EQ_LABEL = {"ativo": "Ativo", "parado": "Parado", "saindo": "Saindo"}

FUNCOES_COMUNS = [
    "", "Pedreiro", "Servente", "Carpinteiro", "Eletricista", "Encanador",
    "Armador", "Pintor", "Azulejista", "Operador de Máquina", "Técnico",
    "Mestre de Obras", "Encarregado", "Engenheiro", "Estagiário"
]


def _init_state():
    if "rdo_form_data" not in st.session_state:
        st.session_state["rdo_form_data"] = {}
    if "rdo_equipe_rows" not in st.session_state:
        st.session_state["rdo_equipe_rows"] = [{"funcao": "", "quantidade": 1, "nome_empresa": ""}]
    if "rdo_ativ_rows" not in st.session_state:
        st.session_state["rdo_ativ_rows"] = [{"descricao": "", "percentual": 0.0, "observacoes": ""}]
    if "rdo_serv_rows" not in st.session_state:
        st.session_state["rdo_serv_rows"] = [{"descricao": ""}]
    if "rdo_mat_rows" not in st.session_state:
        st.session_state["rdo_mat_rows"] = [{"material": "", "quantidade": 0.0, "unidade": "", "fornecedor": "", "valor_unitario": 0.0}]
    if "rdo_equip_rows" not in st.session_state:
        st.session_state["rdo_equip_rows"] = [{"equipamento": "", "quantidade": 1, "status_eq": "ativo"}]
    if "rdo_ocor_rows" not in st.session_state:
        st.session_state["rdo_ocor_rows"] = [{"tipo": "Outra", "descricao": "", "acao_tomada": ""}]


def _load_rdo_into_state(rdo: dict):
    """Load an existing RDO into session state for editing."""
    st.session_state["rdo_form_data"] = {
        "data_relatorio": rdo.get("data_relatorio", str(date.today())),
        "engenheiro_id": rdo.get("engenheiro_id"),
        "clima_manha": rdo.get("clima_manha", "Não Observado"),
        "clima_tarde": rdo.get("clima_tarde", "Não Observado"),
        "clima_noite": rdo.get("clima_noite", "Não Observado"),
        "temperatura_manha": rdo.get("temperatura_manha") or 0.0,
        "temperatura_tarde": rdo.get("temperatura_tarde") or 0.0,
        "temperatura_noite": rdo.get("temperatura_noite") or 0.0,
        "comentarios_gerais": rdo.get("comentarios_gerais", ""),
    }
    st.session_state["rdo_equipe_rows"] = rdo.get("equipe", []) or [{"funcao": "", "quantidade": 1, "nome_empresa": ""}]
    st.session_state["rdo_ativ_rows"] = rdo.get("atividades", []) or [{"descricao": "", "percentual": 0.0, "observacoes": ""}]
    st.session_state["rdo_serv_rows"] = rdo.get("servicos", []) or [{"descricao": ""}]
    st.session_state["rdo_mat_rows"] = rdo.get("materiais", []) or [{"material": "", "quantidade": 0.0, "unidade": "", "fornecedor": "", "valor_unitario": 0.0}]
    st.session_state["rdo_equip_rows"] = rdo.get("equipamentos", []) or [{"equipamento": "", "quantidade": 1, "status_eq": "ativo"}]
    st.session_state["rdo_ocor_rows"] = rdo.get("ocorrencias", []) or [{"tipo": "Outra", "descricao": "", "acao_tomada": ""}]


def _clear_state():
    for key in ["rdo_form_data","rdo_equipe_rows","rdo_ativ_rows","rdo_serv_rows",
                "rdo_mat_rows","rdo_equip_rows","rdo_ocor_rows"]:
        st.session_state.pop(key, None)


def _collect_children() -> dict:
    return {
        "equipe":       st.session_state.get("rdo_equipe_rows", []),
        "atividades":   st.session_state.get("rdo_ativ_rows", []),
        "servicos":     st.session_state.get("rdo_serv_rows", []),
        "materiais":    st.session_state.get("rdo_mat_rows", []),
        "equipamentos": st.session_state.get("rdo_equip_rows", []),
        "ocorrencias":  st.session_state.get("rdo_ocor_rows", []),
    }


def render():
    obra = st.session_state.get("obra_selecionada")
    if not obra:
        st.warning("Selecione uma obra na barra lateral para criar um RDO.")
        return

    edit_id = st.session_state.get("edit_rdo_id")
    is_edit = edit_id is not None

    # Load existing RDO for editing
    if is_edit and "rdo_form_data" not in st.session_state:
        rdo_existente = db.get_rdo_full(edit_id)
        if rdo_existente:
            _load_rdo_into_state(rdo_existente)
        else:
            st.error("RDO não encontrado.")
            return

    _init_state()

    obra_id = obra["id"]
    engenheiros = db.get_engenheiros_ativos()

    if not engenheiros:
        st.error("Nenhum engenheiro cadastrado. Solicite ao coordenador que cadastre engenheiros.")
        return

    # Header
    if is_edit:
        rdo_num = db.get_rdo_full(edit_id)["numero_rdo"]
        st.title(f"✏️ Editar RDO #{rdo_num:03d} — {obra['nome']}")
    else:
        prox_num = db.next_rdo_number(obra_id)
        st.title(f"📋 Novo RDO #{prox_num:03d} — {obra['nome']}")

    # Action buttons at top
    col_save, col_submit, col_cancel = st.columns([2, 2, 1])
    btn_salvar = col_save.button("💾 Salvar Rascunho", type="secondary", use_container_width=True, key="btn_salvar_top")
    btn_enviar = col_submit.button("📤 Enviar para Aprovação", type="primary", use_container_width=True, key="btn_enviar_top")
    if col_cancel.button("✖ Cancelar", use_container_width=True, key="btn_cancel_top"):
        _clear_state()
        st.session_state["edit_rdo_id"] = None
        st.session_state["page"] = "ver_rdos"
        st.rerun()

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "1️⃣ Identificação",
        "2️⃣ Equipe",
        "3️⃣ Atividades",
        "4️⃣ Materiais",
        "5️⃣ Equipamentos",
        "6️⃣ Ocorrências",
        "7️⃣ Fotos & Obs.",
    ])

    # ── Aba 1: Identificação + Clima ──────────────────────────────────────────
    with tab1:
        st.subheader("Identificação da Obra")
        c1, c2 = st.columns(2)
        c1.info(f"**Obra:** {obra['nome']}")
        c2.info(f"**Cliente:** {obra.get('cliente') or '—'}")

        st.subheader("Dados do RDO")
        col_a, col_b = st.columns(2)

        data_default = st.session_state["rdo_form_data"].get("data_relatorio", str(date.today()))
        try:
            data_val = date.fromisoformat(data_default)
        except Exception:
            data_val = date.today()

        data_rel = col_a.date_input("Data do Relatório *", value=data_val, key="data_rel_input")
        st.session_state["rdo_form_data"]["data_relatorio"] = str(data_rel)

        eng_options = {e["nome"]: e["id"] for e in engenheiros}
        eng_saved_id = st.session_state["rdo_form_data"].get("engenheiro_id")
        eng_saved_name = next((n for n, i in eng_options.items() if i == eng_saved_id), list(eng_options.keys())[0])
        eng_idx = list(eng_options.keys()).index(eng_saved_name) if eng_saved_name in eng_options else 0
        eng_nome = col_b.selectbox("Engenheiro Responsável *", options=list(eng_options.keys()), index=eng_idx, key="eng_sel")
        st.session_state["rdo_form_data"]["engenheiro_id"] = eng_options[eng_nome]

        st.subheader("Condições Climáticas")
        col1, col2, col3 = st.columns(3)

        def clima_idx(val):
            try:
                return CLIMA_OPTIONS.index(val)
            except ValueError:
                return CLIMA_OPTIONS.index("Não Observado")

        cm = col1.selectbox("Manhã", CLIMA_OPTIONS, index=clima_idx(st.session_state["rdo_form_data"].get("clima_manha","Não Observado")), key="clima_m")
        ct = col2.selectbox("Tarde", CLIMA_OPTIONS, index=clima_idx(st.session_state["rdo_form_data"].get("clima_tarde","Não Observado")), key="clima_t")
        cn = col3.selectbox("Noite", CLIMA_OPTIONS, index=clima_idx(st.session_state["rdo_form_data"].get("clima_noite","Não Observado")), key="clima_n")
        st.session_state["rdo_form_data"]["clima_manha"] = cm
        st.session_state["rdo_form_data"]["clima_tarde"] = ct
        st.session_state["rdo_form_data"]["clima_noite"] = cn

        col4, col5, col6 = st.columns(3)
        tm = col4.number_input("Temp. Manhã (°C)", value=float(st.session_state["rdo_form_data"].get("temperatura_manha") or 0), step=0.5, format="%.1f", key="temp_m")
        tt = col5.number_input("Temp. Tarde (°C)", value=float(st.session_state["rdo_form_data"].get("temperatura_tarde") or 0), step=0.5, format="%.1f", key="temp_t")
        tn = col6.number_input("Temp. Noite (°C)", value=float(st.session_state["rdo_form_data"].get("temperatura_noite") or 0), step=0.5, format="%.1f", key="temp_n")
        st.session_state["rdo_form_data"]["temperatura_manha"] = tm
        st.session_state["rdo_form_data"]["temperatura_tarde"] = tt
        st.session_state["rdo_form_data"]["temperatura_noite"] = tn

    # ── Aba 2: Equipe ─────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Equipe de Trabalho")
        st.caption("Registre todos os profissionais presentes na obra hoje.")

        equipe = st.session_state["rdo_equipe_rows"]

        df_equipe = pd.DataFrame(equipe).reindex(columns=["funcao","quantidade","nome_empresa"])
        df_equipe["funcao"] = df_equipe["funcao"].fillna("")
        df_equipe["quantidade"] = pd.to_numeric(df_equipe["quantidade"], errors="coerce").fillna(1).astype(int)
        df_equipe["nome_empresa"] = df_equipe["nome_empresa"].fillna("")

        edited_equipe = st.data_editor(
            df_equipe,
            column_config={
                "funcao": st.column_config.SelectboxColumn("Função", options=FUNCOES_COMUNS, required=False),
                "quantidade": st.column_config.NumberColumn("Qtd.", min_value=1, max_value=200, step=1),
                "nome_empresa": st.column_config.TextColumn("Empresa / Empreiteira"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_equipe",
        )
        st.session_state["rdo_equipe_rows"] = edited_equipe.to_dict("records")

        total_workers = int(edited_equipe["quantidade"].sum())
        st.metric("Total de Trabalhadores", total_workers)

    # ── Aba 3: Atividades + Serviços ──────────────────────────────────────────
    with tab3:
        st.subheader("Atividades Executadas no Dia")
        st.caption("Informe o percentual de conclusão de cada atividade. Este valor atualiza automaticamente o cronograma do dashboard após aprovação.")

        ativ = st.session_state["rdo_ativ_rows"]
        df_ativ = pd.DataFrame(ativ).reindex(columns=["descricao","percentual","observacoes"])
        df_ativ["descricao"] = df_ativ["descricao"].fillna("")
        df_ativ["percentual"] = pd.to_numeric(df_ativ["percentual"], errors="coerce").fillna(0.0)
        df_ativ["observacoes"] = df_ativ["observacoes"].fillna("")

        edited_ativ = st.data_editor(
            df_ativ,
            column_config={
                "descricao": st.column_config.TextColumn("Descrição da Atividade", width="large"),
                "percentual": st.column_config.NumberColumn("% Concluído", min_value=0, max_value=100, step=1, format="%.0f%%"),
                "observacoes": st.column_config.TextColumn("Observações"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_ativ",
        )
        st.session_state["rdo_ativ_rows"] = edited_ativ.to_dict("records")

        st.divider()
        st.subheader("Serviços em Andamento")

        serv = st.session_state["rdo_serv_rows"]
        df_serv = pd.DataFrame(serv).reindex(columns=["descricao"])
        df_serv["descricao"] = df_serv["descricao"].fillna("")

        edited_serv = st.data_editor(
            df_serv,
            column_config={
                "descricao": st.column_config.TextColumn("Descrição do Serviço em Andamento", width="large"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_serv",
        )
        st.session_state["rdo_serv_rows"] = edited_serv.to_dict("records")

    # ── Aba 4: Materiais ──────────────────────────────────────────────────────
    with tab4:
        st.subheader("Materiais Recebidos e Custos")
        st.caption("Os custos informados aqui serão abatidos no orçamento do dashboard após aprovação do RDO.")

        mat = st.session_state["rdo_mat_rows"]
        df_mat = pd.DataFrame(mat).reindex(columns=["material","quantidade","unidade","fornecedor","valor_unitario","valor_total"])
        df_mat["material"] = df_mat["material"].fillna("")
        df_mat["quantidade"] = pd.to_numeric(df_mat["quantidade"], errors="coerce").fillna(0.0)
        df_mat["unidade"] = df_mat["unidade"].fillna("")
        df_mat["fornecedor"] = df_mat["fornecedor"].fillna("")
        df_mat["valor_unitario"] = pd.to_numeric(df_mat["valor_unitario"], errors="coerce").fillna(0.0)
        df_mat["valor_total"] = (df_mat["quantidade"] * df_mat["valor_unitario"]).round(2)

        edited_mat = st.data_editor(
            df_mat[["material","quantidade","unidade","fornecedor","valor_unitario","valor_total"]],
            column_config={
                "material": st.column_config.TextColumn("Material", width="medium"),
                "quantidade": st.column_config.NumberColumn("Qtd.", min_value=0.0, format="%.2f"),
                "unidade": st.column_config.TextColumn("Un.", width="small"),
                "fornecedor": st.column_config.TextColumn("Fornecedor"),
                "valor_unitario": st.column_config.NumberColumn("Vlr. Unit. (R$)", min_value=0.0, format="R$ %.2f"),
                "valor_total": st.column_config.NumberColumn("Vlr. Total (R$)", disabled=True, format="R$ %.2f"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_mat",
        )
        # Recalculate valor_total
        edited_mat["valor_total"] = (edited_mat["quantidade"] * edited_mat["valor_unitario"]).round(2)
        st.session_state["rdo_mat_rows"] = edited_mat.to_dict("records")

        total_mat = float(edited_mat["valor_total"].sum())
        st.metric("Total de Custos de Materiais", f"R$ {total_mat:,.2f}")

    # ── Aba 5: Equipamentos ───────────────────────────────────────────────────
    with tab5:
        st.subheader("Equipamentos Locados")

        equip = st.session_state["rdo_equip_rows"]
        df_equip = pd.DataFrame(equip).reindex(columns=["equipamento","quantidade","status_eq"])
        df_equip["equipamento"] = df_equip["equipamento"].fillna("")
        df_equip["quantidade"] = pd.to_numeric(df_equip["quantidade"], errors="coerce").fillna(1).astype(int)
        df_equip["status_eq"] = df_equip["status_eq"].fillna("ativo")

        edited_equip = st.data_editor(
            df_equip,
            column_config={
                "equipamento": st.column_config.TextColumn("Equipamento", width="large"),
                "quantidade": st.column_config.NumberColumn("Qtd.", min_value=1, step=1),
                "status_eq": st.column_config.SelectboxColumn("Status", options=STATUS_EQ),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_equip",
        )
        st.session_state["rdo_equip_rows"] = edited_equip.to_dict("records")

    # ── Aba 6: Ocorrências ────────────────────────────────────────────────────
    with tab6:
        st.subheader("Ocorrências e Interferências")
        st.caption("Registre qualquer evento que impactou ou possa impactar a obra.")

        ocor = st.session_state["rdo_ocor_rows"]
        df_ocor = pd.DataFrame(ocor).reindex(columns=["tipo","descricao","acao_tomada"])
        df_ocor["tipo"] = df_ocor["tipo"].fillna("Outra")
        df_ocor["descricao"] = df_ocor["descricao"].fillna("")
        df_ocor["acao_tomada"] = df_ocor["acao_tomada"].fillna("")

        edited_ocor = st.data_editor(
            df_ocor,
            column_config={
                "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPO_OCORRENCIA, width="medium"),
                "descricao": st.column_config.TextColumn("Descrição", width="large"),
                "acao_tomada": st.column_config.TextColumn("Ação Tomada", width="large"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_ocor",
        )
        st.session_state["rdo_ocor_rows"] = edited_ocor.to_dict("records")

    # ── Aba 7: Fotos + Comentários ────────────────────────────────────────────
    with tab7:
        st.subheader("Registro Fotográfico")

        if is_edit and edit_id:
            fotos_existentes = db.get_fotos(edit_id)
            if fotos_existentes:
                st.caption(f"{len(fotos_existentes)} foto(s) já salvas.")
                cols = st.columns(3)
                for i, foto in enumerate(fotos_existentes):
                    with cols[i % 3]:
                        try:
                            st.image(foto["file_path"], caption=foto.get("legenda",""), use_container_width=True)
                        except Exception:
                            st.text(f"Foto: {foto.get('legenda','sem legenda')}")
                        if st.button("🗑️ Remover", key=f"del_foto_{foto['id']}"):
                            db.delete_photo(foto["id"])
                            st.rerun()
            st.divider()

        uploaded_files = st.file_uploader(
            "Adicionar fotos (JPG, PNG)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="foto_uploader",
        )
        if uploaded_files:
            for i, uf in enumerate(uploaded_files):
                leg = st.text_input(f"Legenda — {uf.name}", key=f"leg_{i}")
                st.session_state[f"_foto_leg_{i}"] = leg

        st.divider()
        st.subheader("Comentários Gerais")
        comentarios = st.text_area(
            "Observações finais, informações adicionais, comunicados...",
            value=st.session_state["rdo_form_data"].get("comentarios_gerais",""),
            height=150,
            key="comentarios_input",
        )
        st.session_state["rdo_form_data"]["comentarios_gerais"] = comentarios

    st.divider()

    # Bottom action buttons
    col_s2, col_e2, col_c2 = st.columns([2, 2, 1])
    btn_salvar2 = col_s2.button("💾 Salvar Rascunho", type="secondary", use_container_width=True, key="btn_salvar_bot")
    btn_enviar2 = col_e2.button("📤 Enviar para Aprovação", type="primary", use_container_width=True, key="btn_enviar_bot")

    # ── Process form actions ───────────────────────────────────────────────────
    should_save = btn_salvar or btn_salvar2
    should_submit = btn_enviar or btn_enviar2

    if should_save or should_submit:
        header = st.session_state["rdo_form_data"].copy()
        if not header.get("engenheiro_id"):
            st.error("Selecione o engenheiro responsável.")
            st.stop()

        children = _collect_children()

        try:
            saved_id = db.save_rdo(header, children, rdo_id=edit_id)

            # Save uploaded photos
            if uploaded_files:
                for i, uf in enumerate(uploaded_files):
                    leg = st.session_state.get(f"_foto_leg_{i}", "")
                    db.save_photo(obra_id, saved_id, uf, legenda=leg, ordem=i)

            if should_submit:
                db.submit_rdo(saved_id)
                st.success(f"RDO enviado para aprovação!")
            else:
                st.success(f"RDO salvo como rascunho.")

            _clear_state()
            st.session_state["edit_rdo_id"] = None
            st.session_state["view_rdo_id"] = saved_id
            st.session_state["page"] = "ver_rdo"
            st.rerun()

        except Exception as e:
            st.error(f"Erro ao salvar RDO: {e}")
