"""
Factory que retorna o LLM correto com base na configuração.

Uso:
    from models.llm_factory import get_llm
    llm = get_llm()  # usa config do .env
    llm = get_llm(provider="google", model="gemini-2.0-flash")  # override
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

    else:
        raise ValueError(
            f"Provider '{_provider}' não suportado. Use 'openai' ou 'google'."
        )


def list_available_models() -> dict[str, list[str]]:
    """Retorna modelos sugeridos por provider."""
    return {
        "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        "google": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    }
