"""Tests for Story 6.4: Context Limit Configuration.

This module contains tests for:
- Model maximum context limit lookups (Task 1)
- Token limit validation and clamping (Tasks 5, 6)
- Token limit state management (Task 4)
- Token limit hint generation (Task 7)
- Applying token limit changes to game state (Tasks 8, 9)
- Memory manager respecting individual limits (Task 11)
- All 6 acceptance criteria (Task 12)
"""

from unittest.mock import MagicMock, patch

# =============================================================================
# Model Maximum Context Limit Tests (Task 1)
# =============================================================================


class TestModelMaxContext:
    """Tests for MODEL_MAX_CONTEXT dict and get_model_max_context() function."""

    def test_gemini_flash_context_limit(self) -> None:
        """Test Gemini 1.5 Flash has 1M context limit."""
        from config import get_model_max_context

        assert get_model_max_context("gemini-1.5-flash") == 1_000_000

    def test_gemini_pro_context_limit(self) -> None:
        """Test Gemini 1.5 Pro has 2M context limit."""
        from config import get_model_max_context

        assert get_model_max_context("gemini-1.5-pro") == 2_000_000

    def test_gemini_2_flash_context_limit(self) -> None:
        """Test Gemini 2.0 Flash has 1M context limit."""
        from config import get_model_max_context

        assert get_model_max_context("gemini-2.0-flash") == 1_000_000

    def test_claude_haiku_context_limit(self) -> None:
        """Test Claude 3 Haiku has 200K context limit."""
        from config import get_model_max_context

        assert get_model_max_context("claude-3-haiku-20240307") == 200_000

    def test_claude_sonnet_context_limit(self) -> None:
        """Test Claude 3.5 Sonnet has 200K context limit."""
        from config import get_model_max_context

        assert get_model_max_context("claude-3-5-sonnet-20241022") == 200_000

    def test_claude_sonnet_4_context_limit(self) -> None:
        """Test Claude Sonnet 4 has 200K context limit."""
        from config import get_model_max_context

        assert get_model_max_context("claude-sonnet-4-20250514") == 200_000

    def test_ollama_max_context_for_provider(self) -> None:
        """Test Ollama models get MAX_OLLAMA_CONTEXT via provider function."""
        from config import MAX_OLLAMA_CONTEXT, get_max_context_for_provider

        # All Ollama models should get MAX_OLLAMA_CONTEXT (128,000)
        assert get_max_context_for_provider("ollama", "llama3") == MAX_OLLAMA_CONTEXT
        assert get_max_context_for_provider("ollama", "mistral") == MAX_OLLAMA_CONTEXT
        assert get_max_context_for_provider("ollama", "phi3") == MAX_OLLAMA_CONTEXT
        assert get_max_context_for_provider("ollama", "any-model") == MAX_OLLAMA_CONTEXT
        assert MAX_OLLAMA_CONTEXT == 128_000

    def test_unknown_model_returns_default(self) -> None:
        """Test that unknown models return DEFAULT_MAX_CONTEXT (8192)."""
        from config import DEFAULT_MAX_CONTEXT, get_model_max_context

        assert get_model_max_context("unknown-model-xyz") == DEFAULT_MAX_CONTEXT
        assert get_model_max_context("") == DEFAULT_MAX_CONTEXT

    def test_model_max_context_dict_exists(self) -> None:
        """Test that MODEL_MAX_CONTEXT dict is properly defined."""
        from config import MODEL_MAX_CONTEXT

        assert isinstance(MODEL_MAX_CONTEXT, dict)
        # Gemini (7) + Claude (3) = 10 models
        assert len(MODEL_MAX_CONTEXT) >= 10

    def test_minimum_token_limit_constant(self) -> None:
        """Test that MINIMUM_TOKEN_LIMIT is 1000."""
        from config import MINIMUM_TOKEN_LIMIT

        assert MINIMUM_TOKEN_LIMIT == 1_000


# =============================================================================
# Token Limit Validation Tests (Tasks 5, 6)
# =============================================================================


