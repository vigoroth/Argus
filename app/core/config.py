from functools import lru_cache
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    anthropic_api_key: str = ""
    google_api_key: str = ""
    database_url: str = "postgresql+psycopg://claude:claude_dev_pw@localhost:5434/claude_desktop"
    nexus_vault_path: str = str(Path.home() / "vault")
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    embed_model: str = "text-embedding-3-small"
    llm_base_url: str | None = None
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "claude-desktop"

    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    def is_local(self) -> bool:
        return self.llm_provider == "ollama"

    @field_validator("llm_base_url", mode="before")
    @classmethod
    def _empty_string_to_none(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()