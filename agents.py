"""Agent definitions and LLM factory.

This module provides the factory function for creating LLM clients
for different providers (Gemini, Claude, Ollama).
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from config import get_config

__all__ = [
    "DEFAULT_MODELS",
    "LLMConfigurationError",
    "SUPPORTED_PROVIDERS",
    "get_default_model",
    "get_llm",
]

# Supported LLM providers (immutable)
SUPPORTED_PROVIDERS: frozenset[str] = frozenset(["gemini", "claude", "ollama"])

# Default models for each provider
DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-1.5-flash",
    "claude": "claude-3-haiku-20240307",
    "ollama": "llama3",
}


class LLMConfigurationError(Exception):
    """Raised when LLM provider is misconfigured."""

    def __init__(self, provider: str, missing_credential: str) -> None:
        """Initialize the error with provider and missing credential info.

        Args:
            provider: The LLM provider name (e.g., "gemini", "claude").
            missing_credential: The name of the missing credential.
        """
        self.provider = provider
        self.missing_credential = missing_credential
        super().__init__(
            f"Cannot use {provider}: {missing_credential} not set. "
            f"Add it to your .env file or environment."
        )


def get_default_model(provider: str) -> str:
    """Get the default model for a provider.

    Args:
        provider: The LLM provider name.

    Returns:
        The default model name for the provider.

    Raises:
        ValueError: If the provider is not supported.
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    return DEFAULT_MODELS[provider]


def get_llm(provider: str, model: str) -> BaseChatModel:
    """Create an LLM client for the specified provider and model.

    Factory function that returns the appropriate LangChain chat model
    based on the provider string. Provider names are case-insensitive.

    Args:
        provider: The LLM provider ("gemini", "claude", or "ollama").
        model: The model name to use.

    Returns:
        A BaseChatModel instance configured for the specified provider.

    Raises:
        ValueError: If the provider is not supported.
        LLMConfigurationError: If required credentials are missing.
    """
    config = get_config()
    provider = provider.lower()

    match provider:
        case "gemini":
            if not config.google_api_key:
                raise LLMConfigurationError("gemini", "GOOGLE_API_KEY")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=config.google_api_key,
            )
        case "claude":
            if not config.anthropic_api_key:
                raise LLMConfigurationError("claude", "ANTHROPIC_API_KEY")
            # type: ignore needed - langchain-anthropic type stubs are incomplete
            return ChatAnthropic(  # type: ignore[call-arg]
                model_name=model,
                api_key=config.anthropic_api_key,
            )
        case "ollama":
            return ChatOllama(
                model=model,
                base_url=config.ollama_base_url,
            )
        case _:
            raise ValueError(f"Unknown provider: {provider}")
