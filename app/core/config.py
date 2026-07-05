from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    database_url: str = "postgresql+psycopg://claude:claude_dev_pw@localhost:5434/claude_desktop"
    # ARGUS_VAULT_PATH is the current name; NEXUS_VAULT_PATH still works for back-compat.
    argus_vault_path: str = Field(
        default=str(Path.home() / "vault"),
        validation_alias=AliasChoices("ARGUS_VAULT_PATH", "NEXUS_VAULT_PATH"),
    )
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    embed_model: str = "text-embedding-3-small"
    llm_base_url: str | None = None
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "argus"

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


def configure_tracing() -> bool:
    """If LangSmith tracing is enabled in settings, export the env vars LangChain
    reads so traces flow. No-op (returns False) when tracing is off or no key.
    Safe to call multiple times. Call once at process start."""
    import os

    s = get_settings()
    if not s.langsmith_tracing or not s.langsmith_api_key:
        return False
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = s.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = s.langsmith_project
    return True