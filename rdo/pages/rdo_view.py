import streamlit as st
from pathlib import Path
import rdo.database as db

STATUS_CONFIG = {
    "rascunho":  {"label": "Rascunho",  "color": "🟡"},
    "pendente":  {"label": "Aguardando Aprovação", "color": "🔵"},
    "aprovado":  {"label": "Aprovado",  "color": "🟢"},
    "rejeitado": {"label": "Rejeitado", "color": "🔴"},
}


def render():
    rdo_id = st.session_state.get("view_rdo_id")
    if not rdo_id:
        st.session_state["page"] = "ver_rdos"
        st.rerun()
        return

    rdo = db.get_rdo_full(rdo_id)
    if not rdo:
        st.error("RDO não encontrado.")
        return

    cfg = STATUS_CONFIG.get(rdo["status"], STATUS_CONFIG["rascunho"])

    # Header
    col_title, col_back = st.columns([4, 1])
    col_title.title(f"📄 RDO #{rdo['numero_rdo']:03d} — {rdo['obra_nome']}")
    if col_back.button("◀ Voltar", use_container_width=True):
        st.session_state["view_rdo_id"] = None
        st.session_state["page"] = "ver_rdos"
        st.rerun()

    # Status banner
    status_color_map = {
        "rascunho": "🟡",
        "pendente": "🔵",
        "aprovado": "🟢",
        "rejeitado": "🔴",
    }
    st.markdown(
        f"**Status:** {cfg['color']} {cfg['label']}"
        + (f"  |  **Data Aprovação:** {rdo['data_aprovacao'][:10] if rdo.get('data_aprovacao') else '—'}" if rdo["status"] == "aprovado" else "")
    )
    if rdo.get("comentario_aprovacao"):
        st.info(f"💬 **Comentário do coordenador:** {rdo['comentario_aprovacao']}")

    # Action buttons
    if rdo["status"] in ("rascunho", "rejeitado"):
        col_e, col_s = st.columns(2)
        if col_e.button("✏️ Editar RDO", type="primary", use_container_width=True):
            for key in ["rdo_form_data","rdo_equipe_rows","rdo_ativ_rows","rdo_serv_rows",
                        "rdo_mat_rows","rdo_equip_rows","rdo_ocor_rows"]:
                st.session_state.pop(key, None)
            st.session_state["edit_rdo_id"] = rdo_id
            st.session_state["page"] = "editar_rdo"
            st.rerun()
        if rdo["status"] == "rascunho":
            if col_s.button("📤 Enviar para Aprovação", type="secondary", use_container_width=True):
                db.submit_rdo(rdo_id)
                st.success("RDO enviado para aprovação!")
                st.rerun()

    st.divider()

    # ── Identificação ─────────────────────────────────────────────────────────
    with st.expander("📋 Identificação", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Data", rdo["data_relatorio"])
        col2.metric("Engenheiro", rdo["engenheiro_nome"])
        col3.metric("Obra", rdo["obra_nome"])

    # ── Clima ─────────────────────────────────────────────────────────────────
    with st.expander("🌤️ Condições Climáticas"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Manhã", f"{rdo.get('clima_manha','—')} {rdo.get('temperatura_manha') or ''}°C".strip())
        col2.metric("Tarde", f"{rdo.get('clima_tarde','—')} {rdo.get('temperatura_tarde') or ''}°C".strip())
        col3.metric("Noite", f"{rdo.get('clima_noite','—')} {rdo.get('temperatura_noite') or ''}°C".strip())

    # ── Equipe ────────────────────────────────────────────────────────────────
    with st.expander(f"👷 Equipe de Trabalho ({len(rdo.get('equipe', []))} registros)"):
        if rdo.get("equipe"):
            total = sum(int(e.get("quantidade",0)) for e in rdo["equipe"])
            for e in rdo["equipe"]:
                st.markdown(f"- **{e.get('funcao','—')}**: {e.get('quantidade',1)} profissional(is)"
                            + (f" — {e['nome_empresa']}" if e.get("nome_empresa") else ""))
            st.caption(f"Total: {total} trabalhadores")
        else:
            st.info("Nenhum registro de equipe.")

    # ── Atividades ────────────────────────────────────────────────────────────
    with st.expander(f"🔨 Atividades Executadas ({len(rdo.get('atividades', []))} registros)"):
        if rdo.get("atividades"):
            for a in rdo["atividades"]:
                pct = float(a.get("percentual",0))
                st.markdown(f"**{a['descricao']}** — {pct:.0f}% concluído")
                st.progress(int(min(pct, 100)))
                if a.get("observacoes"):
                    st.caption(f"Obs: {a['observacoes']}")
        else:
            st.info("Nenhuma atividade registrada.")

    # ── Serviços ──────────────────────────────────────────────────────────────
    with st.expander(f"🔧 Serviços em Andamento ({len(rdo.get('servicos', []))} registros)"):
        if rdo.get("servicos"):
            for s in rdo["servicos"]:
                st.markdown(f"- {s['descricao']}")
        else:
            st.info("Nenhum serviço registrado.")

    # ── Materiais ─────────────────────────────────────────────────────────────
    with st.expander(f"📦 Materiais Recebidos ({len(rdo.get('materiais', []))} registros)"):
        if rdo.get("materiais"):
            total_custo = sum(float(m.get("valor_total",0)) for m in rdo["materiais"])
            for m in rdo["materiais"]:
                st.markdown(
                    f"- **{m['material']}** — {m.get('quantidade',0)} {m.get('unidade','')} "
                    f"| R$ {float(m.get('valor_unitario',0)):,.2f}/un "
                    f"= **R$ {float(m.get('valor_total',0)):,.2f}**"
                    + (f" | Fornecedor: {m['fornecedor']}" if m.get("fornecedor") else "")
                )
            st.metric("Total de Materiais", f"R$ {total_custo:,.2f}")
        else:
            st.info("Nenhum material registrado.")

    # ── Equipamentos ──────────────────────────────────────────────────────────
    with st.expander(f"🏗️ Equipamentos Locados ({len(rdo.get('equipamentos', []))} registros)"):
        if rdo.get("equipamentos"):
            status_label = {"ativo": "Ativo", "parado": "Parado", "saindo": "Saindo"}
            for eq in rdo["equipamentos"]:
                st.markdown(f"- **{eq['equipamento']}** — {eq.get('quantidade',1)} un. | {status_label.get(eq.get('status_eq','ativo'),'')}")
        else:
            st.info("Nenhum equipamento registrado.")

    # ── Ocorrências ───────────────────────────────────────────────────────────
    with st.expander(f"⚠️ Ocorrências / Interferências ({len(rdo.get('ocorrencias', []))} registros)"):
        if rdo.get("ocorrencias"):
            tipo_emoji = {"Segurança":"🦺","Qualidade":"📐","Prazo":"⏰","Custo":"💰",
                          "Ambiental":"🌿","Interferência":"⚡","Outra":"📝"}
            for oc in rdo["ocorrencias"]:
                emoji = tipo_emoji.get(oc.get("tipo","Outra"),"📝")
                st.markdown(f"{emoji} **[{oc.get('tipo','—')}]** {oc['descricao']}")
                if oc.get("acao_tomada"):
                    st.caption(f"Ação tomada: {oc['acao_tomada']}")
        else:
            st.info("Nenhuma ocorrência registrada.")

    # ── Fotos ─────────────────────────────────────────────────────────────────
    with st.expander(f"📷 Registro Fotográfico ({len(rdo.get('fotos', []))} foto(s))"):
        if rdo.get("fotos"):
            cols = st.columns(3)
            for i, foto in enumerate(rdo["fotos"]):
                with cols[i % 3]:
                    try:
                        p = Path(foto["file_path"])
                        if p.exists():
                            st.image(str(p), caption=foto.get("legenda",""), use_container_width=True)
                        else:
                            st.caption(f"Arquivo não encontrado: {foto.get('legenda','')}")
                    except Exception:
                        st.caption(foto.get("legenda","Foto"))
        else:
            st.info("Nenhuma foto registrada.")

    # ── Comentários ───────────────────────────────────────────────────────────
    if rdo.get("comentarios_gerais"):
        with st.expander("💬 Comentários Gerais", expanded=True):
            st.write(rdo["comentarios_gerais"])
