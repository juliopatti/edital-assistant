"""Página admin: revisar extrações e ingerir novos editais."""

import json
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from database.db import get_connection, listar_editais, inserir_edital
from models.schemas import EditalInfo
from ingestion.pdf_extractor import extrair_texto_pdf
from ingestion.structured_extract import extrair_estruturado
from config import settings

st.set_page_config(page_title="Admin - Editais", page_icon="⚙️")
st.title("⚙️ Admin — Gestão de Editais")

# --- Upload ---
st.header("📤 Ingerir novo edital")

uploaded = st.file_uploader("Envie um PDF de edital", type=["pdf"])

if uploaded and st.button("Processar edital"):
    # Salvar PDF em disco
    destino = Path(settings.editais_dir) / uploaded.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(uploaded.read())

    with st.spinner("1/3 Extraindo texto do PDF..."):
        texto = extrair_texto_pdf(str(destino))
    st.write(f"✅ {len(texto)} caracteres extraídos")

    with st.spinner("2/3 Extraindo dados via LLM (pode demorar)..."):
        try:
            edital = extrair_estruturado(texto, arquivo_origem=uploaded.name)
            st.write(f"✅ Órgão: {edital.orgao} | Ênfases: {len(edital.enfases)}")
        except Exception as e:
            st.error(f"Erro na extração: {e}")
            st.stop()

    with st.spinner("3/3 Salvando no banco..."):
        edital_id = inserir_edital(edital, texto_completo=texto)
    st.success(f"Edital salvo com id={edital_id}")
    st.rerun()

# --- Revisar extrações ---
st.header("📋 Editais cadastrados")

editais = listar_editais()

if not editais:
    st.info("Nenhum edital cadastrado.")
    st.stop()

for e in editais:
    st.write(f"**{e.orgao}** — {e.numero_edital} ({e.cargo})")

# Selecionar edital pra revisar
edital_ids = []
edital_labels = []
conn = get_connection()
rows = conn.execute("SELECT id, orgao, numero_edital FROM editais").fetchall()
conn.close()

for row in rows:
    edital_ids.append(row["id"])
    edital_labels.append(f"{row['orgao']} - {row['numero_edital']} (id:{row['id']})")

if edital_labels:
    escolha = st.selectbox("Selecione um edital para revisar", edital_labels)
    idx = edital_labels.index(escolha)
    edital_id = edital_ids[idx]

    conn = get_connection()
    row = conn.execute("SELECT dados_json FROM editais WHERE id = ?", (edital_id,)).fetchone()
    conn.close()

    dados = json.loads(row["dados_json"])

    st.subheader("JSON extraído (editável)")
    editado = st.text_area(
        "Edite o JSON se necessário:",
        value=json.dumps(dados, ensure_ascii=False, indent=2),
        height=500,
    )

    if st.button("🗑️ Deletar este edital"):
        conn = get_connection()
        conn.execute("DELETE FROM enfases WHERE edital_id = ?", (edital_id,))
        conn.execute("DELETE FROM editais WHERE id = ?", (edital_id,))
        conn.commit()
        conn.close()
        st.success("Edital deletado.")
        st.rerun()

    if st.button("💾 Salvar correções"):
        try:
            # Valida com Pydantic antes de salvar
            edital_corrigido = EditalInfo.model_validate_json(editado)
            conn = get_connection()
            conn.execute(
                "UPDATE editais SET dados_json = ?, orgao = ?, numero_edital = ?, cargo = ?, salario_inicial = ? WHERE id = ?",
                (edital_corrigido.model_dump_json(), edital_corrigido.orgao, edital_corrigido.numero_edital,
                 edital_corrigido.cargo, edital_corrigido.salario_inicial, edital_id)
            )
            conn.commit()
            conn.close()
            st.success("Salvo com sucesso! Pydantic validou sem erros.")
        except json.JSONDecodeError as e:
            st.error(f"JSON inválido: {e}")
        except Exception as e:
            st.error(f"Erro de validação: {e}")