"""Tests for Story 10-3: Secret Knowledge Injection.

Tests the injection of secret whispers into agent context prompts,
ensuring PC agents only see their own secrets while the DM sees all.
"""

from agents import (
    _build_dm_context,
    _build_pc_context,
    format_all_secrets_context,
    format_pc_secrets_context,
)
from models import (
    AgentMemory,
    AgentSecrets,
    CharacterConfig,
    DMConfig,
    GameConfig,
    GameState,
    NarrativeElementStore,
    Whisper,
    create_whisper,
)

# =============================================================================
# format_pc_secrets_context Tests
# =============================================================================


class TestFormatPcSecretsContext:
    """Tests for format_pc_secrets_context helper function."""

    def test_empty_secrets_returns_empty_string(self) -> None:
        """Test that empty AgentSecrets returns empty string."""
        secrets = AgentSecrets(whispers=[])
        result = format_pc_secrets_context(secrets)
        assert result == ""

    def test_single_active_whisper_formats_correctly(self) -> None:
        """Test formatting a single active whisper."""
        whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="You see a hidden door.",
            turn_created=10,
        )
        secrets = AgentSecrets(whispers=[whisper])

        result = format_pc_secrets_context(secrets)

        assert "## Secret Knowledge (Only You Know This)" in result
        assert "- [Turn 10] You see a hidden door." in result

    def test_multiple_active_whispers_format_in_order(self) -> None:
        """Test multiple whispers are formatted in order."""
        whisper1 = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="First secret.",
            turn_created=5,
        )
        whisper2 = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="Second secret.",
            turn_created=15,
        )
        secrets = AgentSecrets(whispers=[whisper1, whisper2])

        result = format_pc_secrets_context(secrets)

        assert "- [Turn 5] First secret." in result
        assert "- [Turn 15] Second secret." in result
        # Verify order (first should come before second)
        lines = result.split("\n")
        idx1 = next(i for i, line in enumerate(lines) if "Turn 5" in line)
        idx2 = next(i for i, line in enumerate(lines) if "Turn 15" in line)
        assert idx1 < idx2

    def test_revealed_whispers_are_excluded(self) -> None:
        """Test that revealed whispers are not included."""
        active_whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="Still secret.",
            turn_created=10,
        )
        revealed_whisper = Whisper(
            id="revealed-id",
            from_agent="dm",
            to_agent="rogue",
            content="No longer secret.",
            turn_created=5,
            revealed=True,
            turn_revealed=8,
        )
        secrets = AgentSecrets(whispers=[revealed_whisper, active_whisper])

        result = format_pc_secrets_context(secrets)

        assert "Still secret." in result
        assert "No longer secret." not in result

    def test_all_revealed_returns_empty_string(self) -> None:
        """Test that all revealed whispers returns empty string."""
        revealed = Whisper(
            id="revealed-id",
            from_agent="dm",
            to_agent="rogue",
            content="Revealed secret.",
            turn_created=5,
            revealed=True,
            turn_revealed=8,
        )
        secrets = AgentSecrets(whispers=[revealed])

        result = format_pc_secrets_context(secrets)

        assert result == ""

    def test_turn_number_displayed_correctly(self) -> None:
        """Test turn number is formatted with brackets."""
        whisper = create_whisper(
            from_agent="dm",
            to_agent="fighter",
            content="Turn test.",
            turn_created=42,
        )
        secrets = AgentSecrets(whispers=[whisper])

        result = format_pc_secrets_context(secrets)

        assert "[Turn 42]" in result

    def test_content_preserved_exactly(self) -> None:
        """Test whisper content is preserved without modification."""
        original_content = "The merchant whispered 'the baron is secretly a vampire!'"
        whisper = create_whisper(
            from_agent="dm",
            to_agent="cleric",
            content=original_content,
            turn_created=22,
        )
        secrets = AgentSecrets(whispers=[whisper])

        result = format_pc_secrets_context(secrets)

        assert original_content in result


