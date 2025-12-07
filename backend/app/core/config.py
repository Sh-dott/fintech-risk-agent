"""
Configuration management for Risk Decision Engine API
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import yaml


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    app_name: str = "Risk Decision Engine API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # CORS Settings
    cors_origins: list = ["*"]

    # Model Configuration
    model_config_path: str = "backend/config/model_config.yaml"

    # Database (for future use)
    database_url: Optional[str] = None

    # Redis (for future use)
    redis_url: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_model_config(config_path: str = "backend/config/model_config.yaml") -> dict:
    """Load model configuration from YAML file."""
    config_file = Path(config_path)

    if not config_file.exists():
        # Try alternate path for backwards compatibility
        config_file = Path("config/model_config.yaml")

    if not config_file.exists():
        raise FileNotFoundError(f"Model config file not found: {config_path}")

    with open(config_file, "r") as f:
        return yaml.safe_load(f)


# Global settings instance
settings = Settings()
