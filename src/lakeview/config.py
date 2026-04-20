"""Runtime config — loaded from environment (and .env in dev)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    # src/lakeview/config.py → project root three parents up.
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment-driven settings.

    Anything here is a knob that varies per deployment / per developer and
    should never be hardcoded in the source tree. `.env` at the project root
    is read automatically in dev; the process environment still wins.
    """

    model_config = SettingsConfigDict(
        env_prefix="LAKEVIEW_",
        env_file=(_project_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Default browse prefix when the UI starts with no ?prefix= in the URL.
    # Empty string means "no default; user picks from the root".
    default_prefix: str = ""


settings = Settings()