class TestFormatPcSecretsContextEdgeCases:
    """Test edge cases in format_pc_secrets_context."""

    def test_minimal_content_whisper(self) -> None:
        """Test whisper with minimal (single character) content string."""
        whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="!",  # Minimal valid content
            turn_created=5,
        )
        secrets = AgentSecrets(whispers=[whisper])

        result = format_pc_secrets_context(secrets)

        # Should still format correctly even with minimal content
        assert "## Secret Knowledge (Only You Know This)" in result
        assert "[Turn 5] !" in result

    def test_unicode_content_in_whisper(self) -> None:
        """Test whisper with unicode and special characters."""
        whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="The wizard spoke: 'Ignis flammarum!' Flames erupted.",
            turn_created=10,
        )
        secrets = AgentSecrets(whispers=[whisper])

        result = format_pc_secrets_context(secrets)

        assert "Ignis flammarum!" in result
        assert "Flames erupted." in result

    def test_multiline_content_in_whisper(self) -> None:
        """Test whisper with multi-line content."""
        multiline_content = "Line one.\nLine two.\nLine three."
        whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content=multiline_content,
            turn_created=15,
        )
        secrets = AgentSecrets(whispers=[whisper])

        result = format_pc_secrets_context(secrets)

        # Content should be preserved including newlines
        assert multiline_content in result


class TestFormatPcSecretsContextFormatSpec:
    """Test that format matches acceptance criteria exactly."""

    def test_pc_secret_format_matches_spec(self) -> None:
        """Verify format matches acceptance criteria exactly."""
        whisper1 = Whisper(
            id="w1",
            from_agent="dm",
            to_agent="shadowmere",
            content="You noticed a concealed door behind the tapestry in the throne room.",
            turn_created=15,
        )
        whisper2 = Whisper(
            id="w2",
            from_agent="dm",
            to_agent="shadowmere",
            content="The merchant whispered that the baron is actually a vampire.",
            turn_created=22,
        )
        secrets = AgentSecrets(whispers=[whisper1, whisper2])

        result = format_pc_secrets_context(secrets)

        expected = """## Secret Knowledge (Only You Know This)
- [Turn 15] You noticed a concealed door behind the tapestry in the throne room.
- [Turn 22] The merchant whispered that the baron is actually a vampire."""

        assert result == expected


# =============================================================================
# format_all_secrets_context Tests
# =============================================================================


