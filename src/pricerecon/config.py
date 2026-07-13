"""Application configuration."""

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    database_path: str = "pricerecon.db"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"

    # Optional API auth
    api_key: str | None = None

    # FlareSolverr configuration
    flaresolverr_url: str | None = None

    # Telegram notification configuration
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # Discord webhook configuration
    discord_webhook_url: str | None = None

    # Webhook configuration
    webhook_url: str | None = None

    class Config:
        env_file = ".env"
        env_prefix = "PRICERECON_"


def _deep_merge(base: dict, overlay: dict) -> dict:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: Path | str | None = None) -> dict:
    """Load YAML config file, optionally overlaying config.local.yml."""
    if path is None:
        path = Path("config.yml")

    config_path = Path(path)
    config: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    local_override = config_path.with_name("config.local.yml")
    if local_override.exists():
        with open(local_override) as f:
            local_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, local_config)

    return config


def get_settings() -> Settings:
    """Get application settings from env vars."""
    return Settings()