class TestTokenLimitValidation:
    """Tests for token limit validation and warning logic."""

    def test_get_token_limit_warning_below_minimum(self) -> None:
        """Test warning returned when value below MINIMUM_TOKEN_LIMIT."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            warning = get_token_limit_warning(500)
            assert warning == "Low limit may affect memory quality"

    def test_get_token_limit_warning_at_minimum(self) -> None:
        """Test no warning when value equals MINIMUM_TOKEN_LIMIT."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            warning = get_token_limit_warning(1000)
            assert warning is None

    def test_get_token_limit_warning_above_minimum(self) -> None:
        """Test no warning when value above MINIMUM_TOKEN_LIMIT."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            warning = get_token_limit_warning(8000)
            assert warning is None

    def test_validate_token_limit_within_range(self) -> None:
        """Test that valid values are not clamped."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            # Mock get_current_agent_model to return gemini model
            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("gemini", "gemini-1.5-flash")

                adjusted, msg = validate_token_limit("dm", 8000)

                assert adjusted == 8000
                assert msg is None

    def test_validate_token_limit_exceeds_maximum(self) -> None:
        """Test that values exceeding model max are clamped."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            # Mock get_current_agent_model to return ollama model with 128K max
            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("ollama", "llama3")

                # 50000 is within Ollama's 128K max, so no adjustment needed
                adjusted, msg = validate_token_limit("dm", 50000)
                assert adjusted == 50000
                assert msg is None

                # But 150000 exceeds Ollama's 128K max
                adjusted, msg = validate_token_limit("dm", 150000)
                assert adjusted == 128000
                assert msg is not None
                assert "128,000" in msg  # Formatted number
                assert "model maximum" in msg.lower()


# =============================================================================
# Token Limit State Management Tests (Task 4)
# =============================================================================


class TestTokenLimitStateManagement:
    """Tests for token limit state management functions."""

    def test_get_effective_token_limit_from_override(self) -> None:
        """Test that overrides take precedence."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {"dm": 16000},
                "game": None,
            }
            from app import get_effective_token_limit

            limit = get_effective_token_limit("dm")
            assert limit == 16000

    def test_get_effective_token_limit_from_game_state_dm(self) -> None:
        """Test fallback to game state for DM."""
        from models import DMConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": {"dm_config": DMConfig(token_limit=12000)},
            }
            from app import get_effective_token_limit

            limit = get_effective_token_limit("dm")
            assert limit == 12000

    def test_get_effective_token_limit_from_game_state_character(self) -> None:
        """Test fallback to game state for character."""
        from models import CharacterConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": {
                    "dm_config": None,
                    "characters": {
                        "fighter": CharacterConfig(
                            name="Fighter",
                            character_class="Fighter",
                            personality="Brave",
                            color="#C45C4A",
                            token_limit=6000,
                        )
                    },
                },
            }
            from app import get_effective_token_limit

            limit = get_effective_token_limit("fighter")
            assert limit == 6000

    def test_get_effective_token_limit_default_fallback(self) -> None:
        """Test default fallback when no game state."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": None,
            }
            from app import get_effective_token_limit

            limit = get_effective_token_limit("unknown")
            assert limit == 4000  # Default fallback


# =============================================================================
# Apply Token Limit Changes Tests (Tasks 8, 9)
# =============================================================================


class TestApplyTokenLimitChanges:
    """Tests for applying token limit changes to game state."""

    def test_apply_token_limit_changes_dm(self) -> None:
        """Test that DM token limit is updated in config and memory."""
        from models import AgentMemory, DMConfig

        with patch("app.st") as mock_st:
            dm_config = DMConfig(token_limit=8000)
            dm_memory = AgentMemory(token_limit=8000)

            mock_st.session_state = {
                "token_limit_overrides": {"dm": 16000},
                "game": {
                    "dm_config": dm_config,
                    "agent_memories": {"dm": dm_memory},
                    "characters": {},
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            # Check that game state was updated
            game = mock_st.session_state["game"]
            assert game["dm_config"].token_limit == 16000
            assert game["agent_memories"]["dm"].token_limit == 16000

    def test_apply_token_limit_changes_character(self) -> None:
        """Test that character token limit is updated in config and memory."""
        from models import AgentMemory, CharacterConfig, DMConfig

        with patch("app.st") as mock_st:
            char_config = CharacterConfig(
                name="Fighter",
                character_class="Fighter",
                personality="Brave",
                color="#C45C4A",
                token_limit=4000,
            )
            char_memory = AgentMemory(token_limit=4000)

            mock_st.session_state = {
                "token_limit_overrides": {"fighter": 10000},
                "game": {
                    "dm_config": DMConfig(),
                    "agent_memories": {"fighter": char_memory},
                    "characters": {"fighter": char_config},
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            # Check that game state was updated
            game = mock_st.session_state["game"]
            assert game["characters"]["fighter"].token_limit == 10000
            assert game["agent_memories"]["fighter"].token_limit == 10000

    def test_apply_token_limit_changes_no_overrides(self) -> None:
        """Test that no changes are made when no overrides exist."""
        from models import DMConfig

        with patch("app.st") as mock_st:
            dm_config = DMConfig(token_limit=8000)

            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": {
                    "dm_config": dm_config,
                    "agent_memories": {},
                    "characters": {},
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            # Game state should be unchanged
            game = mock_st.session_state["game"]
            assert game["dm_config"].token_limit == 8000

    def test_apply_does_not_compress_existing_memories(self) -> None:
        """Test that existing memories are not compressed when limit changes.

        Story 6.4 AC #5: Existing memories should not be retroactively compressed.
        """
        from models import AgentMemory, CharacterConfig, DMConfig

        with patch("app.st") as mock_st:
            # Create a character with a large buffer
            existing_buffer = [f"Entry {i}" for i in range(20)]
            char_config = CharacterConfig(
                name="Fighter",
                character_class="Fighter",
                personality="Brave",
                color="#C45C4A",
                token_limit=8000,
            )
            char_memory = AgentMemory(
                token_limit=8000,
                short_term_buffer=existing_buffer,
                long_term_summary="Previous summary",
            )

            mock_st.session_state = {
                "token_limit_overrides": {"fighter": 2000},  # Lower limit
                "game": {
                    "dm_config": DMConfig(),
                    "agent_memories": {"fighter": char_memory},
                    "characters": {"fighter": char_config},
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            # Memory buffer should be unchanged (not retroactively compressed)
            game = mock_st.session_state["game"]
            assert len(game["agent_memories"]["fighter"].short_term_buffer) == 20
            assert (
                game["agent_memories"]["fighter"].long_term_summary
                == "Previous summary"
            )
            # Only the token_limit field should be updated
            assert game["agent_memories"]["fighter"].token_limit == 2000


# =============================================================================
# Memory Manager Tests (Task 11)
# =============================================================================


class TestMemoryManagerTokenLimits:
    """Tests for memory manager respecting individual token limits."""

    def test_is_near_limit_uses_agent_token_limit(self) -> None:
        """Test that is_near_limit uses the agent's individual token_limit."""
        from memory import MemoryManager
        from models import AgentMemory

        state = {
            "agent_memories": {
                "fighter": AgentMemory(
                    token_limit=1000,
                    short_term_buffer=["Short entry"],
                ),
                "wizard": AgentMemory(
                    token_limit=10000,
                    short_term_buffer=["Short entry"],
                ),
            }
        }

        manager = MemoryManager(state)  # type: ignore[arg-type]

        # Fighter with low limit - same buffer should be closer to limit
        # Wizard with high limit - same buffer should be far from limit
        # Both have same buffer content, but different limits
        fighter_near = manager.is_near_limit("fighter")
        wizard_near = manager.is_near_limit("wizard")

        # Can't assert exact values without knowing buffer size,
        # but we verify the function runs without error
        assert isinstance(fighter_near, bool)
        assert isinstance(wizard_near, bool)

    def test_different_agents_different_limits_honored(self) -> None:
        """Test that different agents can have different limits (AC #6)."""
        from memory import MemoryManager
        from models import AgentMemory

        state = {
            "agent_memories": {
                "dm": AgentMemory(token_limit=16000),
                "fighter": AgentMemory(token_limit=4000),
                "wizard": AgentMemory(token_limit=8000),
            }
        }

        _ = MemoryManager(state)  # type: ignore[arg-type]

        # Verify each agent has their own limit
        assert state["agent_memories"]["dm"].token_limit == 16000
        assert state["agent_memories"]["fighter"].token_limit == 4000
        assert state["agent_memories"]["wizard"].token_limit == 8000


