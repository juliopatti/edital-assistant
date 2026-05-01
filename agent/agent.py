"""Agente principal com SOP, tools baseadas em ID e self-check determinístico."""

import re
from pathlib import Path

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from models.llm_factory import get_llm
from agent.tools.info_editais import listar_editais
from agent.tools.search_edital import buscar_no_edital
from agent.tools.ler_capitulo import listar_capitulos, ler_capitulo
from agent.tools.data_hoje import data_hoje
from database.db import get_connection
from config import settings


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
- Se o usuário mencionar outro órgão, avise-o que precisa trocar o edital ativo no
  menu lateral para consultar outro.

COMPARAÇÃO DE DATAS — REGRA OBRIGATÓRIA:
- Para QUALQUER pergunta que envolva vigência, prazos, se está aberto/fechado,
  se ainda dá tempo, se já passou, quanto tempo falta — SEMPRE chame data_hoje()
  PRIMEIRO para obter a data atual, depois compare explicitamente com as datas do edital.
- NÃO confie em suposições sobre "agora" ou "hoje". Só a tool data_hoje() é fonte confiável.
- Ao responder, seja explícito: "Hoje é DD/MM/AAAA. A inscrição foi de X a Y.
  Portanto, JÁ ENCERROU / AINDA ESTÁ ABERTA / AINDA NÃO COMEÇOU."

ESCOLHA DA FERRAMENTA por tipo de pergunta:

- Pergunta sobre qualquer detalhe do edital (salário, taxa, vagas, cronograma, regras,
  conteúdo, o que levar no dia, critérios, etc.): use buscar_no_edital(pergunta, edital_id).
  Essa é sua ferramenta PRINCIPAL e deve ser sua PRIMEIRA escolha para qualquer
  pergunta factual sobre o edital.
- Pergunta sobre uma SEÇÃO INTEIRA (conteúdo programático completo, cronograma completo,
  todas as regras das provas, todas as etapas): use ler_capitulo(edital_id, cap_num).
  Se não souber qual cap_num, primeiro use listar_capitulos(edital_id).
- Quando buscar_no_edital retorna só parte de uma lista/tabela e o usuário pediu
  a coisa inteira: mude para listar_capitulos + ler_capitulo.

FALLBACK OBRIGATÓRIO — NUNCA RESPONDA "NÃO ENCONTREI" SEM ANTES:
- Se buscar_no_edital() não achou → reformule a query com outras palavras e tente de novo.
- Se ainda não achou → use listar_capitulos() para identificar capítulos candidatos
  (ex: taxa e inscrição geralmente estão nos primeiros capítulos; cronograma pode
  estar em anexo; conteúdo programático em anexos).
- Em seguida use ler_capitulo() nos capítulos candidatos.
- Só responda "não encontrei" depois de esgotar essas tentativas — e seja explícito
  sobre o que foi tentado.

NUNCA INVENTE informação. Se o edital não cobre a pergunta, diga isso claramente.
NUNCA responda baseado apenas em conhecimento geral sobre concursos. TODA afirmação
factual sobre este edital deve vir de uma consulta via ferramenta no turno atual.

REFERÊNCIAS — OBRIGATÓRIO:
- Toda resposta factual sobre o edital DEVE terminar com uma linha separada,
  no formato EXATO abaixo (sem colchetes externos, sem negrito, sem aspas):

ref: edital [5.1, 9.6.6]

- Os valores dentro dos colchetes são os números de itens do edital que
  fundamentam sua resposta (ex: 5.1, 9.6.6, 7.11.4). Separe por vírgula.
- Para anexos, use Anexo I, Anexo IV, etc.:

ref: edital [Anexo IV]

- Múltiplas fontes:

ref: edital [5.1, Anexo IV]

- Se a pergunta não pede fato do edital (cumprimento, conversa genérica),
  NÃO inclua a referência.
- Se você não encontrou a informação, NÃO invente referências. Diga que
  não encontrou.

REGRAS GERAIS:
- Foque em Ciência de Dados, a menos que o usuário peça outra coisa.
- Responda em português brasileiro.
- Seja direto e objetivo.
- Prefira ler_capitulo a emendar múltiplas buscas quando a pergunta abrange uma seção inteira.
"""


SELF_CHECK_PROMPT = """\
Você é um verificador determinístico de respostas a perguntas sobre editais.

