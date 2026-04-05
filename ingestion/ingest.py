"""Pipeline de ingestão: PDF → texto → LLM → Pydantic → SQLite."""

from pathlib import Path
from ingestion.pdf_extractor import extrair_texto_pdf
from ingestion.structured_extract import extrair_estruturado
from database.db import inserir_edital
from ingestion.rag import indexar_edital
from ingestion.resumo import gerar_resumo


def ingerir_edital(caminho_pdf: str) -> int:
    """Processa um PDF e salva no banco. Retorna o id do edital."""

    caminho = Path(caminho_pdf)
    print(f"1/5 Extraindo texto de {caminho.name}...")
    texto = extrair_texto_pdf(str(caminho))
    print(f"     {len(texto)} caracteres extraídos.")

    print("2/5 Extraindo dados estruturados via LLM...")
    edital = extrair_estruturado(texto, arquivo_origem=caminho.name)
    print(f"     Órgão: {edital.orgao} | Ênfases: {len(edital.enfases)}")

    print("3/5 Salvando no banco...")
    edital_id = inserir_edital(edital, texto_completo=texto)
    print(f"     Salvo com id={edital_id}")

    print("4/5 Indexando no ChromaDB (RAG)...")
    indexar_edital(edital_id, edital.orgao, texto)

    print("5/5 Gerando resumo...")
    gerar_resumo(edital_id, edital.model_dump_json())

    return edital_id


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python -m ingestion.ingest caminho/do/edital.pdf")
    else:
        ingerir_edital(sys.argv[1])