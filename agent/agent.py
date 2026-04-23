"""Agente principal com SOP e tools baseadas em ID."""

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from models.llm_factory import get_llm
from agent.tools.info_editais import listar_editais
from agent.tools.info_edital import consultar_edital
from agent.tools.search_edital import buscar_no_edital
from agent.tools.resumo_perfil import resumo_edital
from agent.tools.ler_capitulo import listar_capitulos, ler_capitulo
from agent.tools.data_hoje import data_hoje
from database.db import get_connection


SYSTEM_PROMPT = """\
Você é um assistente especializado em concursos públicos na área de Ciência de Dados.

EDITAL ATIVO NESTA CONVERSA:
{contexto_edital}

REGRAS DE ESCOPO — OBRIGATÓRIAS:
- O usuário já escolheu o edital desta conversa na interface. Você NÃO deve perguntar
  "qual edital?", NÃO deve pedir para o usuário identificar o órgão, e NÃO deve chamar
  listar_editais exceto quando o edital ativo for "Todos os editais".
- Quando o edital ativo tem um ID específico, SEMPRE use esse ID nas chamadas às tools
  que recebem edital_id. Ignore qualquer ID que tenha aparecido em turnos anteriores
  desta ou de outra conversa.
- Se o usuário mencionar outro órgão (ex: está na conversa da CVM mas pergunta sobre
  o BNDES), avise-o que a conversa atual é da CVM e que ele precisa trocar o edital
  ativo no menu lateral para consultar outro.

COMPARAÇÃO DE DATAS — REGRA OBRIGATÓRIA:
- Para QUALQUER pergunta que envolva vigência, prazos, se está aberto/fechado,
  se ainda dá tempo, se já passou, quanto tempo falta — SEMPRE chame data_hoje()
  PRIMEIRO para obter a data atual, depois compare explicitamente com as datas do edital.
- NÃO confie em suposições sobre "agora" ou "hoje". Só a tool data_hoje() é fonte confiável.
- Ao responder, seja explícito: "Hoje é DD/MM/AAAA. A inscrição foi de X a Y.
  Portanto, JÁ ENCERROU / AINDA ESTÁ ABERTA / AINDA NÃO COMEÇOU."

ESCOLHA DA FERRAMENTA por tipo de pergunta:

- Dados objetivos agregados (salário, benefícios, banca): use consultar_edital(edital_id, campo).
- Resumo geral do edital: use resumo_edital(edital_id).
- Pergunta específica sobre regras ou detalhes ("posso levar calculadora?", "quantas vagas PcD?",
  "como é a eliminação?"): use buscar_no_edital(pergunta, edital_id).
- Pergunta sobre uma SEÇÃO INTEIRA (conteúdo programático completo, cronograma completo,
  todas as regras das provas): use ler_capitulo(edital_id, cap_num).
  Se não souber qual cap_num, primeiro use listar_capitulos(edital_id).
- Quando buscar_no_edital retorna só parte de uma lista (ex: "tópico 2") e o usuário
  pediu a lista inteira: mude para ler_capitulo ou listar_capitulos + ler_capitulo.

FALLBACK OBRIGATÓRIO — NUNCA RESPONDA "NÃO ENCONTREI" SEM ANTES:
- Se consultar_edital() não trouxe a informação específica pedida → tente buscar_no_edital().
- Se resumo_edital() não cobre o detalhe pedido → tente buscar_no_edital().
- Se buscar_no_edital() não achou → tente ler_capitulo() em capítulos candidatos
  (ex: vagas/cotas geralmente estão em caps iniciais; conteúdo programático em anexos).
- Se TUDO falhou, só então responda que não encontrou — e seja explícito sobre o que tentou.

NUNCA INVENTE informação. Se o edital não cobre a pergunta, diga isso claramente.

REGRAS GERAIS:
- Foque em Ciência de Dados, a menos que o usuário peça outra coisa.
- Responda em português brasileiro.
- Seja direto e objetivo.
- Prefira ler_capitulo a emendar múltiplas buscas quando a pergunta abrange uma seção inteira.
"""

ALL_TOOLS = [
    listar_editais,
    consultar_edital,
    buscar_no_edital,
    resumo_edital,
    listar_capitulos,
    ler_capitulo,
    data_hoje,
]

TOOLS_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}


def _montar_contexto_edital(edital_id_ativo: int) -> str:
    """Monta o texto descritivo do edital ativo para injetar no SYSTEM_PROMPT."""
    if edital_id_ativo == 0:
        return (
            "Modo 'TODOS OS EDITAIS' — o usuário não fixou um edital específico. "
            "Neste modo você PODE e DEVE chamar listar_editais primeiro, e depois "
            "perguntar ao usuário sobre qual edital ele quer falar, OU buscar em "
            "todos usando edital_id=0 nas tools que aceitam esse parâmetro."
        )

    conn = get_connection()
    row = conn.execute(
        "SELECT orgao, numero_edital, cargo FROM editais WHERE id = ?",
        (edital_id_ativo,),
    ).fetchone()
    conn.close()

    if not row:
        return f"ID={edital_id_ativo} não encontrado no banco."

    return (
        f"ID={edital_id_ativo} | {row['orgao']} — {row['numero_edital']} — {row['cargo']}\n"
        f"USE SEMPRE edital_id={edital_id_ativo} nas chamadas às tools desta conversa."
    )


class Agent:
    def __init__(self, provider=None, model=None):
        llm = get_llm(provider=provider, model=model)
        self.llm = llm.bind_tools(ALL_TOOLS)
        self.max_iterations = 10

    def ask(self, question, chat_history=None, edital_id_ativo=0):
        contexto = _montar_contexto_edital(edital_id_ativo)
        system_msg = SYSTEM_PROMPT.format(contexto_edital=contexto)

        messages = [SystemMessage(content=system_msg)]
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=question))

        for _ in range(self.max_iterations):
            response = self.llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return response.content

            for tool_call in response.tool_calls:
                tool_fn = TOOLS_BY_NAME.get(tool_call["name"])
                if tool_fn:
                    try:
                        result = tool_fn.invoke(tool_call["args"])
                    except Exception as e:
                        result = (
                            f"Erro ao executar {tool_call['name']}: {e}. "
                            "Tente outra ferramenta ou reformule os argumentos."
                        )
                else:
                    result = (
                        f"Ferramenta '{tool_call['name']}' não existe. "
                        f"Disponíveis: {', '.join(TOOLS_BY_NAME.keys())}"
                    )

                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

        return "Não consegui completar a consulta após várias tentativas. Tente reformular a pergunta."


def build_agent(provider=None, model=None):
    return Agent(provider=provider, model=model)


def ask(agent, question, chat_history=None, edital_id_ativo=0):
    return agent.ask(
        question=question,
        chat_history=chat_history,
        edital_id_ativo=edital_id_ativo,
    )