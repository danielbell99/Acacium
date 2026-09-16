from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration with safe local defaults for the interview prototype."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ACACIUM_")

    data_dir: Path = Field(default=Path("data"))
    demo_mode: bool = True
    cors_origins: str = "http://localhost:5173"

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def manifest_path(self) -> Path:
        return Path("config/source-manifest.json")


@lru_cache
def get_settings() -> Settings:
    return Settings()
