"""Configuration management."""

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

    # FlareSolverr configuration
    flaresolverr_url: str | None = None

    class Config:
        env_file = ".env"
        env_prefix = "PRICERECON_"


def load_config(path: Path | str | None = None) -> dict:
    """Load YAML config file.

    Args:
        path: Path to config file (default: config.yml)

    Returns:
        Config dictionary
    """
    if path is None:
        path = Path("config.yml")

    config_path = Path(path)

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def get_settings() -> Settings:
    """Get application settings from env vars."""
    return Settings()