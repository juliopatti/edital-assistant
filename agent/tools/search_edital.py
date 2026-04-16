"""Busca semântica no texto completo dos editais — versão RAG puro."""

from langchain_core.tools import tool
from ingestion.rag import buscar_chunks


@tool
def buscar_no_edital(pergunta: str) -> str:
    """Busca trechos relevantes nos editais cadastrados.
    Use para qualquer pergunta sobre concursos.

    Args:
        pergunta: a pergunta do usuário.
    """

    chunks = buscar_chunks(pergunta, n_results=5)

    if not chunks:
        return f"Nenhum trecho relevante encontrado para: '{pergunta}'."

    resultado = ""
    for i, c in enumerate(chunks, 1):
        resultado += f"\n--- Trecho {i} ---\n"
        resultado += c["texto"] + "\n"

    return resultado