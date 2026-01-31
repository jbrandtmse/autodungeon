"""Configuration loading and defaults.

This module handles configuration from multiple sources:
1. config/defaults.yaml - Base configuration values
2. Environment variables (.env file) - Override defaults
3. Runtime UI changes - Session-level overrides (future stories)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from models import CharacterConfig, DMConfig, ValidationResult
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "AgentConfig",
    "AgentsConfig",
    "AppConfig",
    "CLAUDE_MODELS",
    "DEFAULT_MAX_CONTEXT",
    "GEMINI_MODELS",
    "MINIMUM_TOKEN_LIMIT",
    "MODEL_MAX_CONTEXT",
    "OLLAMA_FALLBACK_MODELS",
    "_sanitize_error_message",
    "get_api_key_source",
    "get_available_models",
    "get_config",
    "get_effective_api_key",
    "get_model_max_context",
    "load_character_configs",
    "load_dm_config",
    "load_user_settings",
    "mask_api_key",
    "save_user_settings",
    "validate_anthropic_api_key",
    "validate_api_keys",
    "validate_google_api_key",
    "validate_ollama_connection",
]

# Load .env file if it exists
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# User settings file path
USER_SETTINGS_PATH = PROJECT_ROOT / "user-settings.yaml"


def load_user_settings() -> dict[str, Any]:
    """Load user settings from user-settings.yaml.

    Returns settings dict with structure:
    {
        "api_keys": {"google": "...", "anthropic": "...", "ollama": "..."},
        "agent_model_overrides": {"dm": {"provider": "...", "model": "..."}, ...},
        "token_limit_overrides": {"dm": 8000, ...}
    }

    Returns empty dict if file doesn't exist.
    """
    if not USER_SETTINGS_PATH.exists():
        return {}
    try:
        with open(USER_SETTINGS_PATH, encoding="utf-8") as f:
            settings = yaml.safe_load(f)
            return settings if settings else {}
    except (yaml.YAMLError, OSError):
        return {}


def save_user_settings(settings: dict[str, Any]) -> None:
    """Save user settings to user-settings.yaml.

    Args:
        settings: Dict with api_keys, agent_model_overrides, token_limit_overrides.
    """
    try:
        with open(USER_SETTINGS_PATH, "w", encoding="utf-8") as f:
            yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
    except OSError:
        pass  # Silently fail if can't write


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
    def load(cls) -> AppConfig:
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


def load_character_configs() -> dict[str, CharacterConfig]:
    """Load all PC character configs from config/characters/*.yaml.

    Discovers and loads all YAML files in the characters directory except dm.yaml.
    Each character config is keyed by lowercase name for turn_queue consistency.

    Returns:
        Dict of CharacterConfig instances keyed by lowercase character name.
        Returns empty dict if characters directory doesn't exist.

    Raises:
        ValueError: If a YAML file is malformed or contains invalid data.
    """
    # Import here to avoid circular import
    from pydantic import ValidationError

    from models import CharacterConfig

    characters_dir = PROJECT_ROOT / "config" / "characters"
    configs: dict[str, CharacterConfig] = {}

    if not characters_dir.exists():
        return configs

    for yaml_file in characters_dir.glob("*.yaml"):
        if yaml_file.stem == "dm":
            continue  # DM handled separately by load_dm_config

        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {yaml_file.name}: {e}") from e

        if data is None:
            continue

        # Map YAML 'class' to Pydantic 'character_class' if needed
        if "class" in data and "character_class" not in data:
            data["character_class"] = data.pop("class")

        try:
            config = CharacterConfig(**data)
        except ValidationError as e:
            raise ValueError(
                f"Invalid character config in {yaml_file.name}: {e}"
            ) from e

        # Key by lowercase name for turn_queue consistency
        configs[config.name.lower()] = config

    return configs


def load_dm_config() -> DMConfig:
    """Load DM configuration from config/characters/dm.yaml.

    Returns:
        DMConfig instance. Returns default DMConfig if file doesn't exist.

    Raises:
        ValueError: If dm.yaml is malformed or contains invalid data.
    """
    # Import here to avoid circular import
    from pydantic import ValidationError

    from models import DMConfig

    dm_yaml_path = PROJECT_ROOT / "config" / "characters" / "dm.yaml"

    if not dm_yaml_path.exists():
        return DMConfig()

    try:
        with open(dm_yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in dm.yaml: {e}") from e

    if data is None:
        return DMConfig()

    try:
        return DMConfig(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid DM config in dm.yaml: {e}") from e


def validate_api_keys(config: AppConfig) -> list[str]:
    """Validate API keys and return warnings for missing ones.

    Checks both environment config and user-settings.yaml for API keys.

    Args:
        config: The application configuration to validate.

    Returns:
        List of warning messages for missing API keys.
    """
    warnings: list[str] = []

    # Get user settings for API key overrides
    user_settings = load_user_settings()
    api_keys = user_settings.get("api_keys", {})

    # Check both env config and user settings
    if not config.google_api_key and not api_keys.get("google"):
        warnings.append("GOOGLE_API_KEY not set - Gemini models will not be available")

    if not config.anthropic_api_key and not api_keys.get("anthropic"):
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


# =============================================================================
# API Key Management (Story 6.2)
# =============================================================================


def mask_api_key(key: str) -> str:
    """Mask an API key, showing only last 4 characters.

    For security, displays most of the key as asterisks with only
    the last 4 characters visible for identification.

    Args:
        key: The API key to mask.

    Returns:
        Masked key string (e.g., "***************xyz9").

    Example:
        >>> mask_api_key("sk-abc123xyz789")
        '**********x789'
    """
    if not key or len(key) < 8:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]


def get_api_key_source(provider: str, overrides: dict[str, str] | None = None) -> str:
    """Determine the source of an API key for a provider.

    Checks for UI override first, then environment variable, then empty.

    Args:
        provider: Provider name ("google", "anthropic", or "ollama").
        overrides: Optional dict of UI override values.

    Returns:
        "ui_override" if set via UI, "environment" if set via env var,
        or "empty" if not set.
    """
    overrides = overrides or {}

    # Check UI override first
    if provider in overrides and overrides[provider]:
        return "ui_override"

    # Check environment variable
    config = get_config()
    match provider:
        case "google":
            if config.google_api_key:
                return "environment"
        case "anthropic":
            if config.anthropic_api_key:
                return "environment"
        case "ollama":
            # Ollama always has a default URL, so check if it differs from default
            if config.ollama_base_url != "http://localhost:11434":
                return "environment"
            # If using default, still consider it "environment" (always available)
            return "environment"
        case _:
            pass  # Unknown provider

    return "empty"


def get_effective_api_key(
    provider: str, overrides: dict[str, str] | None = None
) -> str | None:
    """Get the effective API key for a provider.

    Priority:
    1. UI override (if set)
    2. Environment variable
    3. None

    Args:
        provider: Provider name ("google", "anthropic", or "ollama").
        overrides: Optional dict of UI override values.

    Returns:
        The effective API key or URL, or None if not available.
    """
    overrides = overrides or {}

    # Check UI override first
    if provider in overrides and overrides[provider]:
        return overrides[provider]

    # Fall back to environment
    config = get_config()
    match provider:
        case "google":
            return config.google_api_key
        case "anthropic":
            return config.anthropic_api_key
        case "ollama":
            return config.ollama_base_url
        case _:
            return None


def validate_google_api_key(api_key: str) -> ValidationResult:
    """Validate Google API key by making a minimal API call.

    Uses the Gemini API's model list endpoint which is lightweight
    and doesn't consume tokens.

    Args:
        api_key: The Google API key to validate.

    Returns:
        ValidationResult with valid status, message, and available models.
    """
    # Import here to avoid circular import and at runtime
    from models import ValidationResult

    if not api_key or not api_key.strip():
        return ValidationResult(valid=False, message="API key is empty", models=None)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        # List models is a lightweight call that validates the key
        models_list = list(genai.list_models())
        # Filter to models that support content generation and are gemini- prefixed
        available_models = [
            m.name.replace("models/", "")  # Strip "models/" prefix
            for m in models_list
            if hasattr(m, "supported_generation_methods")
            and "generateContent" in m.supported_generation_methods
            and m.name.startswith("models/gemini-")  # Only gemini models
        ]
        return ValidationResult(
            valid=True,
            message=f"Valid - {len(available_models)} models available",
            models=available_models,  # Return all gemini models
        )
    except Exception as e:
        error_str = str(e).lower()
        if (
            "api_key" in error_str
            or "api key" in error_str
            or "401" in str(e)
            or "403" in str(e)
            or "invalid" in error_str
        ):
            return ValidationResult(valid=False, message="Invalid API key", models=None)
        # Network or other error - sanitize to prevent key leakage
        error_str_raw = str(e)
        # Remove any potential API key patterns from error message
        sanitized_msg = _sanitize_error_message(error_str_raw)
        error_msg = sanitized_msg[:50] if len(sanitized_msg) > 50 else sanitized_msg
        return ValidationResult(
            valid=False, message=f"Connection error: {error_msg}", models=None
        )


def _sanitize_error_message(message: str) -> str:
    """Sanitize error message to prevent API key leakage.

    Removes any patterns that look like API keys from error messages
    to prevent accidental exposure in the UI.

    Args:
        message: Raw error message that may contain sensitive data.

    Returns:
        Sanitized message safe for display.
    """
    import re

    # Pattern for common API key formats (sk-, AIza, etc.)
    # Remove anything that looks like it could be an API key
    patterns = [
        r"sk-[a-zA-Z0-9_-]{10,}",  # OpenAI/Anthropic style
        r"AIza[a-zA-Z0-9_-]{30,}",  # Google style
        r"key[=:\s]+['\"]?[a-zA-Z0-9_-]{20,}['\"]?",  # Generic key= pattern
        r"api[_-]?key[=:\s]+['\"]?[a-zA-Z0-9_-]{10,}['\"]?",  # api_key= pattern
    ]
    result = message
    for pattern in patterns:
        result = re.sub(pattern, "[REDACTED]", result, flags=re.IGNORECASE)
    return result


def validate_anthropic_api_key(api_key: str) -> ValidationResult:
    """Validate Anthropic API key by making a lightweight API call.

    Uses the beta.messages.count_tokens endpoint which validates the key
    with minimal cost. Note: This may incur small API usage charges.

    Args:
        api_key: The Anthropic API key to validate.

    Returns:
        ValidationResult with valid status and message.
    """
    # Import here to avoid circular import
    from models import ValidationResult

    if not api_key or not api_key.strip():
        return ValidationResult(valid=False, message="API key is empty", models=None)

    # Check key format - Anthropic keys typically start with "sk-ant-"
    # But also allow other formats as they may change
    api_key = api_key.strip()

    # Basic format validation
    if len(api_key) < 20:
        return ValidationResult(
            valid=False, message="API key appears too short", models=None
        )

    # Try to make a minimal API call to verify the key
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        # Use beta.messages.count_tokens which validates key without generating
        # This validates the API key without consuming output tokens
        client.beta.messages.count_tokens(  # type: ignore[attr-defined]
            model="claude-3-haiku-20240307",
            messages=[{"role": "user", "content": "Hi"}],
        )
        return ValidationResult(
            valid=True,
            message="Valid - Claude models available",
            models=[
                "claude-sonnet-4-20250514",
                "claude-3-5-sonnet-20241022",
                "claude-3-haiku-20240307",
            ],
        )
    except Exception as e:
        error_str = str(e).lower()
        if (
            "authentication" in error_str
            or "api_key" in error_str
            or "api key" in error_str
            or "invalid" in error_str
            or "401" in str(e)
            or "403" in str(e)
        ):
            return ValidationResult(valid=False, message="Invalid API key", models=None)
        # Network or other error - sanitize to prevent key leakage
        sanitized_msg = _sanitize_error_message(str(e))
        error_msg = sanitized_msg[:50] if len(sanitized_msg) > 50 else sanitized_msg
        return ValidationResult(
            valid=False, message=f"Connection error: {error_msg}", models=None
        )


def validate_ollama_connection(base_url: str) -> ValidationResult:
    """Validate Ollama connection by checking the server and listing models.

    No API key required - just needs network access to the Ollama server.

    Args:
        base_url: The Ollama server base URL.

    Returns:
        ValidationResult with valid status, message, and available models.
    """
    # Import here to avoid circular import
    import httpx

    from models import ValidationResult

    if not base_url or not base_url.strip():
        return ValidationResult(valid=False, message="Base URL is empty", models=None)

    try:
        # Use sync client with timeout
        with httpx.Client(timeout=5.0) as client:
            url = f"{base_url.rstrip('/')}/api/tags"
            response = client.get(url)

            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    return ValidationResult(
                        valid=True,
                        message=f"Connected - {len(models)} models available",
                        models=models[:10],  # Limit for display
                    )
                else:
                    return ValidationResult(
                        valid=True,
                        message="Connected - no models installed",
                        models=[],
                    )
            else:
                return ValidationResult(
                    valid=False,
                    message=f"Server error: HTTP {response.status_code}",
                    models=None,
                )
    except httpx.ConnectError:
        return ValidationResult(
            valid=False,
            message=f"Server not responding at {base_url}",
            models=None,
        )
    except httpx.TimeoutException:
        return ValidationResult(
            valid=False,
            message="Connection timed out",
            models=None,
        )
    except Exception as e:
        error_msg = str(e)[:50] if len(str(e)) > 50 else str(e)
        return ValidationResult(
            valid=False,
            message=f"Connection error: {error_msg}",
            models=None,
        )


# =============================================================================
# Model Context Limits (Story 6.4)
# =============================================================================

# Model maximum context window sizes in tokens
# These represent the maximum tokens a model can accept as input context
MODEL_MAX_CONTEXT: dict[str, int] = {
    # Gemini models (as of 2024-2025)
    "gemini-1.5-flash": 1_000_000,
    "gemini-1.5-pro": 2_000_000,
    "gemini-2.0-flash": 1_000_000,
    # Claude models
    "claude-3-haiku-20240307": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-sonnet-4-20250514": 200_000,
    # Ollama models - conservative defaults (varies by model/hardware)
    "llama3": 8_192,
    "mistral": 32_768,
    "phi3": 128_000,
}

# Default for unknown models (conservative)
DEFAULT_MAX_CONTEXT = 8_192

# Default for Ollama models (conservative for local inference)
DEFAULT_OLLAMA_CONTEXT = 8_000

# Minimum token limit threshold for low-limit warning (Story 6.4 AC #3)
MINIMUM_TOKEN_LIMIT = 1_000


def get_model_max_context(model: str) -> int:
    """Get maximum context window for a model.

    Args:
        model: Model name string.

    Returns:
        Maximum token count for the model's context window.
        Returns DEFAULT_MAX_CONTEXT for unknown models.

    Example:
        >>> get_model_max_context("gemini-1.5-flash")
        1000000
        >>> get_model_max_context("unknown-model")
        8192
    """
    return MODEL_MAX_CONTEXT.get(model, DEFAULT_MAX_CONTEXT)


def get_default_token_limit(provider: str, model: str) -> int:
    """Get the default token limit for a provider/model combination.

    Used to auto-set token limits when the user changes models.
    - Ollama: Returns 8000 (conservative default for local inference)
    - Gemini/Claude: Returns model's max context window

    Args:
        provider: Provider name (gemini, claude, ollama).
        model: Model name string.

    Returns:
        Default token limit for the provider/model combination.

    Example:
        >>> get_default_token_limit("ollama", "llama3")
        8000
        >>> get_default_token_limit("gemini", "gemini-2.0-flash")
        1000000
    """
    if provider.lower() == "ollama":
        return DEFAULT_OLLAMA_CONTEXT

    # For Gemini/Claude, use max context as default
    return get_model_max_context(model)


# =============================================================================
# Per-Agent Model Selection (Story 6.3)
# =============================================================================

# Model lists by provider (static for Gemini/Claude, dynamic for Ollama)
GEMINI_MODELS: list[str] = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
]

CLAUDE_MODELS: list[str] = [
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20241022",
    "claude-sonnet-4-20250514",
]

OLLAMA_FALLBACK_MODELS: list[str] = [
    "llama3",
    "mistral",
    "phi3",
]


def get_available_models(provider: str) -> list[str]:
    """Get available models for a provider.

    Returns the list of models available for selection in the Models tab.
    For Gemini and Claude, returns static lists. For Ollama, returns
    dynamically discovered models or a fallback suggestion list.

    Args:
        provider: Provider name ("gemini", "claude", or "ollama").

    Returns:
        List of model names for the provider.

    Example:
        >>> get_available_models("gemini")
        ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash']
    """
    provider = provider.lower()

    if provider == "gemini":
        # Try to get models from session state (set by validation)
        try:
            import streamlit as st

            models = st.session_state.get("gemini_available_models")
            if models and isinstance(models, list) and len(models) > 0:
                return list(models)
        except (ImportError, AttributeError):
            # Streamlit not available (e.g., in tests)
            pass
        # Fallback to static list
        return GEMINI_MODELS.copy()
    elif provider == "claude":
        return CLAUDE_MODELS.copy()
    elif provider == "ollama":
        # Try to get models from session state (set by Story 6.2 validation)
        try:
            import streamlit as st

            models = st.session_state.get("ollama_available_models")
            if models and isinstance(models, list) and len(models) > 0:
                return list(models)
        except (ImportError, AttributeError):
            # Streamlit not available (e.g., in tests)
            pass
        # Fallback to suggestions
        return OLLAMA_FALLBACK_MODELS.copy()
    else:
        # Unknown provider - return empty list
        return []
