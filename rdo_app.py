import streamlit as st
from rdo.database import init_db, get_obras_ativas
from rdo.auth import verify_coord_password

st.set_page_config(
    page_title="RDO — Gestão de Obras",
    page_icon="🏗️",
    layout="wide",
)

# ── Inicializa banco na primeira execução ─────────────────────────────────────
init_db()

# ── Estado global ─────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state["page"] = "novo_rdo"
if "coord_mode" not in st.session_state:
    st.session_state["coord_mode"] = False
if "view_rdo_id" not in st.session_state:
    st.session_state["view_rdo_id"] = None
if "edit_rdo_id" not in st.session_state:
    st.session_state["edit_rdo_id"] = None


def nav_to(page: str):
    st.session_state["page"] = page
    st.session_state["view_rdo_id"] = None
    st.session_state["edit_rdo_id"] = None


# ── Modal de senha do coordenador ─────────────────────────────────────────────
@st.dialog("🔒 Área do Coordenador")
def coord_login_dialog():
    senha = st.text_input("Senha", type="password", key="coord_senha_input")
    col1, col2 = st.columns(2)
    if col1.button("Entrar", type="primary", use_container_width=True):
        if verify_coord_password(senha):
            st.session_state["coord_mode"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    if col2.button("Cancelar", use_container_width=True):
        st.rerun()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏗️ RDO — Gestão de Obras")

    obras = get_obras_ativas()
    if obras:
        obra_options = {o["nome"]: o for o in obras}
        obra_atual = st.session_state.get("obra_selecionada_nome")
        if obra_atual not in obra_options:
            obra_atual = list(obra_options.keys())[0]
        obra_nome = st.selectbox(
            "Selecione a obra",
            options=list(obra_options.keys()),
            index=list(obra_options.keys()).index(obra_atual),
            key="obra_select",
        )
        st.session_state["obra_selecionada_nome"] = obra_nome
        st.session_state["obra_selecionada"] = obra_options[obra_nome]
    else:
        st.warning("Nenhuma obra cadastrada.")
        st.session_state["obra_selecionada"] = None
        st.session_state["obra_selecionada_nome"] = None

    st.divider()

    if not st.session_state["coord_mode"]:
        # Modo engenheiro
        if st.button("📋 Novo RDO", use_container_width=True,
                     type="primary" if st.session_state["page"] == "novo_rdo" else "secondary"):
            nav_to("novo_rdo")
            st.rerun()

        if st.button("📁 Ver RDOs", use_container_width=True,
                     type="primary" if st.session_state["page"] == "ver_rdos" else "secondary"):
            nav_to("ver_rdos")
            st.rerun()

        st.divider()
        if st.button("🔒 Área do Coordenador", use_container_width=True):
            coord_login_dialog()
    else:
        # Modo coordenador
        st.success("✅ Modo Coordenador")

        pages_coord = {
            "aprovacoes": "✅ Aprovações",
            "obras":      "🏗️ Obras",
            "engenheiros": "👷 Engenheiros",
        }
        for page_key, label in pages_coord.items():
            is_active = st.session_state["page"] == page_key
            if st.button(label, use_container_width=True,
                         type="primary" if is_active else "secondary",
                         key=f"nav_{page_key}"):
                nav_to(page_key)
                st.rerun()

        st.divider()
        if st.button("🚪 Sair do modo coordenador", use_container_width=True):
            st.session_state["coord_mode"] = False
            nav_to("novo_rdo")
            st.rerun()


# ── Roteamento de páginas ─────────────────────────────────────────────────────
page = st.session_state["page"]

if page in ("novo_rdo", "editar_rdo"):
    from rdo.pages import rdo_form
    rdo_form.render()

elif page == "ver_rdos":
    if st.session_state.get("view_rdo_id"):
        from rdo.pages import rdo_view
        rdo_view.render()
    else:
        from rdo.pages import rdo_list
        rdo_list.render()

elif page == "ver_rdo":
    from rdo.pages import rdo_view
    rdo_view.render()

elif page == "aprovacoes":
    if not st.session_state["coord_mode"]:
        st.error("Acesso restrito ao coordenador.")
    else:
        from rdo.pages import approvals
        approvals.render()

elif page == "obras":
    if not st.session_state["coord_mode"]:
        st.error("Acesso restrito ao coordenador.")
    else:
        from rdo.pages import obras
        obras.render()

elif page == "engenheiros":
    if not st.session_state["coord_mode"]:
        st.error("Acesso restrito ao coordenador.")
    else:
        from rdo.pages import admin_engineers
        admin_engineers.render()

else:
    nav_to("novo_rdo")
    st.rerun()
