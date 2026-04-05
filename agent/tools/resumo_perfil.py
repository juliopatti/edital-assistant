"""Retorna resumo do edital focado em Ciência de Dados."""

from langchain_core.tools import tool
from database.db import get_connection


@tool
def resumo_por_perfil(orgao: str = "") -> str:
    """Retorna um resumo completo do edital sob o ponto de vista de Ciência de Dados.
    Use quando o usuário pedir algo como 'resuma o concurso' ou
    'o que preciso saber sobre esse concurso'.

    Args:
        orgao: filtro por órgão (ex: 'BNDES'). Vazio retorna todos.
    """

    conn = get_connection()
    if orgao:
        rows = conn.execute(
            "SELECT orgao, numero_edital, resumo_ciencia_dados FROM editais WHERE LOWER(orgao) LIKE ?",
            (f"%{orgao.lower()}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT orgao, numero_edital, resumo_ciencia_dados FROM editais"
        ).fetchall()
    conn.close()

    if not rows:
        return "Nenhum edital encontrado."

    resultado = ""
    for row in rows:
        resumo = row["resumo_ciencia_dados"] or "Resumo não disponível. Reingira o edital."
        resultado += f"=== {row['orgao']} — {row['numero_edital']} ===\n{resumo}\n\n"

    return resultado