"""Expanded test coverage for TEA automate workflow.

This file contains additional tests to fill coverage gaps identified
by the Test Expansion Automation analysis:
- config.py edge cases
- agents.py context building functions
- models.py edge cases
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Config.py Expanded Coverage
# =============================================================================


class TestValidateApiKeysExpanded:
    """Expanded tests for validate_api_keys function."""

    def test_validate_api_keys_no_warnings_when_all_present(self) -> None:
        """Test that no warnings when all API keys are configured."""
        from config import AppConfig, validate_api_keys

        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_KEY": "test-google-key",
                "ANTHROPIC_API_KEY": "test-anthropic-key",
            },
            clear=False,
        ):
            config = AppConfig()
            warnings = validate_api_keys(config)
            assert len(warnings) == 0

    def test_validate_api_keys_only_google_missing(self) -> None:
        """Test warning only for Google when only that key is missing."""
        from config import AppConfig, validate_api_keys

        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-anthropic-key"},
            clear=True,
        ):
            config = AppConfig()
            warnings = validate_api_keys(config)
            assert len(warnings) == 1
            assert "GOOGLE_API_KEY" in warnings[0]
            assert "ANTHROPIC" not in warnings[0]

    def test_validate_api_keys_only_anthropic_missing(self) -> None:
        """Test warning only for Anthropic when only that key is missing."""
        from config import AppConfig, validate_api_keys

        with patch.dict(
            os.environ,
            {"GOOGLE_API_KEY": "test-google-key"},
            clear=True,
        ):
            config = AppConfig()
            warnings = validate_api_keys(config)
            assert len(warnings) == 1
            assert "ANTHROPIC_API_KEY" in warnings[0]
            assert "GOOGLE" not in warnings[0]


class TestLoadYamlDefaultsEdgeCases:
    """Tests for _load_yaml_defaults edge cases."""

    def test_load_yaml_defaults_missing_file_returns_empty_dict(self) -> None:
        """Test that missing defaults.yaml returns empty dict."""
        from config import _load_yaml_defaults

        with patch("config.PROJECT_ROOT", Path("/nonexistent/path")):
            result = _load_yaml_defaults()
            assert result == {}

    def test_load_yaml_defaults_empty_file_returns_empty_dict(self) -> None:
        """Test that empty defaults.yaml returns empty dict."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            # Create empty YAML file
            (config_dir / "defaults.yaml").write_text("")

            with patch("config.PROJECT_ROOT", Path(tmpdir)):
                from config import _load_yaml_defaults

                result = _load_yaml_defaults()
                assert result == {}


