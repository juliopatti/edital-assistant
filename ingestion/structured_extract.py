"""Extração estruturada — foco em Ciência de Dados."""

import json
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


def extrair_estruturado(texto_edital: str, arquivo_origem: str = "") -> EditalInfo:
    """Extrai dados gerais + ênfase de Ciência de Dados em uma única chamada."""

    prompt = """Você é um especialista em editais de concursos públicos brasileiros.

Extraia as informações deste edital. FOCO: apenas a ênfase de Ciência de Dados (ou nome mais próximo como "Análise de Dados", "Data Science", etc). Ignore as demais ênfases.

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
  "conteudo_basico": {"Língua Portuguesa": [], "Língua Inglesa": [], "Conhecimentos Transversais": []},
  "cronograma": [{"evento": "", "data": ""}],
  "enfases": [
    {
      "enfase": "nome exato da ênfase de Ciência de Dados conforme o edital",
      "requisito_basico": "COPIE O TEXTO EXATO DO EDITAL, NÃO PARAFRASEIE",
      "registro_profissional": null,
      "vagas_imediatas": {"ampla_concorrencia": 0, "pessoa_com_deficiencia": 0, "candidato_negro": 0, "total": 0},
      "cadastro_reserva": {"ampla_concorrencia": 0, "pessoa_com_deficiencia": 0, "candidato_negro": 0, "total": 0},
      "conteudo_programatico": ["APENAS O NOME de cada bloco/seção, ex: 'Matemática', 'Probabilidade e Estatística'. NÃO inclua subtópicos."]
    }
  ]
}

REGRAS CRÍTICAS:
1. O campo requisito_basico deve conter o texto LITERAL do edital, copiado palavra por palavra.
2. O campo conteudo_programatico deve listar o NOME de TODOS os blocos/seções do conteúdo específico (ex: "I - Matemática", "II - Probabilidade e Estatística"). Liste APENAS os nomes, sem subtópicos. Não omita nenhum bloco.
3. Se o edital não tiver ênfase de Ciência de Dados, use a ênfase mais próxima e informe no campo enfase.
4. Extraia apenas UMA ênfase (Ciência de Dados). O array enfases deve ter exatamente 1 item."""

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=texto_edital),
    ])

    raw = _limpar_json(response.content)
    data = json.loads(raw)
    data["arquivo_origem"] = arquivo_origem

    return EditalInfo.model_validate(data)