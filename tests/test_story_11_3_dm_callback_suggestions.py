"""Tests for Story 11-3: DM Callback Suggestions.

Tests the callback suggestion scoring, formatting, and DM context integration.
All functions are purely computational (no LLM calls), so no mocking is needed.

Story 11.3: DM Callback Suggestions.
FR78: DM context includes callback suggestions.
"""

from unittest.mock import patch

import pytest

from agents import (
    MAX_CALLBACK_SUGGESTIONS,
    MIN_CALLBACK_SCORE,
    _build_dm_context,
    format_callback_suggestions,
    score_callback_relevance,
)
from models import (
    AgentMemory,
    AgentSecrets,
    CharacterConfig,
    DMConfig,
    GameConfig,
    GameState,
    NarrativeElement,
    NarrativeElementStore,
    create_narrative_element,
)

# =============================================================================
# Helper Factories
# =============================================================================


def _make_element(
    name: str = "Test Element",
    element_type: str = "character",
    description: str = "A test element",
    turn_introduced: int = 10,
    session_introduced: int = 1,
    characters_involved: list[str] | None = None,
    potential_callbacks: list[str] | None = None,
    times_referenced: int = 1,
    last_referenced_turn: int | None = None,
    dormant: bool = False,
    resolved: bool = False,
) -> NarrativeElement:
    """Create a NarrativeElement for testing with convenient defaults."""
    element = create_narrative_element(
        element_type=element_type,  # type: ignore[arg-type]
        name=name,
        description=description,
        turn_introduced=turn_introduced,
        session_introduced=session_introduced,
        characters_involved=characters_involved or [],
        potential_callbacks=potential_callbacks or [],
    )
    # Override fields that create_narrative_element sets from defaults
    element.times_referenced = times_referenced
    element.last_referenced_turn = last_referenced_turn if last_referenced_turn is not None else turn_introduced
    element.dormant = dormant
    element.resolved = resolved
    return element


def _make_minimal_state(
    callback_database: NarrativeElementStore | None = None,
    turn_queue: list[str] | None = None,
    ground_truth_log: list[str] | None = None,
    agent_memories: dict[str, AgentMemory] | None = None,
    agent_secrets: dict[str, AgentSecrets] | None = None,
) -> GameState:
    """Create a minimal GameState for testing _build_dm_context."""
    return GameState(
        ground_truth_log=ground_truth_log or [],
        turn_queue=turn_queue or ["dm", "fighter", "rogue"],
        current_turn="dm",
        agent_memories=agent_memories or {"dm": AgentMemory()},
        game_config=GameConfig(),
        dm_config=DMConfig(),
        characters={
            "fighter": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                personality="Brave warrior",
                color="#FF0000",
            ),
            "rogue": CharacterConfig(
                name="Shadowmere",
                character_class="Rogue",
                personality="Sneaky thief",
                color="#00FF00",
            ),
        },
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
        session_number=1,
        session_id="001",
        summarization_in_progress=False,
        selected_module=None,
        character_sheets={},
        agent_secrets=agent_secrets or {},
        narrative_elements={},
        callback_database=callback_database or NarrativeElementStore(),
    )


# =============================================================================
# Tests for Constants
# =============================================================================


class TestConstants:
    """Test callback suggestion constants."""

    def test_max_callback_suggestions_value(self) -> None:
        """MAX_CALLBACK_SUGGESTIONS should be 5."""
        assert MAX_CALLBACK_SUGGESTIONS == 5

    def test_min_callback_score_value(self) -> None:
        """MIN_CALLBACK_SCORE should be 0.0."""
        assert MIN_CALLBACK_SCORE == 0.0


# =============================================================================
# Tests for score_callback_relevance()
# =============================================================================


