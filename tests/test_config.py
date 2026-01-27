"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError


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


class TestCharacterConfigLoading:
    """Tests for character YAML configuration loading."""

    def test_load_character_configs_from_directory(self) -> None:
        """Test that all character configs are loaded from config/characters/."""
        from config import load_character_configs

        configs = load_character_configs()
        # Should have 4 PC characters (not dm)
        assert len(configs) == 4
        # Check lowercase keys
        assert "thorin" in configs
        assert "shadowmere" in configs
        assert "elara" in configs
        assert "brother aldric" in configs

    def test_character_config_validation(self) -> None:
        """Test that loaded configs are valid CharacterConfig instances."""
        from config import load_character_configs
        from models import CharacterConfig

        configs = load_character_configs()
        for _name, config in configs.items():
            assert isinstance(config, CharacterConfig)
            assert config.name.strip() != ""
            assert config.character_class.strip() != ""
            assert config.color.startswith("#")

    def test_load_dm_config(self) -> None:
        """Test that DM config is loaded correctly from dm.yaml."""
        from config import load_dm_config
        from models import DMConfig

        dm_config = load_dm_config()
        assert isinstance(dm_config, DMConfig)
        assert dm_config.name == "Dungeon Master"
        assert dm_config.provider == "gemini"
        assert dm_config.color == "#D4A574"

    def test_character_colors_from_yaml(self) -> None:
        """Test that character colors match UX spec values."""
        from config import load_character_configs, load_dm_config

        dm_config = load_dm_config()
        pc_configs = load_character_configs()

        # Verify UX spec colors
        assert dm_config.color == "#D4A574"  # gold
        assert pc_configs["thorin"].color == "#C45C4A"  # red (Fighter)
        assert pc_configs["shadowmere"].color == "#6B8E6B"  # green (Rogue)
        assert pc_configs["elara"].color == "#7B68B8"  # purple (Wizard)
        assert pc_configs["brother aldric"].color == "#4A90A4"  # blue (Cleric)

    def test_missing_required_field_raises_validation_error(self) -> None:
        """Test that missing required fields raise ValidationError."""
        from models import CharacterConfig

        # Missing 'name' field should raise
        with pytest.raises(ValidationError):
            CharacterConfig(
                character_class="Rogue",
                personality="test",
                color="#123456",
            )

    def test_invalid_color_format_raises_validation_error(self) -> None:
        """Test that invalid hex color format raises ValidationError."""
        from models import CharacterConfig

        with pytest.raises(ValidationError) as exc_info:
            CharacterConfig(
                name="Test",
                character_class="Rogue",
                personality="test",
                color="not-a-color",  # Invalid format
            )
        assert "hex color" in str(exc_info.value).lower()

    def test_load_character_configs_handles_missing_directory(self) -> None:
        """Test graceful handling when characters directory doesn't exist."""
        from config import load_character_configs

        # Temporarily patch PROJECT_ROOT to a non-existent path
        with patch("config.PROJECT_ROOT", Path("/nonexistent/path")):
            configs = load_character_configs()
            # Should return empty dict, not crash
            assert configs == {}

    def test_load_dm_config_handles_missing_file(self) -> None:
        """Test graceful handling when dm.yaml doesn't exist."""
        from config import load_dm_config
        from models import DMConfig

        # Temporarily patch PROJECT_ROOT to a non-existent path
        with patch("config.PROJECT_ROOT", Path("/nonexistent/path")):
            dm_config = load_dm_config()
            # Should return default DMConfig
            assert isinstance(dm_config, DMConfig)
            assert dm_config.name == "Dungeon Master"

    def test_dynamic_character_discovery(self) -> None:
        """Test that new YAML files are discovered on load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            characters_dir = Path(tmpdir) / "config" / "characters"
            characters_dir.mkdir(parents=True)

            # Create a test character YAML
            test_char = {
                "name": "TestHero",
                "class": "Barbarian",
                "personality": "Fierce and bold",
                "color": "#FF0000",
            }
            with open(characters_dir / "testhero.yaml", "w") as f:
                yaml.dump(test_char, f)

            # Patch PROJECT_ROOT to use temp directory
            with patch("config.PROJECT_ROOT", Path(tmpdir)):
                from config import load_character_configs

                configs = load_character_configs()
                assert "testhero" in configs
                assert configs["testhero"].name == "TestHero"
                assert configs["testhero"].character_class == "Barbarian"

    def test_malformed_yaml_raises_value_error(self) -> None:
        """Test that malformed YAML files raise ValueError with clear message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            characters_dir = Path(tmpdir) / "config" / "characters"
            characters_dir.mkdir(parents=True)

            # Create a malformed YAML file
            with open(characters_dir / "bad.yaml", "w") as f:
                f.write("name: Test\n  bad indent: broken")

            with patch("config.PROJECT_ROOT", Path(tmpdir)):
                from config import load_character_configs

                with pytest.raises(ValueError) as exc_info:
                    load_character_configs()
                assert "Invalid YAML" in str(exc_info.value)
                assert "bad.yaml" in str(exc_info.value)

    def test_invalid_provider_in_yaml_raises_value_error(self) -> None:
        """Test that invalid provider in YAML raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            characters_dir = Path(tmpdir) / "config" / "characters"
            characters_dir.mkdir(parents=True)

            # Create a character with invalid provider
            bad_char = {
                "name": "BadProvider",
                "class": "Fighter",
                "personality": "Test",
                "color": "#FF0000",
                "provider": "openai",  # Not supported
            }
            with open(characters_dir / "badprovider.yaml", "w") as f:
                yaml.dump(bad_char, f)

            with patch("config.PROJECT_ROOT", Path(tmpdir)):
                from config import load_character_configs

                with pytest.raises(ValueError) as exc_info:
                    load_character_configs()
                assert "Invalid character config" in str(exc_info.value)
                assert "badprovider.yaml" in str(exc_info.value)
