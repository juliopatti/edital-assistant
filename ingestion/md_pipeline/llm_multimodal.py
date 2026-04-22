"""
Utilitário para montar um LLM multimodal e o bloco de PDF (base64)
no formato esperado por cada provider.

Anthropic espera content blocks do tipo "document" com source base64.
Google espera content blocks do tipo "media" com mime_type.

Essa função centraliza o que estava duplicado em três células do notebook
(get_toc_md, extrair_md_capitulo, extrair_texto_cap0). Nenhum comportamento
novo é introduzido — mesmos modelos, mesmos tipos de bloco, temperature=0.
"""

import base64
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from ingestion.md_pipeline.prompts import MODELOS


def carregar_pdf_base64(path_pdf: str | Path) -> str:
    """Lê um PDF do disco e retorna string base64."""
    return base64.b64encode(Path(path_pdf).read_bytes()).decode("utf-8")


def montar_llm_e_bloco_pdf(
    pdf_b64: str,
    provider: str,
    modelo: str,
    max_tokens: int,
):
    """
    Retorna (llm, bloco_pdf) apropriados para o provider escolhido.

    Args:
        pdf_b64:    PDF já codificado em base64.
        provider:   "anthropic" ou "google".
        modelo:     apelido definido em MODELOS[provider] (ex.: "sonnet", "haiku", "flash-lite").
        max_tokens: limite de tokens de saída.

    Raises:
        KeyError: se provider/modelo não existirem em MODELOS.
        ValueError: se provider não for suportado.
    """
    if provider not in MODELOS:
        raise ValueError(
            f"Provider '{provider}' não suportado. Use um de: {list(MODELOS.keys())}."
        )
    if modelo not in MODELOS[provider]:
        raise KeyError(
            f"Modelo '{modelo}' não definido para provider '{provider}'. "
            f"Disponíveis: {list(MODELOS[provider].keys())}."
        )

    model_id = MODELOS[provider][modelo]

    if provider == "anthropic":
        llm = ChatAnthropic(
            model=model_id,
            max_tokens=max_tokens,
            temperature=0,
        )
        bloco_pdf = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        }
    else:  # google
        llm = ChatGoogleGenerativeAI(
            model=model_id,
            max_tokens=max_tokens,
            temperature=0,
        )
        bloco_pdf = {
            "type": "media",
            "mime_type": "application/pdf",
            "data": pdf_b64,
        }

    return llm, bloco_pdf