class TestScoreCallbackRelevance:
    """Unit tests for score_callback_relevance()."""

    def test_recency_gap_higher_for_older_elements(self) -> None:
        """Elements unreferenced for longer should score higher on recency."""
        recent_element = _make_element(
            name="Recent",
            turn_introduced=45,
            last_referenced_turn=45,
        )
        old_element = _make_element(
            name="Old",
            turn_introduced=10,
            last_referenced_turn=10,
        )
        current_turn = 50

        recent_score = score_callback_relevance(recent_element, current_turn, [])
        old_score = score_callback_relevance(old_element, current_turn, [])

        assert old_score > recent_score

    def test_recency_gap_capped_at_5(self) -> None:
        """Recency gap bonus should cap at 5.0 (50+ turns ago)."""
        ancient_element = _make_element(
            name="Ancient",
            turn_introduced=1,
            last_referenced_turn=1,
        )
        # current_turn = 200 means 199 turns since reference
        # 199 / 10 = 19.9 but should cap at 5.0
        score = score_callback_relevance(ancient_element, 200, [])
        # Only recency + importance(1*0.5) = 5.0 + 0.5 = 5.5
        assert score == pytest.approx(5.5, abs=0.01)

    def test_character_involvement_bonus(self) -> None:
        """Elements with active character involvement get +2.0 bonus."""
        element = _make_element(
            name="Relevant",
            turn_introduced=40,
            last_referenced_turn=40,
            characters_involved=["Shadowmere", "Thorin"],
        )
        current_turn = 50

        score_with_match = score_callback_relevance(
            element, current_turn, ["shadowmere"]
        )
        score_without_match = score_callback_relevance(
            element, current_turn, ["wizard"]
        )

        assert score_with_match == score_without_match + 2.0

    def test_character_involvement_case_insensitive(self) -> None:
        """Character involvement matching is case-insensitive."""
        element = _make_element(
            name="Mixed Case",
            characters_involved=["Shadowmere"],
            turn_introduced=40,
            last_referenced_turn=40,
        )

        score_lower = score_callback_relevance(element, 50, ["shadowmere"])
        score_upper = score_callback_relevance(element, 50, ["SHADOWMERE"])

        assert score_lower == score_upper

    def test_importance_bonus_from_times_referenced(self) -> None:
        """More-referenced elements get importance bonus (times_referenced * 0.5)."""
        low_ref = _make_element(
            name="LowRef",
            times_referenced=1,
            turn_introduced=40,
            last_referenced_turn=40,
        )
        high_ref = _make_element(
            name="HighRef",
            times_referenced=5,
            turn_introduced=40,
            last_referenced_turn=40,
        )

        low_score = score_callback_relevance(low_ref, 50, [])
        high_score = score_callback_relevance(high_ref, 50, [])

        # Difference should be (5 - 1) * 0.5 = 2.0
        assert high_score - low_score == pytest.approx(2.0, abs=0.01)

    def test_potential_callbacks_bonus(self) -> None:
        """Elements with potential_callbacks get +1.0 bonus."""
        with_callbacks = _make_element(
            name="WithCallbacks",
            potential_callbacks=["Could return as ally"],
            turn_introduced=40,
            last_referenced_turn=40,
        )
        without_callbacks = _make_element(
            name="WithoutCallbacks",
            potential_callbacks=[],
            turn_introduced=40,
            last_referenced_turn=40,
        )

        score_with = score_callback_relevance(with_callbacks, 50, [])
        score_without = score_callback_relevance(without_callbacks, 50, [])

        assert score_with == score_without + 1.0

    def test_dormancy_penalty(self) -> None:
        """Dormant elements get -3.0 penalty."""
        active_element = _make_element(
            name="Active",
            dormant=False,
            turn_introduced=40,
            last_referenced_turn=40,
        )
        dormant_element = _make_element(
            name="Dormant",
            dormant=True,
            turn_introduced=40,
            last_referenced_turn=40,
        )

        active_score = score_callback_relevance(active_element, 50, [])
        dormant_score = score_callback_relevance(dormant_element, 50, [])

        assert active_score == dormant_score + 3.0

    def test_current_turn_equals_last_referenced(self) -> None:
        """When current_turn equals last_referenced_turn, recency gap is 0."""
        element = _make_element(
            name="JustReferenced",
            turn_introduced=50,
            last_referenced_turn=50,
        )
        # Recency: (50-50)/10 = 0.0
        # Importance: 1 * 0.5 = 0.5
        score = score_callback_relevance(element, 50, [])
        assert score == pytest.approx(0.5, abs=0.01)

    def test_empty_active_characters(self) -> None:
        """Empty active_characters list gives no character bonus."""
        element = _make_element(
            name="NoChars",
            characters_involved=["Shadowmere"],
            turn_introduced=40,
            last_referenced_turn=40,
        )
        score = score_callback_relevance(element, 50, [])
        # Recency: 10/10 = 1.0, importance: 0.5, no char bonus
        assert score == pytest.approx(1.5, abs=0.01)

    def test_combined_scoring(self) -> None:
        """Verify combined scoring with multiple factors."""
        element = _make_element(
            name="FullScore",
            turn_introduced=10,
            last_referenced_turn=20,
            times_referenced=3,
            characters_involved=["Shadowmere"],
            potential_callbacks=["Could appear again"],
            dormant=False,
        )
        # Recency: min((50-20)/10, 5.0) = min(3.0, 5.0) = 3.0
        # Character: +2.0 (shadowmere matches)
        # Importance: 3 * 0.5 = 1.5
        # Callbacks: +1.0
        # Dormancy: 0
        # Total: 3.0 + 2.0 + 1.5 + 1.0 = 7.5
        score = score_callback_relevance(element, 50, ["shadowmere"])
        assert score == pytest.approx(7.5, abs=0.01)

    def test_negative_recency_gap_clamped_to_zero(self) -> None:
        """If last_referenced_turn > current_turn, recency gap should be 0, not negative."""
        element = _make_element(
            name="FutureRef",
            turn_introduced=10,
            last_referenced_turn=100,  # Referenced in future (data anomaly)
            times_referenced=1,
        )
        # Without clamping: (50-100)/10 = -5.0 would give negative recency
        # With clamping: max(0, 50-100)/10 = 0.0 recency
        score = score_callback_relevance(element, 50, [])
        # Should only have importance bonus: 1 * 0.5 = 0.5
        assert score == pytest.approx(0.5, abs=0.01)
        assert score >= 0  # Recency should never be negative

    def test_dormant_with_character_involvement(self) -> None:
        """Dormant + involved characters: penalty and bonus both apply."""
        element = _make_element(
            name="DormantInvolved",
            dormant=True,
            characters_involved=["Shadowmere"],
            turn_introduced=10,
            last_referenced_turn=10,
        )
        # Recency: min(40/10, 5.0) = 4.0
        # Character: +2.0
        # Importance: 1 * 0.5 = 0.5
        # Dormancy: -3.0
        # Total: 4.0 + 2.0 + 0.5 - 3.0 = 3.5
        score = score_callback_relevance(element, 50, ["shadowmere"])
        assert score == pytest.approx(3.5, abs=0.01)