class TestFormatAllSecretsContext:
    """Tests for format_all_secrets_context helper function."""

    def test_empty_dict_returns_empty_string(self) -> None:
        """Test that empty agent_secrets dict returns empty string."""
        result = format_all_secrets_context({})
        assert result == ""

    def test_single_agent_with_secrets_formats_correctly(self) -> None:
        """Test formatting secrets for a single agent."""
        whisper = create_whisper(
            from_agent="dm",
            to_agent="fighter",
            content="You sense danger.",
            turn_created=8,
        )
        agent_secrets = {"fighter": AgentSecrets(whispers=[whisper])}

        result = format_all_secrets_context(agent_secrets)

        assert "## Active Secrets (You Know All)" in result
        assert "[Fighter]" in result  # Title case
        assert "[Turn 8]" in result
        assert "You sense danger." in result

    def test_multiple_agents_format_alphabetically(self) -> None:
        """Test multiple agents' secrets are sorted alphabetically."""
        whisper_rogue = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="Rogue secret.",
            turn_created=5,
        )
        whisper_fighter = create_whisper(
            from_agent="dm",
            to_agent="fighter",
            content="Fighter secret.",
            turn_created=7,
        )
        agent_secrets = {
            "rogue": AgentSecrets(whispers=[whisper_rogue]),
            "fighter": AgentSecrets(whispers=[whisper_fighter]),
        }

        result = format_all_secrets_context(agent_secrets)

        # Fighter should come before Rogue (alphabetical)
        lines = result.split("\n")
        fighter_idx = next(i for i, line in enumerate(lines) if "Fighter" in line)
        rogue_idx = next(i for i, line in enumerate(lines) if "Rogue" in line)
        assert fighter_idx < rogue_idx

    def test_agent_names_capitalized(self) -> None:
        """Test agent names are title-cased."""
        whisper = create_whisper(
            from_agent="dm",
            to_agent="shadowmere",
            content="Secret.",
            turn_created=1,
        )
        agent_secrets = {"shadowmere": AgentSecrets(whispers=[whisper])}

        result = format_all_secrets_context(agent_secrets)

        assert "[Shadowmere]" in result
        assert "[shadowmere]" not in result

    def test_revealed_whispers_excluded_across_all_agents(self) -> None:
        """Test revealed whispers are excluded from all agents."""
        active = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="Active secret.",
            turn_created=10,
        )
        revealed = Whisper(
            id="revealed-id",
            from_agent="dm",
            to_agent="fighter",
            content="Revealed secret.",
            turn_created=5,
            revealed=True,
            turn_revealed=8,
        )
        agent_secrets = {
            "rogue": AgentSecrets(whispers=[active]),
            "fighter": AgentSecrets(whispers=[revealed]),
        }

        result = format_all_secrets_context(agent_secrets)

        assert "Active secret." in result
        assert "Revealed secret." not in result

    def test_all_whispers_revealed_returns_empty(self) -> None:
        """Test that all revealed whispers returns empty string."""
        revealed = Whisper(
            id="revealed-id",
            from_agent="dm",
            to_agent="fighter",
            content="Revealed.",
            turn_created=5,
            revealed=True,
            turn_revealed=8,
        )
        agent_secrets = {"fighter": AgentSecrets(whispers=[revealed])}

        result = format_all_secrets_context(agent_secrets)

        assert result == ""

    def test_agents_with_no_active_whispers_excluded(self) -> None:
        """Test agents with only revealed whispers don't appear."""
        active = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="Active.",
            turn_created=10,
        )
        revealed = Whisper(
            id="revealed-id",
            from_agent="dm",
            to_agent="fighter",
            content="Revealed.",
            turn_created=5,
            revealed=True,
            turn_revealed=8,
        )
        agent_secrets = {
            "rogue": AgentSecrets(whispers=[active]),
            "fighter": AgentSecrets(whispers=[revealed]),
        }

        result = format_all_secrets_context(agent_secrets)

        # Fighter appears in result only if they have active whispers
        assert "[Rogue]" in result
        assert "[Fighter]" not in result


class TestFormatAllSecretsContextFormatSpec:
    """Test DM secrets format specification."""

    def test_dm_secrets_format_structure(self) -> None:
        """Test DM secrets section has correct structure."""
        whisper1 = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="The trap is on the left.",
            turn_created=12,
        )
        whisper2 = create_whisper(
            from_agent="dm",
            to_agent="wizard",
            content="The scroll is a fake.",
            turn_created=18,
        )
        agent_secrets = {
            "rogue": AgentSecrets(whispers=[whisper1]),
            "wizard": AgentSecrets(whispers=[whisper2]),
        }

        result = format_all_secrets_context(agent_secrets)

        # Verify header
        assert result.startswith("## Active Secrets (You Know All)")
        # Verify format: - [Agent] [Turn X] content
        assert "- [Rogue] [Turn 12] The trap is on the left." in result
        assert "- [Wizard] [Turn 18] The scroll is a fake." in result


# =============================================================================
# PC Context Integration Tests
# =============================================================================


