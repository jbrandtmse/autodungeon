"""Tests for agent definitions and LLM factory."""

import os
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

import agents
import config as config_module
from agents import (
    DEFAULT_MODELS,
    SUPPORTED_PROVIDERS,
    LLMConfigurationError,
    get_default_model,
    get_llm,
)


@pytest.fixture(autouse=True)
def reset_config_singleton() -> Generator[None, None, None]:
    """Reset config singleton before each test to ensure isolation."""
    config_module._config = None
    yield
    config_module._config = None


class TestSupportedProviders:
    """Tests for provider constants."""

    def test_supported_providers_frozenset(self) -> None:
        """Test that SUPPORTED_PROVIDERS is an immutable frozenset with expected providers."""
        assert isinstance(SUPPORTED_PROVIDERS, frozenset)
        assert "gemini" in SUPPORTED_PROVIDERS
        assert "claude" in SUPPORTED_PROVIDERS
        assert "ollama" in SUPPORTED_PROVIDERS
        assert len(SUPPORTED_PROVIDERS) == 3

    def test_default_models_dict(self) -> None:
        """Test that DEFAULT_MODELS has entries for all providers."""
        for provider in SUPPORTED_PROVIDERS:
            assert provider in DEFAULT_MODELS
            assert isinstance(DEFAULT_MODELS[provider], str)
            assert len(DEFAULT_MODELS[provider]) > 0


class TestGetDefaultModel:
    """Tests for get_default_model helper."""

    def test_get_default_model_gemini(self) -> None:
        """Test getting default model for gemini."""
        model = get_default_model("gemini")
        assert model == "gemini-1.5-flash"

    def test_get_default_model_claude(self) -> None:
        """Test getting default model for claude."""
        model = get_default_model("claude")
        assert model == "claude-3-haiku-20240307"

    def test_get_default_model_ollama(self) -> None:
        """Test getting default model for ollama."""
        model = get_default_model("ollama")
        assert model == "llama3"

    def test_get_default_model_unknown_provider(self) -> None:
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            get_default_model("unknown")


class TestLLMConfigurationError:
    """Tests for LLMConfigurationError exception."""

    def test_error_attributes(self) -> None:
        """Test that error has provider and missing_credential attributes."""
        error = LLMConfigurationError("gemini", "GOOGLE_API_KEY")
        assert error.provider == "gemini"
        assert error.missing_credential == "GOOGLE_API_KEY"

    def test_error_message_format(self) -> None:
        """Test that error message is descriptive."""
        error = LLMConfigurationError("claude", "ANTHROPIC_API_KEY")
        message = str(error)
        assert "claude" in message
        assert "ANTHROPIC_API_KEY" in message
        assert ".env" in message


class TestGetLLMGemini:
    """Tests for get_llm with Gemini provider."""

    @patch("agents.ChatGoogleGenerativeAI")
    def test_get_llm_gemini_returns_correct_type(self, mock_class: MagicMock) -> None:
        """Test that get_llm returns ChatGoogleGenerativeAI for gemini."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-12345"}, clear=False):
            result = get_llm("gemini", "gemini-1.5-flash")

        assert result is mock_instance
        mock_class.assert_called_once()
        call_kwargs = mock_class.call_args.kwargs
        assert call_kwargs["model"] == "gemini-1.5-flash"
        assert call_kwargs["google_api_key"] == "test-key-12345"

    def test_get_llm_gemini_missing_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing GOOGLE_API_KEY raises LLMConfigurationError."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            get_llm("gemini", "gemini-1.5-flash")

        assert exc_info.value.provider == "gemini"
        assert exc_info.value.missing_credential == "GOOGLE_API_KEY"
        assert "GOOGLE_API_KEY" in str(exc_info.value)


class TestGetLLMClaude:
    """Tests for get_llm with Claude provider."""

    @patch("agents.ChatAnthropic")
    def test_get_llm_claude_returns_correct_type(self, mock_class: MagicMock) -> None:
        """Test that get_llm returns ChatAnthropic for claude."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"}, clear=False
        ):
            result = get_llm("claude", "claude-3-haiku-20240307")

        assert result is mock_instance
        mock_class.assert_called_once()
        call_kwargs = mock_class.call_args.kwargs
        assert call_kwargs["model_name"] == "claude-3-haiku-20240307"
        assert call_kwargs["api_key"] == "test-anthropic-key"

    def test_get_llm_claude_missing_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing ANTHROPIC_API_KEY raises LLMConfigurationError."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            get_llm("claude", "claude-3-haiku-20240307")

        assert exc_info.value.provider == "claude"
        assert exc_info.value.missing_credential == "ANTHROPIC_API_KEY"


class TestGetLLMOllama:
    """Tests for get_llm with Ollama provider."""

    @patch("agents.ChatOllama")
    def test_get_llm_ollama_returns_correct_type(self, mock_class: MagicMock) -> None:
        """Test that get_llm returns ChatOllama for ollama."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        result = get_llm("ollama", "llama3")

        assert result is mock_instance
        mock_class.assert_called_once()
        call_kwargs = mock_class.call_args.kwargs
        assert call_kwargs["model"] == "llama3"
        assert call_kwargs["base_url"] == "http://localhost:11434"

    @patch("agents.ChatOllama")
    def test_get_llm_ollama_uses_custom_base_url(
        self, mock_class: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that Ollama uses custom base URL from config."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:11434")

        result = get_llm("ollama", "mistral")

        assert result is mock_instance
        call_kwargs = mock_class.call_args.kwargs
        assert call_kwargs["base_url"] == "http://custom:11434"

    @patch("agents.ChatOllama")
    def test_get_llm_ollama_no_api_key_required(
        self, mock_class: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that Ollama doesn't require API keys."""
        mock_class.return_value = MagicMock()

        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Should not raise - Ollama doesn't need API keys
        result = get_llm("ollama", "llama3")
        assert result is not None


class TestGetLLMUnknownProvider:
    """Tests for get_llm with unknown provider."""

    def test_get_llm_unknown_provider_raises_valueerror(self) -> None:
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            get_llm("unknown", "some-model")

    def test_get_llm_valueerror_message_includes_provider(self) -> None:
        """Test that ValueError message includes the provider name."""
        with pytest.raises(ValueError) as exc_info:
            get_llm("not-a-provider", "model")

        assert "not-a-provider" in str(exc_info.value)


class TestProviderNormalization:
    """Tests for provider string normalization."""

    @patch("agents.ChatGoogleGenerativeAI")
    def test_get_llm_accepts_uppercase_provider(
        self, mock_class: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that uppercase provider names are accepted."""
        mock_class.return_value = MagicMock()
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        # Should not raise - provider should be normalized
        result = get_llm("GEMINI", "gemini-1.5-flash")
        assert result is not None

    @patch("agents.ChatAnthropic")
    def test_get_llm_accepts_mixed_case_provider(
        self, mock_class: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that mixed case provider names are accepted."""
        mock_class.return_value = MagicMock()
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Should not raise - provider should be normalized
        result = get_llm("Claude", "claude-3-haiku-20240307")
        assert result is not None


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_public_symbols_exported(self) -> None:
        """Test that all public symbols are in __all__."""
        # Expected exports defined in agents module
        expected_exports = {
            "get_llm",
            "get_default_model",
            "LLMConfigurationError",
            "SUPPORTED_PROVIDERS",
            "DEFAULT_MODELS",
        }

        assert set(agents.__all__) == expected_exports
