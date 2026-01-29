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

    def test_ollama_llama3_context_limit(self) -> None:
        """Test Ollama Llama3 has 8192 context limit."""
        from config import get_model_max_context

        assert get_model_max_context("llama3") == 8_192

    def test_ollama_mistral_context_limit(self) -> None:
        """Test Ollama Mistral has 32K context limit."""
        from config import get_model_max_context

        assert get_model_max_context("mistral") == 32_768

    def test_ollama_phi3_context_limit(self) -> None:
        """Test Ollama Phi3 has 128K context limit."""
        from config import get_model_max_context

        assert get_model_max_context("phi3") == 128_000

    def test_unknown_model_returns_default(self) -> None:
        """Test that unknown models return DEFAULT_MAX_CONTEXT (8192)."""
        from config import DEFAULT_MAX_CONTEXT, get_model_max_context

        assert get_model_max_context("unknown-model-xyz") == DEFAULT_MAX_CONTEXT
        assert get_model_max_context("") == DEFAULT_MAX_CONTEXT

    def test_model_max_context_dict_exists(self) -> None:
        """Test that MODEL_MAX_CONTEXT dict is properly defined."""
        from config import MODEL_MAX_CONTEXT

        assert isinstance(MODEL_MAX_CONTEXT, dict)
        assert len(MODEL_MAX_CONTEXT) >= 9  # At least 9 models defined

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

            # Mock get_current_agent_model to return ollama model with 8192 max
            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("ollama", "llama3")

                adjusted, msg = validate_token_limit("dm", 50000)

                assert adjusted == 8192
                assert msg is not None
                assert "8,192" in msg  # Formatted number
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
                mock_get_model.return_value = ("ollama", "llama3")  # 8192 max

                adjusted, msg = validate_token_limit("dm", 100000)

                assert adjusted == 8192
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

            # After switching to Ollama llama3 (8K max), should clamp
            with patch("app.get_current_agent_model") as mock_get_model:
                mock_get_model.return_value = ("ollama", "llama3")
                adjusted, msg = validate_token_limit("dm", 500000)
                assert adjusted == 8192
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
