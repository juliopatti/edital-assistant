"""
Agente principal que orquestra as tools.

Usa bind_tools do LangChain (API estável) em vez de AgentExecutor.
"""

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from models.llm_factory import get_llm
from datetime import date


SYSTEM_PROMPT = f"""\
Você é um assistente especializado em concursos públicos na área de Ciência de Dados.
A data de hoje é {date.today().strftime('%d/%m/%Y')}.
Ao responder sobre prazos e validade, sempre compare as datas do edital com a data de hoje.

Seu papel é ajudar o usuário a entender editais de concursos, responder dúvidas sobre
vagas, requisitos, conteúdo programático, datas, e tudo mais relacionado.

Regras:
- Antes de responder qualquer pergunta sobre editais, use info_editais_cadastrados para saber quais editais existem no sistema e seus nomes exatos.
- Se uma ferramenta retornar resultado vazio, NÃO desista. Tente outra ferramenta ou reformule a busca.
- Ao buscar por órgão, use o nome exato como aparece no sistema (ex: use o nome completo, não abreviações).
- Foque nas informações relevantes para a área de Ciência de Dados, a menos que o usuário peça outra coisa.
- Responda em português brasileiro.
- Seja direto e objetivo.
- NUNCA diga que não tem informação sem antes tentar TODAS as ferramentas disponíveis.
"""

from agent.tools.info_editais import info_editais_cadastrados
from agent.tools.search_edital import search_edital
from agent.tools.resumo_perfil import resumo_por_perfil
from agent.tools.info_edital import info_edital

ALL_TOOLS = [
    info_editais_cadastrados,
    search_edital,
    resumo_por_perfil,
    info_edital,
]

TOOLS_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}


class Agent:
    def __init__(self, provider=None, model=None):
        llm = get_llm(provider=provider, model=model)
        self.llm = llm.bind_tools(ALL_TOOLS)
        self.max_iterations = 5

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
                print(f"\n>>> TOOL CHAMADA: {tool_call['name']}({tool_call['args']})\n")
                tool_fn = TOOLS_BY_NAME.get(tool_call["name"])
                if tool_fn:
                    try:
                        result = tool_fn.invoke(tool_call["args"])
                    except Exception as e:
                        result = f"Erro: {e}"
                else:
                    result = f"Tool '{tool_call['name']}' não encontrada."

                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

        return "Não consegui completar a consulta. Tente reformular."


def build_agent(provider=None, model=None):
    return Agent(provider=provider, model=model)


def ask(agent, question, chat_history=None):
    return agent.ask(question=question, chat_history=chat_history)