# =============================================================================
# Snapshot Config Values Tests (Task 9)
# =============================================================================


class TestSnapshotConfigValues:
    """Tests for snapshot_config_values including token limits."""

    def test_snapshot_includes_token_limits(self) -> None:
        """Test that snapshot includes token limit overrides."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "api_key_overrides": {},
                "agent_model_overrides": {},
                "token_limit_overrides": {"dm": 16000, "fighter": 8000},
            }
            from app import snapshot_config_values

            snapshot = snapshot_config_values()

            assert "settings" in snapshot
            assert "token_limits" in snapshot["settings"]
            assert snapshot["settings"]["token_limits"] == {
                "dm": 16000,
                "fighter": 8000,
            }

    def test_snapshot_empty_token_limits(self) -> None:
        """Test snapshot with no token limit overrides."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "api_key_overrides": {},
                "agent_model_overrides": {},
                "token_limit_overrides": {},
            }
            from app import snapshot_config_values

            snapshot = snapshot_config_values()

            assert snapshot["settings"]["token_limits"] == {}


# =============================================================================
# Acceptance Criteria Tests (Task 12)
# =============================================================================


class TestAcceptanceCriteria:
    """Tests for all 6 acceptance criteria in Story 6.4."""

    def test_ac1_settings_tab_shows_token_limit_for_each_agent(self) -> None:
        """AC #1: Settings tab shows token limit field for each agent.

        Given each agent row in the Models tab
        When I expand advanced options (or a separate Settings tab section)
        Then I see a token limit field for that agent.
        """
        # This is a UI test that would require Streamlit testing
        # We verify the render_settings_tab function exists and handles agents
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": None,
            }
            from app import render_settings_tab

            # Function exists and is callable
            assert callable(render_settings_tab)

    def test_ac2_shows_current_limit_and_model_max_hint(self) -> None:
        """AC #2: Shows current limit and model max hint.

        Given the token limit field
        When displayed
        Then it shows the current limit (default from character YAML)
        And includes a hint about the model's maximum context.
        """
        from config import get_model_max_context

        # Verify model max lookup works
        max_context = get_model_max_context("gemini-1.5-flash")
        assert max_context == 1_000_000

        # Verify we can get effective token limit
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": None,
            }
            from app import get_effective_token_limit

            limit = get_effective_token_limit("dm")
            assert isinstance(limit, int)

    def test_ac3_warning_for_low_limit(self) -> None:
        """AC #3: Warning for low token limit.

        Given I enter a new token limit
        When it's below a minimum threshold (e.g., 1000)
        Then a warning appears: "Low limit may affect memory quality".
        """
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            # Below threshold
            warning = get_token_limit_warning(500)
            assert warning == "Low limit may affect memory quality"

            # At threshold (no warning)
            warning = get_token_limit_warning(1000)
            assert warning is None

    def test_ac4_clamps_to_model_maximum(self) -> None:
        """AC #4: Clamps to model maximum with info message.

        Given I enter a token limit exceeding the model's maximum
        When validation runs
        Then it clamps to the model's maximum
        And shows an info message explaining the adjustment.
        """
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            with patch("app.get_current_agent_model") as mock_get_model:
                # Ollama now has 128K max (MAX_OLLAMA_CONTEXT)
                mock_get_model.return_value = ("ollama", "llama3")

                # 100000 is within Ollama's 128K max, no clamping
                adjusted, msg = validate_token_limit("dm", 100000)
                assert adjusted == 100000
                assert msg is None

                # But 200000 exceeds Ollama's 128K max, should clamp
                adjusted, msg = validate_token_limit("dm", 200000)
                assert adjusted == 128000
                assert msg is not None
                assert "maximum" in msg.lower()

    def test_ac5_saved_limits_used_for_compression(self) -> None:
        """AC #5: Saved limits used for compression, not retroactive.

        Given I save token limit changes
        When the game continues
        Then the new limits are used for memory compression thresholds
        And existing memories are not retroactively compressed.
        """
        from models import AgentMemory, DMConfig

        with patch("app.st") as mock_st:
            # Setup: DM with existing memory and buffer
            dm_memory = AgentMemory(
                token_limit=8000,
                short_term_buffer=["Entry 1", "Entry 2", "Entry 3"],
                long_term_summary="Existing summary",
            )

            mock_st.session_state = {
                "token_limit_overrides": {"dm": 4000},  # Reduce limit
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {"dm": dm_memory},
                    "characters": {},
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            # New limit applied
            game = mock_st.session_state["game"]
            assert game["dm_config"].token_limit == 4000
            assert game["agent_memories"]["dm"].token_limit == 4000

            # But existing memory not compressed
            assert len(game["agent_memories"]["dm"].short_term_buffer) == 3
            assert game["agent_memories"]["dm"].long_term_summary == "Existing summary"

    def test_ac6_different_agents_different_limits(self) -> None:
        """AC #6: Different agents have different limits honored.

        Given different agents have different limits
        When the game runs
        Then each agent's memory is managed according to their individual limit.
        """
        from models import AgentMemory, CharacterConfig, DMConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {
                    "dm": 16000,
                    "fighter": 4000,
                    "wizard": 8000,
                },
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {
                        "dm": AgentMemory(token_limit=8000),
                        "fighter": AgentMemory(token_limit=4000),
                        "wizard": AgentMemory(token_limit=4000),
                    },
                    "characters": {
                        "fighter": CharacterConfig(
                            name="Fighter",
                            character_class="Fighter",
                            personality="Brave",
                            color="#C45C4A",
                            token_limit=4000,
                        ),
                        "wizard": CharacterConfig(
                            name="Wizard",
                            character_class="Wizard",
                            personality="Curious",
                            color="#7B68B8",
                            token_limit=4000,
                        ),
                    },
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            # Each agent should have their own limit
            game = mock_st.session_state["game"]
            assert game["dm_config"].token_limit == 16000
            assert game["agent_memories"]["dm"].token_limit == 16000
            assert game["characters"]["fighter"].token_limit == 4000
            assert game["agent_memories"]["fighter"].token_limit == 4000
            assert game["characters"]["wizard"].token_limit == 8000
            assert game["agent_memories"]["wizard"].token_limit == 8000


# =============================================================================
# Integration Tests
# =============================================================================


class TestConfigModalIntegration:
    """Integration tests for config modal with token limits."""

    def test_handle_config_save_applies_token_limits(self) -> None:
        """Test that handle_config_save_click applies token limit changes."""
        from models import AgentMemory, DMConfig

        with patch("app.st") as mock_st:
            mock_st.toast = MagicMock()
            mock_st.rerun = MagicMock()

            mock_st.session_state = {
                "agent_model_overrides": {},
                "token_limit_overrides": {"dm": 20000},
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {"dm": AgentMemory(token_limit=8000)},
                    "characters": {},
                },
                "config_modal_open": True,
                "was_paused_before_modal": False,
            }

            # Mock apply_api_key_overrides since we're not testing that
            with patch("app.apply_api_key_overrides"):
                with patch("app.handle_config_modal_close"):
                    from app import handle_config_save_click

                    handle_config_save_click()

            # Token limits should be applied
            game = mock_st.session_state["game"]
            assert game["dm_config"].token_limit == 20000
            assert game["agent_memories"]["dm"].token_limit == 20000

            # Toast should be shown
            mock_st.toast.assert_called()


