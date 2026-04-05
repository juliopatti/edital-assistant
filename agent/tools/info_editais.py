"""
Tool dummy — será substituída por tools reais no Passo 1.
Serve para validar que o fluxo agente → tool → resposta funciona.
"""

from langchain_core.tools import tool
from database.db import listar_editais


@tool
def info_editais_cadastrados() -> str:
    """Retorna informações sobre os editais cadastrados no sistema.
    Use quando o usuário perguntar quais editais estão disponíveis,
    ou quando precisar saber o que já foi cadastrado."""

    editais = listar_editais()

    if not editais:
        return (
            "Nenhum edital cadastrado ainda. "
            "O sistema precisa que editais sejam ingeridos primeiro."
        )

    linhas = []
    for e in editais:
        linhas.append(
            f"- {e.orgao} ({e.numero_edital}): {e.cargo}, "
            f"salário {e.salario_inicial}, "
            f"{e.total_vagas_foco} vagas em Ciência de Dados, "
            f"status: {e.status}"
        )

    return f"Editais cadastrados ({len(editais)}):\n" + "\n".join(linhas)
