"""Página admin: revisar extrações e ingerir novos editais."""

import json
import shutil
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from database.db import get_connection, listar_editais
from models.schemas import EditalInfo
from ingestion.ingest import ingerir_edital
from config import settings

st.set_page_config(page_title="Admin - Editais", page_icon="⚙️")
st.title("⚙️ Admin — Gestão de Editais")

# --- Upload ---
st.header("📤 Ingerir novo edital")

uploaded = st.file_uploader("Envie um PDF de edital", type=["pdf"])

if uploaded and st.button("Processar edital"):
    destino = Path(settings.editais_dir) / uploaded.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(uploaded.read())

    with st.spinner(
        "Processando edital (6 etapas: texto, LLM estruturado, SQLite, ChromaDB, "
        "resumo, TOC/splits/markdowns). Pode levar vários minutos — acompanhe "
        "pelo terminal."
    ):
        try:
            edital_id = ingerir_edital(str(destino))
        except Exception as e:
            st.error(f"Erro na ingestão: {e}")
            st.stop()

    st.success(f"Edital ingerido com id={edital_id}")
    st.rerun()


# --- Revisar extrações ---
st.header("📋 Editais cadastrados")

editais = listar_editais()

if not editais:
    st.info("Nenhum edital cadastrado.")
    st.stop()

for e in editais:
    st.write(f"**{e.orgao}** — {e.numero_edital} ({e.cargo})")

conn = get_connection()
rows = conn.execute(
    "SELECT id, orgao, numero_edital, arquivo_origem FROM editais"
).fetchall()
conn.close()

edital_ids = [row["id"] for row in rows]
edital_labels = [
    f"{row['orgao']} - {row['numero_edital']} (id:{row['id']})" for row in rows
]
arquivos = {row["id"]: row["arquivo_origem"] for row in rows}

if edital_labels:
    escolha = st.selectbox("Selecione um edital para revisar", edital_labels)
    idx = edital_labels.index(escolha)
    edital_id = edital_ids[idx]

    conn = get_connection()
    row = conn.execute(
        "SELECT dados_json FROM editais WHERE id = ?", (edital_id,)
    ).fetchone()
    conn.close()

    dados = json.loads(row["dados_json"])

    st.subheader("JSON extraído (editável)")
    editado = st.text_area(
        "Edite o JSON se necessário:",
        value=json.dumps(dados, ensure_ascii=False, indent=2),
        height=500,
    )

    if st.button("🗑️ Deletar este edital"):
        # 1. SQLite: linhas em editais + enfases
        conn = get_connection()
        conn.execute("DELETE FROM enfases WHERE edital_id = ?", (edital_id,))
        conn.execute("DELETE FROM editais WHERE id = ?", (edital_id,))
        conn.commit()
        conn.close()

        # 2. ChromaDB: chunks indexados com metadata edital_id
        try:
            from ingestion.rag import get_chroma_collection
            collection = get_chroma_collection()
            existing = collection.get(where={"edital_id": edital_id})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception as e:
            st.warning(f"Falha ao limpar ChromaDB: {e}")

        # 3. Arquivos em disco: PDF original, _toc.txt e splits/{stem}/
        arquivo_origem = arquivos.get(edital_id)
        if arquivo_origem:
            stem = Path(arquivo_origem).stem
            pdf_path = settings.editais_dir / arquivo_origem
            toc_path = settings.editais_dir / f"{stem}_toc.txt"
            splits_dir = settings.editais_dir / "splits" / stem

            for p in (pdf_path, toc_path):
                if p.exists():
                    p.unlink()
            if splits_dir.exists():
                shutil.rmtree(splits_dir)

        st.success("Edital deletado (DB, ChromaDB, PDF, TOC, splits).")
        st.rerun()

    if st.button("💾 Salvar correções"):
        try:
            # Valida com Pydantic antes de salvar
            edital_corrigido = EditalInfo.model_validate_json(editado)
            conn = get_connection()
            conn.execute(
                "UPDATE editais SET dados_json = ?, orgao = ?, numero_edital = ?, "
                "cargo = ?, salario_inicial = ? WHERE id = ?",
                (
                    edital_corrigido.model_dump_json(),
                    edital_corrigido.orgao,
                    edital_corrigido.numero_edital,
                    edital_corrigido.cargo,
                    edital_corrigido.salario_inicial,
                    edital_id,
                ),
            )
            conn.commit()
            conn.close()
            st.success("Salvo com sucesso! Pydantic validou sem erros.")
        except json.JSONDecodeError as e:
            st.error(f"JSON inválido: {e}")
        except Exception as e:
            st.error(f"Erro de validação: {e}")