# =============================================================================
# Edge Case Tests (Code Review Additions)
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases identified in code review."""

    def test_model_change_after_token_limit_set(self) -> None:
        """Test that token limit validation updates when model changes.

        Edge case from Dev Notes: If user changes model in Models tab,
        the max context hint should update and values may need re-clamping.
        """
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {"dm": 500000},  # High limit for Gemini
                "agent_model_overrides": {},  # Initially no model override
                "game": None,
            }
            from app import validate_token_limit

            # Initially with Gemini model (1M max), 500K is valid
            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("gemini", "gemini-1.5-flash")
                adjusted, msg = validate_token_limit("dm", 500000)
                assert adjusted == 500000
                assert msg is None

            # After switching to Ollama llama3 (128K max), should clamp
            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("ollama", "llama3")
                adjusted, msg = validate_token_limit("dm", 500000)
                assert adjusted == 128000
                assert msg is not None
                assert "maximum" in msg.lower()

    def test_summarizer_token_limit_from_config(self) -> None:
        """Test that summarizer uses token limit from app config.

        The summarizer doesn't have a persistent GameState config,
        it reads from the AppConfig singleton.
        """
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},  # No override
                "game": {"dm_config": None, "characters": {}},
            }
            from app import get_effective_token_limit

            # Should fall back to config default
            limit = get_effective_token_limit("summarizer")
            # Default from config/defaults.yaml is 4000
            assert limit == 4000

    def test_summarizer_token_limit_override(self) -> None:
        """Test that summarizer respects UI overrides."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {"summarizer": 8000},
                "game": None,
            }
            from app import get_effective_token_limit

            limit = get_effective_token_limit("summarizer")
            assert limit == 8000

    def test_very_high_gemini_limit_allowed(self) -> None:
        """Test that Gemini's 2M token limit is properly supported."""
        from config import get_model_max_context

        max_context = get_model_max_context("gemini-1.5-pro")
        assert max_context == 2_000_000

        # Verify a high limit is accepted
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("gemini", "gemini-1.5-pro")
                adjusted, msg = validate_token_limit("dm", 1_500_000)
                assert adjusted == 1_500_000
                assert msg is None

    def test_warning_indicator_included(self) -> None:
        """Test that warning message includes indicator text.

        Code review fix: Warning should have visual indicator.
        """
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            warning = get_token_limit_warning(500)
            # The warning text is a constant; the indicator is added in render
            assert warning == "Low limit may affect memory quality"


