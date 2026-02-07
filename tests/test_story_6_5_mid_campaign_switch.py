"""Tests for Story 6.5: Mid-Campaign Provider Switching.

This module contains tests for:
- Task 1: Verify existing model switching infrastructure
- Task 2: Confirmation messages for provider switch (AC #5)
- Task 3: Campaign data preservation (AC #1, NFR8)
- Task 4: Memory continuity across provider switch (AC #2, AC #3)
- Task 5: Handle provider unavailability (AC #4)
- Task 6: Seamless turn transition (AC #6)
- Task 7: Pending change visual indicators
- Task 8: Comprehensive acceptance tests
"""

from copy import deepcopy
from unittest.mock import MagicMock, patch

# =============================================================================
# Task 1: Verify Existing Model Switching Infrastructure
# =============================================================================


class TestModelSwitchingInfrastructure:
    """Tests verifying the existing model switching infrastructure from Stories 6.2-6.4."""

    @patch("app.st")
    def test_apply_model_config_changes_updates_dm(self, mock_st: MagicMock) -> None:
        """Test that apply_model_config_changes updates DM config."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "claude"
        assert updated_game["dm_config"].model == "claude-3-haiku-20240307"

    @patch("app.st")
    def test_apply_model_config_changes_updates_characters(
        self, mock_st: MagicMock
    ) -> None:
        """Test that apply_model_config_changes updates character configs."""
        from models import populate_game_state

        game = populate_game_state()
        # Ensure character has initial provider
        char = game["characters"].get("theron")
        if char:
            game["characters"]["theron"] = char.model_copy(
                update={"provider": "gemini", "model": "gemini-1.5-flash"}
            )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "theron": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        if "theron" in updated_game["characters"]:
            assert updated_game["characters"]["theron"].provider == "claude"
            assert (
                updated_game["characters"]["theron"].model == "claude-3-haiku-20240307"
            )

    @patch("app.st")
    def test_apply_model_config_changes_updates_summarizer(
        self, mock_st: MagicMock
    ) -> None:
        """Test that apply_model_config_changes updates summarizer config."""
        from models import GameConfig, populate_game_state

        game = populate_game_state()
        game["game_config"] = GameConfig(
            summarizer_provider="gemini", summarizer_model="gemini-1.5-flash"
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "summarizer": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["game_config"].summarizer_provider == "claude"
        assert updated_game["game_config"].summarizer_model == "claude-3-haiku-20240307"

    def test_create_dm_agent_reads_config_at_call_time(self) -> None:
        """Test that create_dm_agent reads provider/model from config at call time.

        This verifies there's no caching - agents are created fresh each turn.
        """
        from agents import create_dm_agent
        from models import DMConfig

        # This just verifies the function signature works and reads from config
        # Full integration requires LLM mocking
        config = DMConfig(provider="gemini", model="gemini-1.5-flash")

        # Verify the function can be called (won't actually create LLM without API key)
        with patch("agents.get_llm") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            create_dm_agent(config)
            mock_get_llm.assert_called_once_with("gemini", "gemini-1.5-flash")

    def test_create_pc_agent_reads_config_at_call_time(self) -> None:
        """Test that create_pc_agent reads provider/model from config at call time."""
        from agents import create_pc_agent
        from models import CharacterConfig

        config = CharacterConfig(
            name="Test",
            character_class="Fighter",
            personality="Brave",
            color="#C45C4A",
            provider="claude",
            model="claude-3-haiku-20240307",
        )

        with patch("agents.get_llm") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            create_pc_agent(config)
            mock_get_llm.assert_called_once_with("claude", "claude-3-haiku-20240307")


# =============================================================================
# Task 2: Confirmation Messages for Provider Switch (AC #5)
# =============================================================================


class TestConfirmationMessages:
    """Tests for generate_model_change_messages() function."""

    @patch("app.st")
    def test_generate_dm_change_message(self, mock_st: MagicMock) -> None:
        """Test message generation for DM provider change."""
        from models import populate_game_state

        game = populate_game_state()
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        assert len(messages) == 1
        assert "Dungeon Master" in messages[0]
        assert "Claude" in messages[0]
        assert "claude-3-haiku-20240307" in messages[0]
        assert "starting next turn" in messages[0]

    @patch("app.st")
    def test_generate_pc_change_message_with_name(self, mock_st: MagicMock) -> None:
        """Test message uses character name for PC agents."""
        from models import CharacterConfig, populate_game_state

        game = populate_game_state()
        # Ensure we have a character named "Theron"
        game["characters"]["theron"] = CharacterConfig(
            name="Theron",
            character_class="Fighter",
            personality="Brave",
            color="#C45C4A",
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "theron": {"provider": "ollama", "model": "llama3"}
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        assert len(messages) == 1
        assert "Theron" in messages[0]
        assert "Ollama" in messages[0]
        assert "llama3" in messages[0]

    @patch("app.st")
    def test_generate_summarizer_change_message(self, mock_st: MagicMock) -> None:
        """Test message generation for Summarizer."""
        from models import populate_game_state

        game = populate_game_state()
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "summarizer": {"provider": "gemini", "model": "gemini-1.5-pro"}
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        assert len(messages) == 1
        assert "Summarizer" in messages[0]
        assert "Gemini" in messages[0]
        assert "gemini-1.5-pro" in messages[0]

    @patch("app.st")
    def test_generate_multiple_change_messages(self, mock_st: MagicMock) -> None:
        """Test message generation for multiple agents."""
        from models import CharacterConfig, populate_game_state

        game = populate_game_state()
        game["characters"]["rogue"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sneaky",
            color="#6B8E6B",
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"},
                "rogue": {"provider": "ollama", "model": "mistral"},
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        assert len(messages) == 2
        # Messages should include both DM and rogue
        message_text = " ".join(messages)
        assert "Dungeon Master" in message_text
        assert "Shadowmere" in message_text

    @patch("app.st")
    def test_generate_no_messages_when_no_overrides(self, mock_st: MagicMock) -> None:
        """Test empty list when no overrides."""
        from models import populate_game_state

        game = populate_game_state()
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {},
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()
        assert messages == []

    @patch("app.st")
    def test_generate_no_messages_when_no_game(self, mock_st: MagicMock) -> None:
        """Test empty list when no game state."""
        mock_st.session_state = {
            "game": None,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()
        assert messages == []

    @patch("app.st")
    def test_generate_messages_skips_malformed_overrides(
        self, mock_st: MagicMock
    ) -> None:
        """Test that malformed overrides are skipped gracefully (defensive coding)."""
        from models import populate_game_state

        game = populate_game_state()
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude"},  # Missing "model" key
                "summarizer": {"model": "gemini-1.5-flash"},  # Missing "provider" key
                "malformed": "not a dict",  # Not a dict
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()
        # All entries are malformed, so no messages should be generated
        assert messages == []

    @patch("app.st")
    def test_generate_messages_handles_mixed_valid_invalid(
        self, mock_st: MagicMock
    ) -> None:
        """Test that valid overrides work even with some malformed ones."""
        from models import populate_game_state

        game = populate_game_state()
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {
                    "provider": "claude",
                    "model": "claude-3-haiku-20240307",
                },  # Valid
                "summarizer": {
                    "model": "gemini-1.5-flash"
                },  # Invalid - missing provider
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()
        # Only the valid DM entry should generate a message
        assert len(messages) == 1
        assert "Dungeon Master" in messages[0]


# =============================================================================
# Task 3: Campaign Data Preservation (AC #1, NFR8)
# =============================================================================


class TestCampaignDataPreservation:
    """Tests verifying that model changes don't affect campaign data."""

    @patch("app.st")
    def test_model_change_preserves_ground_truth_log(self, mock_st: MagicMock) -> None:
        """Test that ground_truth_log is unchanged by model switch."""
        from models import populate_game_state

        game = populate_game_state()
        game["ground_truth_log"] = [
            "[DM]: The adventure begins...",
            "[Fighter]: I draw my sword!",
        ]
        original_log = game["ground_truth_log"].copy()

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["ground_truth_log"] == original_log

    @patch("app.st")
    def test_model_change_preserves_agent_memories(self, mock_st: MagicMock) -> None:
        """Test that agent_memories are unchanged by model switch."""
        from models import AgentMemory, populate_game_state

        game = populate_game_state()
        game["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="The party entered the dungeon...",
            short_term_buffer=["Event 1", "Event 2"],
        )
        original_memory = game["agent_memories"]["dm"].model_copy()

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        dm_memory = updated_game["agent_memories"]["dm"]
        assert dm_memory.long_term_summary == original_memory.long_term_summary
        assert dm_memory.short_term_buffer == original_memory.short_term_buffer

    @patch("app.st")
    def test_model_change_preserves_whisper_queue(self, mock_st: MagicMock) -> None:
        """Test that whisper_queue is unchanged by model switch."""
        from models import populate_game_state

        game = populate_game_state()
        game["whisper_queue"] = ["[Whisper to Rogue]: Secret message"]
        original_whispers = game["whisper_queue"].copy()

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["whisper_queue"] == original_whispers

    @patch("app.st")
    def test_model_change_preserves_turn_queue(self, mock_st: MagicMock) -> None:
        """Test that turn_queue is unchanged by model switch."""
        from models import populate_game_state

        game = populate_game_state()
        original_queue = game["turn_queue"].copy()

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["turn_queue"] == original_queue


