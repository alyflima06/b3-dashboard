import sqlite3
import os
import uuid
from pathlib import Path

DB_PATH = Path("rdo_data/rdo.db")
PHOTO_BASE = Path("rdo_data/photos")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS obras (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT NOT NULL,
                endereco   TEXT,
                cliente    TEXT,
                orcamento  REAL DEFAULT 0,
                ativo      INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS engenheiros (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT NOT NULL UNIQUE,
                ativo      INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS rdos (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id              INTEGER NOT NULL REFERENCES obras(id),
                numero_rdo           INTEGER NOT NULL,
                data_relatorio       TEXT NOT NULL,
                engenheiro_id        INTEGER NOT NULL REFERENCES engenheiros(id),
                status               TEXT NOT NULL DEFAULT 'rascunho'
                                       CHECK(status IN ('rascunho','pendente','aprovado','rejeitado')),
                clima_manha          TEXT,
                clima_tarde          TEXT,
                clima_noite          TEXT,
                temperatura_manha    REAL,
                temperatura_tarde    REAL,
                temperatura_noite    REAL,
                comentarios_gerais   TEXT,
                comentario_aprovacao TEXT,
                data_aprovacao       TEXT,
                created_at           TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at           TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(obra_id, numero_rdo)
            );

            CREATE TABLE IF NOT EXISTS rdo_equipe (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                rdo_id       INTEGER NOT NULL REFERENCES rdos(id) ON DELETE CASCADE,
                funcao       TEXT NOT NULL,
                quantidade   INTEGER NOT NULL DEFAULT 1,
                nome_empresa TEXT
            );

            CREATE TABLE IF NOT EXISTS rdo_atividades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                rdo_id      INTEGER NOT NULL REFERENCES rdos(id) ON DELETE CASCADE,
                descricao   TEXT NOT NULL,
                percentual  REAL DEFAULT 0,
                observacoes TEXT
            );

            CREATE TABLE IF NOT EXISTS rdo_servicos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                rdo_id    INTEGER NOT NULL REFERENCES rdos(id) ON DELETE CASCADE,
                descricao TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rdo_materiais (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                rdo_id         INTEGER NOT NULL REFERENCES rdos(id) ON DELETE CASCADE,
                material       TEXT NOT NULL,
                quantidade     REAL NOT NULL DEFAULT 0,
                unidade        TEXT,
                fornecedor     TEXT,
                valor_unitario REAL DEFAULT 0,
                valor_total    REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS rdo_equipamentos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                rdo_id      INTEGER NOT NULL REFERENCES rdos(id) ON DELETE CASCADE,
                equipamento TEXT NOT NULL,
                quantidade  INTEGER NOT NULL DEFAULT 1,
                status_eq   TEXT NOT NULL DEFAULT 'ativo'
                                CHECK(status_eq IN ('ativo','parado','saindo'))
            );

            CREATE TABLE IF NOT EXISTS rdo_ocorrencias (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                rdo_id      INTEGER NOT NULL REFERENCES rdos(id) ON DELETE CASCADE,
                tipo        TEXT NOT NULL,
                descricao   TEXT NOT NULL,
                acao_tomada TEXT
            );

            CREATE TABLE IF NOT EXISTS rdo_fotos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                rdo_id    INTEGER NOT NULL REFERENCES rdos(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                legenda   TEXT,
                ordem     INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS cronograma (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id              INTEGER NOT NULL REFERENCES obras(id) ON DELETE CASCADE,
                atividade            TEXT NOT NULL,
                data_inicio          TEXT NOT NULL,
                data_fim             TEXT NOT NULL,
                peso_percentual      REAL DEFAULT 0,
                percentual_executado REAL DEFAULT 0,
                ordem                INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS orcamento_itens (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                obra_id   INTEGER NOT NULL REFERENCES obras(id) ON DELETE CASCADE,
                item      TEXT NOT NULL,
                descricao TEXT,
                valor     REAL DEFAULT 0
            );
        """)
    # Migration: add new columns to obras if they don't exist yet
    for col, definition in [
        ("data_inicio", "TEXT"),
        ("data_prazo",  "TEXT"),
        ("responsavel", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE obras ADD COLUMN {col} {definition}")
            conn.commit()
        except Exception:
            pass  # Column already exists
    conn.close()
    seed_demo_data()


def seed_demo_data() -> None:
    import bcrypt
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key='coord_password_hash'").fetchone()
        if row:
            conn.close()
            return
        hash_ = bcrypt.hashpw(b"coordenador123", bcrypt.gensalt()).decode()
        with conn:
            conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('coord_password_hash',?)", (hash_,))
            for nome, end, cli, orc in [
                ("Residencial Park Sul", "Av. das Flores, 100 — São Paulo/SP", "Construtora ABC", 2500000.0),
                ("Edifício Comercial Centro", "Rua XV de Novembro, 500 — Curitiba/PR", "Grupo Delta", 8000000.0),
                ("Galpão Industrial Norte", "Rod. BR-116, km 45 — Guarulhos/SP", "Indústrias XYZ", 1200000.0),
            ]:
                conn.execute(
                    "INSERT OR IGNORE INTO obras(nome,endereco,cliente,orcamento) VALUES(?,?,?,?)",
                    (nome, end, cli, orc)
                )
            for eng in ["Carlos Menezes", "Ana Ferreira", "Ricardo Souza"]:
                conn.execute("INSERT OR IGNORE INTO engenheiros(nome) VALUES(?)", (eng,))
    finally:
        conn.close()


# ── Settings ──────────────────────────────────────────────────────────────────

def get_setting(key: str) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def update_setting(key: str, value: str) -> None:
    conn = get_connection()
    with conn:
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.close()


# ── Obras ─────────────────────────────────────────────────────────────────────

def get_obras_ativas() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM obras WHERE ativo=1 ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_obras() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT o.*,
               COUNT(r.id) AS total_rdos,
               COALESCE(SUM(CASE WHEN r.status='aprovado' THEN m.soma ELSE 0 END),0) AS gasto_aprovado
        FROM obras o
        LEFT JOIN rdos r ON r.obra_id = o.id
        LEFT JOIN (
            SELECT rdo_id, SUM(valor_total) AS soma FROM rdo_materiais GROUP BY rdo_id
        ) m ON m.rdo_id = r.id
        GROUP BY o.id
        ORDER BY o.nome
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_obra(nome: str, endereco: str, cliente: str, orcamento: float,
                data_inicio: str = "", data_prazo: str = "", responsavel: str = "") -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO obras(nome,endereco,cliente,orcamento,data_inicio,data_prazo,responsavel) VALUES(?,?,?,?,?,?,?)",
            (nome, endereco, cliente, orcamento, data_inicio or None, data_prazo or None, responsavel or None)
        )
    conn.close()
    return cur.lastrowid


def update_obra(obra_id: int, nome: str, endereco: str, cliente: str, orcamento: float,
                data_inicio: str = "", data_prazo: str = "", responsavel: str = "") -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE obras SET nome=?,endereco=?,cliente=?,orcamento=?,data_inicio=?,data_prazo=?,responsavel=? WHERE id=?",
            (nome, endereco, cliente, orcamento,
             data_inicio or None, data_prazo or None, responsavel or None, obra_id)
        )
    conn.close()


def archive_obra(obra_id: int) -> None:
    conn = get_connection()
    with conn:
        conn.execute("UPDATE obras SET ativo=0 WHERE id=?", (obra_id,))
    conn.close()


def reactivate_obra(obra_id: int) -> None:
    conn = get_connection()
    with conn:
        conn.execute("UPDATE obras SET ativo=1 WHERE id=?", (obra_id,))
    conn.close()


# ── Engenheiros ───────────────────────────────────────────────────────────────

def get_engenheiros_ativos() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM engenheiros WHERE ativo=1 ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_engenheiros() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM engenheiros ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_engenheiro(nome: str) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute("INSERT INTO engenheiros(nome) VALUES(?)", (nome,))
    conn.close()
    return cur.lastrowid


def toggle_engenheiro(eng_id: int, ativo: bool) -> None:
    conn = get_connection()
    with conn:
        conn.execute("UPDATE engenheiros SET ativo=? WHERE id=?", (1 if ativo else 0, eng_id))
    conn.close()


# ── RDOs ──────────────────────────────────────────────────────────────────────

def next_rdo_number(obra_id: int) -> int:
    conn = get_connection()
    with conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(numero_rdo),0)+1 AS next FROM rdos WHERE obra_id=?",
            (obra_id,)
        ).fetchone()
    conn.close()
    return row["next"]


def save_rdo(header: dict, children: dict, rdo_id: int | None = None) -> int:
    """
    Insert or update an RDO and all its child rows in a single transaction.
    header: dict with RDO main fields
    children: dict with keys equipe, atividades, servicos, materiais, equipamentos, ocorrencias
    Returns the rdo_id.
    """
    conn = get_connection()
    try:
        with conn:
            if rdo_id is None:
                numero = next_rdo_number(header["obra_id"])
                cur = conn.execute("""
                    INSERT INTO rdos(obra_id, numero_rdo, data_relatorio, engenheiro_id,
                        clima_manha, clima_tarde, clima_noite,
                        temperatura_manha, temperatura_tarde, temperatura_noite,
                        comentarios_gerais, status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,'rascunho')
                """, (
                    header["obra_id"], numero, header["data_relatorio"], header["engenheiro_id"],
                    header.get("clima_manha"), header.get("clima_tarde"), header.get("clima_noite"),
                    header.get("temperatura_manha"), header.get("temperatura_tarde"), header.get("temperatura_noite"),
                    header.get("comentarios_gerais"),
                ))
                rdo_id = cur.lastrowid
            else:
                conn.execute("""
                    UPDATE rdos SET
                        data_relatorio=?, engenheiro_id=?,
                        clima_manha=?, clima_tarde=?, clima_noite=?,
                        temperatura_manha=?, temperatura_tarde=?, temperatura_noite=?,
                        comentarios_gerais=?,
                        updated_at=datetime('now')
                    WHERE id=?
                """, (
                    header["data_relatorio"], header["engenheiro_id"],
                    header.get("clima_manha"), header.get("clima_tarde"), header.get("clima_noite"),
                    header.get("temperatura_manha"), header.get("temperatura_tarde"), header.get("temperatura_noite"),
                    header.get("comentarios_gerais"),
                    rdo_id,
                ))
                # Delete and re-insert child rows (photos kept separately)
                for tbl in ["rdo_equipe","rdo_atividades","rdo_servicos",
                            "rdo_materiais","rdo_equipamentos","rdo_ocorrencias"]:
                    conn.execute(f"DELETE FROM {tbl} WHERE rdo_id=?", (rdo_id,))

            # Insert child rows
            for row in children.get("equipe", []):
                if row.get("funcao","").strip():
                    conn.execute(
                        "INSERT INTO rdo_equipe(rdo_id,funcao,quantidade,nome_empresa) VALUES(?,?,?,?)",
                        (rdo_id, row["funcao"], row.get("quantidade",1), row.get("nome_empresa",""))
                    )
            for row in children.get("atividades", []):
                if row.get("descricao","").strip():
                    conn.execute(
                        "INSERT INTO rdo_atividades(rdo_id,descricao,percentual,observacoes) VALUES(?,?,?,?)",
                        (rdo_id, row["descricao"], row.get("percentual",0), row.get("observacoes",""))
                    )
            for row in children.get("servicos", []):
                if row.get("descricao","").strip():
                    conn.execute(
                        "INSERT INTO rdo_servicos(rdo_id,descricao) VALUES(?,?)",
                        (rdo_id, row["descricao"])
                    )
            for row in children.get("materiais", []):
                if row.get("material","").strip():
                    qtd = float(row.get("quantidade",0) or 0)
                    vu = float(row.get("valor_unitario",0) or 0)
                    conn.execute(
                        """INSERT INTO rdo_materiais(rdo_id,material,quantidade,unidade,
                           fornecedor,valor_unitario,valor_total) VALUES(?,?,?,?,?,?,?)""",
                        (rdo_id, row["material"], qtd, row.get("unidade",""),
                         row.get("fornecedor",""), vu, round(qtd * vu, 2))
                    )
            for row in children.get("equipamentos", []):
                if row.get("equipamento","").strip():
                    conn.execute(
                        "INSERT INTO rdo_equipamentos(rdo_id,equipamento,quantidade,status_eq) VALUES(?,?,?,?)",
                        (rdo_id, row["equipamento"], row.get("quantidade",1),
                         row.get("status_eq","ativo"))
                    )
            for row in children.get("ocorrencias", []):
                if row.get("descricao","").strip():
                    conn.execute(
                        "INSERT INTO rdo_ocorrencias(rdo_id,tipo,descricao,acao_tomada) VALUES(?,?,?,?)",
                        (rdo_id, row.get("tipo","Outra"), row["descricao"], row.get("acao_tomada",""))
                    )
    finally:
        conn.close()
    return rdo_id


def submit_rdo(rdo_id: int) -> None:
    conn = get_connection()
    with conn:
        conn.execute("UPDATE rdos SET status='pendente', updated_at=datetime('now') WHERE id=?", (rdo_id,))
    conn.close()


def reopen_rdo(rdo_id: int) -> None:
    conn = get_connection()
    with conn:
        conn.execute("UPDATE rdos SET status='rascunho', updated_at=datetime('now') WHERE id=?", (rdo_id,))
    conn.close()


def get_rdos_by_obra(obra_id: int, status_filter: list | None = None) -> list[dict]:
    conn = get_connection()
    query = """
        SELECT r.*, e.nome AS engenheiro_nome, o.nome AS obra_nome
        FROM rdos r
        JOIN engenheiros e ON e.id = r.engenheiro_id
        JOIN obras o ON o.id = r.obra_id
        WHERE r.obra_id=?
    """
    params: list = [obra_id]
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        query += f" AND r.status IN ({placeholders})"
        params.extend(status_filter)
    query += " ORDER BY r.numero_rdo DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_rdos(status_filter: list | None = None) -> list[dict]:
    conn = get_connection()
    query = """
        SELECT r.*, e.nome AS engenheiro_nome, o.nome AS obra_nome
        FROM rdos r
        JOIN engenheiros e ON e.id = r.engenheiro_id
        JOIN obras o ON o.id = r.obra_id
    """
    params: list = []
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        query += f" WHERE r.status IN ({placeholders})"
        params.extend(status_filter)
    query += " ORDER BY r.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_rdos() -> list[dict]:
    return get_all_rdos(status_filter=["pendente"])


def get_rdo_full(rdo_id: int) -> dict | None:
    conn = get_connection()
    rdo = conn.execute("""
        SELECT r.*, e.nome AS engenheiro_nome, o.nome AS obra_nome, o.orcamento AS obra_orcamento
        FROM rdos r
        JOIN engenheiros e ON e.id = r.engenheiro_id
        JOIN obras o ON o.id = r.obra_id
        WHERE r.id=?
    """, (rdo_id,)).fetchone()
    if not rdo:
        conn.close()
        return None
    result = dict(rdo)
    for tbl, key in [
        ("rdo_equipe", "equipe"),
        ("rdo_atividades", "atividades"),
        ("rdo_servicos", "servicos"),
        ("rdo_materiais", "materiais"),
        ("rdo_equipamentos", "equipamentos"),
        ("rdo_ocorrencias", "ocorrencias"),
        ("rdo_fotos", "fotos"),
    ]:
        rows = conn.execute(f"SELECT * FROM {tbl} WHERE rdo_id=?", (rdo_id,)).fetchall()
        result[key] = [dict(r) for r in rows]
    conn.close()
    return result


def approve_rdo(rdo_id: int, comment: str) -> None:
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE rdos SET status='aprovado', comentario_aprovacao=?,
            data_aprovacao=datetime('now'), updated_at=datetime('now')
            WHERE id=?
        """, (comment, rdo_id))
    conn.close()
    update_cronograma_from_rdo(rdo_id)


def reject_rdo(rdo_id: int, comment: str) -> None:
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE rdos SET status='rejeitado', comentario_aprovacao=?,
            updated_at=datetime('now')
            WHERE id=?
        """, (comment, rdo_id))
    conn.close()


# ── Fotos ─────────────────────────────────────────────────────────────────────

def save_photo(obra_id: int, rdo_id: int, uploaded_file, legenda: str = "", ordem: int = 0) -> str:
    dest_dir = PHOTO_BASE / str(obra_id) / str(rdo_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(uploaded_file.name).suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = dest_dir / filename
    dest_path.write_bytes(uploaded_file.getbuffer())
    rel_path = str(dest_path)
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO rdo_fotos(rdo_id,file_path,legenda,ordem) VALUES(?,?,?,?)",
            (rdo_id, rel_path, legenda, ordem)
        )
    conn.close()
    return rel_path


def delete_photo(foto_id: int) -> None:
    conn = get_connection()
    row = conn.execute("SELECT file_path FROM rdo_fotos WHERE id=?", (foto_id,)).fetchone()
    if row:
        p = Path(row["file_path"])
        if p.exists():
            p.unlink()
        with conn:
            conn.execute("DELETE FROM rdo_fotos WHERE id=?", (foto_id,))
    conn.close()


def get_fotos(rdo_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM rdo_fotos WHERE rdo_id=? ORDER BY ordem", (rdo_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Cronograma ────────────────────────────────────────────────────────────────

def get_cronograma(obra_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM cronograma WHERE obra_id=? ORDER BY ordem, id",
        (obra_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_cronograma(obra_id: int, linhas: list[dict]) -> None:
    """Replace all cronograma items for a project."""
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM cronograma WHERE obra_id=?", (obra_id,))
        for i, row in enumerate(linhas):
            ativ = str(row.get("atividade","")).strip()
            if not ativ:
                continue
            conn.execute(
                """INSERT INTO cronograma(obra_id,atividade,data_inicio,data_fim,
                   peso_percentual,percentual_executado,ordem)
                   VALUES(?,?,?,?,?,?,?)""",
                (obra_id, ativ,
                 str(row.get("data_inicio","")) or "",
                 str(row.get("data_fim","")) or "",
                 float(row.get("peso_percentual",0) or 0),
                 float(row.get("percentual_executado",0) or 0),
                 i)
            )
    conn.close()


def update_cronograma_item(item_id: int, percentual_executado: float) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE cronograma SET percentual_executado=? WHERE id=?",
            (percentual_executado, item_id)
        )
    conn.close()


def update_cronograma_from_rdo(rdo_id: int) -> None:
    """
    After approving an RDO, update cronograma percentual_executado
    based on the atividades reported in that RDO.
    Matches by LIKE on atividade name (case-insensitive).
    """
    conn = get_connection()
    try:
        rdo = conn.execute("SELECT obra_id FROM rdos WHERE id=?", (rdo_id,)).fetchone()
        if not rdo:
            return
        obra_id = rdo["obra_id"]
        atividades = conn.execute(
            "SELECT descricao, percentual FROM rdo_atividades WHERE rdo_id=?",
            (rdo_id,)
        ).fetchall()
        with conn:
            for atv in atividades:
                desc = atv["descricao"].strip()
                pct = float(atv["percentual"] or 0)
                # Find matching cronograma item(s)
                matches = conn.execute(
                    "SELECT id FROM cronograma WHERE obra_id=? AND LOWER(atividade) LIKE LOWER(?)",
                    (obra_id, f"%{desc}%")
                ).fetchall()
                for m in matches:
                    conn.execute(
                        "UPDATE cronograma SET percentual_executado=? WHERE id=?",
                        (pct, m["id"])
                    )
    finally:
        conn.close()


# ── Orçamento Analítico ───────────────────────────────────────────────────────

def get_orcamento_itens(obra_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM orcamento_itens WHERE obra_id=? ORDER BY id",
        (obra_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_orcamento_itens(obra_id: int, itens: list[dict]) -> None:
    """Replace all budget items for a project."""
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM orcamento_itens WHERE obra_id=?", (obra_id,))
        for row in itens:
            item = str(row.get("item","")).strip()
            if not item:
                continue
            conn.execute(
                "INSERT INTO orcamento_itens(obra_id,item,descricao,valor) VALUES(?,?,?,?)",
                (obra_id, item,
                 str(row.get("descricao","")),
                 float(row.get("valor",0) or 0))
            )
    conn.close()


# ── KPIs do Dashboard ─────────────────────────────────────────────────────────

def get_kpis_obra(obra_id: int) -> dict:
    """
    Returns all KPI data for a project dashboard.
    All financial and schedule data comes exclusively from approved RDOs.
    """
    conn = get_connection()
    try:
        obra = conn.execute("SELECT * FROM obras WHERE id=?", (obra_id,)).fetchone()
        if not obra:
            return {}
        obra = dict(obra)

        # Cost KPIs from approved RDOs
        cost_row = conn.execute("""
            SELECT COALESCE(SUM(m.valor_total), 0) AS gasto_aprovado
            FROM rdos r
            JOIN rdo_materiais m ON m.rdo_id = r.id
            WHERE r.obra_id=? AND r.status='aprovado'
        """, (obra_id,)).fetchone()
        gasto_aprovado = float(cost_row["gasto_aprovado"] or 0)
        orcamento = float(obra.get("orcamento") or 0)
        pct_custo = round(gasto_aprovado / orcamento * 100, 1) if orcamento > 0 else 0.0

        # RDO counts
        counts = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='aprovado'  THEN 1 ELSE 0 END) AS aprovados,
                SUM(CASE WHEN status='pendente'  THEN 1 ELSE 0 END) AS pendentes,
                SUM(CASE WHEN status='rejeitado' THEN 1 ELSE 0 END) AS rejeitados,
                SUM(CASE WHEN status='rascunho'  THEN 1 ELSE 0 END) AS rascunhos
            FROM rdos WHERE obra_id=?
        """, (obra_id,)).fetchone()

        # Working days = distinct dates from approved RDOs
        dias_row = conn.execute("""
            SELECT COUNT(DISTINCT data_relatorio) AS dias
            FROM rdos WHERE obra_id=? AND status='aprovado'
        """, (obra_id,)).fetchone()
        dias_trabalhados = int(dias_row["dias"] or 0)

        # Schedule KPIs from cronograma
        crono_rows = conn.execute(
            "SELECT peso_percentual, percentual_executado FROM cronograma WHERE obra_id=?",
            (obra_id,)
        ).fetchall()
        total_peso = sum(float(r["peso_percentual"] or 0) for r in crono_rows)
        if total_peso > 0:
            exec_ponderado = sum(
                float(r["percentual_executado"] or 0) * float(r["peso_percentual"] or 0)
                for r in crono_rows
            ) / total_peso
        elif crono_rows:
            exec_ponderado = sum(float(r["percentual_executado"] or 0) for r in crono_rows) / len(crono_rows)
        else:
            exec_ponderado = 0.0

        # Calculate scheduled % based on current date
        from datetime import date
        hoje = date.today()
        crono_full = conn.execute(
            "SELECT data_inicio, data_fim, peso_percentual FROM cronograma WHERE obra_id=?",
            (obra_id,)
        ).fetchall()
        if crono_full and total_peso > 0:
            previsto_pond = 0.0
            for r in crono_full:
                try:
                    di = date.fromisoformat(str(r["data_inicio"]))
                    df = date.fromisoformat(str(r["data_fim"]))
                    total_dias = (df - di).days
                    if total_dias <= 0:
                        pct_prev = 100.0 if hoje >= df else 0.0
                    elif hoje < di:
                        pct_prev = 0.0
                    elif hoje >= df:
                        pct_prev = 100.0
                    else:
                        pct_prev = (hoje - di).days / total_dias * 100
                    previsto_pond += pct_prev * float(r["peso_percentual"] or 0)
                except Exception:
                    pass
            cronograma_previsto = round(previsto_pond / total_peso, 1)
        else:
            cronograma_previsto = 0.0
        cronograma_executado = round(exec_ponderado, 1)

        # Last 5 occurrences from approved RDOs
        ultimas_ocorrencias = conn.execute("""
            SELECT o.tipo, o.descricao, o.acao_tomada, r.data_relatorio, r.numero_rdo
            FROM rdo_ocorrencias o
            JOIN rdos r ON r.id = o.rdo_id
            WHERE r.obra_id=? AND r.status='aprovado'
            ORDER BY r.data_relatorio DESC, o.id DESC
            LIMIT 5
        """, (obra_id,)).fetchall()

        # Cost evolution: gasto por data (approved RDOs)
        custo_por_data = conn.execute("""
            SELECT r.data_relatorio, COALESCE(SUM(m.valor_total),0) AS custo_dia
            FROM rdos r
            LEFT JOIN rdo_materiais m ON m.rdo_id = r.id
            WHERE r.obra_id=? AND r.status='aprovado'
            GROUP BY r.data_relatorio
            ORDER BY r.data_relatorio
        """, (obra_id,)).fetchall()

        # Team summary from approved RDOs (last approved RDO)
        equipe_resumo = conn.execute("""
            SELECT eq.funcao, SUM(eq.quantidade) AS total
            FROM rdo_equipe eq
            JOIN rdos r ON r.id = eq.rdo_id
            WHERE r.obra_id=? AND r.status='aprovado'
            GROUP BY eq.funcao
            ORDER BY total DESC
        """, (obra_id,)).fetchall()

        return {
            "obra": obra,
            "orcamento": orcamento,
            "gasto_aprovado": gasto_aprovado,
            "saldo": orcamento - gasto_aprovado,
            "pct_custo": pct_custo,
            "cronograma_previsto": cronograma_previsto,
            "cronograma_executado": cronograma_executado,
            "rdos_total": int(counts["total"] or 0),
            "rdos_aprovados": int(counts["aprovados"] or 0),
            "rdos_pendentes": int(counts["pendentes"] or 0),
            "rdos_rejeitados": int(counts["rejeitados"] or 0),
            "rdos_rascunhos": int(counts["rascunhos"] or 0),
            "dias_trabalhados": dias_trabalhados,
            "ultimas_ocorrencias": [dict(r) for r in ultimas_ocorrencias],
            "custo_por_data": [dict(r) for r in custo_por_data],
            "equipe_resumo": [dict(r) for r in equipe_resumo],
        }
    finally:
        conn.close()