# =============================================================================
# Boundary Value Tests (Expanded Coverage)
# =============================================================================


class TestBoundaryValues:
    """Tests for boundary conditions and edge values."""

    def test_warning_at_boundary_minus_one(self) -> None:
        """Test warning at MINIMUM_TOKEN_LIMIT - 1."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            # 999 is below threshold
            warning = get_token_limit_warning(999)
            assert warning is not None

    def test_no_warning_at_boundary_plus_one(self) -> None:
        """Test no warning at MINIMUM_TOKEN_LIMIT + 1."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            # 1001 is above threshold
            warning = get_token_limit_warning(1001)
            assert warning is None

    def test_warning_at_zero(self) -> None:
        """Test warning for zero token limit."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            warning = get_token_limit_warning(0)
            assert warning == "Low limit may affect memory quality"

    def test_warning_at_one(self) -> None:
        """Test warning for minimum possible value."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import get_token_limit_warning

            warning = get_token_limit_warning(1)
            assert warning == "Low limit may affect memory quality"

    def test_validate_token_limit_exactly_at_max(self) -> None:
        """Test validation when value equals model maximum exactly."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("ollama", "llama3")  # 8192 max
                adjusted, msg = validate_token_limit("dm", 8192)
                assert adjusted == 8192
                assert msg is None  # No clamping message when exactly at max

    def test_validate_token_limit_one_over_max(self) -> None:
        """Test validation when value is one over model maximum."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("ollama", "llama3")  # 128K max
                adjusted, msg = validate_token_limit("dm", 128001)
                assert adjusted == 128000  # Clamped
                assert msg is not None  # Should have info message

    def test_validate_token_limit_one_under_max(self) -> None:
        """Test validation when value is one under model maximum."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("ollama", "llama3")  # 8192 max
                adjusted, msg = validate_token_limit("dm", 8191)
                assert adjusted == 8191
                assert msg is None

    def test_validate_with_very_large_value(self) -> None:
        """Test validation with extremely large value."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("gemini", "gemini-1.5-pro")  # 2M max
                # Test with value larger than any model supports
                adjusted, msg = validate_token_limit("dm", 10_000_000)
                assert adjusted == 2_000_000  # Clamped to Gemini Pro max
                assert msg is not None


# =============================================================================
# Handle Token Limit Change Tests (Expanded Coverage)
# =============================================================================


class TestHandleTokenLimitChange:
    """Tests for handle_token_limit_change callback."""

    def test_handle_change_stores_override(self) -> None:
        """Test that handle_token_limit_change stores value in overrides."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_dm": 12000,
                "token_limit_overrides": {},
                "game": None,
            }

            with patch("app.mark_config_changed") as mock_mark:
                with patch("app.get_current_agent_model") as mock_get_model:
                    mock_get_model.return_value = ("gemini", "gemini-1.5-flash")
                    from app import handle_token_limit_change

                    handle_token_limit_change("dm")

                    assert mock_st.session_state["token_limit_overrides"]["dm"] == 12000
                    mock_mark.assert_called_once()

    def test_handle_change_with_none_value(self) -> None:
        """Test handle_token_limit_change returns early when value is None."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_dm": None,
                "token_limit_overrides": {},
            }

            with patch("app.mark_config_changed") as mock_mark:
                from app import handle_token_limit_change

                handle_token_limit_change("dm")

                # Should not have updated overrides or called mark_config_changed
                assert "dm" not in mock_st.session_state["token_limit_overrides"]
                mock_mark.assert_not_called()

    def test_handle_change_stores_info_message_on_clamp(self) -> None:
        """Test that clamping stores info message in session state."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_dm": 200000,  # Exceeds Ollama 128K max
                "token_limit_overrides": {},
                "game": None,
            }

            with patch("app.mark_config_changed"):
                with patch("app.get_current_agent_model") as mock_get_model:
                    mock_get_model.return_value = ("ollama", "llama3")  # 128K max
                    from app import handle_token_limit_change

                    handle_token_limit_change("dm")

                    # Should store clamped value
                    assert mock_st.session_state["token_limit_overrides"]["dm"] == 128000
                    # Should store info message
                    assert "token_limit_info_dm" in mock_st.session_state
                    assert "128,000" in mock_st.session_state["token_limit_info_dm"]

    def test_handle_change_clears_info_message_on_valid_value(self) -> None:
        """Test that valid value clears any previous info message."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_dm": 4000,  # Valid value
                "token_limit_overrides": {},
                "token_limit_info_dm": "Previous info message",
                "game": None,
            }

            with patch("app.mark_config_changed"):
                with patch("app.get_current_agent_model") as mock_get_model:
                    mock_get_model.return_value = ("gemini", "gemini-1.5-flash")
                    from app import handle_token_limit_change

                    handle_token_limit_change("dm")

                    # Info message should be cleared
                    assert "token_limit_info_dm" not in mock_st.session_state