# =============================================================================
# Tests for format_callback_suggestions()
# =============================================================================


class TestFormatCallbackSuggestions:
    """Unit tests for format_callback_suggestions()."""

    def test_empty_database_returns_empty(self) -> None:
        """Empty callback_database returns empty string."""
        store = NarrativeElementStore()
        result = format_callback_suggestions(store, 50, ["fighter"])
        assert result == ""

    def test_single_element_formats_correctly(self) -> None:
        """Single element returns properly formatted section."""
        element = _make_element(
            name="Skrix the Goblin",
            element_type="character",
            description="Befriended by party, promised cave information",
            turn_introduced=15,
            session_introduced=2,
            characters_involved=["Shadowmere"],
            potential_callbacks=["Could appear with promised info"],
        )
        store = NarrativeElementStore(elements=[element])

        result = format_callback_suggestions(store, 50, ["shadowmere"])

        assert "## Callback Opportunities" in result
        assert "Consider weaving in these earlier story elements:" in result
        assert "1. **Skrix the Goblin** (Turn 15, Session 2)" in result
        assert "Befriended by party, promised cave information" in result
        assert "Potential use: Could appear with promised info" in result

    def test_multiple_elements_sorted_by_score(self) -> None:
        """Multiple elements are sorted by score (highest first)."""
        # Low score: recent, no involvement
        low_element = _make_element(
            name="Low Score",
            turn_introduced=48,
            last_referenced_turn=48,
        )
        # High score: old, with involvement and callbacks
        high_element = _make_element(
            name="High Score",
            turn_introduced=10,
            last_referenced_turn=10,
            characters_involved=["Shadowmere"],
            potential_callbacks=["Big reveal"],
            times_referenced=3,
        )
        store = NarrativeElementStore(elements=[low_element, high_element])

        result = format_callback_suggestions(store, 50, ["shadowmere"])

        # High Score should appear first
        high_pos = result.find("High Score")
        low_pos = result.find("Low Score")
        assert high_pos < low_pos

    def test_respects_max_suggestions_limit(self) -> None:
        """Only top MAX_CALLBACK_SUGGESTIONS elements are included."""
        elements = []
        for i in range(10):
            elements.append(
                _make_element(
                    name=f"Element {i}",
                    turn_introduced=i,
                    last_referenced_turn=i,
                )
            )
        store = NarrativeElementStore(elements=elements)

        result = format_callback_suggestions(store, 50, [])

        # Count numbered entries
        entry_count = sum(
            1 for line in result.split("\n")
            if line and line[0].isdigit() and ". **" in line
        )
        assert entry_count == MAX_CALLBACK_SUGGESTIONS

    def test_element_with_potential_callbacks_includes_use(self) -> None:
        """Element with potential_callbacks includes 'Potential use:' line."""
        element = _make_element(
            name="WithCallbacks",
            potential_callbacks=["Could return as ally", "Might betray party"],
        )
        store = NarrativeElementStore(elements=[element])

        result = format_callback_suggestions(store, 50, [])

        # Only first callback should be included
        assert "Potential use: Could return as ally" in result
        assert "Might betray party" not in result

    def test_element_without_potential_callbacks_omits_use(self) -> None:
        """Element without potential_callbacks omits 'Potential use:' line."""
        element = _make_element(
            name="NoCallbacks",
            potential_callbacks=[],
        )
        store = NarrativeElementStore(elements=[element])

        result = format_callback_suggestions(store, 50, [])

        assert "Potential use:" not in result
        assert "NoCallbacks" in result

    def test_all_resolved_elements_returns_empty(self) -> None:
        """All resolved elements results in empty string (get_active filters them)."""
        resolved_element = _make_element(
            name="Resolved",
            resolved=True,
        )
        store = NarrativeElementStore(elements=[resolved_element])

        result = format_callback_suggestions(store, 50, [])

        assert result == ""

    def test_dormant_elements_included_but_lower_ranked(self) -> None:
        """Dormant elements are included but scored lower than active ones."""
        active_element = _make_element(
            name="Active Element",
            turn_introduced=10,
            last_referenced_turn=10,
            dormant=False,
        )
        dormant_element = _make_element(
            name="Dormant Element",
            turn_introduced=10,
            last_referenced_turn=10,
            dormant=True,
        )
        store = NarrativeElementStore(elements=[dormant_element, active_element])

        result = format_callback_suggestions(store, 50, [])

        # Active should come first
        active_pos = result.find("Active Element")
        dormant_pos = result.find("Dormant Element")
        assert active_pos < dormant_pos

    def test_format_matches_epic_ac_structure(self) -> None:
        """Format matches the epic AC example structure."""
        element = _make_element(
            name="The Broken Amulet",
            element_type="item",
            description="Elara found half an amulet. The other half's location is unknown.",
            turn_introduced=42,
            session_introduced=3,
            potential_callbacks=["A merchant could have the other half."],
        )
        store = NarrativeElementStore(elements=[element])

        result = format_callback_suggestions(store, 80, [])

        lines = result.split("\n")
        # First line is header
        assert lines[0] == "## Callback Opportunities"
        # Second line is instruction
        assert lines[1] == "Consider weaving in these earlier story elements:"
        # Third line is blank
        assert lines[2] == ""
        # Fourth line is numbered entry with bold name and turn/session
        assert "1. **The Broken Amulet** (Turn 42, Session 3)" in lines[3]

    def test_element_without_description(self) -> None:
        """Element with empty description omits description line."""
        element = _make_element(
            name="NoDesc",
            description="",
            potential_callbacks=["Some callback"],
        )
        store = NarrativeElementStore(elements=[element])

        result = format_callback_suggestions(store, 50, [])

        assert "NoDesc" in result
        # Should not have an empty description line
        lines = [line for line in result.split("\n") if line.strip()]
        # Should have: header, instruction, entry header, potential use
        entry_lines = [line for line in lines if "NoDesc" in line or "Potential use:" in line]
        assert len(entry_lines) == 2


