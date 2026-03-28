import streamlit as st
import rdo.database as db
from rdo.auth import verify_coord_password, update_coord_password


def render():
    st.title("👷 Gerenciamento de Engenheiros")

    engenheiros = db.get_all_engenheiros()

    # ── Listagem ──────────────────────────────────────────────────────────────
    st.subheader("Engenheiros Cadastrados")

    if not engenheiros:
        st.info("Nenhum engenheiro cadastrado ainda.")
    else:
        for e in engenheiros:
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                badge = "🟢 Ativo" if e["ativo"] else "🔴 Inativo"
                col1.markdown(f"**{e['nome']}**  &nbsp;&nbsp; {badge}")
                with col2:
                    if e["ativo"]:
                        if st.button("Desativar", key=f"deact_{e['id']}", type="secondary"):
                            db.toggle_engenheiro(e["id"], False)
                            st.success(f"'{e['nome']}' desativado.")
                            st.rerun()
                    else:
                        if st.button("Reativar", key=f"react_{e['id']}", type="primary"):
                            db.toggle_engenheiro(e["id"], True)
                            st.success(f"'{e['nome']}' reativado.")
                            st.rerun()

    st.divider()

    # ── Novo Engenheiro ───────────────────────────────────────────────────────
    st.subheader("➕ Novo Engenheiro")
    with st.form("form_novo_eng"):
        nome = st.text_input("Nome completo *")
        submitted = st.form_submit_button("Cadastrar", type="primary")

    if submitted:
        if not nome.strip():
            st.error("O nome é obrigatório.")
        else:
            try:
                db.create_engenheiro(nome.strip())
                st.success(f"Engenheiro '{nome.strip()}' cadastrado.")
                st.rerun()
            except Exception:
                st.error("Já existe um engenheiro com esse nome.")

    st.divider()

    # ── Alterar Senha do Coordenador ──────────────────────────────────────────
    st.subheader("🔑 Alterar Senha do Coordenador")
    with st.form("form_senha"):
        senha_atual = st.text_input("Senha atual", type="password")
        nova_senha = st.text_input("Nova senha", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        trocar = st.form_submit_button("Alterar senha", type="primary")

    if trocar:
        if not verify_coord_password(senha_atual):
            st.error("Senha atual incorreta.")
        elif len(nova_senha) < 6:
            st.error("A nova senha deve ter ao menos 6 caracteres.")
        elif nova_senha != confirmar:
            st.error("As senhas não conferem.")
        else:
            update_coord_password(nova_senha)
            st.success("Senha alterada com sucesso!")
