"""Lista editais cadastrados com IDs."""

from langchain_core.tools import tool
from database.db import get_connection


@tool
def listar_editais() -> str:
    """Lista todos os editais cadastrados no sistema.
    SEMPRE chame esta ferramenta PRIMEIRO antes de qualquer outra consulta.
    Use os IDs retornados para chamar as demais ferramentas.
    Para detalhes de um edital específico, use consultar_edital(edital_id, campo)."""

    conn = get_connection()
    rows = conn.execute("""
        SELECT e.id, e.orgao, e.numero_edital, e.cargo,
               en.enfase, en.vagas_imediatas_total
        FROM editais e
        LEFT JOIN enfases en ON e.id = en.edital_id
        ORDER BY e.id
    """).fetchall()
    conn.close()

    if not rows:
        return "Nenhum edital cadastrado no sistema."

    editais = {}
    for row in rows:
        eid = row["id"]
        if eid not in editais:
            editais[eid] = {
                "id": eid,
                "orgao": row["orgao"],
                "numero_edital": row["numero_edital"],
                "cargo": row["cargo"],
                "vagas": 0,
                "enfase": "",
            }
        if row["enfase"]:
            editais[eid]["enfase"] = row["enfase"]
            editais[eid]["vagas"] = row["vagas_imediatas_total"] or 0

    linhas = []
    for e in editais.values():
        linhas.append(
            f"ID={e['id']} | {e['orgao']} | {e['numero_edital']} | "
            f"{e['cargo']} | {e['enfase']}: {e['vagas']} vagas"
        )

    resultado = f"Editais cadastrados ({len(editais)}):\n" + "\n".join(linhas)
    resultado += "\n\nUse consultar_edital(edital_id, campo) para detalhes como cronograma, provas, vagas, requisitos, salário, benefícios, conteúdo programático."
    return resultado