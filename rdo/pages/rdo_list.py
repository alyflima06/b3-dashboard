import streamlit as st
import rdo.database as db

STATUS_CONFIG = {
    "rascunho":  {"label": "Rascunho",  "color": "🟡", "badge": "secondary"},
    "pendente":  {"label": "Pendente",  "color": "🔵", "badge": "primary"},
    "aprovado":  {"label": "Aprovado",  "color": "🟢", "badge": "primary"},
    "rejeitado": {"label": "Rejeitado", "color": "🔴", "badge": "primary"},
}


def render():
    obra = st.session_state.get("obra_selecionada")
    if not obra:
        st.warning("Selecione uma obra na barra lateral.")
        return

    obra_id = obra["id"]
    st.title(f"📁 RDOs — {obra['nome']}")

    col_filter, col_new = st.columns([3, 1])
    status_opts = ["Todos", "rascunho", "pendente", "aprovado", "rejeitado"]
    status_sel = col_filter.selectbox(
        "Filtrar por status",
        options=status_opts,
        format_func=lambda s: "Todos" if s == "Todos" else STATUS_CONFIG[s]["label"],
        key="rdo_list_filter",
    )
    if col_new.button("➕ Novo RDO", type="primary", use_container_width=True):
        st.session_state["edit_rdo_id"] = None
        for key in ["rdo_form_data","rdo_equipe_rows","rdo_ativ_rows","rdo_serv_rows",
                    "rdo_mat_rows","rdo_equip_rows","rdo_ocor_rows"]:
            st.session_state.pop(key, None)
        st.session_state["page"] = "novo_rdo"
        st.rerun()

    filter_list = None if status_sel == "Todos" else [status_sel]
    rdos = db.get_rdos_by_obra(obra_id, status_filter=filter_list)

    if not rdos:
        st.info("Nenhum RDO encontrado para este filtro.")
        return

    st.caption(f"{len(rdos)} RDO(s) encontrado(s)")

    for rdo in rdos:
        cfg = STATUS_CONFIG.get(rdo["status"], STATUS_CONFIG["rascunho"])
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([1, 2, 3, 1])
            col1.markdown(f"### #{rdo['numero_rdo']:03d}")
            col2.markdown(
                f"**{rdo['data_relatorio']}**  \n"
                f"👷 {rdo['engenheiro_nome']}"
            )
            col3.markdown(
                f"{cfg['color']} **{cfg['label']}**"
                + (f"  \n💬 _{rdo['comentario_aprovacao']}_" if rdo.get("comentario_aprovacao") and rdo["status"] in ("aprovado","rejeitado") else "")
            )
            with col4:
                if st.button("👁️ Ver", key=f"ver_{rdo['id']}", use_container_width=True):
                    st.session_state["view_rdo_id"] = rdo["id"]
                    st.session_state["page"] = "ver_rdo"
                    st.rerun()
                if rdo["status"] in ("rascunho", "rejeitado"):
                    if st.button("✏️ Editar", key=f"edit_{rdo['id']}", use_container_width=True):
                        for key in ["rdo_form_data","rdo_equipe_rows","rdo_ativ_rows","rdo_serv_rows",
                                    "rdo_mat_rows","rdo_equip_rows","rdo_ocor_rows"]:
                            st.session_state.pop(key, None)
                        st.session_state["edit_rdo_id"] = rdo["id"]
                        st.session_state["page"] = "editar_rdo"
                        st.rerun()
