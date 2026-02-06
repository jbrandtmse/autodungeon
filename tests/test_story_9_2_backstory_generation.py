"""Tests for Story 9-2: AI-Assisted Backstory Generation.

Tests the backstory generation prompt creation and response parsing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestBackstoryPromptGeneration:
    """Tests for backstory prompt generation."""

    def test_generate_backstory_prompt_returns_string(self) -> None:
        """Prompt generator returns a string."""
        from app import generate_backstory_prompt

        wizard_data = {
            "name": "Thorin",
            "race_id": "dwarf",
            "class_id": "fighter",
            "background_id": "soldier",
        }

        prompt = generate_backstory_prompt(wizard_data)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_prompt_includes_character_name(self) -> None:
        """Prompt includes the character's name."""
        from app import generate_backstory_prompt

        wizard_data = {
            "name": "Elara Moonwhisper",
            "race_id": "elf",
            "class_id": "wizard",
            "background_id": "sage",
        }

        prompt = generate_backstory_prompt(wizard_data)
        assert "Elara Moonwhisper" in prompt

    def test_prompt_includes_race_info(self) -> None:
        """Prompt includes race name and traits."""
        from app import generate_backstory_prompt

        wizard_data = {
            "name": "Test",
            "race_id": "elf",
            "class_id": "rogue",
            "background_id": "criminal",
        }

        prompt = generate_backstory_prompt(wizard_data)
        assert "Elf" in prompt
        assert "Darkvision" in prompt or "traits" in prompt.lower()

    def test_prompt_includes_class_name(self) -> None:
        """Prompt includes class name."""
        from app import generate_backstory_prompt

        wizard_data = {
            "name": "Test",
            "race_id": "human",
            "class_id": "paladin",
            "background_id": "acolyte",
        }

        prompt = generate_backstory_prompt(wizard_data)
        assert "Paladin" in prompt

    def test_prompt_includes_background_info(self) -> None:
        """Prompt includes background name and feature."""
        from app import generate_backstory_prompt

        wizard_data = {
            "name": "Test",
            "race_id": "human",
            "class_id": "cleric",
            "background_id": "acolyte",
        }

        prompt = generate_backstory_prompt(wizard_data)
        assert "Acolyte" in prompt
        assert "Shelter of the Faithful" in prompt or "feature" in prompt.lower()

    def test_prompt_requests_structured_format(self) -> None:
        """Prompt requests specific sections."""
        from app import generate_backstory_prompt

        wizard_data = {
            "name": "Test",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
        }

        prompt = generate_backstory_prompt(wizard_data)
        assert "PERSONALITY_TRAITS" in prompt
        assert "IDEALS" in prompt
        assert "BONDS" in prompt
        assert "FLAWS" in prompt
        assert "BACKSTORY" in prompt

    def test_prompt_handles_missing_selections(self) -> None:
        """Prompt handles missing race/class/background gracefully."""
        from app import generate_backstory_prompt

        wizard_data = {
            "name": "Test",
            "race_id": "",
            "class_id": "",
            "background_id": "",
        }

        prompt = generate_backstory_prompt(wizard_data)
        assert "Unknown" in prompt  # Falls back to Unknown


class TestBackstoryResponseParsing:
    """Tests for parsing LLM backstory responses."""

    def test_parse_complete_response(self) -> None:
        """Parse a complete well-formatted response."""
        from app import parse_backstory_response

        response = """PERSONALITY_TRAITS:
I am always polite and respectful.
I have a strong sense of justice.

IDEALS:
Honor. I never break my word. (Lawful)

BONDS:
I protect those who cannot protect themselves.

FLAWS:
I am too trusting of authority figures.

BACKSTORY:
Born in a small village, I trained for years to become a warrior.
My mentor taught me the value of honor and duty.
Now I seek to prove myself in the wider world."""

        result = parse_backstory_response(response)

        assert "polite" in result["personality_traits"]
        assert "justice" in result["personality_traits"]
        assert "Honor" in result["ideals"]
        assert "protect" in result["bonds"]
        assert "trusting" in result["flaws"]
        assert "village" in result["backstory"]

    def test_parse_response_with_extra_whitespace(self) -> None:
        """Parse handles extra whitespace."""
        from app import parse_backstory_response

        response = """

PERSONALITY_TRAITS:

  I love adventure.


IDEALS:
  Freedom above all.

BONDS:
My family.

FLAWS:
  I'm reckless.

BACKSTORY:
A simple story.

"""

        result = parse_backstory_response(response)

        assert "adventure" in result["personality_traits"]
        assert "Freedom" in result["ideals"]
        assert "family" in result["bonds"]
        assert "reckless" in result["flaws"]
        assert "simple" in result["backstory"]

    def test_parse_response_handles_missing_sections(self) -> None:
        """Parse returns empty strings for missing sections."""
        from app import parse_backstory_response

        response = """PERSONALITY_TRAITS:
I am brave.

BACKSTORY:
Short story."""

        result = parse_backstory_response(response)

        assert result["personality_traits"] != ""
        assert result["ideals"] == ""
        assert result["bonds"] == ""
        assert result["flaws"] == ""
        assert result["backstory"] != ""

    def test_parse_empty_response(self) -> None:
        """Parse handles empty response."""
        from app import parse_backstory_response

        result = parse_backstory_response("")

        assert result["personality_traits"] == ""
        assert result["ideals"] == ""
        assert result["bonds"] == ""
        assert result["flaws"] == ""
        assert result["backstory"] == ""

    def test_parse_returns_all_required_keys(self) -> None:
        """Parse always returns all required keys."""
        from app import parse_backstory_response

        result = parse_backstory_response("random text without sections")

        assert "personality_traits" in result
        assert "ideals" in result
        assert "bonds" in result
        assert "flaws" in result
        assert "backstory" in result