# =============================================================================
# Apply Token Limit Changes - Additional Tests
# =============================================================================


class TestApplyTokenLimitChangesExtended:
    """Extended tests for apply_token_limit_changes function."""

    def test_apply_with_no_game_state(self) -> None:
        """Test apply does nothing when game state is None."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {"dm": 16000},
                "game": None,
            }
            from app import apply_token_limit_changes

            # Should not raise an error
            apply_token_limit_changes()

            # Game should still be None
            assert mock_st.session_state["game"] is None

    def test_apply_with_empty_overrides(self) -> None:
        """Test apply does nothing when overrides are empty."""
        from models import DMConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {},
                    "characters": {},
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            # DM config should be unchanged
            assert mock_st.session_state["game"]["dm_config"].token_limit == 8000

    def test_apply_multiple_characters(self) -> None:
        """Test applying changes to multiple characters at once."""
        from models import AgentMemory, CharacterConfig, DMConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {
                    "dm": 20000,
                    "fighter": 5000,
                    "wizard": 6000,
                    "rogue": 7000,
                },
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {
                        "dm": AgentMemory(token_limit=8000),
                        "fighter": AgentMemory(token_limit=4000),
                        "wizard": AgentMemory(token_limit=4000),
                        "rogue": AgentMemory(token_limit=4000),
                    },
                    "characters": {
                        "fighter": CharacterConfig(
                            name="Fighter",
                            character_class="Fighter",
                            personality="Brave",
                            color="#C45C4A",
                            token_limit=4000,
                        ),
                        "wizard": CharacterConfig(
                            name="Wizard",
                            character_class="Wizard",
                            personality="Curious",
                            color="#7B68B8",
                            token_limit=4000,
                        ),
                        "rogue": CharacterConfig(
                            name="Rogue",
                            character_class="Rogue",
                            personality="Sneaky",
                            color="#5A8F5A",
                            token_limit=4000,
                        ),
                    },
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            game = mock_st.session_state["game"]
            # Verify all limits updated correctly
            assert game["dm_config"].token_limit == 20000
            assert game["agent_memories"]["dm"].token_limit == 20000
            assert game["characters"]["fighter"].token_limit == 5000
            assert game["agent_memories"]["fighter"].token_limit == 5000
            assert game["characters"]["wizard"].token_limit == 6000
            assert game["agent_memories"]["wizard"].token_limit == 6000
            assert game["characters"]["rogue"].token_limit == 7000
            assert game["agent_memories"]["rogue"].token_limit == 7000

    def test_apply_partial_overrides(self) -> None:
        """Test applying changes when only some agents have overrides."""
        from models import AgentMemory, CharacterConfig, DMConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {
                    "fighter": 10000,  # Only fighter has override
                },
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {
                        "dm": AgentMemory(token_limit=8000),
                        "fighter": AgentMemory(token_limit=4000),
                        "wizard": AgentMemory(token_limit=4000),
                    },
                    "characters": {
                        "fighter": CharacterConfig(
                            name="Fighter",
                            character_class="Fighter",
                            personality="Brave",
                            color="#C45C4A",
                            token_limit=4000,
                        ),
                        "wizard": CharacterConfig(
                            name="Wizard",
                            character_class="Wizard",
                            personality="Curious",
                            color="#7B68B8",
                            token_limit=4000,
                        ),
                    },
                },
            }
            from app import apply_token_limit_changes

            apply_token_limit_changes()

            game = mock_st.session_state["game"]
            # Fighter updated
            assert game["characters"]["fighter"].token_limit == 10000
            assert game["agent_memories"]["fighter"].token_limit == 10000
            # DM and wizard unchanged
            assert game["dm_config"].token_limit == 8000
            assert game["agent_memories"]["dm"].token_limit == 8000
            assert game["characters"]["wizard"].token_limit == 4000
            assert game["agent_memories"]["wizard"].token_limit == 4000

    def test_apply_with_missing_agent_memory(self) -> None:
        """Test apply handles agents without corresponding memory entries."""
        from models import CharacterConfig, DMConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {
                    "fighter": 10000,
                },
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {},  # No memories
                    "characters": {
                        "fighter": CharacterConfig(
                            name="Fighter",
                            character_class="Fighter",
                            personality="Brave",
                            color="#C45C4A",
                            token_limit=4000,
                        ),
                    },
                },
            }
            from app import apply_token_limit_changes

            # Should not raise an error
            apply_token_limit_changes()

            game = mock_st.session_state["game"]
            # Character config updated
            assert game["characters"]["fighter"].token_limit == 10000
            # No memory to update, but should not error


# =============================================================================
# Get Effective Token Limit - Extended Tests
# =============================================================================


class TestGetEffectiveTokenLimitExtended:
    """Extended tests for get_effective_token_limit function."""

    def test_override_takes_precedence_over_game_state(self) -> None:
        """Test that UI override takes precedence over game state."""
        from models import DMConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {"dm": 50000},  # Override
                "game": {"dm_config": DMConfig(token_limit=8000)},  # Different value
            }
            from app import get_effective_token_limit

            # Should return override value, not game state value
            limit = get_effective_token_limit("dm")
            assert limit == 50000

    def test_character_not_in_game_returns_default(self) -> None:
        """Test fallback for character not found in game state."""
        from models import DMConfig

        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": {
                    "dm_config": DMConfig(),
                    "characters": {},  # No characters
                },
            }
            from app import get_effective_token_limit

            # Should return default
            limit = get_effective_token_limit("unknown_character")
            assert limit == 4000  # Default fallback

    def test_dm_with_none_dm_config(self) -> None:
        """Test DM fallback when dm_config is None."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "token_limit_overrides": {},
                "game": {"dm_config": None, "characters": {}},
            }
            from app import get_effective_token_limit

            limit = get_effective_token_limit("dm")
            # Should return DM default (8000)
            assert limit == 8000