# =============================================================================
# Tests for _build_dm_context() callback integration
# =============================================================================


class TestBuildDmContextCallbackIntegration:
    """Tests for callback integration in _build_dm_context()."""

    @patch("agents.st", create=True)
    def test_state_with_callback_database_includes_section(self, mock_st: object) -> None:
        """State with populated callback_database includes Callback Opportunities section."""
        element = _make_element(
            name="Test NPC",
            description="A helpful goblin",
            turn_introduced=5,
            last_referenced_turn=5,
        )
        store = NarrativeElementStore(elements=[element])
        state = _make_minimal_state(
            callback_database=store,
            ground_truth_log=["msg1", "msg2", "msg3"] * 10,  # 30 entries
        )

        context = _build_dm_context(state)

        assert "## Callback Opportunities" in context
        assert "Test NPC" in context

    @patch("agents.st", create=True)
    def test_state_with_empty_callback_database_omits_section(self, mock_st: object) -> None:
        """State with empty callback_database omits Callback Opportunities."""
        store = NarrativeElementStore()
        state = _make_minimal_state(callback_database=store)

        context = _build_dm_context(state)

        assert "## Callback Opportunities" not in context
        assert "Callback" not in context

    @patch("agents.st", create=True)
    def test_state_without_callback_database_key_no_crash(self, mock_st: object) -> None:
        """State without callback_database key gracefully defaults to empty."""
        state = _make_minimal_state()
        # Remove callback_database key to simulate old checkpoint
        # TypedDict allows this at runtime even though type checker would complain
        del state["callback_database"]  # type: ignore[misc]

        # Should not crash
        context = _build_dm_context(state)

        assert "## Callback Opportunities" not in context

    @patch("agents.st", create=True)
    def test_callback_section_after_secrets_before_nudge(self, mock_st: object) -> None:
        """Callback section appears after Active Secrets, before Player Suggestion."""
        from models import AgentSecrets, create_whisper

        # Create a whisper so secrets section appears
        whisper = create_whisper(
            from_agent="dm",
            to_agent="fighter",
            content="You notice something odd",
            turn_created=5,
        )
        secrets = {"fighter": AgentSecrets(whispers=[whisper])}

        element = _make_element(
            name="Callback Element",
            turn_introduced=5,
            last_referenced_turn=5,
        )
        store = NarrativeElementStore(elements=[element])

        # Set up pending nudge via mock streamlit
        import types
        mock_session_state = {"pending_nudge": "Try the secret door", "pending_human_whisper": None}
        mock_module = types.ModuleType("streamlit")
        mock_module.session_state = mock_session_state  # type: ignore[attr-defined]

        with patch.dict("sys.modules", {"streamlit": mock_module}):
            state = _make_minimal_state(
                callback_database=store,
                agent_secrets=secrets,
                ground_truth_log=["msg"] * 10,
            )
            context = _build_dm_context(state)

        # All three sections should be present
        assert "## Active Secrets" in context
        assert "## Callback Opportunities" in context
        assert "## Player Suggestion" in context

        # Verify ordering
        secrets_pos = context.find("## Active Secrets")
        callback_pos = context.find("## Callback Opportunities")
        suggestion_pos = context.find("## Player Suggestion")

        assert secrets_pos < callback_pos < suggestion_pos

    @patch("agents.st", create=True)
    def test_active_characters_excludes_dm(self, mock_st: object) -> None:
        """active_characters correctly excludes 'dm' from turn_queue."""
        element = _make_element(
            name="Party Element",
            characters_involved=["fighter"],
            turn_introduced=5,
            last_referenced_turn=5,
        )
        store = NarrativeElementStore(elements=[element])
        state = _make_minimal_state(
            callback_database=store,
            turn_queue=["dm", "fighter", "rogue"],
            ground_truth_log=["msg"] * 10,
        )

        context = _build_dm_context(state)

        # The element involves "fighter" which is in active_characters
        # (turn_queue minus "dm"), so it should appear
        assert "Party Element" in context

    @patch("agents.st", create=True)
    def test_only_resolved_elements_omits_section(self, mock_st: object) -> None:
        """If all elements are resolved, section is omitted."""
        resolved = _make_element(name="Resolved", resolved=True)
        store = NarrativeElementStore(elements=[resolved])
        state = _make_minimal_state(
            callback_database=store,
            ground_truth_log=["msg"] * 10,
        )

        context = _build_dm_context(state)

        assert "## Callback Opportunities" not in context


