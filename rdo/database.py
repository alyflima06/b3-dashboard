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
        """)
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


def create_obra(nome: str, endereco: str, cliente: str, orcamento: float) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO obras(nome,endereco,cliente,orcamento) VALUES(?,?,?,?)",
            (nome, endereco, cliente, orcamento)
        )
    conn.close()
    return cur.lastrowid


def update_obra(obra_id: int, nome: str, endereco: str, cliente: str, orcamento: float) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE obras SET nome=?,endereco=?,cliente=?,orcamento=? WHERE id=?",
            (nome, endereco, cliente, orcamento, obra_id)
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