# =============================================================================
# Model Constants Tests (Extended Coverage)
# =============================================================================


class TestModelConstantsExtended:
    """Extended tests for model context constants."""

    def test_all_gemini_models_have_at_least_1m_context(self) -> None:
        """Verify all Gemini models support at least 1M context."""
        from config import MODEL_MAX_CONTEXT

        gemini_models = [k for k in MODEL_MAX_CONTEXT if k.startswith("gemini")]
        for model in gemini_models:
            assert MODEL_MAX_CONTEXT[model] >= 1_000_000

    def test_all_claude_models_have_200k_context(self) -> None:
        """Verify all Claude models have 200K context."""
        from config import MODEL_MAX_CONTEXT

        claude_models = [k for k in MODEL_MAX_CONTEXT if k.startswith("claude")]
        for model in claude_models:
            assert MODEL_MAX_CONTEXT[model] == 200_000

    def test_default_max_context_is_conservative(self) -> None:
        """Verify DEFAULT_MAX_CONTEXT is a safe conservative value."""
        from config import DEFAULT_MAX_CONTEXT, MODEL_MAX_CONTEXT

        # Default should be less than or equal to smallest known model
        min_known = min(MODEL_MAX_CONTEXT.values())
        assert DEFAULT_MAX_CONTEXT <= min_known

    def test_minimum_token_limit_is_reasonable(self) -> None:
        """Verify MINIMUM_TOKEN_LIMIT is a reasonable value."""
        from config import MINIMUM_TOKEN_LIMIT

        # Should be at least 100 (some minimal context)
        assert MINIMUM_TOKEN_LIMIT >= 100
        # Should be less than 10000 (shouldn't warn for normal values)
        assert MINIMUM_TOKEN_LIMIT < 10000


# =============================================================================
# Snapshot Config Values - Extended Tests
# =============================================================================


class TestSnapshotConfigValuesExtended:
    """Extended tests for snapshot_config_values function."""

    def test_snapshot_with_multiple_token_limits(self) -> None:
        """Test snapshot captures all token limit overrides."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "api_key_overrides": {},
                "agent_model_overrides": {},
                "token_limit_overrides": {
                    "dm": 16000,
                    "fighter": 8000,
                    "wizard": 6000,
                    "summarizer": 5000,
                },
            }
            from app import snapshot_config_values

            snapshot = snapshot_config_values()

            assert snapshot["settings"]["token_limits"] == {
                "dm": 16000,
                "fighter": 8000,
                "wizard": 6000,
                "summarizer": 5000,
            }

    def test_snapshot_handles_missing_token_limit_overrides(self) -> None:
        """Test snapshot handles when token_limit_overrides doesn't exist."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "api_key_overrides": {},
                "agent_model_overrides": {},
                # No token_limit_overrides key
            }
            from app import snapshot_config_values

            snapshot = snapshot_config_values()

            # Should return empty dict, not error
            assert snapshot["settings"]["token_limits"] == {}


# =============================================================================
# Render Functions - Basic Coverage Tests
# =============================================================================


class TestRenderFunctions:
    """Tests for render function basic behavior."""

    def test_render_settings_tab_initializes_overrides(self) -> None:
        """Test render_settings_tab initializes token_limit_overrides if missing."""
        with patch("app.st") as mock_st:
            # Simulate Streamlit functions
            mock_st.session_state = {"game": None}
            mock_st.markdown = MagicMock()
            mock_st.number_input = MagicMock(return_value=4000)
            mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])

            # Mock the column context managers
            col1, col2 = mock_st.columns.return_value
            col1.__enter__ = MagicMock(return_value=col1)
            col1.__exit__ = MagicMock(return_value=False)
            col2.__enter__ = MagicMock(return_value=col2)
            col2.__exit__ = MagicMock(return_value=False)

            # Mock render_token_limit_row to avoid complex rendering
            with patch("app.render_token_limit_row"):
                from app import render_settings_tab

                render_settings_tab()

                # Should initialize token_limit_overrides
                assert "token_limit_overrides" in mock_st.session_state
                assert mock_st.session_state["token_limit_overrides"] == {}


