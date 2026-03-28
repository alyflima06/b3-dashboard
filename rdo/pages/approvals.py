import streamlit as st
import rdo.database as db


def _render_rdo_summary(rdo: dict):
    """Render a compact read-only summary of an RDO for coordinator review."""
    st.markdown(f"**Obra:** {rdo['obra_nome']} | **Data:** {rdo['data_relatorio']} | **Engenheiro:** {rdo['engenheiro_nome']}")

    col1, col2, col3 = st.columns(3)
    total_workers = sum(int(e.get("quantidade",0)) for e in rdo.get("equipe",[]))
    total_materiais = sum(float(m.get("valor_total",0)) for m in rdo.get("materiais",[]))
    col1.metric("Trabalhadores", total_workers)
    col2.metric("Custo Materiais", f"R$ {total_materiais:,.2f}")
    col3.metric("Ocorrências", len(rdo.get("ocorrencias",[])))

    if rdo.get("atividades"):
        st.caption("**Atividades:**")
        for a in rdo["atividades"]:
            pct = float(a.get("percentual",0))
            st.markdown(f"- {a['descricao']} — **{pct:.0f}%**")

    if rdo.get("materiais"):
        st.caption("**Materiais:**")
        for m in rdo["materiais"]:
            st.markdown(
                f"- {m['material']} ({m.get('quantidade',0)} {m.get('unidade','')}) "
                f"= R$ {float(m.get('valor_total',0)):,.2f}"
            )

    if rdo.get("ocorrencias"):
        st.caption("**Ocorrências:**")
        for oc in rdo["ocorrencias"]:
            st.markdown(f"- **[{oc.get('tipo','—')}]** {oc['descricao']}")

    if rdo.get("comentarios_gerais"):
        st.caption(f"**Comentários:** {rdo['comentarios_gerais']}")


def render():
    if not st.session_state.get("coord_mode"):
        st.error("Acesso restrito ao coordenador.")
        return

    st.title("✅ Aprovações de RDO")

    pendentes = db.get_pending_rdos()

    if not pendentes:
        st.success("Nenhum RDO aguardando aprovação.")
        return

    st.info(f"{len(pendentes)} RDO(s) aguardando aprovação.")

    for rdo_meta in pendentes:
        rdo_id = rdo_meta["id"]
        key_prefix = f"aprov_{rdo_id}"

        with st.container(border=True):
            col_header, col_btn = st.columns([4, 1])
            col_header.markdown(
                f"### RDO #{rdo_meta['numero_rdo']:03d} — {rdo_meta['obra_nome']}\n"
                f"📅 {rdo_meta['data_relatorio']} | 👷 {rdo_meta['engenheiro_nome']}"
            )
            expand_key = f"expand_{rdo_id}"
            if expand_key not in st.session_state:
                st.session_state[expand_key] = False

            if col_btn.button(
                "📖 Revisar" if not st.session_state[expand_key] else "▲ Fechar",
                key=f"toggle_{rdo_id}",
                use_container_width=True
            ):
                st.session_state[expand_key] = not st.session_state[expand_key]
                st.rerun()

            if st.session_state.get(expand_key):
                rdo_full = db.get_rdo_full(rdo_id)
                if rdo_full:
                    with st.container():
                        _render_rdo_summary(rdo_full)

                    st.divider()
                    comentario = st.text_area(
                        "Comentário (obrigatório para rejeição, opcional para aprovação)",
                        key=f"comment_{rdo_id}",
                        placeholder="Digite seu comentário...",
                        height=80,
                    )

                    col_ap, col_rej, col_ver = st.columns(3)
                    if col_ap.button("✅ Aprovar", key=f"btn_ap_{rdo_id}", type="primary", use_container_width=True):
                        db.approve_rdo(rdo_id, comentario)
                        st.session_state.pop(expand_key, None)
                        st.success(f"RDO #{rdo_meta['numero_rdo']:03d} aprovado. Dashboard atualizado!")
                        st.rerun()

                    if col_rej.button("❌ Rejeitar", key=f"btn_rej_{rdo_id}", type="secondary", use_container_width=True):
                        if not comentario.strip():
                            st.error("Informe o motivo da rejeição.")
                        else:
                            db.reject_rdo(rdo_id, comentario)
                            st.session_state.pop(expand_key, None)
                            st.warning(f"RDO #{rdo_meta['numero_rdo']:03d} rejeitado.")
                            st.rerun()

                    if col_ver.button("👁️ Ver Completo", key=f"btn_ver_{rdo_id}", use_container_width=True):
                        st.session_state["view_rdo_id"] = rdo_id
                        st.session_state["page"] = "ver_rdo"
                        st.rerun()
