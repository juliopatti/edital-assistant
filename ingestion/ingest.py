"""
Pipeline de ingestão de um edital.

Nova ordem (MDs como fonte única, pdfplumber aposentado):
    1. MD pipeline: TOC + splits + cap_N.md (idempotente)
    2. Texto-base = concat dos cap_N.md (em ordem de capítulo)
    3. Extração estruturada via LLM sobre o texto-base
    4. Salvar no SQLite (texto_completo = texto-base)
    5. Indexar no ChromaDB com chunker estrutural + metadados ricos
    6. Gerar resumo focado em Ciência de Dados

Uso via CLI:
    python -m ingestion.ingest caminho/do/edital.pdf
"""

from pathlib import Path

from ingestion.structured_extract import extrair_estruturado
from database.db import inserir_edital
from ingestion.rag import indexar_chunks
from ingestion.resumo import gerar_resumo
from ingestion.md_pipeline.pipeline import gerar_md_edital
from ingestion.md_pipeline.md_chunker import chunk_edital


def _concat_mds(capitulos: list[dict]) -> str:
    """Concatena todos os cap_N.md em um texto único, em ordem de capítulo."""
    partes = []
    for cap in sorted(capitulos, key=lambda c: c["chapter_num"]):
        md_path = Path(cap["cap_path"]).with_suffix(".md")
        if md_path.exists():
            partes.append(md_path.read_text(encoding="utf-8"))
    return "\n\n".join(partes)


def ingerir_edital(caminho_pdf: str) -> int:
    """Processa um PDF e salva no banco. Retorna o id do edital."""

    caminho = Path(caminho_pdf)

    print("1/5 Gerando TOC + splits + markdowns (idempotente)...")
    info_md = gerar_md_edital(str(caminho))
    capitulos = info_md["capitulos"]

    print("2/5 Extraindo dados estruturados via LLM (a partir dos MDs)...")
    texto_base = _concat_mds(capitulos)
    print(f"     Texto-base: {len(texto_base):,} chars ({info_md['n_capitulos']} capítulos).")
    edital = extrair_estruturado(texto_base, arquivo_origem=caminho.name)
    print(f"     Órgão: {edital.orgao} | Ênfases: {len(edital.enfases)}")

    print("3/5 Salvando no banco...")
    edital_id = inserir_edital(edital, texto_completo=texto_base)
    print(f"     Salvo com id={edital_id}")

    print("4/5 Indexando chunks estruturais no ChromaDB...")
    chunks = chunk_edital(
        capitulos,
        edital_id=edital_id,
        orgao=edital.orgao,
        arquivo_origem=caminho.name,
        numero_edital=edital.numero_edital,
    )
    print(f"     {len(chunks)} chunks gerados a partir dos markdowns.")
    indexar_chunks(edital_id, chunks)

    print("5/5 Gerando resumo...")
    gerar_resumo(edital_id, edital.model_dump_json())

    return edital_id


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python -m ingestion.ingest caminho/do/edital.pdf")
    else:
        ingerir_edital(sys.argv[1])