Um agente tentou responder a pergunta abaixo SEM consultar NENHUMA ferramenta neste turno.

Pergunta do usuário:
{pergunta}

Resposta que o agente pretende dar:
{resposta}

SUA TAREFA: decidir se essa resposta PODE ser enviada sem consulta, OU se o agente
precisa consultar alguma ferramenta antes.

REGRAS DE DECISÃO:
1. O contexto anterior da conversa NÃO é garantia de resposta correta para a pergunta
   atual. Perguntas de turnos anteriores podem ser sobre temas diferentes.
2. Qualquer pergunta que peça FATO ESPECÍFICO do edital (taxa, data, valor, número
   de vagas, regra, conteúdo programático, critério, etc.) PRECISA consultar ferramenta,
   a menos que a resposta cite explicitamente um trecho do edital já recuperado no
   turno atual.
3. Cumprimentos, agradecimentos, perguntas sobre capacidades do assistente, ou
   conversa genérica NÃO precisam de ferramenta.
4. Em caso de dúvida, exija consulta.

RESPONDA APENAS COM UMA DESTAS DUAS PALAVRAS, SEM MAIS NADA:
- PRECISA_CONSULTAR
- PODE_RESPONDER
"""


ALL_TOOLS = [
    listar_editais,
    buscar_no_edital,
    listar_capitulos,
    ler_capitulo,
    data_hoje,
]

TOOLS_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}


# Casa entradas de TOC nível 1: "# Título (p. X–Y)" — mesmo padrão do pdf_splitter.
_TOC_LEVEL1_RE = re.compile(
    r'^#\s+(?P<title>.+?)\s+\(p\.\s*\d+\s*[–\-]\s*\d+\)\s*$'
)


def _montar_contexto_edital(edital_id_ativo: int) -> str:
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


def _mapa_anexos(edital_id: int) -> dict[int, str]:
    """
    Retorna {cap_num: rotulo_curto} apenas dos capítulos do edital que são
    ANEXO ou APÊNDICE. Ex (BNDES): {13: 'Anexo I', 14: 'Anexo II',
    15: 'Anexo III', 16: 'Anexo IV'}.

    Capítulos do corpo (não-anexo) NÃO entram aqui de propósito: '5' como
    referência significa legitimamente 'item 5 do edital' e não deve ser
    reescrito.

    No modo 'Todos os editais' (edital_id<=0) retorna mapa vazio.
    """
    if edital_id <= 0:
        return {}

    conn = get_connection()
    row = conn.execute(
        "SELECT arquivo_origem FROM editais WHERE id = ?", (edital_id,)
    ).fetchone()
    conn.close()
    if not row or not row["arquivo_origem"]:
        return {}

    stem = Path(row["arquivo_origem"]).stem
    toc_path = settings.editais_dir / f"{stem}_toc.txt"
    if not toc_path.exists():
        return {}

    mapa: dict[int, str] = {}
    cap_num = 0  # cap_0 = preâmbulo; nível 1 do TOC começa em cap_1
    for linha in toc_path.read_text(encoding="utf-8").splitlines():
        m = _TOC_LEVEL1_RE.match(linha)
        if not m:
            continue
        cap_num += 1
        titulo = m.group("title").strip()
        if not titulo.upper().startswith(("ANEXO", "APÊNDICE", "APENDICE")):
            continue
        # Mantém só o rótulo curto antes do primeiro travessão/hífen separador.
        rotulo = re.split(r"\s+[—–-]\s+", titulo, maxsplit=1)[0].strip()
        # 'ANEXO I' → 'Anexo I'
        partes = rotulo.split()
        if partes:
            partes[0] = partes[0].capitalize()
            rotulo = " ".join(partes)
        mapa[cap_num] = rotulo
    return mapa


def _corrigir_refs_anexos(texto: str, mapa_anexos: dict[int, str]) -> str:
    """
    Encontra ocorrências de 'ref: edital [...]' e substitui itens que sejam
    inteiros puros e correspondam a um cap_num de anexo pelo rótulo do anexo.
    Itens com ponto (5.1, 9.6.6) ou já textuais (Anexo I) ficam intocados.
    """
    if not mapa_anexos:
        return texto

    def _substituir(match: re.Match) -> str:
        conteudo = match.group(1)
        itens = [it.strip() for it in conteudo.split(",")]
        novos: list[str] = []
        for it in itens:
            if it.isdigit() and int(it) in mapa_anexos:
                novos.append(mapa_anexos[int(it)])
            else:
                novos.append(it)
        return f"ref: edital [{', '.join(novos)}]"

    return re.sub(
        r"ref:\s*edital\s*\[([^\]]+)\]",
        _substituir,
        texto,
        flags=re.IGNORECASE,
    )


class Agent:
    def __init__(self, provider=None, model=None):
        self._provider = provider
        self._model = model
        llm = get_llm(provider=provider, model=model)
        self.llm = llm.bind_tools(ALL_TOOLS)
        self.llm_check = get_llm(provider=provider, model=model)
        self.max_iterations = 10

    def _self_check(self, pergunta: str, resposta: str) -> bool:
        prompt = SELF_CHECK_PROMPT.format(pergunta=pergunta, resposta=resposta)
        resp = self.llm_check.invoke([HumanMessage(content=prompt)])
        conteudo = resp.content if isinstance(resp.content, str) else str(resp.content)
        return "PRECISA_CONSULTAR" in conteudo.strip().upper()

    def ask(self, question, chat_history=None, edital_id_ativo=0):
        contexto = _montar_contexto_edital(edital_id_ativo)
        system_msg = SYSTEM_PROMPT.format(contexto_edital=contexto)
        mapa_anexos = _mapa_anexos(edital_id_ativo)

        if self._provider == "anthropic":
            sys_content = [{
                "type": "text",
                "text": system_msg,
                "cache_control": {"type": "ephemeral"},
            }]
        else:
            sys_content = system_msg
        messages = [SystemMessage(content=sys_content)]
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=question))

        tool_calls_no_turno = 0
        self_check_ja_disparado = False

        for _ in range(self.max_iterations):
            response = self.llm.invoke(messages)
            messages.append(response)

            if response.tool_calls:
                tool_calls_no_turno += len(response.tool_calls)
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
                continue

            if tool_calls_no_turno == 0 and not self_check_ja_disparado:
                self_check_ja_disparado = True
                precisa = self._self_check(
                    pergunta=question,
                    resposta=response.content if isinstance(response.content, str) else str(response.content),
                )
                if precisa:
                    messages.append(HumanMessage(content=(
                        "ATENÇÃO — verificação interna: sua resposta foi gerada sem "
                        "consultar nenhuma ferramenta neste turno. O contexto anterior "
                        "pode não cobrir a pergunta atual. Reconsidere e, se a pergunta "
                        "envolve qualquer fato específico do edital (taxa, data, valor, "
                        "regra, vaga, conteúdo programático, critério, etc.), chame a "
                        "ferramenta apropriada agora antes de responder."
                    )))
                    continue

            # Pós-processamento da resposta final.
            conteudo = response.content if isinstance(response.content, str) else str(response.content)
            # Normaliza "[ref: edital [7.2]]" → "ref: edital [7.2]"
            conteudo = re.sub(r"\[\s*(ref:\s*edital\s*\[[^\]]+\])\s*\]", r"\1", conteudo, flags=re.IGNORECASE)
            conteudo = re.sub(r"[ \t]+(ref:\s*edital\s*\[[^\]]+\])([.!?])?", r"\2\n\n\1", conteudo, flags=re.IGNORECASE)
            conteudo = re.sub(r"\n{3,}(ref:\s*edital\s*\[[^\]]+\])", r"\n\n\1", conteudo, flags=re.IGNORECASE)
            # Corrige refs numéricas que apontam para anexos (ex.: [13] → [Anexo I])
            conteudo = _corrigir_refs_anexos(conteudo, mapa_anexos)
            return conteudo

        return "Não consegui completar a consulta após várias tentativas. Tente reformular a pergunta."


def build_agent(provider=None, model=None):
    return Agent(provider=provider, model=model)


def ask(agent, question, chat_history=None, edital_id_ativo=0):
    return agent.ask(
        question=question,
        chat_history=chat_history,
        edital_id_ativo=edital_id_ativo,
    )