class TestBuildPcContextSecretsIntegration:
    """Test _build_pc_context includes secrets correctly."""

    def _create_minimal_state(
        self,
        agent_name: str = "rogue",
        agent_secrets: dict[str, AgentSecrets] | None = None,
    ) -> GameState:
        """Create minimal game state for testing."""
        return GameState(
            ground_truth_log=[],
            turn_queue=["dm", "rogue", "fighter"],
            current_turn="dm",
            agent_memories={
                "dm": AgentMemory(token_limit=4000),
                "rogue": AgentMemory(token_limit=4000),
                "fighter": AgentMemory(token_limit=4000),
            },
            game_config=GameConfig(session_name="test"),
            dm_config=DMConfig(provider="gemini", model="gemini-test"),
            characters={
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="Sneaky",
                    color="#6B8E6B",
                    provider="gemini",
                    model="test",
                ),
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    personality="Bold",
                    color="#8B4513",
                    provider="gemini",
                    model="test",
                ),
            },
            whisper_queue=[],
            human_active=False,
            controlled_character=None,
            session_number=1,
            session_id="test-session",
            agent_secrets=agent_secrets or {},
            narrative_elements={},
            callback_database=NarrativeElementStore(),
        )

    def test_pc_context_includes_secret_section_when_whispers_exist(self) -> None:
        """Test PC context includes secret section when agent has whispers."""
        whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="You spotted a hidden lever.",
            turn_created=5,
        )
        state = self._create_minimal_state(
            agent_secrets={"rogue": AgentSecrets(whispers=[whisper])}
        )

        result = _build_pc_context(state, "rogue")

        assert "## Secret Knowledge (Only You Know This)" in result
        assert "You spotted a hidden lever." in result

    def test_pc_context_excludes_secret_section_when_no_whispers(self) -> None:
        """Test PC context excludes secret section when no whispers."""
        state = self._create_minimal_state(agent_secrets={})

        result = _build_pc_context(state, "rogue")

        assert "## Secret Knowledge" not in result

    def test_pc_only_sees_own_secrets(self) -> None:
        """Test PC agent only sees their own secrets (memory isolation)."""
        rogue_whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="Rogue's secret.",
            turn_created=5,
        )
        fighter_whisper = create_whisper(
            from_agent="dm",
            to_agent="fighter",
            content="Fighter's secret.",
            turn_created=7,
        )
        state = self._create_minimal_state(
            agent_secrets={
                "rogue": AgentSecrets(whispers=[rogue_whisper]),
                "fighter": AgentSecrets(whispers=[fighter_whisper]),
            }
        )

        # Rogue's context
        rogue_context = _build_pc_context(state, "rogue")
        assert "Rogue's secret." in rogue_context
        assert "Fighter's secret." not in rogue_context

        # Fighter's context
        fighter_context = _build_pc_context(state, "fighter")
        assert "Fighter's secret." in fighter_context
        assert "Rogue's secret." not in fighter_context

    def test_other_agents_secrets_not_visible_in_pc_context(self) -> None:
        """Test PC cannot see other agents' secrets (explicit isolation test)."""
        other_secret = create_whisper(
            from_agent="dm",
            to_agent="fighter",
            content="Top secret fighter intel.",
            turn_created=10,
        )
        state = self._create_minimal_state(
            agent_secrets={"fighter": AgentSecrets(whispers=[other_secret])}
        )

        # Rogue should NOT see fighter's secret
        rogue_context = _build_pc_context(state, "rogue")
        assert "Top secret fighter intel." not in rogue_context
        assert "## Secret Knowledge" not in rogue_context

    def test_pc_context_handles_missing_agent_in_secrets(self) -> None:
        """Test PC context handles agent not in agent_secrets dict."""
        # Rogue has no entry in agent_secrets at all
        state = self._create_minimal_state(
            agent_secrets={"fighter": AgentSecrets(whispers=[])}
        )

        result = _build_pc_context(state, "rogue")

        # Should not crash, should not have secrets section
        assert "## Secret Knowledge" not in result


# =============================================================================
# DM Context Integration Tests
# =============================================================================


