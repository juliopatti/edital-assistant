"""
Fase 1: extração de TOC (Table of Contents) de um PDF via LLM multimodal.

Fluxo:
    1. carrega PDF em base64 e invoca o LLM com PROMPT_TOC
    2. parseia a resposta em itens {texto, pagina_inicial, nivel}
    3. calcula pagina_final_aprox por item (janela até o próximo item de nível <=)
    4. formata como markdown com headers # / ## / ### / #### e ranges de página
    5. (opcional) salva em {stem}_toc.txt ao lado do PDF

Porta da célula 0 do notebook toc_sonnet.ipynb (sem alterações de comportamento).
"""

import re
from pathlib import Path

from langchain_core.messages import HumanMessage
from pypdf import PdfReader

from ingestion.md_pipeline.llm_multimodal import (
    carregar_pdf_base64,
    montar_llm_e_bloco_pdf,
)
from ingestion.md_pipeline.prompts import PROMPT_TOC, MAX_TOKENS_TOC


# ---------------------------------------------------------------------------
# Helpers puros (sem LLM)
# ---------------------------------------------------------------------------

def contar_paginas(caminho: str | Path) -> int:
    return len(PdfReader(str(caminho)).pages)


def nivel_linha(linha: str) -> int:
    """Nível visual conforme o bullet prefix. 99 = não reconhecido."""
    linha = linha.lstrip()
    if linha.startswith("▶"):
        return 1
    if linha.startswith("•"):
        return 2
    if linha.startswith("◦"):
        return 3
    if linha.startswith("▪"):
        return 4
    return 99


def extrair_itens(resultado: str) -> list[dict]:
    """Parseia a saída do LLM em lista de dicts {texto, pagina_inicial, nivel}."""
    itens = []
    padrao = re.compile(
        r"^(?P<raw>\s*[▶•◦▪]\s+.+?)\s+\(p\.\s*(?P<pagina>\d+)(?:–\d+)?\)\s*$"
    )

    for linha in resultado.splitlines():
        linha = linha.rstrip()
        if not linha:
            continue

        m = padrao.match(linha)
        if not m:
            continue

        texto = re.sub(r"^[\s▶•◦▪]+", "", m.group("raw")).strip()

        itens.append({
            "texto": texto,
            "pagina_inicial": int(m.group("pagina")),
            "nivel": nivel_linha(linha),
        })
    return itens


def inferir_janelas(resultado: str, ultima_pagina: int | None = None) -> list[dict]:
    """
    Para cada item, calcula 'pagina_final_aprox' como a página inicial do próximo
    item de nível <= ao atual (ou ultima_pagina se for o último).
    """
    itens = extrair_itens(resultado)

    for i, item in enumerate(itens):
        fim_aprox = ultima_pagina if ultima_pagina is not None else item["pagina_inicial"]

        for j in range(i + 1, len(itens)):
            prox = itens[j]
            if prox["nivel"] <= item["nivel"]:
                fim_aprox = prox["pagina_inicial"]
                break

        item["pagina_final_aprox"] = fim_aprox

    return itens


def formatar_toc_md(itens: list[dict]) -> str:
    """Converte os itens em markdown com #/##/###/#### e ranges (p. X–Y)."""
    linhas = []
    for item in itens:
        if item["nivel"] == 1:
            prefixo = "#"
        elif item["nivel"] == 2:
            prefixo = "##"
        elif item["nivel"] == 3:
            prefixo = "###"
        elif item["nivel"] == 4:
            prefixo = "####"
        else:
            prefixo = "#####"

        linhas.append(
            f'{prefixo} {item["texto"]} (p. {item["pagina_inicial"]}–{item["pagina_final_aprox"]})'
        )

    return "\n".join(linhas)


def salvar_toc_md(path_pdf: str | Path, toc_md: str) -> Path:
    """Salva o TOC em {stem}_toc.txt ao lado do PDF. Retorna o Path salvo."""
    path_pdf = Path(path_pdf)
    path_saida = path_pdf.with_name(f"{path_pdf.stem}_toc.txt")
    path_saida.write_text(toc_md, encoding="utf-8")
    return path_saida


# ---------------------------------------------------------------------------
# Top-level (com chamada LLM)
# ---------------------------------------------------------------------------

def get_toc_md(
    path_pdf: str | Path,
    provider: str,
    modelo: str,
    max_tokens: int = MAX_TOKENS_TOC,
) -> str:
    """
    Extrai, processa e retorna o TOC do PDF como markdown.
    Não salva em disco — use salvar_toc_md() para isso.
    """
    pdf_b64 = carregar_pdf_base64(path_pdf)
    llm, bloco_pdf = montar_llm_e_bloco_pdf(pdf_b64, provider, modelo, max_tokens)

    mensagem = HumanMessage(content=[bloco_pdf, {"type": "text", "text": PROMPT_TOC}])
    resposta = llm.invoke([mensagem])

    conteudo = resposta.content
    if isinstance(conteudo, list):
        conteudo = "".join(
            b["text"]
            for b in conteudo
            if isinstance(b, dict) and b.get("type") == "text"
        )

    ultima_pagina = contar_paginas(path_pdf)
    itens = inferir_janelas(conteudo, ultima_pagina=ultima_pagina)
    return formatar_toc_md(itens)
