"""Configuration loaded from environment variables (.env supported)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration for LineagePulse.

    All fields can be overridden via env vars or a local ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # DataHub
    datahub_gms_url: str = "http://localhost:8080"
    datahub_token: str | None = None
    datahub_mutations_enabled: bool = True

    # LLM
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-5"
    llm_temperature: float = 0.1
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Slack
    slack_webhook_url: str | None = None
    slack_default_channel: str = "#data-incidents"
    slack_channel_routing: dict[str, str] = Field(default_factory=dict)

    # Agent behavior
    poll_interval_seconds: int = 300
    lineage_depth: int = 3
    dry_run: bool = True

    # Misc
    log_level: str = "INFO"

    @field_validator("slack_channel_routing", mode="before")
    @classmethod
    def parse_channel_routing(cls, v: Any) -> dict[str, str]:
        if v in (None, "", {}):
            return {}
        if isinstance(v, dict):
            return {str(k): str(val) for k, val in v.items()}
        if isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return {str(k): str(val) for k, val in parsed.items()}
            except json.JSONDecodeError:
                pass
        return {}

    def has_llm_credentials(self) -> bool:
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        return False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