class TestBuildDmContextSecretsIntegration:
    """Test _build_dm_context includes all secrets correctly."""

    def _create_minimal_state(
        self,
        agent_secrets: dict[str, AgentSecrets] | None = None,
    ) -> GameState:
        """Create minimal game state for testing."""
        return GameState(
            ground_truth_log=[],
            turn_queue=["dm", "rogue", "fighter"],
            current_turn="dm",
            agent_memories={
                "dm": AgentMemory(token_limit=4000),
                "rogue": AgentMemory(token_limit=4000),
                "fighter": AgentMemory(token_limit=4000),
            },
            game_config=GameConfig(session_name="test"),
            dm_config=DMConfig(provider="gemini", model="gemini-test"),
            characters={
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="Sneaky",
                    color="#6B8E6B",
                    provider="gemini",
                    model="test",
                ),
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    personality="Bold",
                    color="#8B4513",
                    provider="gemini",
                    model="test",
                ),
            },
            whisper_queue=[],
            human_active=False,
            controlled_character=None,
            session_number=1,
            session_id="test-session",
            agent_secrets=agent_secrets or {},
            narrative_elements={},
            callback_database=NarrativeElementStore(),
        )

    def test_dm_context_includes_all_secrets_section(self) -> None:
        """Test DM context includes secrets when whispers exist."""
        whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="The DM's whisper to rogue.",
            turn_created=5,
        )
        state = self._create_minimal_state(
            agent_secrets={"rogue": AgentSecrets(whispers=[whisper])}
        )

        result = _build_dm_context(state)

        assert "## Active Secrets (You Know All)" in result
        assert "The DM's whisper to rogue." in result

    def test_dm_context_excludes_section_when_no_whispers(self) -> None:
        """Test DM context excludes secrets section when no whispers."""
        state = self._create_minimal_state(agent_secrets={})

        result = _build_dm_context(state)

        assert "## Active Secrets" not in result

    def test_dm_sees_secrets_from_all_agents(self) -> None:
        """Test DM sees all secrets from all agents."""
        rogue_whisper = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="Rogue's private secret.",
            turn_created=5,
        )
        fighter_whisper = create_whisper(
            from_agent="dm",
            to_agent="fighter",
            content="Fighter's private secret.",
            turn_created=7,
        )
        state = self._create_minimal_state(
            agent_secrets={
                "rogue": AgentSecrets(whispers=[rogue_whisper]),
                "fighter": AgentSecrets(whispers=[fighter_whisper]),
            }
        )

        result = _build_dm_context(state)

        assert "Rogue's private secret." in result
        assert "Fighter's private secret." in result
        assert "[Rogue]" in result
        assert "[Fighter]" in result

    def test_dm_context_excludes_revealed_secrets(self) -> None:
        """Test DM context excludes revealed whispers."""
        active = create_whisper(
            from_agent="dm",
            to_agent="rogue",
            content="Still secret.",
            turn_created=10,
        )
        revealed = Whisper(
            id="revealed-id",
            from_agent="dm",
            to_agent="fighter",
            content="No longer secret.",
            turn_created=5,
            revealed=True,
            turn_revealed=8,
        )
        state = self._create_minimal_state(
            agent_secrets={
                "rogue": AgentSecrets(whispers=[active]),
                "fighter": AgentSecrets(whispers=[revealed]),
            }
        )

        result = _build_dm_context(state)

        assert "Still secret." in result
        assert "No longer secret." not in result

    def test_secrets_grouped_by_agent_in_output(self) -> None:
        """Test secrets are labeled by agent in DM output."""
        w1 = create_whisper("dm", "rogue", "Whisper 1.", 1)
        w2 = create_whisper("dm", "rogue", "Whisper 2.", 2)
        w3 = create_whisper("dm", "fighter", "Whisper 3.", 3)

        state = self._create_minimal_state(
            agent_secrets={
                "rogue": AgentSecrets(whispers=[w1, w2]),
                "fighter": AgentSecrets(whispers=[w3]),
            }
        )

        result = _build_dm_context(state)

        # All three whispers should be present with agent labels
        lines = [line for line in result.split("\n") if "Whisper" in line]
        assert len(lines) == 3
        assert any("[Rogue]" in line and "Whisper 1." in line for line in lines)
        assert any("[Rogue]" in line and "Whisper 2." in line for line in lines)
        assert any("[Fighter]" in line and "Whisper 3." in line for line in lines)


# =============================================================================
# Memory Isolation Verification Tests
# =============================================================================


