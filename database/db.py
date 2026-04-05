"""
Camada de persistência com SQLite.

Armazena:
- Editais como JSON estruturado (validado por Pydantic)
- Texto completo do edital (para contexto nas tools)
- Metadata para consultas rápidas
"""

import sqlite3
import json
from pathlib import Path
from models.schemas import EditalInfo, EditalResumo
from config import settings


def get_connection() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas se não existirem."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS editais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orgao TEXT NOT NULL,
            numero_edital TEXT,
            cargo TEXT,
            salario_inicial TEXT,
            data_publicacao TEXT,
            banca TEXT,
            status TEXT DEFAULT 'desconhecido',
            arquivo_origem TEXT,
            data_extracao TEXT,

            -- JSON completo do EditalInfo (validado por Pydantic)
            dados_json TEXT NOT NULL,

            -- Texto completo do PDF (para contexto nas tools)
            texto_completo TEXT
        );

        CREATE TABLE IF NOT EXISTS enfases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            edital_id INTEGER NOT NULL,
            enfase TEXT NOT NULL,
            requisito_basico TEXT,
            registro_profissional TEXT,
            vagas_imediatas_total INTEGER DEFAULT 0,
            cadastro_reserva_total INTEGER DEFAULT 0,
            conteudo_programatico TEXT,  -- JSON list

            FOREIGN KEY (edital_id) REFERENCES editais(id)
        );

        CREATE INDEX IF NOT EXISTS idx_enfases_edital ON enfases(edital_id);
        CREATE INDEX IF NOT EXISTS idx_enfases_nome ON enfases(enfase);
    """)
    conn.commit()
    conn.close()


def inserir_edital(edital: EditalInfo, texto_completo: str = "") -> int:
    """Insere um edital e suas ênfases. Retorna o id do edital."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO editais (orgao, numero_edital, cargo, salario_inicial,
            data_publicacao, banca, arquivo_origem, data_extracao, dados_json, texto_completo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        edital.orgao,
        edital.numero_edital,
        edital.cargo,
        edital.salario_inicial,
        edital.data_publicacao,
        edital.banca,
        edital.arquivo_origem,
        edital.data_extracao,
        edital.model_dump_json(),
        texto_completo,
    ))
    edital_id = cursor.lastrowid

    for enfase in edital.enfases:
        cursor.execute("""
            INSERT INTO enfases (edital_id, enfase, requisito_basico, registro_profissional,
                vagas_imediatas_total, cadastro_reserva_total, conteudo_programatico)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            edital_id,
            enfase.enfase,
            enfase.requisito_basico,
            enfase.registro_profissional,
            enfase.vagas_imediatas.total,
            enfase.cadastro_reserva.total,
            json.dumps(enfase.conteudo_programatico, ensure_ascii=False),
        ))

    conn.commit()
    conn.close()
    return edital_id


def listar_editais() -> list[EditalResumo]:
    """Lista resumo de todos os editais cadastrados."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.id, e.orgao, e.numero_edital, e.cargo, e.salario_inicial,
               e.data_publicacao, e.status,
               COALESCE(SUM(en.vagas_imediatas_total), 0) as total_vagas
        FROM editais e
        LEFT JOIN enfases en ON e.id = en.edital_id
            AND LOWER(en.enfase) LIKE '%dados%'
        GROUP BY e.id
    """).fetchall()
    conn.close()

    return [
        EditalResumo(
            id=row["id"],
            orgao=row["orgao"],
            numero_edital=row["numero_edital"],
            cargo=row["cargo"],
            salario_inicial=row["salario_inicial"],
            total_vagas_foco=row["total_vagas"],
            data_publicacao=row["data_publicacao"],
            status=row["status"],
        )
        for row in rows
    ]


def buscar_edital_completo(edital_id: int) -> EditalInfo | None:
    """Retorna o EditalInfo completo a partir do JSON armazenado."""
    conn = get_connection()
    row = conn.execute(
        "SELECT dados_json FROM editais WHERE id = ?", (edital_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None
    return EditalInfo.model_validate_json(row["dados_json"])


def buscar_texto_completo(edital_id: int) -> str:
    """Retorna o texto completo do edital."""
    conn = get_connection()
    row = conn.execute(
        "SELECT texto_completo FROM editais WHERE id = ?", (edital_id,)
    ).fetchone()
    conn.close()
    return row["texto_completo"] if row else ""


# Inicializa o banco na importação
init_db()