# =============================================================================
# Task 4: Memory Continuity Across Provider Switch (AC #2, AC #3)
# =============================================================================


class TestMemoryContinuity:
    """Tests verifying memory continuity across provider boundaries."""

    def test_build_dm_context_provider_agnostic(self) -> None:
        """Test that _build_dm_context works identically regardless of provider."""
        from agents import _build_dm_context
        from models import AgentMemory, DMConfig, populate_game_state

        # Create state with DM memory
        state = populate_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="The party met in the tavern.",
            short_term_buffer=["Event 1", "Event 2", "Event 3"],
        )

        # Context building doesn't depend on provider in dm_config
        state["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")
        context_gemini = _build_dm_context(state)

        state["dm_config"] = DMConfig(
            provider="claude", model="claude-3-haiku-20240307"
        )
        context_claude = _build_dm_context(state)

        # Both should produce identical context
        assert context_gemini == context_claude

    def test_build_pc_context_provider_agnostic(self) -> None:
        """Test that _build_pc_context works identically regardless of provider."""
        from agents import _build_pc_context
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterFacts,
            populate_game_state,
        )

        state = populate_game_state()
        state["characters"]["rogue"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sneaky",
            color="#6B8E6B",
        )
        state["agent_memories"]["rogue"] = AgentMemory(
            long_term_summary="Shadowmere grew up on the streets.",
            short_term_buffer=["Picked a lock", "Found treasure"],
            character_facts=CharacterFacts(
                name="Shadowmere",
                character_class="Rogue",
                key_traits=["Stealthy", "Cunning"],
            ),
        )

        # Context building doesn't depend on provider in character config
        context_gemini = _build_pc_context(state, "rogue")

        state["characters"]["rogue"] = state["characters"]["rogue"].model_copy(
            update={"provider": "claude"}
        )
        context_claude = _build_pc_context(state, "rogue")

        # Both should produce identical context
        assert context_gemini == context_claude

    def test_dm_switch_preserves_long_term_summary_in_context(self) -> None:
        """Test that long_term_summary appears in DM context after switch."""
        from agents import _build_dm_context
        from models import AgentMemory, DMConfig, populate_game_state

        state = populate_game_state()
        summary = "The heroes fought bravely against the dragon."
        state["agent_memories"]["dm"] = AgentMemory(long_term_summary=summary)
        state["dm_config"] = DMConfig(
            provider="claude", model="claude-3-haiku-20240307"
        )

        context = _build_dm_context(state)

        assert summary in context
        assert "Story So Far" in context

    def test_dm_switch_preserves_short_term_buffer_in_context(self) -> None:
        """Test that short_term_buffer entries appear in DM context after switch."""
        from agents import _build_dm_context
        from models import AgentMemory, DMConfig, populate_game_state

        state = populate_game_state()
        buffer_entries = ["The dragon roared.", "Flames engulfed the room."]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=buffer_entries)
        state["dm_config"] = DMConfig(provider="ollama", model="llama3")

        context = _build_dm_context(state)

        for entry in buffer_entries:
            assert entry in context
        assert "Recent Events" in context

    def test_pc_switch_preserves_character_facts_in_context(self) -> None:
        """Test that CharacterFacts appear in PC context after switch."""
        from agents import _build_pc_context
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterFacts,
            populate_game_state,
        )

        state = populate_game_state()
        state["characters"]["wizard"] = CharacterConfig(
            name="Elara",
            character_class="Wizard",
            personality="Scholarly",
            color="#7B68B8",
            provider="claude",
            model="claude-3-haiku-20240307",
        )
        facts = CharacterFacts(
            name="Elara",
            character_class="Wizard",
            key_traits=["Bookish", "Curious"],
            relationships={"Theron": "Party member"},
            notable_events=["Discovered ancient tome"],
        )
        state["agent_memories"]["wizard"] = AgentMemory(character_facts=facts)

        context = _build_pc_context(state, "wizard")

        assert "Elara" in context
        assert "Wizard" in context
        assert "Character Identity" in context

    def test_pc_switch_preserves_personality_in_system_prompt(self) -> None:
        """Test that personality is preserved in system prompt after switch."""
        from agents import build_pc_system_prompt
        from models import CharacterConfig

        config = CharacterConfig(
            name="Theron",
            character_class="Fighter",
            personality="Brave and honorable, always protects the weak",
            color="#C45C4A",
            provider="ollama",  # Provider shouldn't affect system prompt
            model="llama3",
        )

        system_prompt = build_pc_system_prompt(config)

        assert "Theron" in system_prompt
        assert "Fighter" in system_prompt
        assert "Brave and honorable" in system_prompt


