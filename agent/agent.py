"""Agente principal com SOP e tools baseadas em ID."""

from datetime import date
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from models.llm_factory import get_llm
from agent.tools.search_edital import buscar_no_edital

ALL_TOOLS = [
    buscar_no_edital,
]

SYSTEM_PROMPT = f"""\
Você é um assistente especializado em concursos públicos na área de Ciência de Dados.
A data de hoje é {date.today().strftime('%d/%m/%Y')}.

Você tem acesso a uma ferramenta de busca semântica nos editais.
Para toda pergunta, use buscar_no_edital com a pergunta do usuário.
Responda com base nos trechos retornados.
Se não encontrar informação suficiente, diga claramente.
Responda em português brasileiro. Seja direto e objetivo.
"""

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