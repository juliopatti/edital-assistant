from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    # LLM
    llm_provider: str = Field(default="openai", description="'openai' ou 'google'")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_temperature: float = Field(default=0.2)

    # API Keys
    openai_api_key: str = Field(default="")
    google_api_key: str = Field(default="")

    # Paths
    base_dir: Path = Field(default=Path(__file__).parent)
    db_path: Path = Field(default=Path(__file__).parent / "storage" / "edital_assistant.db")
    editais_dir: Path = Field(default=Path(__file__).parent / "data" / "editais")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