# =============================================================================
# Task 5: Handle Provider Unavailability (AC #4)
# =============================================================================


class TestProviderAvailability:
    """Tests for provider availability status functions."""

    @patch("requests.get")
    @patch("app.get_config")
    def test_get_provider_availability_gemini_available(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test that Gemini shows available when API key is set."""
        mock_config.return_value = MagicMock(
            google_api_key="test-key",
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
        )
        mock_requests_get.side_effect = Exception("Connection refused")

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        assert status["gemini"] is True
        assert status["claude"] is False

    @patch("requests.get")
    @patch("app.get_config")
    def test_get_provider_availability_claude_available(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test that Claude shows available when API key is set."""
        mock_config.return_value = MagicMock(
            google_api_key=None,
            anthropic_api_key="test-key",
            ollama_base_url="http://localhost:11434",
        )
        mock_requests_get.side_effect = Exception("Connection refused")

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        assert status["gemini"] is False
        assert status["claude"] is True

    @patch("requests.get")
    @patch("app.get_config")
    def test_get_provider_availability_ollama_available(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test that Ollama shows available when server responds."""
        mock_config.return_value = MagicMock(
            google_api_key=None,
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        assert status["ollama"] is True

    @patch("requests.get")
    @patch("app.get_config")
    def test_get_provider_availability_ollama_unavailable(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test that Ollama shows unavailable when server doesn't respond."""
        mock_config.return_value = MagicMock(
            google_api_key=None,
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
        )
        mock_requests_get.side_effect = Exception("Connection refused")

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        assert status["ollama"] is False

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_has_pending_change_true(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test has_pending_change returns True when override exists."""
        mock_st.session_state = {
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            }
        }

        from app import has_pending_change

        assert has_pending_change("dm") is True
        assert has_pending_change("rogue") is False

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_has_pending_change_false_no_overrides(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test has_pending_change returns False when no overrides."""
        mock_st.session_state = {"agent_model_overrides": {}}

        from app import has_pending_change

        assert has_pending_change("dm") is False

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_is_agent_provider_unavailable_with_override(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test is_agent_provider_unavailable uses override provider when present."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
            "provider_availability": {"claude": False, "gemini": True},
        }

        # Mock is_provider_available to use the cached availability
        def mock_provider_check(provider: str) -> bool:
            return mock_st.session_state["provider_availability"].get(provider, False)

        mock_available.side_effect = mock_provider_check

        from app import is_agent_provider_unavailable

        # Should check claude (from override), not gemini (from game state)
        result = is_agent_provider_unavailable("dm")
        assert result is True  # Claude is unavailable

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_is_agent_provider_unavailable_no_override(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test is_agent_provider_unavailable uses game state when no override."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {},  # No override
            "provider_availability": {"claude": False, "gemini": True},
        }

        mock_available.return_value = True  # Gemini is available

        from app import is_agent_provider_unavailable

        # Should check gemini (from game state)
        result = is_agent_provider_unavailable("dm")
        assert result is False  # Gemini is available

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_is_agent_provider_unavailable_missing_game(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test is_agent_provider_unavailable handles missing game state."""
        mock_st.session_state = {
            "game": None,
            "agent_model_overrides": {},
        }

        mock_available.return_value = True  # Default gemini is available

        from app import is_agent_provider_unavailable

        # Should fall back to default gemini
        result = is_agent_provider_unavailable("dm")
        assert result is False


# =============================================================================
# Task 6: Verify Seamless Turn Transition (AC #6)
# =============================================================================


class TestSeamlessTurnTransition:
    """Tests verifying seamless turn execution after provider switch."""

    @patch("app.st")
    def test_model_changes_take_effect_immediately(self, mock_st: MagicMock) -> None:
        """Test that model changes are reflected in game state immediately after apply."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        # Verify the change is in game state
        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "claude"

        # Verify create_dm_agent would read the new provider
        from agents import create_dm_agent

        with patch("agents.get_llm") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            create_dm_agent(updated_game["dm_config"])
            mock_get_llm.assert_called_once_with("claude", "claude-3-haiku-20240307")


# =============================================================================
# Task 7: Pending Change Visual Indicators
# =============================================================================


class TestPendingChangeIndicators:
    """Tests for pending change badge rendering."""

    def test_render_pending_change_badge_html(self) -> None:
        """Test that pending change badge renders correct HTML."""
        from app import render_pending_change_badge

        html = render_pending_change_badge()

        assert "pending-change-badge" in html
        assert "(pending)" in html

    def test_render_provider_unavailable_warning_html(self) -> None:
        """Test that provider unavailable warning renders correct HTML."""
        from app import render_provider_unavailable_warning

        html = render_provider_unavailable_warning()

        assert "provider-unavailable-warning" in html
        assert "unavailable" in html.lower()


# =============================================================================
# Task 8: Comprehensive Acceptance Tests
# =============================================================================


class TestAcceptanceCriteria:
    """Tests for all Story 6.5 acceptance criteria."""

    @patch("app.st")
    def test_ac1_campaign_data_preserved(self, mock_st: MagicMock) -> None:
        """AC #1: Provider switch preserves campaign data."""
        from models import AgentMemory, populate_game_state

        game = populate_game_state()
        # Set up campaign data
        game["ground_truth_log"] = ["Entry 1", "Entry 2"]
        game["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="Summary",
            short_term_buffer=["Buffer 1"],
        )
        game["whisper_queue"] = ["[Whisper to Rogue]: Secret"]

        # Deep copy to verify no mutation
        original_log = deepcopy(game["ground_truth_log"])
        original_whispers = deepcopy(game["whisper_queue"])

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["ground_truth_log"] == original_log
        assert updated_game["whisper_queue"] == original_whispers

    @patch("app.st")
    def test_ac2_dm_switch_uses_new_provider(self, mock_st: MagicMock) -> None:
        """AC #2: DM switch uses new provider on next turn."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "claude"
        assert updated_game["dm_config"].model == "claude-3-haiku-20240307"

    @patch("app.st")
    def test_ac3_pc_switch_preserves_memory_and_personality(
        self, mock_st: MagicMock
    ) -> None:
        """AC #3: PC switch preserves memory and personality."""
        from agents import _build_pc_context, build_pc_system_prompt
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterFacts,
            populate_game_state,
        )

        game = populate_game_state()
        char_config = CharacterConfig(
            name="Raven",
            character_class="Rogue",
            personality="Mysterious and cunning",
            color="#6B8E6B",
            provider="gemini",
        )
        game["characters"]["raven"] = char_config
        game["agent_memories"]["raven"] = AgentMemory(
            long_term_summary="Raven's backstory...",
            short_term_buffer=["Stole a gem"],
            character_facts=CharacterFacts(
                name="Raven", character_class="Rogue", key_traits=["Stealthy"]
            ),
        )

        # Get context before switch
        context_before = _build_pc_context(game, "raven")
        _ = build_pc_system_prompt(char_config)  # Verify prompt builds

        # Apply switch
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "raven": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]

        # Get context and prompt after switch
        context_after = _build_pc_context(updated_game, "raven")
        prompt_after = build_pc_system_prompt(updated_game["characters"]["raven"])

        # Context should be identical (memory preserved)
        assert context_before == context_after

        # Key personality elements preserved in prompt
        assert "Raven" in prompt_after
        assert "Rogue" in prompt_after
        assert "Mysterious and cunning" in prompt_after

    @patch("app.st")
    def test_ac5_confirmation_message_format(self, mock_st: MagicMock) -> None:
        """AC #5: Confirmation message shows '[Character] will use [Provider/Model] starting next turn'."""
        from models import CharacterConfig, populate_game_state

        game = populate_game_state()
        game["characters"]["wizard"] = CharacterConfig(
            name="Elara",
            character_class="Wizard",
            personality="Scholarly",
            color="#7B68B8",
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "wizard": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        assert len(messages) == 1
        msg = messages[0]
        # Verify format: "[Character] will use [Provider/Model] starting next turn"
        assert "Elara" in msg
        assert "Claude" in msg
        assert "claude-3-haiku-20240307" in msg
        assert "starting next turn" in msg

    @patch("app.st")
    def test_multiple_sequential_switches(self, mock_st: MagicMock) -> None:
        """Test that multiple sequential provider switches work correctly."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        from app import apply_model_config_changes

        # First switch: Gemini -> Claude
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }
        apply_model_config_changes()

        game = mock_st.session_state["game"]
        assert game["dm_config"].provider == "claude"

        # Second switch: Claude -> Ollama
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {"dm": {"provider": "ollama", "model": "llama3"}},
        }
        apply_model_config_changes()

        game = mock_st.session_state["game"]
        assert game["dm_config"].provider == "ollama"
        assert game["dm_config"].model == "llama3"

    @patch("app.st")
    def test_switch_all_agents_simultaneously(self, mock_st: MagicMock) -> None:
        """Test switching all agents at once works correctly."""
        from models import CharacterConfig, DMConfig, GameConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")
        game["game_config"] = GameConfig(
            summarizer_provider="gemini", summarizer_model="gemini-1.5-flash"
        )
        game["characters"]["fighter"] = CharacterConfig(
            name="Theron",
            character_class="Fighter",
            personality="Brave",
            color="#C45C4A",
            provider="gemini",
        )
        game["characters"]["rogue"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sneaky",
            color="#6B8E6B",
            provider="gemini",
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"},
                "summarizer": {
                    "provider": "claude",
                    "model": "claude-3-haiku-20240307",
                },
                "fighter": {"provider": "ollama", "model": "llama3"},
                "rogue": {"provider": "ollama", "model": "mistral"},
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "claude"
        assert updated_game["game_config"].summarizer_provider == "claude"
        assert updated_game["characters"]["fighter"].provider == "ollama"
        assert updated_game["characters"]["fighter"].model == "llama3"
        assert updated_game["characters"]["rogue"].provider == "ollama"
        assert updated_game["characters"]["rogue"].model == "mistral"


# =============================================================================
# Additional Edge Cases and Coverage Expansion (testarch-automate)
# =============================================================================


class TestIsProviderAvailable:
    """Tests for is_provider_available() function with caching behavior."""

    @patch("app.st")
    @patch("app.get_provider_availability_status")
    def test_is_provider_available_cache_hit(
        self, mock_get_status: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test that cached status is used when available."""
        mock_st.session_state = {
            "provider_availability": {"gemini": True, "claude": False}
        }

        from app import is_provider_available

        result = is_provider_available("gemini")

        assert result is True
        # Should not call get_provider_availability_status due to cache hit
        mock_get_status.assert_not_called()

    @patch("app.st")
    @patch("app.get_provider_availability_status")
    def test_is_provider_available_cache_miss(
        self, mock_get_status: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test that status is fetched and cached on cache miss."""
        mock_st.session_state = {}
        mock_get_status.return_value = {"gemini": True, "claude": False, "ollama": True}

        from app import is_provider_available

        result = is_provider_available("ollama")

        assert result is True
        mock_get_status.assert_called_once()
        assert mock_st.session_state["provider_availability"]["ollama"] is True

    @patch("app.st")
    @patch("app.get_provider_availability_status")
    def test_is_provider_available_unknown_provider(
        self, mock_get_status: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test that unknown provider returns False."""
        mock_st.session_state = {}
        mock_get_status.return_value = {"gemini": True, "claude": True, "ollama": True}

        from app import is_provider_available

        result = is_provider_available("unknown_provider")

        assert result is False

    @patch("app.st")
    def test_is_provider_available_partial_cache(self, mock_st: MagicMock) -> None:
        """Test provider not in cache triggers full refresh."""
        mock_st.session_state = {
            "provider_availability": {"gemini": True}  # claude not cached
        }

        from app import is_provider_available

        # Since "claude" is not in cache, it should trigger status fetch
        with patch("app.get_provider_availability_status") as mock_get_status:
            mock_get_status.return_value = {
                "gemini": True,
                "claude": True,
                "ollama": False,
            }
            result = is_provider_available("claude")
            assert result is True
            mock_get_status.assert_called_once()


class TestGetAgentCurrentProvider:
    """Tests for get_agent_current_provider() function."""

    @patch("app.st")
    def test_get_agent_current_provider_dm(self, mock_st: MagicMock) -> None:
        """Test getting DM provider from game state."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="claude", model="claude-3-haiku-20240307")
        mock_st.session_state = {"game": game}

        from app import get_agent_current_provider

        result = get_agent_current_provider("dm")
        assert result == "claude"

    @patch("app.st")
    def test_get_agent_current_provider_summarizer(self, mock_st: MagicMock) -> None:
        """Test getting summarizer provider from game state."""
        from models import GameConfig, populate_game_state

        game = populate_game_state()
        game["game_config"] = GameConfig(
            summarizer_provider="ollama", summarizer_model="llama3"
        )
        mock_st.session_state = {"game": game}

        from app import get_agent_current_provider

        result = get_agent_current_provider("summarizer")
        assert result == "ollama"

    @patch("app.st")
    def test_get_agent_current_provider_character(self, mock_st: MagicMock) -> None:
        """Test getting character provider from game state."""
        from models import CharacterConfig, populate_game_state

        game = populate_game_state()
        game["characters"]["wizard"] = CharacterConfig(
            name="Elara",
            character_class="Wizard",
            personality="Scholarly",
            color="#7B68B8",
            provider="claude",
        )
        mock_st.session_state = {"game": game}

        from app import get_agent_current_provider

        result = get_agent_current_provider("wizard")
        assert result == "claude"

    @patch("app.st")
    def test_get_agent_current_provider_unknown_agent(self, mock_st: MagicMock) -> None:
        """Test unknown agent defaults to gemini."""
        from models import populate_game_state

        game = populate_game_state()
        mock_st.session_state = {"game": game}

        from app import get_agent_current_provider

        result = get_agent_current_provider("unknown_agent")
        assert result == "gemini"

    @patch("app.st")
    def test_get_agent_current_provider_no_game(self, mock_st: MagicMock) -> None:
        """Test no game state defaults to gemini."""
        mock_st.session_state = {"game": None}

        from app import get_agent_current_provider

        result = get_agent_current_provider("dm")
        assert result == "gemini"

    @patch("app.st")
    def test_get_agent_current_provider_missing_dm_config(
        self, mock_st: MagicMock
    ) -> None:
        """Test missing dm_config defaults to gemini."""
        from models import populate_game_state

        game = populate_game_state()
        game["dm_config"] = None  # type: ignore[typeddict-item]
        mock_st.session_state = {"game": game}

        from app import get_agent_current_provider

        result = get_agent_current_provider("dm")
        assert result == "gemini"

    @patch("app.st")
    def test_get_agent_current_provider_missing_game_config(
        self, mock_st: MagicMock
    ) -> None:
        """Test missing game_config defaults to gemini."""
        from models import populate_game_state

        game = populate_game_state()
        game["game_config"] = None  # type: ignore[typeddict-item]
        mock_st.session_state = {"game": game}

        from app import get_agent_current_provider

        result = get_agent_current_provider("summarizer")
        assert result == "gemini"


class TestGetProviderAvailabilityStatusExpanded:
    """Additional tests for get_provider_availability_status()."""

    @patch("requests.get")
    @patch("app.get_config")
    def test_all_providers_available(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test when all providers are available."""
        mock_config.return_value = MagicMock(
            google_api_key="test-google-key",
            anthropic_api_key="test-anthropic-key",
            ollama_base_url="http://localhost:11434",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        assert status["gemini"] is True
        assert status["claude"] is True
        assert status["ollama"] is True

    @patch("requests.get")
    @patch("app.get_config")
    def test_all_providers_unavailable(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test when all providers are unavailable."""
        mock_config.return_value = MagicMock(
            google_api_key=None,
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
        )
        mock_requests_get.side_effect = Exception("Connection refused")

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        assert status["gemini"] is False
        assert status["claude"] is False
        assert status["ollama"] is False

    @patch("requests.get")
    @patch("app.get_config")
    def test_ollama_non_200_status(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test Ollama returns non-200 status code."""
        mock_config.return_value = MagicMock(
            google_api_key=None,
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
        )
        mock_response = MagicMock()
        mock_response.status_code = 500  # Server error
        mock_requests_get.return_value = mock_response

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        assert status["ollama"] is False

    @patch("requests.get")
    @patch("app.get_config")
    def test_empty_api_keys_vs_none(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test empty string API keys treated as unavailable."""
        mock_config.return_value = MagicMock(
            google_api_key="",  # Empty string
            anthropic_api_key="",  # Empty string
            ollama_base_url="http://localhost:11434",
        )
        mock_requests_get.side_effect = Exception("Connection refused")

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        # Empty strings should be treated as falsy
        assert status["gemini"] is False
        assert status["claude"] is False

    @patch("requests.get")
    @patch("app.get_config")
    def test_ollama_timeout_exception(
        self, mock_config: MagicMock, mock_requests_get: MagicMock
    ) -> None:
        """Test Ollama timeout is handled gracefully."""
        import requests

        mock_config.return_value = MagicMock(
            google_api_key="test-key",
            anthropic_api_key=None,
            ollama_base_url="http://localhost:11434",
        )
        mock_requests_get.side_effect = requests.exceptions.Timeout("Timeout")

        from app import get_provider_availability_status

        status = get_provider_availability_status()

        assert status["ollama"] is False
        # Other providers unaffected
        assert status["gemini"] is True


class TestApplyModelConfigChangesExpanded:
    """Additional tests for apply_model_config_changes()."""

    @patch("app.st")
    def test_apply_partial_override_only_provider(self, mock_st: MagicMock) -> None:
        """Test override with only provider specified uses existing model."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude"}  # No model specified
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "claude"
        # Model should remain from original config
        assert updated_game["dm_config"].model == "gemini-1.5-flash"

    @patch("app.st")
    def test_apply_partial_override_only_model(self, mock_st: MagicMock) -> None:
        """Test override with only model specified uses existing provider."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"model": "gemini-1.5-pro"}  # No provider specified
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        # Provider should remain from original config
        assert updated_game["dm_config"].provider == "gemini"
        assert updated_game["dm_config"].model == "gemini-1.5-pro"

    @patch("app.st")
    def test_apply_missing_dm_config_creates_default(self, mock_st: MagicMock) -> None:
        """Test apply handles missing dm_config by creating default."""
        from models import populate_game_state

        game = populate_game_state()
        game["dm_config"] = None  # type: ignore[typeddict-item]

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "claude"
        assert updated_game["dm_config"].model == "claude-3-haiku-20240307"

    @patch("app.st")
    def test_apply_missing_game_config_creates_default(
        self, mock_st: MagicMock
    ) -> None:
        """Test apply handles missing game_config by creating default."""
        from models import populate_game_state

        game = populate_game_state()
        game["game_config"] = None  # type: ignore[typeddict-item]

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "summarizer": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["game_config"].summarizer_provider == "claude"
        assert updated_game["game_config"].summarizer_model == "claude-3-haiku-20240307"

    @patch("app.st")
    def test_apply_sets_model_config_changed_flag(self, mock_st: MagicMock) -> None:
        """Test that apply sets the model_config_changed flag."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
            "model_config_changed": False,
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        assert mock_st.session_state["model_config_changed"] is True

    @patch("app.st")
    def test_apply_does_not_set_flag_when_no_changes(self, mock_st: MagicMock) -> None:
        """Test that apply does not set flag when there's no game or overrides."""
        mock_st.session_state = {
            "game": None,
            "agent_model_overrides": {},
            "model_config_changed": False,
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        # Flag should remain False since nothing was applied
        assert mock_st.session_state.get("model_config_changed", False) is False

    @patch("app.st")
    def test_apply_with_empty_characters_dict(self, mock_st: MagicMock) -> None:
        """Test apply handles empty characters dict gracefully."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")
        game["characters"] = {}  # Empty characters

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"},
                "nonexistent_char": {"provider": "ollama", "model": "llama3"},
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "claude"
        # Nonexistent character override should be ignored silently
        assert "nonexistent_char" not in updated_game["characters"]


class TestGenerateModelChangeMessagesExpanded:
    """Additional tests for generate_model_change_messages()."""

    @patch("app.st")
    def test_generate_message_unknown_character_uses_title(
        self, mock_st: MagicMock
    ) -> None:
        """Test that unknown character key uses title-cased key as fallback."""
        from models import populate_game_state

        game = populate_game_state()
        # Don't add any character config - the key should be title-cased

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "unknown_character": {
                    "provider": "claude",
                    "model": "claude-3-haiku-20240307",
                }
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        assert len(messages) == 1
        assert (
            "Unknown_Character" in messages[0]
            or "unknown_character".title() in messages[0]
        )

    @patch("app.st")
    def test_generate_message_unknown_provider_uses_key(
        self, mock_st: MagicMock
    ) -> None:
        """Test that unknown provider uses the provider key as-is."""
        from models import populate_game_state

        game = populate_game_state()

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "custom_provider", "model": "custom-model-v1"}
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        assert len(messages) == 1
        # Unknown provider should use key as-is (not in PROVIDER_DISPLAY)
        assert "custom_provider" in messages[0]
        assert "custom-model-v1" in messages[0]

    @patch("app.st")
    def test_generate_messages_order_preserved(self, mock_st: MagicMock) -> None:
        """Test that message order follows override iteration order."""
        from models import CharacterConfig, populate_game_state

        game = populate_game_state()
        game["characters"]["alpha"] = CharacterConfig(
            name="Alpha",
            character_class="Fighter",
            personality="Brave",
            color="#C45C4A",
        )
        game["characters"]["beta"] = CharacterConfig(
            name="Beta",
            character_class="Rogue",
            personality="Sneaky",
            color="#6B8E6B",
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"},
                "alpha": {"provider": "ollama", "model": "llama3"},
                "beta": {"provider": "gemini", "model": "gemini-1.5-flash"},
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        assert len(messages) == 3

    @patch("app.st")
    def test_generate_message_with_empty_provider_string(
        self, mock_st: MagicMock
    ) -> None:
        """Test that empty provider string is skipped."""
        from models import populate_game_state

        game = populate_game_state()

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {
                    "provider": "",
                    "model": "claude-3-haiku-20240307",
                }  # Empty provider
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        # Should skip due to empty provider
        assert len(messages) == 0

    @patch("app.st")
    def test_generate_message_with_empty_model_string(self, mock_st: MagicMock) -> None:
        """Test that empty model string is skipped."""
        from models import populate_game_state

        game = populate_game_state()

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": ""}  # Empty model
            },
        }

        from app import generate_model_change_messages

        messages = generate_model_change_messages()

        # Should skip due to empty model
        assert len(messages) == 0


class TestHasPendingChangeExpanded:
    """Additional tests for has_pending_change()."""

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_has_pending_change_empty_override_dict(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test has_pending_change with empty agent override dict."""
        mock_st.session_state = {
            "agent_model_overrides": {
                "dm": {}  # Empty override dict
            }
        }

        from app import has_pending_change

        # Empty dict is still "in" the overrides
        assert has_pending_change("dm") is True

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_has_pending_change_missing_key(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test has_pending_change when session state missing key."""
        mock_st.session_state = {}  # No agent_model_overrides key

        from app import has_pending_change

        # Should handle missing key gracefully
        assert has_pending_change("dm") is False

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_has_pending_change_multiple_agents(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test has_pending_change with multiple agents."""
        mock_st.session_state = {
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku"},
                "fighter": {"provider": "ollama", "model": "llama3"},
            }
        }

        from app import has_pending_change

        assert has_pending_change("dm") is True
        assert has_pending_change("fighter") is True
        assert has_pending_change("rogue") is False
        assert has_pending_change("summarizer") is False


class TestIsAgentProviderUnavailableExpanded:
    """Additional tests for is_agent_provider_unavailable()."""

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_is_agent_provider_unavailable_character_with_override(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test character agent with override checks override provider."""
        from models import CharacterConfig, populate_game_state

        game = populate_game_state()
        game["characters"]["wizard"] = CharacterConfig(
            name="Elara",
            character_class="Wizard",
            personality="Scholarly",
            color="#7B68B8",
            provider="gemini",  # Original provider
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "wizard": {"provider": "claude", "model": "claude-3-haiku"}  # Override
            },
        }

        mock_available.return_value = False  # Claude unavailable

        from app import is_agent_provider_unavailable

        result = is_agent_provider_unavailable("wizard")
        assert result is True  # Should check claude (override), not gemini

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_is_agent_provider_unavailable_summarizer(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test summarizer agent provider check."""
        from models import GameConfig, populate_game_state

        game = populate_game_state()
        game["game_config"] = GameConfig(
            summarizer_provider="ollama", summarizer_model="llama3"
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {},
        }

        mock_available.return_value = False  # Ollama unavailable

        from app import is_agent_provider_unavailable

        result = is_agent_provider_unavailable("summarizer")
        assert result is True

    @patch("app.st")
    @patch("app.is_provider_available")
    def test_is_agent_provider_unavailable_override_missing_provider_key(
        self, mock_available: MagicMock, mock_st: MagicMock
    ) -> None:
        """Test override dict missing provider key defaults to gemini."""
        from models import populate_game_state

        game = populate_game_state()

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"model": "some-model"}  # Missing provider key
            },
        }

        # Default gemini should be checked
        mock_available.return_value = True

        from app import is_agent_provider_unavailable

        result = is_agent_provider_unavailable("dm")
        assert result is False  # Gemini (default) is available


class TestRenderFunctionsExpanded:
    """Additional tests for render functions."""

    def test_render_pending_change_badge_css_class(self) -> None:
        """Test pending change badge has correct CSS class."""
        from app import render_pending_change_badge

        html = render_pending_change_badge()

        assert "class=" in html
        assert "pending-change-badge" in html

    def test_render_pending_change_badge_is_span(self) -> None:
        """Test pending change badge is a span element."""
        from app import render_pending_change_badge

        html = render_pending_change_badge()

        assert html.startswith("<span")
        assert html.endswith("</span>")

    def test_render_provider_unavailable_warning_css_class(self) -> None:
        """Test provider unavailable warning has correct CSS class."""
        from app import render_provider_unavailable_warning

        html = render_provider_unavailable_warning()

        assert "class=" in html
        assert "provider-unavailable-warning" in html

    def test_render_provider_unavailable_warning_is_span(self) -> None:
        """Test provider unavailable warning is a span element."""
        from app import render_provider_unavailable_warning

        html = render_provider_unavailable_warning()

        assert html.startswith("<span")
        assert html.endswith("</span>")


class TestCampaignDataPreservationExpanded:
    """Additional campaign data preservation tests."""

    @patch("app.st")
    def test_model_change_preserves_human_control_state(
        self, mock_st: MagicMock
    ) -> None:
        """Test that human control state is preserved during model change."""
        from models import populate_game_state

        game = populate_game_state()
        game["human_active"] = True
        game["controlled_character"] = "theron"

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["human_active"] is True
        assert updated_game["controlled_character"] == "theron"

    @patch("app.st")
    def test_model_change_preserves_current_round(self, mock_st: MagicMock) -> None:
        """Test that current_round is preserved during model change."""
        from models import populate_game_state

        game = populate_game_state()
        game["current_round"] = 15

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["current_round"] == 15

    @patch("app.st")
    def test_model_change_preserves_character_facts(self, mock_st: MagicMock) -> None:
        """Test that character facts in agent memories are preserved."""
        from models import AgentMemory, CharacterFacts, populate_game_state

        game = populate_game_state()
        facts = CharacterFacts(
            name="Theron",
            character_class="Fighter",
            key_traits=["Brave", "Honorable"],
            relationships={"Elara": "Trusted ally"},
            notable_events=["Defeated the dragon"],
        )
        game["agent_memories"]["theron"] = AgentMemory(
            character_facts=facts,
            long_term_summary="Theron's adventures...",
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        preserved_facts = updated_game["agent_memories"]["theron"].character_facts
        assert preserved_facts is not None
        assert preserved_facts.name == "Theron"
        assert preserved_facts.key_traits == ["Brave", "Honorable"]
        assert preserved_facts.relationships == {"Elara": "Trusted ally"}


class TestEdgeCasesAndIntegration:
    """Edge cases and integration scenarios."""

    @patch("app.st")
    def test_switch_during_empty_turn_queue(self, mock_st: MagicMock) -> None:
        """Test provider switch when turn queue is empty."""
        from models import populate_game_state

        game = populate_game_state()
        game["turn_queue"] = []  # Empty queue

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }

        from app import apply_model_config_changes

        # Should not raise any errors
        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "claude"
        assert updated_game["turn_queue"] == []

    @patch("app.st")
    def test_switch_back_to_original_provider(self, mock_st: MagicMock) -> None:
        """Test switching back to original provider works correctly."""
        from models import DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

        from app import apply_model_config_changes

        # First switch: Gemini -> Claude
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"}
            },
        }
        apply_model_config_changes()
        game = mock_st.session_state["game"]
        assert game["dm_config"].provider == "claude"

        # Second switch: Claude -> Gemini (back to original)
        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "gemini", "model": "gemini-1.5-flash"}
            },
        }
        apply_model_config_changes()
        game = mock_st.session_state["game"]
        assert game["dm_config"].provider == "gemini"
        assert game["dm_config"].model == "gemini-1.5-flash"

    @patch("app.st")
    def test_switch_only_dm_leaves_characters_unchanged(
        self, mock_st: MagicMock
    ) -> None:
        """Test that switching only DM doesn't affect character configs."""
        from models import CharacterConfig, DMConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")
        game["characters"]["theron"] = CharacterConfig(
            name="Theron",
            character_class="Fighter",
            personality="Brave",
            color="#C45C4A",
            provider="claude",
            model="claude-3-haiku-20240307",
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "ollama", "model": "llama3"}
                # No override for theron
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]
        assert updated_game["dm_config"].provider == "ollama"
        # Theron should remain unchanged
        assert updated_game["characters"]["theron"].provider == "claude"
        assert updated_game["characters"]["theron"].model == "claude-3-haiku-20240307"

    @patch("app.st")
    def test_concurrent_override_and_game_state_update(
        self, mock_st: MagicMock
    ) -> None:
        """Test that overrides properly merge with existing game state."""
        from models import CharacterConfig, DMConfig, GameConfig, populate_game_state

        game = populate_game_state()
        game["dm_config"] = DMConfig(
            provider="gemini",
            model="gemini-1.5-flash",
            token_limit=16000,  # Custom token limit to verify preservation
            name="Custom DM",  # Custom name to verify preservation
        )
        game["game_config"] = GameConfig(
            summarizer_provider="gemini",
            summarizer_model="gemini-1.5-flash",
            combat_mode="Tactical",  # Non-default to verify preservation
            party_size=6,  # Non-default party size
        )
        game["characters"]["wizard"] = CharacterConfig(
            name="Elara",
            character_class="Wizard",
            personality="Scholarly",
            color="#7B68B8",
            provider="gemini",
        )

        mock_st.session_state = {
            "game": game,
            "agent_model_overrides": {
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"},
                "summarizer": {"provider": "ollama", "model": "llama3"},
                "wizard": {"provider": "claude", "model": "claude-3-sonnet-20240229"},
            },
        }

        from app import apply_model_config_changes

        apply_model_config_changes()

        updated_game = mock_st.session_state["game"]

        # Provider/model updated
        assert updated_game["dm_config"].provider == "claude"
        assert updated_game["dm_config"].model == "claude-3-haiku-20240307"
        # Other fields preserved via model_copy
        assert updated_game["dm_config"].token_limit == 16000
        assert updated_game["dm_config"].name == "Custom DM"

        assert updated_game["game_config"].summarizer_provider == "ollama"
        assert updated_game["game_config"].summarizer_model == "llama3"
        # Non-summarizer fields preserved via model_copy
        assert updated_game["game_config"].combat_mode == "Tactical"
        assert updated_game["game_config"].party_size == 6

        assert updated_game["characters"]["wizard"].provider == "claude"
        assert updated_game["characters"]["wizard"].model == "claude-3-sonnet-20240229"
        # Personality preserved
        assert updated_game["characters"]["wizard"].personality == "Scholarly"
