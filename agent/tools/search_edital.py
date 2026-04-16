"""Busca semântica no texto completo dos editais."""

from langchain_core.tools import tool
from ingestion.rag import buscar_chunks
from database.db import get_connection


@tool
def buscar_no_edital(pergunta: str, edital_id: int = 0) -> str:
    """Busca trechos relevantes no texto completo dos editais via busca semântica.
    Use para perguntas detalhadas não cobertas por dados estruturados.
    Exemplos: regras da prova, o que pode levar, critérios de eliminação, detalhes de conteúdo.

    Args:
        pergunta: a pergunta do usuário.
        edital_id: ID numérico do edital (obtido via listar_editais). 0 busca em todos.
    """

    orgao_filtro = None
    if edital_id > 0:
        conn = get_connection()
        row = conn.execute("SELECT orgao FROM editais WHERE id = ?", (edital_id,)).fetchone()
        conn.close()
        if row:
            orgao_filtro = row["orgao"]
        else:
            return (
                f"Edital com ID={edital_id} não encontrado. "
                "Use listar_editais() para ver os IDs disponíveis."
            )

    chunks = buscar_chunks(pergunta, n_results=5, orgao=orgao_filtro)

    if not chunks:
        if edital_id > 0:
            return (
                f"Nenhum trecho relevante encontrado no edital ID={edital_id} para: '{pergunta}'. "
                "Tente reformular a pergunta ou buscar sem filtro (edital_id=0). "
                "Você também pode tentar consultar_edital para dados estruturados."
            )
        return (
            f"Nenhum trecho relevante encontrado para: '{pergunta}'. "
            "Verifique se os editais foram indexados. "
            "Tente também consultar_edital para dados estruturados."
        )

    resultado = f"Trechos relevantes para '{pergunta}':\n"
    for i, c in enumerate(chunks, 1):
        resultado += f"\n--- Trecho {i} ({c['metadata']['orgao']}) ---\n"
        resultado += c["texto"] + "\n"

    return resultado