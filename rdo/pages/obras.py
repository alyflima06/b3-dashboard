import streamlit as st
import rdo.database as db


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
                col1.markdown(f"**{o['nome']}**  \n{ativo_badge} &nbsp;|&nbsp; Cliente: {o['cliente'] or '—'}")
                col2.markdown(
                    f"Orçamento: **R$ {o['orcamento']:,.2f}**  \n"
                    f"Gasto (aprovado): R$ {o['gasto_aprovado']:,.2f}  \n"
                    f"RDOs: {o['total_rdos']}"
                )
                with col3:
                    if o["ativo"]:
                        if st.button("✏️", key=f"edit_obra_{o['id']}", help="Editar"):
                            st.session_state[f"editing_obra_{o['id']}"] = True
                            st.rerun()
                        if st.button("📦 Arquivar", key=f"arch_{o['id']}"):
                            db.archive_obra(o["id"])
                            st.success(f"Obra '{o['nome']}' arquivada.")
                            st.rerun()
                    else:
                        if st.button("♻️ Reativar", key=f"react_{o['id']}"):
                            db.reactivate_obra(o["id"])
                            st.success(f"Obra '{o['nome']}' reativada.")
                            st.rerun()

                # Inline edit form
                if st.session_state.get(f"editing_obra_{o['id']}"):
                    with st.form(key=f"form_edit_obra_{o['id']}"):
                        st.markdown("**Editar Obra**")
                        c1, c2 = st.columns(2)
                        nome_e = c1.text_input("Nome", value=o["nome"])
                        cliente_e = c2.text_input("Cliente", value=o["cliente"] or "")
                        end_e = st.text_input("Endereço", value=o["endereco"] or "")
                        orc_e = st.number_input("Orçamento (R$)", value=float(o["orcamento"] or 0),
                                                min_value=0.0, step=1000.0, format="%.2f")
                        s1, s2 = st.columns(2)
                        if s1.form_submit_button("💾 Salvar", type="primary"):
                            if nome_e.strip():
                                db.update_obra(o["id"], nome_e.strip(), end_e.strip(),
                                               cliente_e.strip(), orc_e)
                                st.session_state.pop(f"editing_obra_{o['id']}", None)
                                st.success("Obra atualizada.")
                                st.rerun()
                            else:
                                st.error("Nome é obrigatório.")
                        if s2.form_submit_button("Cancelar"):
                            st.session_state.pop(f"editing_obra_{o['id']}", None)
                            st.rerun()

    st.divider()

    # ── Nova Obra ─────────────────────────────────────────────────────────────
    st.subheader("➕ Nova Obra")
    with st.form("form_nova_obra"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome da obra *")
        cliente = c2.text_input("Cliente")
        endereco = st.text_input("Endereço")
        orcamento = st.number_input("Orçamento Total (R$)", min_value=0.0, step=1000.0,
                                    format="%.2f", value=0.0)
        submitted = st.form_submit_button("Criar Obra", type="primary")

    if submitted:
        if not nome.strip():
            st.error("O nome da obra é obrigatório.")
        else:
            db.create_obra(nome.strip(), endereco.strip(), cliente.strip(), orcamento)
            st.success(f"Obra '{nome.strip()}' criada com sucesso!")
            st.rerun()
