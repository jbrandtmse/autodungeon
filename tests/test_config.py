"""Tests for configuration loading."""

import os
from unittest.mock import patch


class TestEnvironmentVariables:
    """Tests for environment variable loading."""

    def test_env_file_loading(self) -> None:
        """Test that .env file values are loaded."""
        from config import AppConfig

        # With no env vars set, should get None for API keys
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig()
            # API keys should be None when not set
            assert config.google_api_key is None
            assert config.anthropic_api_key is None

    def test_env_vars_override(self) -> None:
        """Test that environment variables are properly read."""
        from config import AppConfig

        test_key = "test-google-key-12345"
        with patch.dict(os.environ, {"GOOGLE_API_KEY": test_key}, clear=False):
            config = AppConfig()
            assert config.google_api_key == test_key

    def test_ollama_default_url(self) -> None:
        """Test that Ollama has a default URL."""
        from config import AppConfig

        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig()
            assert config.ollama_base_url == "http://localhost:11434"

    def test_missing_api_keys_no_crash(self) -> None:
        """Test that missing API keys produce warnings, not crashes."""
        from config import AppConfig, validate_api_keys

        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig()
            # Should not raise, just return warnings
            warnings = validate_api_keys(config)
            assert len(warnings) > 0
            assert any("GOOGLE_API_KEY" in w for w in warnings)


class TestPydanticSettings:
    """Tests for Pydantic Settings configuration."""

    def test_yaml_defaults_loaded(self) -> None:
        """Test that defaults.yaml values are loaded."""
        from config import AppConfig

        config = AppConfig.load()
        # These should match config/defaults.yaml
        assert config.default_provider == "gemini"
        assert config.default_model == "gemini-1.5-flash"
        assert config.party_size == 4
        assert config.auto_save is True

    def test_agent_configs_from_yaml(self) -> None:
        """Test that agent-specific configs are loaded from YAML."""
        from config import AppConfig

        config = AppConfig.load()
        # DM agent config
        assert config.agents.dm.provider == "gemini"
        assert config.agents.dm.model == "gemini-1.5-flash"
        assert config.agents.dm.token_limit == 8000
        # Summarizer agent config
        assert config.agents.summarizer.provider == "gemini"
        assert config.agents.summarizer.token_limit == 4000

    def test_env_overrides_yaml(self) -> None:
        """Test that environment variables override YAML defaults."""
        from config import AppConfig

        with patch.dict(os.environ, {"DEFAULT_PROVIDER": "anthropic"}, clear=False):
            config = AppConfig.load()
            # Env var should override YAML default
            assert config.default_provider == "anthropic"

    def test_singleton_get_config(self) -> None:
        """Test that get_config returns a singleton instance.

        Note: conftest.py fixture resets the singleton before each test.
        """
        import config as config_module

        config1 = config_module.get_config()
        config2 = config_module.get_config()

        # Should be the same instance
        assert config1 is config2
