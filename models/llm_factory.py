"""
Factory que retorna o LLM correto com base na configuração.

Uso:
    from models.llm_factory import get_llm
    llm = get_llm()  # usa config do .env
    llm = get_llm(provider="anthropic", model="claude-sonnet-4-6")  # override
"""

from langchain_core.language_models import BaseChatModel
from config import settings


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """Retorna o LLM configurado. Parâmetros sobrescrevem o .env."""

    _provider = (provider or settings.llm_provider).lower()
    _model = model or settings.llm_model
    _temperature = temperature if temperature is not None else settings.llm_temperature

    if _provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=_model,
            temperature=_temperature,
            api_key=settings.openai_api_key,
        )

    elif _provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=_model,
            temperature=_temperature,
            google_api_key=settings.google_api_key,
        )

    elif _provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=_model,
            temperature=_temperature,
            api_key=settings.anthropic_api_key,
        )

    elif _provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=_model,
            temperature=_temperature,
            api_key=settings.groq_api_key,
        )

    else:
        raise ValueError(
            f"Provider '{_provider}' não suportado. "
            "Use 'openai', 'google', 'anthropic' ou 'groq'."
        )


def list_available_models() -> dict[str, list[str]]:
    """Retorna modelos sugeridos por provider."""
    return {
        "openai": [
            "gpt-4o-mini",
            "gpt-5.4-mini",
            "gpt-5.4",
            "gpt-5.5",
        ],
        "google": [
            "gemini-2.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.1-pro-preview",
        ],
        "anthropic": [
            "claude-haiku-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-7",
        ],
        "groq": [
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.3-70b-versatile",
        ],
    }