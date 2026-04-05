"""Gera resumo do edital focado em Ciência de Dados."""

from models.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from database.db import get_connection


def gerar_resumo(edital_id: int, dados_json: str):
    """Gera resumo focado em Ciência de Dados e salva no banco."""

    llm = get_llm()
    resp = llm.invoke([
        SystemMessage(content="""Você é um especialista em concursos públicos.
Receba os dados estruturados de um edital e gere um RESUMO COMPLETO E PRÁTICO
focado na ênfase "Ciência de Dados".

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

    conn = get_connection()
    conn.execute("UPDATE editais SET resumo_ciencia_dados = ? WHERE id = ?", (resp.content, edital_id))
    conn.commit()
    conn.close()