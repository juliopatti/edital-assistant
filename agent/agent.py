"""Agente principal com SOP e tools baseadas em ID."""

from datetime import date
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from models.llm_factory import get_llm
from agent.tools.info_editais import listar_editais
from agent.tools.info_edital import consultar_edital
from agent.tools.search_edital import buscar_no_edital
from agent.tools.resumo_perfil import resumo_edital


SYSTEM_PROMPT = f"""\
Você é um assistente especializado em concursos públicos na área de Ciência de Dados.
A data de hoje é {date.today().strftime('%d/%m/%Y')}.

PROCEDIMENTO OBRIGATÓRIO (siga sempre nesta ordem):

1. SEMPRE comece chamando listar_editais() para saber quais editais existem e seus IDs.
2. Use os IDs retornados para chamar as demais ferramentas. NUNCA invente IDs.
3. Para dados objetivos (vagas, salário, cronograma, provas): use consultar_edital(edital_id, campo).
4. Para perguntas detalhadas (regras, o que pode levar, eliminação): use buscar_no_edital(pergunta, edital_id).
5. Para resumos gerais: use resumo_edital(edital_id).
6. Se uma ferramenta retornar resultado vazio ou erro, NÃO desista. Tente outra ferramenta ou reformule.
7. Se o usuário mencionar um órgão por abreviação (BNDES, Petrobras), identifique o ID correspondente na listagem.
8. Ao responder sobre prazos e validade, compare as datas do edital com a data de hoje ({date.today().strftime('%d/%m/%Y')}).

Regras:
- Foque em Ciência de Dados, a menos que o usuário peça outra coisa.
- Responda em português brasileiro.
- Seja direto e objetivo.
- NUNCA diga que não tem informação sem antes tentar TODAS as ferramentas disponíveis.
"""

ALL_TOOLS = [
    listar_editais,
    consultar_edital,
    buscar_no_edital,
    resumo_edital,
]

TOOLS_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}


class Agent:
    def __init__(self, provider=None, model=None):
        llm = get_llm(provider=provider, model=model)
        self.llm = llm.bind_tools(ALL_TOOLS)
        self.max_iterations = 10

    def ask(self, question, chat_history=None):
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
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


def ask(agent, question, chat_history=None):
    return agent.ask(question=question, chat_history=chat_history)