"""Extração estruturada em etapas — lida com editais grandes."""

import json
import re
from models.llm_factory import get_llm
from models.schemas import EditalInfo
from langchain_core.messages import SystemMessage, HumanMessage


def _limpar_json(raw: str) -> str:
    """Remove marcadores markdown e lixo ao redor do JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


def _chamar_llm(system: str, user: str) -> str:
    """Faz uma chamada ao LLM e retorna o conteúdo."""
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])
    return response.content


def _extrair_dados_gerais(texto_parcial: str) -> dict:
    """Etapa 1: extrai dados gerais do edital (sem detalhes das ênfases)."""

    prompt = """Extraia os dados gerais deste edital de concurso.
Retorne APENAS JSON, sem markdown, sem explicação.

{
  "orgao": "",
  "numero_edital": "",
  "data_publicacao": "",
  "banca": "",
  "cargo": "",
  "salario_inicial": "",
  "jornada_trabalho": "",
  "beneficios": [],
  "regime_contratacao": "",
  "prazo_validade": "",
  "locais_prova": "",
  "etapas": [{"numero": 1, "nome": "", "tipo": "", "descricao": ""}],
  "provas": [{"disciplina": "", "num_questoes": 0, "pontos_por_questao": 0, "total_pontos": 0, "nota_minima": null, "carater": ""}],
  "criterios_desempate": [],
  "conteudo_basico": {"Língua Portuguesa": [], "Língua Inglesa": []},
  "cronograma": [{"evento": "", "data": ""}],
  "lista_enfases": ["nome de cada ênfase que aparecer no edital"]
}

IMPORTANTE: em "lista_enfases" coloque o nome de TODAS as ênfases/especialidades mencionadas, sem nenhuma exceção."""

    raw = _chamar_llm(prompt, texto_parcial)
    return json.loads(_limpar_json(raw))


def _extrair_enfases(texto_parcial: str, nomes_enfases: list[str]) -> list[dict]:
    """Etapa 2: extrai detalhes de um lote de ênfases."""

    nomes_str = "\n".join(f"- {n}" for n in nomes_enfases)

    prompt = f"""Extraia os dados das seguintes ênfases deste edital:
{nomes_str}

Retorne APENAS um JSON array, sem markdown:
[
  {{
    "enfase": "nome exato",
    "requisito_basico": "",
    "registro_profissional": "" ou null,
    "vagas_imediatas": {{"ampla_concorrencia": 0, "pessoa_com_deficiencia": 0, "candidato_negro": 0, "total": 0}},
    "cadastro_reserva": {{"ampla_concorrencia": 0, "pessoa_com_deficiencia": 0, "candidato_negro": 0, "total": 0}},
    "conteudo_programatico": ["tópico 1", "tópico 2"]
  }}
]

IMPORTANTE: retorne dados para TODAS as ênfases listadas acima, mesmo que tenha que deixar campos vazios."""

    raw = _chamar_llm(prompt, texto_parcial)
    return json.loads(_limpar_json(raw))


def _dividir_texto(texto: str, max_chars: int = 40000) -> list[str]:
    """Divide o texto em blocos por páginas, respeitando o limite."""
    paginas = texto.split("--- PÁGINA ")
    blocos = []
    bloco_atual = ""

    for pagina in paginas:
        if len(bloco_atual) + len(pagina) > max_chars and bloco_atual:
            blocos.append(bloco_atual)
            bloco_atual = ""
        bloco_atual += pagina

    if bloco_atual:
        blocos.append(bloco_atual)

    return blocos


def extrair_estruturado(texto_edital: str, arquivo_origem: str = "") -> EditalInfo:
    """Pipeline completo: extrai em etapas e monta o EditalInfo."""

    blocos = _dividir_texto(texto_edital)

    # Etapa 1: dados gerais (usa primeiro bloco que tem as info principais)
    print("  Etapa 1/2: extraindo dados gerais...")
    dados_gerais = _extrair_dados_gerais(texto_edital)

    lista_enfases = dados_gerais.pop("lista_enfases", [])
    print(f"  Ênfases encontradas: {len(lista_enfases)}")

    # Etapa 2: detalhes das ênfases em lotes
    print("  Etapa 2/2: extraindo detalhes das ênfases...")
    todas_enfases = []

    # Lotes de até 5 ênfases por chamada
    tamanho_lote = 5
    for i in range(0, len(lista_enfases), tamanho_lote):
        lote = lista_enfases[i:i + tamanho_lote]
        print(f"    Lote {i // tamanho_lote + 1}: {lote}")

        # Usa o bloco mais completo (todo o texto se couber, senão o maior bloco)
        texto_busca = texto_edital

        try:
            enfases_lote = _extrair_enfases(texto_busca, lote)
            todas_enfases.extend(enfases_lote)
        except Exception as e:
            print(f"    ERRO no lote: {e}")
            # Cria entries vazias pras ênfases que falharam
            for nome in lote:
                todas_enfases.append({"enfase": nome, "requisito_basico": "", "conteudo_programatico": []})

    dados_gerais["enfases"] = todas_enfases
    dados_gerais["arquivo_origem"] = arquivo_origem

    return EditalInfo.model_validate(dados_gerais)