class TestMemoryIsolation:
    """Tests verifying strict memory isolation for secrets."""

    def _create_state_with_multiple_secrets(self) -> GameState:
        """Create state with secrets for multiple agents."""
        return GameState(
            ground_truth_log=[],
            turn_queue=["dm", "rogue", "fighter", "wizard"],
            current_turn="dm",
            agent_memories={
                "dm": AgentMemory(token_limit=4000),
                "rogue": AgentMemory(token_limit=4000),
                "fighter": AgentMemory(token_limit=4000),
                "wizard": AgentMemory(token_limit=4000),
            },
            game_config=GameConfig(session_name="test"),
            dm_config=DMConfig(provider="gemini", model="gemini-test"),
            characters={
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="Sneaky",
                    color="#6B8E6B",
                    provider="gemini",
                    model="test",
                ),
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    personality="Bold",
                    color="#8B4513",
                    provider="gemini",
                    model="test",
                ),
                "wizard": CharacterConfig(
                    name="Gandara",
                    character_class="Wizard",
                    personality="Wise",
                    color="#4169E1",
                    provider="gemini",
                    model="test",
                ),
            },
            whisper_queue=[],
            human_active=False,
            controlled_character=None,
            session_number=1,
            session_id="test-session",
            agent_secrets={
                "rogue": AgentSecrets(whispers=[
                    create_whisper("dm", "rogue", "Rogue secret alpha", 1),
                    create_whisper("dm", "rogue", "Rogue secret beta", 3),
                ]),
                "fighter": AgentSecrets(whispers=[
                    create_whisper("dm", "fighter", "Fighter secret gamma", 2),
                ]),
                "wizard": AgentSecrets(whispers=[
                    create_whisper("dm", "wizard", "Wizard secret delta", 4),
                ]),
            },
        )

    def test_rogue_sees_only_rogue_secrets(self) -> None:
        """Rogue should only see rogue secrets."""
        state = self._create_state_with_multiple_secrets()
        context = _build_pc_context(state, "rogue")

        assert "Rogue secret alpha" in context
        assert "Rogue secret beta" in context
        assert "Fighter secret gamma" not in context
        assert "Wizard secret delta" not in context

    def test_fighter_sees_only_fighter_secrets(self) -> None:
        """Fighter should only see fighter secrets."""
        state = self._create_state_with_multiple_secrets()
        context = _build_pc_context(state, "fighter")

        assert "Fighter secret gamma" in context
        assert "Rogue secret alpha" not in context
        assert "Rogue secret beta" not in context
        assert "Wizard secret delta" not in context

    def test_wizard_sees_only_wizard_secrets(self) -> None:
        """Wizard should only see wizard secrets."""
        state = self._create_state_with_multiple_secrets()
        context = _build_pc_context(state, "wizard")

        assert "Wizard secret delta" in context
        assert "Rogue secret alpha" not in context
        assert "Rogue secret beta" not in context
        assert "Fighter secret gamma" not in context

    def test_dm_sees_all_secrets(self) -> None:
        """DM should see ALL secrets from all agents."""
        state = self._create_state_with_multiple_secrets()
        context = _build_dm_context(state)

        assert "Rogue secret alpha" in context
        assert "Rogue secret beta" in context
        assert "Fighter secret gamma" in context
        assert "Wizard secret delta" in context

    def test_asymmetric_access_pattern(self) -> None:
        """Verify asymmetric access: DM sees all, PCs see only own."""
        state = self._create_state_with_multiple_secrets()

        # DM context should contain all 4 secrets
        dm_context = _build_dm_context(state)
        assert dm_context.count("secret") >= 4  # All four secrets mentioned

        # Each PC context should contain only their own
        rogue_context = _build_pc_context(state, "rogue")
        fighter_context = _build_pc_context(state, "fighter")
        wizard_context = _build_pc_context(state, "wizard")

        # Count secrets in each context
        rogue_secret_count = sum(
            1 for s in ["alpha", "beta"] if s in rogue_context
        )
        fighter_secret_count = sum(
            1 for s in ["gamma"] if s in fighter_context
        )
        wizard_secret_count = sum(
            1 for s in ["delta"] if s in wizard_context
        )

        assert rogue_secret_count == 2
        assert fighter_secret_count == 1
        assert wizard_secret_count == 1

        # Verify cross-contamination didn't occur
        assert "gamma" not in rogue_context
        assert "delta" not in rogue_context
        assert "alpha" not in fighter_context
        assert "delta" not in fighter_context
        assert "alpha" not in wizard_context
        assert "gamma" not in wizard_context
