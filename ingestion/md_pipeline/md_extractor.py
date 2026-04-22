"""
Fases 3 e 4: cada PDF de capítulo é convertido em markdown (ou texto corrido, no
cap_0) via LLM multimodal com filtro pela ênfase "Ciência de Dados".

- cap_0 é tratado à parte: não é capítulo estrutural, é o preâmbulo do edital
  (órgão, edital, data). PROMPT_CAP0 pede texto corrido, sem formatação.
- cap_1..cap_N usam PROMPT_EXTRACAO_CAP, que:
    * limita o escopo entre o título atual e o próximo (robusto à imprecisão do
      split por página, que pode invadir o início do próximo capítulo)
    * omite seções exclusivas de outras ênfases
    * preserva texto literal, numeração e tabelas

Porta das células 7, 9 e 11 do notebook toc_sonnet.ipynb.
"""

from pathlib import Path

from langchain_core.messages import HumanMessage

from ingestion.md_pipeline.llm_multimodal import (
    carregar_pdf_base64,
    montar_llm_e_bloco_pdf,
)
from ingestion.md_pipeline.prompts import (
    PROMPT_EXTRACAO_CAP,
    PROMPT_CAP0,
    MAX_TOKENS_CAP,
)


def _invocar(llm, bloco_pdf, prompt: str) -> str:
    """Invoca o LLM com (pdf + texto) e retorna a string de resposta."""
    msg = HumanMessage(content=[bloco_pdf, {"type": "text", "text": prompt}])
    resp = llm.invoke([msg])
    return resp.content if isinstance(resp.content, str) else resp.content[0]["text"]


def extrair_md_capitulo(
    path_pdf_cap: str | Path,
    titulo_capitulo: str,
    titulo_proximo: str | None,
    provider: str,
    modelo: str,
    max_tokens: int = MAX_TOKENS_CAP,
) -> str:
    """
    Extrai markdown filtrado de UM capítulo (cap_1..cap_N).

    Passa o título do próximo capítulo pro LLM para que ele pare corretamente
    quando o PDF contiver o início do capítulo seguinte (efeito colateral do
    split por página, que é impreciso).
    """
    if titulo_proximo:
        trecho_proximo = f' ("{titulo_proximo}")'
        trecho_parada  = f' — identificado pelo título "{titulo_proximo}"'
    else:
        trecho_proximo = ""
        trecho_parada  = ""

    prompt = PROMPT_EXTRACAO_CAP.format(
        titulo_capitulo=titulo_capitulo,
        trecho_proximo=trecho_proximo,
        trecho_parada=trecho_parada,
    )

    pdf_b64 = carregar_pdf_base64(path_pdf_cap)
    llm, bloco_pdf = montar_llm_e_bloco_pdf(pdf_b64, provider, modelo, max_tokens)
    return _invocar(llm, bloco_pdf, prompt)


def extrair_texto_cap0(
    path_pdf_cap: str | Path,
    titulo_proximo: str | None,
    provider: str,
    modelo: str,
    max_tokens: int = MAX_TOKENS_CAP,
) -> str:
    """
    Extrai texto corrido do cap_0 (preâmbulo do edital).
    Diferente dos demais caps, aqui NÃO se aplica markdown.
    """
    trecho_parada = f' ("{titulo_proximo}")' if titulo_proximo else ""
    prompt = PROMPT_CAP0.format(trecho_parada=trecho_parada)

    pdf_b64 = carregar_pdf_base64(path_pdf_cap)
    llm, bloco_pdf = montar_llm_e_bloco_pdf(pdf_b64, provider, modelo, max_tokens)
    return _invocar(llm, bloco_pdf, prompt)


def processar_edital(
    capitulos: list[dict],
    provider: str,
    modelo: str,
    pular: list[int] | None = None,
) -> None:
    """
    Gera arquivos .md para todos os capítulos do edital.

    Args:
        capitulos: lista retornada por pdf_splitter.split_edital.
        provider:  provider do LLM multimodal (ex.: "anthropic", "google").
        modelo:    apelido do modelo (ex.: "haiku", "flash-lite").
        pular:     lista de chapter_num a pular (útil pra reexecução parcial).

    Cada .md é salvo ao lado do respectivo cap_N.pdf, com o mesmo stem.
    """
    pular = set(pular or [])
    caps_por_num = {c["chapter_num"]: c for c in capitulos}

    for cap in sorted(capitulos, key=lambda c: c["chapter_num"]):
        cap_num  = cap["chapter_num"]
        cap_path = cap["cap_path"]

        if cap_num in pular or not isinstance(cap_path, str):
            print(f"[skip] cap_{cap_num}")
            continue

        prox = caps_por_num.get(cap_num + 1)
        titulo_proximo = prox["title"] if prox else None

        if cap_num == 0:
            md = extrair_texto_cap0(cap_path, titulo_proximo, provider, modelo)
        else:
            md = extrair_md_capitulo(
                cap_path, cap["title"], titulo_proximo, provider, modelo
            )

        out_path = Path(cap_path).with_suffix(".md")
        out_path.write_text(md, encoding="utf-8")
        print(f"[ok]   cap_{cap_num}: {len(md):>6,} chars → {out_path.name}")
