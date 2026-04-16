"""Retorna resumo do edital focado em Ciência de Dados."""

from langchain_core.tools import tool
from database.db import get_connection


@tool
def resumo_edital(edital_id: int) -> str:
    """Retorna o resumo completo do edital focado em Ciência de Dados.
    Use quando o usuário pedir 'resuma o concurso' ou 'o que preciso saber'.

    Args:
        edital_id: ID numérico do edital (obtido via listar_editais).
    """

    conn = get_connection()
    row = conn.execute(
        "SELECT orgao, numero_edital, resumo_ciencia_dados FROM editais WHERE id = ?",
        (edital_id,)
    ).fetchone()
    conn.close()

    if not row:
        return (
            f"Edital com ID={edital_id} não encontrado. "
            "Use listar_editais() para ver os IDs disponíveis."
        )

    resumo = row["resumo_ciencia_dados"]
    if not resumo:
        return (
            f"Resumo do edital {row['orgao']} ({row['numero_edital']}) ainda não foi gerado. "
            "Reingira o edital para gerar o resumo."
        )

    return f"=== {row['orgao']} — {row['numero_edital']} ===\n{resumo}"