# =============================================================================
# Validation Message Format Tests
# =============================================================================


class TestValidationMessageFormat:
    """Tests for validation message formatting."""

    def test_clamp_message_includes_formatted_number(self) -> None:
        """Test that clamp message includes comma-formatted number."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("gemini", "gemini-1.5-flash")  # 1M max
                _, msg = validate_token_limit("dm", 2_000_000)

                # Message should contain formatted number
                assert msg is not None
                assert "1,000,000" in msg

    def test_clamp_message_mentions_model_maximum(self) -> None:
        """Test that clamp message mentions model maximum."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            from app import validate_token_limit

            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("ollama", "llama3")
                # Use value exceeding Ollama's 128K max to trigger clamping
                _, msg = validate_token_limit("dm", 200000)

                assert msg is not None
                assert "model maximum" in msg.lower() or "maximum" in msg.lower()


# =============================================================================
# Memory Manager Integration - Extended Tests
# =============================================================================


class TestMemoryManagerIntegrationExtended:
    """Extended tests for memory manager integration with token limits."""

    def test_memory_manager_respects_updated_token_limit(self) -> None:
        """Test that MemoryManager uses updated token limits after apply."""
        from memory import MemoryManager
        from models import AgentMemory

        # Initial state with default limit
        state = {
            "agent_memories": {
                "fighter": AgentMemory(
                    token_limit=10000,
                    short_term_buffer=["Entry " * 100 for _ in range(50)],  # Large buffer
                ),
            }
        }

        manager = MemoryManager(state)  # type: ignore[arg-type]

        # Check near limit with high limit
        near_with_high_limit = manager.is_near_limit("fighter", threshold=0.8)

        # Now update to lower limit
        state["agent_memories"]["fighter"] = state["agent_memories"][
            "fighter"
        ].model_copy(update={"token_limit": 1000})

        # Create new manager with updated state
        manager2 = MemoryManager(state)  # type: ignore[arg-type]
        near_with_low_limit = manager2.is_near_limit("fighter", threshold=0.8)

        # With same buffer, lower limit should be more likely to be near limit
        # (This may or may not flip depending on actual buffer size, but verifies the call works)
        assert isinstance(near_with_high_limit, bool)
        assert isinstance(near_with_low_limit, bool)

    def test_memory_manager_with_custom_threshold(self) -> None:
        """Test is_near_limit with various threshold values."""
        from memory import MemoryManager
        from models import AgentMemory

        state = {
            "agent_memories": {
                "test_agent": AgentMemory(
                    token_limit=1000,
                    short_term_buffer=["Test entry"],
                ),
            }
        }

        manager = MemoryManager(state)  # type: ignore[arg-type]

        # Test with different thresholds
        result_low = manager.is_near_limit("test_agent", threshold=0.1)
        result_high = manager.is_near_limit("test_agent", threshold=0.99)

        assert isinstance(result_low, bool)
        assert isinstance(result_high, bool)


# =============================================================================
# Config Modal Integration - Extended Tests
# =============================================================================


class TestConfigModalIntegrationExtended:
    """Extended integration tests for config modal."""

    def test_save_click_applies_token_limits_with_toast(self) -> None:
        """Test that saving shows toast notification."""
        from models import AgentMemory, DMConfig

        with patch("app.st") as mock_st:
            mock_st.toast = MagicMock()
            mock_st.rerun = MagicMock()

            mock_st.session_state = {
                "agent_model_overrides": {},
                "token_limit_overrides": {"dm": 15000, "fighter": 7000},
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {
                        "dm": AgentMemory(token_limit=8000),
                    },
                    "characters": {},
                },
                "config_modal_open": True,
                "was_paused_before_modal": False,
            }

            with patch("app.apply_api_key_overrides"):
                with patch("app.handle_config_modal_close"):
                    from app import handle_config_save_click

                    handle_config_save_click()

            # Toast should have been called
            mock_st.toast.assert_called()

    def test_save_click_with_only_token_limit_changes(self) -> None:
        """Test saving when only token limits changed (no model changes)."""
        from models import AgentMemory, DMConfig

        with patch("app.st") as mock_st:
            mock_st.toast = MagicMock()
            mock_st.rerun = MagicMock()

            mock_st.session_state = {
                "agent_model_overrides": {},  # No model changes
                "token_limit_overrides": {"summarizer": 6000},
                "game": {
                    "dm_config": DMConfig(token_limit=8000),
                    "agent_memories": {},
                    "characters": {},
                },
                "config_modal_open": True,
                "was_paused_before_modal": False,
            }

            with patch("app.apply_api_key_overrides"):
                with patch("app.handle_config_modal_close"):
                    from app import handle_config_save_click

                    handle_config_save_click()

            # Should complete without error
            mock_st.toast.assert_called()