class TestGenerateBackstoryFunction:
    """Tests for the main generate_backstory function."""

    @patch("agents.get_llm")
    @patch("config.get_config")
    def test_generate_backstory_calls_llm(
        self, mock_get_config: MagicMock, mock_get_llm: MagicMock
    ) -> None:
        """Generate backstory calls the LLM."""
        from app import generate_backstory

        # Setup mocks
        mock_config = MagicMock()
        mock_config.dm.provider = "gemini"
        mock_config.dm.model = "gemini-2.0-flash"
        mock_get_config.return_value = mock_config

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """PERSONALITY_TRAITS:
Brave and bold.

IDEALS:
Justice.

BONDS:
My village.

FLAWS:
Too trusting.

BACKSTORY:
A hero's tale."""
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        wizard_data = {
            "name": "Test Hero",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
        }

        result = generate_backstory(wizard_data)

        assert isinstance(result, dict)
        assert "personality_traits" in result
        mock_llm.invoke.assert_called_once()

    @patch("agents.get_llm")
    @patch("config.get_config")
    def test_generate_backstory_handles_llm_config_error(
        self, mock_get_config: MagicMock, mock_get_llm: MagicMock
    ) -> None:
        """Generate backstory returns error string on config error."""
        from agents import LLMConfigurationError
        from app import generate_backstory

        mock_config = MagicMock()
        mock_config.dm.provider = "gemini"
        mock_config.dm.model = "gemini-2.0-flash"
        mock_get_config.return_value = mock_config

        mock_get_llm.side_effect = LLMConfigurationError("gemini", "GOOGLE_API_KEY")

        wizard_data = {
            "name": "Test",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
        }

        result = generate_backstory(wizard_data)

        assert isinstance(result, str)
        assert "not configured" in result.lower() or "error" in result.lower()

    @patch("agents.get_llm")
    @patch("config.get_config")
    def test_generate_backstory_handles_llm_error(
        self, mock_get_config: MagicMock, mock_get_llm: MagicMock
    ) -> None:
        """Generate backstory returns error string on LLM error."""
        from agents import LLMError
        from app import generate_backstory

        mock_config = MagicMock()
        mock_config.dm.provider = "gemini"
        mock_config.dm.model = "gemini-2.0-flash"
        mock_get_config.return_value = mock_config

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = LLMError(
            provider="gemini",
            agent="dm",
            error_type="api_error",
            original_error=Exception("API call failed"),
        )
        mock_get_llm.return_value = mock_llm

        wizard_data = {
            "name": "Test",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
        }

        result = generate_backstory(wizard_data)

        assert isinstance(result, str)
        assert "error" in result.lower()


class TestBackstoryIntegration:
    """Integration tests for backstory generation components."""

    def test_prompt_and_parse_roundtrip(self) -> None:
        """Prompt format matches what parser expects."""
        from app import generate_backstory_prompt, parse_backstory_response

        wizard_data = {
            "name": "Aria",
            "race_id": "half-elf",
            "class_id": "bard",
            "background_id": "entertainer",
        }

        prompt = generate_backstory_prompt(wizard_data)

        # Verify prompt asks for the exact sections parser expects
        assert "PERSONALITY_TRAITS:" in prompt
        assert "IDEALS:" in prompt
        assert "BONDS:" in prompt
        assert "FLAWS:" in prompt
        assert "BACKSTORY:" in prompt

    def test_all_races_produce_valid_prompts(self) -> None:
        """All races can be used in prompt generation."""
        from app import generate_backstory_prompt
        from config import get_dnd5e_races

        races = get_dnd5e_races()

        for race in races:
            wizard_data = {
                "name": "Test",
                "race_id": race["id"],
                "class_id": "fighter",
                "background_id": "soldier",
            }

            prompt = generate_backstory_prompt(wizard_data)
            assert race["name"] in prompt

    def test_all_classes_produce_valid_prompts(self) -> None:
        """All classes can be used in prompt generation."""
        from app import generate_backstory_prompt
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()

        for cls in classes:
            wizard_data = {
                "name": "Test",
                "race_id": "human",
                "class_id": cls["id"],
                "background_id": "soldier",
            }

            prompt = generate_backstory_prompt(wizard_data)
            assert cls["name"] in prompt

    def test_all_backgrounds_produce_valid_prompts(self) -> None:
        """All backgrounds can be used in prompt generation."""
        from app import generate_backstory_prompt
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()

        for bg in backgrounds:
            wizard_data = {
                "name": "Test",
                "race_id": "human",
                "class_id": "fighter",
                "background_id": bg["id"],
            }

            prompt = generate_backstory_prompt(wizard_data)
            assert bg["name"] in prompt
