"""Configuration loading and defaults.

This module handles configuration from multiple sources:
1. config/defaults.yaml - Base configuration values
2. Environment variables (.env file) - Override defaults
3. Runtime UI changes - Session-level overrides (future stories)
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "AgentConfig",
    "AgentsConfig",
    "AppConfig",
    "get_config",
    "validate_api_keys",
]

# Load .env file if it exists
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent


def _load_yaml_defaults() -> dict[str, Any]:
    """Load defaults from config/defaults.yaml."""
    defaults_path = PROJECT_ROOT / "config" / "defaults.yaml"
    if defaults_path.exists():
        with open(defaults_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


class AgentConfig(BaseSettings):
    """Configuration for a single agent."""

    provider: str = "gemini"
    model: str = "gemini-1.5-flash"
    token_limit: int = 8000


class AgentsConfig(BaseSettings):
    """Configuration for all agents."""

    dm: AgentConfig = Field(default_factory=AgentConfig)
    summarizer: AgentConfig = Field(
        default_factory=lambda: AgentConfig(token_limit=4000)
    )


class AppConfig(BaseSettings):
    """Application configuration with environment variable support.

    Configuration hierarchy:
    1. Environment variables (highest priority)
    2. .env file
    3. defaults.yaml (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys (from environment)
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # LLM Defaults (from YAML, overridable by env)
    default_provider: str = "gemini"
    default_model: str = "gemini-1.5-flash"

    # Game defaults
    party_size: int = 4
    auto_save: bool = True

    # Agent-specific configs
    agents: AgentsConfig = Field(default_factory=AgentsConfig)

    @classmethod
    def load(cls) -> "AppConfig":
        """Load config with YAML defaults + env overrides.

        Returns:
            AppConfig instance with merged configuration.
        """
        yaml_defaults = _load_yaml_defaults()

        # Extract agent configs from YAML if present
        agents_yaml = yaml_defaults.pop("agents", {})
        dm_config = AgentConfig(**agents_yaml.get("dm", {}))
        summarizer_config = AgentConfig(**agents_yaml.get("summarizer", {}))
        agents_config = AgentsConfig(dm=dm_config, summarizer=summarizer_config)

        # Build kwargs from YAML, but let env vars take precedence
        kwargs: dict[str, Any] = {
            "agents": agents_config,
        }

        # Only set YAML defaults if env var is not set
        if "DEFAULT_PROVIDER" not in os.environ:
            kwargs["default_provider"] = yaml_defaults.get("default_provider", "gemini")
        if "DEFAULT_MODEL" not in os.environ:
            kwargs["default_model"] = yaml_defaults.get(
                "default_model", "gemini-1.5-flash"
            )
        if "PARTY_SIZE" not in os.environ:
            kwargs["party_size"] = yaml_defaults.get("party_size", 4)
        if "AUTO_SAVE" not in os.environ:
            kwargs["auto_save"] = yaml_defaults.get("auto_save", True)

        return cls(**kwargs)


def validate_api_keys(config: AppConfig) -> list[str]:
    """Validate API keys and return warnings for missing ones.

    Args:
        config: The application configuration to validate.

    Returns:
        List of warning messages for missing API keys.
    """
    warnings: list[str] = []

    if not config.google_api_key:
        warnings.append("GOOGLE_API_KEY not set - Gemini models will not be available")

    if not config.anthropic_api_key:
        warnings.append(
            "ANTHROPIC_API_KEY not set - Claude models will not be available"
        )

    return warnings


# Singleton config instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the singleton configuration instance.

    Returns:
        The application configuration.
    """
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config