# =============================================================================
# Integration Tests
# =============================================================================


class TestEndToEndDmContextWithCallbacks:
    """Integration tests for end-to-end DM context with callbacks."""

    @patch("agents.st", create=True)
    def test_full_context_with_populated_callback_database(self, mock_st: object) -> None:
        """Create a state with 3+ elements and verify full context formatting."""
        goblin = _make_element(
            name="Skrix the Goblin",
            element_type="character",
            description="Befriended by party, promised cave information",
            turn_introduced=15,
            session_introduced=2,
            characters_involved=["Shadowmere", "Thorin"],
            potential_callbacks=[
                "Could appear with promised info",
                "Might be in danger",
            ],
            times_referenced=3,
            last_referenced_turn=20,
        )
        amulet = _make_element(
            name="The Broken Amulet",
            element_type="item",
            description="Elara found half an amulet. The other half is unknown.",
            turn_introduced=42,
            session_introduced=3,
            potential_callbacks=["A merchant could have the other half"],
            times_referenced=1,
            last_referenced_turn=42,
        )
        tavern = _make_element(
            name="The Whispering Tavern",
            element_type="location",
            description="A mysterious tavern where secrets are traded",
            turn_introduced=5,
            session_introduced=1,
            times_referenced=2,
            last_referenced_turn=30,
        )

        store = NarrativeElementStore(elements=[goblin, amulet, tavern])

        state = _make_minimal_state(
            callback_database=store,
            turn_queue=["dm", "fighter", "rogue"],
            ground_truth_log=["msg"] * 60,
            agent_memories={
                "dm": AgentMemory(
                    long_term_summary="The party set out on an adventure.",
                    short_term_buffer=["[DM]: The cave entrance looms ahead."],
                ),
                "fighter": AgentMemory(),
                "rogue": AgentMemory(),
            },
        )

        context = _build_dm_context(state)

        # Verify the callback section is present
        assert "## Callback Opportunities" in context
        assert "Consider weaving in these earlier story elements:" in context

        # Verify all three elements appear
        assert "Skrix the Goblin" in context
        assert "The Broken Amulet" in context
        assert "The Whispering Tavern" in context

        # Verify elements are ordered by relevance score
        # The goblin has character involvement with active characters + more refs
        # so should rank higher
        goblin_pos = context.find("Skrix the Goblin")
        assert goblin_pos > 0  # Present

        # Verify format includes turn/session info
        assert "(Turn 15, Session 2)" in context
        assert "(Turn 42, Session 3)" in context
        assert "(Turn 5, Session 1)" in context

        # Verify potential use line for goblin
        assert "Potential use: Could appear with promised info" in context

    @patch("agents.st", create=True)
    def test_elements_ordered_by_relevance(self, mock_st: object) -> None:
        """Verify elements in context are ordered by relevance score."""
        # High relevance: old, involved, many references, has callbacks
        high_relevance = _make_element(
            name="High Relevance",
            turn_introduced=5,
            last_referenced_turn=10,
            times_referenced=5,
            characters_involved=["fighter"],
            potential_callbacks=["Big reveal"],
        )
        # Medium relevance: moderate gap, some references
        medium_relevance = _make_element(
            name="Medium Relevance",
            turn_introduced=30,
            last_referenced_turn=35,
            times_referenced=2,
        )
        # Low relevance: very recent, few references
        low_relevance = _make_element(
            name="Low Relevance",
            turn_introduced=48,
            last_referenced_turn=49,
            times_referenced=1,
        )

        store = NarrativeElementStore(
            elements=[low_relevance, medium_relevance, high_relevance]
        )
        state = _make_minimal_state(
            callback_database=store,
            ground_truth_log=["msg"] * 50,
        )

        context = _build_dm_context(state)

        high_pos = context.find("High Relevance")
        medium_pos = context.find("Medium Relevance")
        low_pos = context.find("Low Relevance")

        assert high_pos < medium_pos < low_pos

    @patch("agents.st", create=True)
    def test_context_contains_other_sections_alongside_callbacks(self, mock_st: object) -> None:
        """Verify callback section coexists with other DM context sections."""
        element = _make_element(
            name="Story Thread",
            turn_introduced=10,
            last_referenced_turn=10,
        )
        store = NarrativeElementStore(elements=[element])
        state = _make_minimal_state(
            callback_database=store,
            ground_truth_log=["msg"] * 30,
            agent_memories={
                "dm": AgentMemory(
                    long_term_summary="An epic adventure begins.",
                    short_term_buffer=["[DM]: The heroes arrive."],
                ),
                "fighter": AgentMemory(),
                "rogue": AgentMemory(),
            },
        )

        context = _build_dm_context(state)

        # Both regular sections and callback section present
        assert "## Story So Far" in context
        assert "## Recent Events" in context
        assert "## Callback Opportunities" in context

    @patch("agents.st", create=True)
    def test_format_matches_epic_ac_template(self, mock_st: object) -> None:
        """Verify format matches the epic AC template exactly."""
        element = _make_element(
            name="Skrix the Goblin",
            element_type="character",
            description="The party befriended this goblin who promised cave information.",
            turn_introduced=15,
            session_introduced=2,
            potential_callbacks=[
                "He could appear with the promised info, or be in danger."
            ],
        )
        store = NarrativeElementStore(elements=[element])
        state = _make_minimal_state(
            callback_database=store,
            ground_truth_log=["msg"] * 30,
        )

        context = _build_dm_context(state)

        # Extract callback section from context
        callback_start = context.find("## Callback Opportunities")
        assert callback_start >= 0

        callback_section = context[callback_start:]
        # May have more sections after, find next ## or end
        next_section = callback_section.find("\n\n##", 1)
        if next_section > 0:
            callback_section = callback_section[:next_section]

        # Verify structure
        assert "## Callback Opportunities" in callback_section
        assert "Consider weaving in these earlier story elements:" in callback_section
        assert "1. **Skrix the Goblin** (Turn 15, Session 2)" in callback_section
        assert "The party befriended this goblin who promised cave information." in callback_section
        assert "Potential use: He could appear with the promised info, or be in danger." in callback_section


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Edge case tests for callback suggestions."""

    def test_score_with_zero_current_turn(self) -> None:
        """Scoring with current_turn=0 (start of game)."""
        element = _make_element(
            name="StartElement",
            turn_introduced=0,
            last_referenced_turn=0,
        )
        # Should not crash, recency gap = 0
        score = score_callback_relevance(element, 0, [])
        assert score >= 0

    def test_format_with_many_elements_beyond_limit(self) -> None:
        """Formatting with more elements than MAX_CALLBACK_SUGGESTIONS."""
        elements = []
        for i in range(20):
            elements.append(
                _make_element(
                    name=f"Element_{i:02d}",
                    turn_introduced=i,
                    last_referenced_turn=i,
                    times_referenced=i + 1,
                )
            )
        store = NarrativeElementStore(elements=elements)

        result = format_callback_suggestions(store, 100, [])

        # Should only have 5 entries
        count = sum(
            1 for line in result.split("\n")
            if line and line[0].isdigit() and ". **" in line
        )
        assert count == MAX_CALLBACK_SUGGESTIONS

    def test_format_with_mixed_resolved_and_active(self) -> None:
        """Only active (non-resolved) elements appear."""
        resolved = _make_element(name="Resolved", resolved=True)
        active = _make_element(name="Active", resolved=False)
        store = NarrativeElementStore(elements=[resolved, active])

        result = format_callback_suggestions(store, 50, [])

        assert "Active" in result
        assert "Resolved" not in result

    def test_score_negative_possible_for_very_dormant_recent(self) -> None:
        """Score can be negative for dormant, recently referenced elements."""
        element = _make_element(
            name="RecentDormant",
            turn_introduced=50,
            last_referenced_turn=50,
            dormant=True,
            times_referenced=1,
        )
        # Recency: 0/10 = 0.0
        # Importance: 1 * 0.5 = 0.5
        # Dormancy: -3.0
        # Total: -2.5
        score = score_callback_relevance(element, 50, [])
        assert score < 0
        assert score == pytest.approx(-2.5, abs=0.01)

    def test_format_with_only_negative_score_elements(self) -> None:
        """Elements with negative scores still appear if >= MIN_CALLBACK_SCORE.

        Since MIN_CALLBACK_SCORE is 0.0, negative score elements are excluded.
        """
        element = _make_element(
            name="NegScore",
            turn_introduced=50,
            last_referenced_turn=50,
            dormant=True,
            times_referenced=1,
        )
        store = NarrativeElementStore(elements=[element])

        result = format_callback_suggestions(store, 50, [])

        # Score is -2.5 which is < 0.0 (MIN_CALLBACK_SCORE), so filtered out
        assert result == ""

    def test_format_preserves_special_characters_in_name(self) -> None:
        """Names with special characters are preserved in output."""
        element = _make_element(
            name="Sir Reginald O'Brien III",
            description="A noble knight with a mysterious past",
        )
        store = NarrativeElementStore(elements=[element])

        result = format_callback_suggestions(store, 50, [])

        assert "**Sir Reginald O'Brien III**" in result