class TestLoadCharacterConfigsEdgeCases:
    """Tests for load_character_configs edge cases."""

    def test_load_character_configs_skips_dm_yaml(self) -> None:
        """Test that dm.yaml is skipped when loading character configs."""
        import tempfile

        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            characters_dir = Path(tmpdir) / "config" / "characters"
            characters_dir.mkdir(parents=True)

            # Create dm.yaml (should be skipped)
            dm_data = {"name": "DM", "provider": "gemini", "model": "gemini-1.5-flash"}
            (characters_dir / "dm.yaml").write_text(yaml.dump(dm_data))

            # Create a regular character
            char_data = {
                "name": "TestChar",
                "class": "Fighter",
                "personality": "Bold",
                "color": "#FF0000",
            }
            (characters_dir / "testchar.yaml").write_text(yaml.dump(char_data))

            with patch("config.PROJECT_ROOT", Path(tmpdir)):
                from config import load_character_configs

                configs = load_character_configs()
                assert "dm" not in configs
                assert "testchar" in configs

    def test_load_character_configs_empty_yaml_file_skipped(self) -> None:
        """Test that empty YAML files are skipped gracefully."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            characters_dir = Path(tmpdir) / "config" / "characters"
            characters_dir.mkdir(parents=True)

            # Create empty YAML file
            (characters_dir / "empty.yaml").write_text("")

            with patch("config.PROJECT_ROOT", Path(tmpdir)):
                from config import load_character_configs

                configs = load_character_configs()
                # Should not crash, just skip empty file
                assert configs == {}


class TestLoadDmConfigEdgeCases:
    """Tests for load_dm_config edge cases."""

    def test_load_dm_config_empty_yaml_returns_default(self) -> None:
        """Test that empty dm.yaml returns default DMConfig."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            characters_dir = Path(tmpdir) / "config" / "characters"
            characters_dir.mkdir(parents=True)

            # Create empty dm.yaml
            (characters_dir / "dm.yaml").write_text("")

            with patch("config.PROJECT_ROOT", Path(tmpdir)):
                from config import load_dm_config
                from models import DMConfig

                dm_config = load_dm_config()
                assert isinstance(dm_config, DMConfig)
                assert dm_config.name == "Dungeon Master"

    def test_load_dm_config_malformed_yaml_raises_value_error(self) -> None:
        """Test that malformed dm.yaml raises ValueError."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            characters_dir = Path(tmpdir) / "config" / "characters"
            characters_dir.mkdir(parents=True)

            # Create malformed dm.yaml
            (characters_dir / "dm.yaml").write_text("name: DM\n  bad: indent")

            with patch("config.PROJECT_ROOT", Path(tmpdir)):
                from config import load_dm_config

                with pytest.raises(ValueError) as exc_info:
                    load_dm_config()
                assert "Invalid YAML" in str(exc_info.value)
                assert "dm.yaml" in str(exc_info.value)


# =============================================================================
# Agents.py Context Building Expanded Coverage
# =============================================================================


class TestBuildDMContextExpanded:
    """Expanded tests for _build_dm_context function."""

    def test_build_dm_context_empty_memories(self) -> None:
        """Test DM context with empty agent memories."""
        from agents import _build_dm_context
        from models import create_initial_game_state

        state = create_initial_game_state()
        context = _build_dm_context(state)
        assert context == ""

    def test_build_dm_context_with_dm_summary_only(self) -> None:
        """Test DM context when DM has long-term summary but no buffer."""
        from agents import _build_dm_context
        from models import AgentMemory, create_initial_game_state

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="The party fought goblins and won.",
            short_term_buffer=[],
        )

        context = _build_dm_context(state)
        assert "## Story So Far" in context
        assert "The party fought goblins and won." in context

    def test_build_dm_context_with_buffer_only(self) -> None:
        """Test DM context when DM has buffer but no summary."""
        from agents import _build_dm_context
        from models import AgentMemory, create_initial_game_state

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="",
            short_term_buffer=["Turn 1: Combat begins", "Turn 2: Fighter attacks"],
        )

        context = _build_dm_context(state)
        assert "## Recent Events" in context
        assert "Combat begins" in context
        assert "Fighter attacks" in context

    def test_build_dm_context_includes_all_player_knowledge(self) -> None:
        """Test that DM context includes all player agent memories."""
        from agents import _build_dm_context
        from models import AgentMemory, create_initial_game_state

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory()
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fighter found a secret door"]
        )
        state["agent_memories"]["rogue"] = AgentMemory(
            short_term_buffer=["Rogue stole a gem"]
        )

        context = _build_dm_context(state)
        assert "## Player Knowledge" in context
        assert "fighter knows" in context
        assert "rogue knows" in context
        assert "secret door" in context
        assert "gem" in context

    def test_build_dm_context_respects_buffer_limit(self) -> None:
        """Test DM context respects the recent events limit."""
        from agents import DM_CONTEXT_RECENT_EVENTS_LIMIT, _build_dm_context
        from models import AgentMemory, create_initial_game_state

        state = create_initial_game_state()
        # Create buffer with more events than the limit
        many_events = [f"Event {i}" for i in range(DM_CONTEXT_RECENT_EVENTS_LIMIT + 5)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=many_events)

        context = _build_dm_context(state)
        # Should only include the last N events
        assert f"Event {DM_CONTEXT_RECENT_EVENTS_LIMIT + 4}" in context  # Last event
        assert "Event 0" not in context  # First event should be truncated


class TestBuildPCContextExpanded:
    """Expanded tests for _build_pc_context function."""

    def test_build_pc_context_empty_memory(self) -> None:
        """Test PC context with no memory for the agent."""
        from agents import _build_pc_context
        from models import create_initial_game_state

        state = create_initial_game_state()
        context = _build_pc_context(state, "fighter")
        assert context == ""

    def test_build_pc_context_with_summary_only(self) -> None:
        """Test PC context when agent has only long-term summary."""
        from agents import _build_pc_context
        from models import AgentMemory, create_initial_game_state

        state = create_initial_game_state()
        state["agent_memories"]["fighter"] = AgentMemory(
            long_term_summary="Fighter has battle experience.",
            short_term_buffer=[],
        )

        context = _build_pc_context(state, "fighter")
        assert "## What You Remember" in context
        assert "battle experience" in context
        assert "## Recent Events" not in context

    def test_build_pc_context_with_buffer_only(self) -> None:
        """Test PC context when agent has only short-term buffer."""
        from agents import _build_pc_context
        from models import AgentMemory, create_initial_game_state

        state = create_initial_game_state()
        state["agent_memories"]["fighter"] = AgentMemory(
            long_term_summary="",
            short_term_buffer=["You entered the tavern", "A stranger approaches"],
        )

        context = _build_pc_context(state, "fighter")
        assert "## Recent Events" in context
        assert "tavern" in context
        assert "stranger" in context
        assert "## What You Remember" not in context

    def test_build_pc_context_strict_isolation(self) -> None:
        """Test that PC context ONLY includes their own memory (strict isolation)."""
        from agents import _build_pc_context
        from models import AgentMemory, create_initial_game_state

        state = create_initial_game_state()
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fighter's secret action"]
        )
        state["agent_memories"]["rogue"] = AgentMemory(
            short_term_buffer=["Rogue's secret action"]
        )
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["DM's global knowledge"]
        )

        context = _build_pc_context(state, "fighter")
        assert "Fighter's secret action" in context
        # Should NOT include other agents' memories
        assert "Rogue's secret" not in context
        assert "DM's global" not in context

    def test_build_pc_context_respects_buffer_limit(self) -> None:
        """Test PC context respects the recent events limit."""
        from agents import PC_CONTEXT_RECENT_EVENTS_LIMIT, _build_pc_context
        from models import AgentMemory, create_initial_game_state

        state = create_initial_game_state()
        # Create buffer with more events than the limit
        many_events = [f"Event {i}" for i in range(PC_CONTEXT_RECENT_EVENTS_LIMIT + 5)]
        state["agent_memories"]["fighter"] = AgentMemory(short_term_buffer=many_events)

        context = _build_pc_context(state, "fighter")
        # Should only include the last N events
        assert f"Event {PC_CONTEXT_RECENT_EVENTS_LIMIT + 4}" in context
        assert "Event 0" not in context


class TestBuildPCSystemPromptExpanded:
    """Expanded tests for build_pc_system_prompt function."""

    def test_build_pc_system_prompt_uses_class_guidance(self) -> None:
        """Test that system prompt includes class-specific guidance."""
        from agents import build_pc_system_prompt
        from models import CharacterConfig

        config = CharacterConfig(
            name="TestFighter",
            character_class="Fighter",
            personality="Brave and bold",
            color="#FF0000",
        )

        prompt = build_pc_system_prompt(config)
        assert "TestFighter" in prompt
        assert "Fighter" in prompt
        # Should include Fighter-specific guidance (front line or martial)
        assert "front line" in prompt or "martial" in prompt.lower()

    def test_build_pc_system_prompt_unknown_class_uses_default(self) -> None:
        """Test that unknown class uses default guidance."""
        from agents import build_pc_system_prompt
        from models import CharacterConfig

        config = CharacterConfig(
            name="TestBarbarian",
            character_class="Barbarian",  # Not in CLASS_GUIDANCE
            personality="Rage incarnate",
            color="#FF0000",
        )

        prompt = build_pc_system_prompt(config)
        assert "TestBarbarian" in prompt
        assert "Barbarian" in prompt
        # Should use default guidance
        assert "class abilities" in prompt.lower()

    def test_build_pc_system_prompt_all_standard_classes(self) -> None:
        """Test system prompt generation for all standard classes."""
        from agents import CLASS_GUIDANCE, build_pc_system_prompt
        from models import CharacterConfig

        for char_class in CLASS_GUIDANCE:
            config = CharacterConfig(
                name=f"Test{char_class}",
                character_class=char_class,
                personality=f"A typical {char_class}",
                color="#FF0000",
            )

            prompt = build_pc_system_prompt(config)
            assert char_class in prompt
            assert f"Test{char_class}" in prompt


# =============================================================================
# Models.py Expanded Coverage
# =============================================================================


class TestGetSampleMessages:
    """Tests for _get_sample_messages helper function."""

    def test_get_sample_messages_empty_characters(self) -> None:
        """Test sample messages with empty characters dict."""
        from models import _get_sample_messages

        messages = _get_sample_messages({})
        # Should still have at least DM messages
        assert len(messages) >= 2
        assert any("[dm]" in msg for msg in messages)

    def test_get_sample_messages_includes_dm(self) -> None:
        """Test that sample messages always include DM narration."""
        from models import CharacterConfig, _get_sample_messages

        characters = {
            "test": CharacterConfig(
                name="Test",
                character_class="Fighter",
                personality="Test",
                color="#FF0000",
            )
        }
        messages = _get_sample_messages(characters)
        dm_messages = [m for m in messages if m.startswith("[dm]")]
        assert len(dm_messages) >= 2

    def test_get_sample_messages_uses_character_names(self) -> None:
        """Test that sample messages use actual character names."""
        from models import CharacterConfig, _get_sample_messages

        characters = {
            "heroname": CharacterConfig(
                name="HeroName",
                character_class="Fighter",
                personality="Heroic",
                color="#FF0000",
            )
        }
        messages = _get_sample_messages(characters)
        # Should have a message from the fighter
        fighter_msgs = [m for m in messages if "[heroname]" in m]
        assert len(fighter_msgs) >= 1
        assert "HeroName" in " ".join(fighter_msgs)


class TestParseLogEntryEdgeCases:
    """Additional edge case tests for parse_log_entry."""

    def test_parse_log_entry_uppercase_dm(self) -> None:
        """Test parsing entry with uppercase DM (case-sensitive)."""
        from models import parse_log_entry

        entry = "[DM] The story continues."
        msg = parse_log_entry(entry)
        assert msg.agent == "DM"  # Should preserve case
        assert msg.content == "The story continues."

    def test_parse_log_entry_numeric_agent(self) -> None:
        """Test parsing entry with numeric character in agent name."""
        from models import parse_log_entry

        entry = "[agent1] Test message"
        msg = parse_log_entry(entry)
        assert msg.agent == "agent1"
        assert msg.content == "Test message"

    def test_parse_log_entry_very_long_agent_name(self) -> None:
        """Test parsing entry with very long agent name."""
        from models import parse_log_entry

        long_name = "a" * 100
        entry = f"[{long_name}] Content"
        msg = parse_log_entry(entry)
        assert msg.agent == long_name
        assert msg.content == "Content"


class TestCharacterConfigWhitespace:
    """Tests for CharacterConfig whitespace handling."""

    def test_character_config_whitespace_name_rejected(self) -> None:
        """Test that whitespace-only name is rejected."""
        from pydantic import ValidationError

        from models import CharacterConfig

        with pytest.raises(ValidationError):
            CharacterConfig(
                name="   ",  # Whitespace only
                character_class="Fighter",
                personality="Test",
                color="#FF0000",
            )

    def test_character_config_preserves_name_with_internal_spaces(self) -> None:
        """Test that names with internal spaces are preserved."""
        from models import CharacterConfig

        config = CharacterConfig(
            name="Brother Aldric",
            character_class="Cleric",
            personality="Pious",
            color="#4A90A4",
        )
        assert config.name == "Brother Aldric"


# =============================================================================
# DM and PC Turn Functions Edge Cases
# =============================================================================


class TestDmTurnEdgeCases:
    """Tests for dm_turn edge cases with mocked LLM."""

    def test_dm_turn_updates_current_turn(self) -> None:
        """Test that dm_turn sets current_turn to 'dm'."""
        from langchain_core.messages import AIMessage

        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "fighter",  # Wrong value to verify update
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        with patch("agents.get_llm") as mock_get_llm:
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content="The DM speaks.")
            mock_get_llm.return_value = mock_model

            from agents import dm_turn

            result = dm_turn(state)

            assert result["current_turn"] == "dm"
            assert "[DM]: The DM speaks." in result["ground_truth_log"]

    def test_dm_turn_creates_dm_memory_if_missing(self) -> None:
        """Test that dm_turn creates DM memory if not present."""
        from langchain_core.messages import AIMessage

        from models import DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {},  # Empty - no DM memory
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        with patch("agents.get_llm") as mock_get_llm:
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content="Adventure begins!")
            mock_get_llm.return_value = mock_model

            from agents import dm_turn

            result = dm_turn(state)

            assert "dm" in result["agent_memories"]
            assert (
                "Adventure begins!"
                in result["agent_memories"]["dm"].short_term_buffer[0]
            )


class TestPcTurnEdgeCases:
    """Tests for pc_turn edge cases with mocked LLM."""

    def test_pc_turn_creates_memory_if_missing(self) -> None:
        """Test that pc_turn creates PC memory if not present."""
        from langchain_core.messages import AIMessage

        from models import CharacterConfig, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "fighter",
            "agent_memories": {},  # Empty - no fighter memory
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="Brave",
                    color="#C45C4A",
                    provider="gemini",
                    model="gemini-1.5-flash",
                )
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        with patch("agents.get_llm") as mock_get_llm:
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content="I attack!")
            mock_get_llm.return_value = mock_model

            from agents import pc_turn

            result = pc_turn(state, "fighter")

            assert "fighter" in result["agent_memories"]
            assert any(
                "Theron" in entry
                for entry in result["agent_memories"]["fighter"].short_term_buffer
            )


class TestDiceResultExpanded:
    """Expanded tests for DiceResult model."""

    def test_dice_result_str_positive_modifier(self) -> None:
        """Test DiceResult string representation with positive modifier."""
        from tools import DiceResult

        result = DiceResult(
            notation="1d20+5",
            rolls={"1d20": [15]},
            modifier=5,
            total=20,
        )
        output = str(result)
        assert "+ 5" in output
        assert "= 20" in output

    def test_dice_result_str_negative_modifier(self) -> None:
        """Test DiceResult string representation with negative modifier."""
        from tools import DiceResult

        result = DiceResult(
            notation="1d20-2",
            rolls={"1d20": [10]},
            modifier=-2,
            total=8,
        )
        output = str(result)
        assert "- 2" in output
        assert "= 8" in output

    def test_dice_result_str_no_modifier(self) -> None:
        """Test DiceResult string representation with no modifier."""
        from tools import DiceResult

        result = DiceResult(
            notation="2d6",
            rolls={"2d6": [3, 4]},
            modifier=0,
            total=7,
        )
        output = str(result)
        assert "+ " not in output
        assert "- " not in output
        assert "= 7" in output
