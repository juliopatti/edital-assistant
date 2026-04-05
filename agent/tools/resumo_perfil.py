"""Gera resumo do edital sob a ótica de um cargo específico."""

import json
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from models.llm_factory import get_llm
from database.db import get_connection


@tool
def resumo_por_perfil(orgao: str = "", cargo_interesse: str = "Ciência de Dados") -> str:
    """Gera um resumo completo e estruturado do edital sob o ponto de vista
    de um cargo/ênfase específico. Use quando o usuário pedir algo como
    'resuma o concurso para ciência de dados' ou 'o que preciso saber sobre esse concurso'.

    Args:
        orgao: filtro por órgão (ex: 'BNDES'). Vazio pega o mais recente.
        cargo_interesse: a ênfase/área de interesse do usuário.
    """

    conn = get_connection()
    if orgao:
        row = conn.execute(
            "SELECT dados_json FROM editais WHERE LOWER(orgao) LIKE ? ORDER BY id DESC LIMIT 1",
            (f"%{orgao.lower()}%",)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT dados_json FROM editais ORDER BY id DESC LIMIT 1"
        ).fetchone()
    conn.close()

    if not row:
        return "Nenhum edital cadastrado."

    dados_json = row["dados_json"]

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=f"""Você é um especialista em concursos públicos.
Receba os dados estruturados de um edital e gere um RESUMO COMPLETO E PRÁTICO
focado na ênfase "{cargo_interesse}".

O resumo deve conter:
1. Visão geral (órgão, cargo, salário, regime, jornada)
2. Vagas disponíveis para essa ênfase (imediatas e cadastro reserva, por categoria)
3. Requisitos de formação e registro profissional
4. Etapas da seleção e como funcionam
5. Estrutura das provas (disciplinas, questões, pontuação, notas mínimas)
6. Conteúdo programático específico da ênfase (organizado por blocos)
7. Conteúdo programático básico (comum a todas ênfases)
8. Datas importantes do cronograma
9. Benefícios

Seja objetivo e prático. O candidato deve sair sabendo tudo que precisa."""),
        HumanMessage(content=dados_json),
    ])

    return response.content