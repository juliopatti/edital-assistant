"""Busca semântica no texto completo dos editais."""

from langchain_core.tools import tool
from ingestion.rag import buscar_chunks


@tool
def search_edital(pergunta: str, orgao: str = "") -> str:
    """Busca trechos relevantes no texto completo dos editais.
    Use para perguntas detalhadas que não são respondidas por dados
    estruturados como vagas, salário ou cronograma. Exemplos:
    regras da prova, critérios de eliminação, documentação necessária,
    procedimentos específicos, conteúdo programático detalhado.

    Args:
        pergunta: a pergunta do usuário
        orgao: filtro por órgão (ex: 'BNDES'). Vazio busca em todos.
    """

    chunks = buscar_chunks(pergunta, n_results=5, orgao=orgao if orgao else None)

    if not chunks:
        return "Nenhum trecho relevante encontrado."

    resultado = "TRECHOS RELEVANTES:\n"
    for i, c in enumerate(chunks, 1):
        resultado += f"\n--- Trecho {i} ({c['metadata']['orgao']}) ---\n"
        resultado += c["texto"] + "\n"

    return resultado