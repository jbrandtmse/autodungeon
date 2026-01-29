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
                "dm": {"provider": "claude", "model": "claude-3-haiku-20240307"},  # Valid
                "summarizer": {"model": "gemini-1.5-flash"},  # Invalid - missing provider
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
    def test_model_change_preserves_ground_truth_log(
        self, mock_st: MagicMock
    ) -> None:
        """Test that ground_truth_log is unchanged by model switch."""
        from models import populate_game_state

        game = populate_game_state()
        game["ground_truth_log"] = ["[DM]: The adventure begins...", "[Fighter]: I draw my sword!"]
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

        state["dm_config"] = DMConfig(provider="claude", model="claude-3-haiku-20240307")
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
        state["dm_config"] = DMConfig(provider="claude", model="claude-3-haiku-20240307")

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
            "agent_model_overrides": {
                "dm": {"provider": "ollama", "model": "llama3"}
            },
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
                "summarizer": {"provider": "claude", "model": "claude-3-haiku-20240307"},
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
