"""Acceptance tests for Story 5.4: Cross-Session Memory & Character Facts.

These tests verify all acceptance criteria for Story 5.4:
- AC1: long_term_summary loaded from previous session on start
- AC2: Agents can reference events from previous sessions
- AC3: Character facts persist across sessions and are always in context
- AC4: Relationships established in earlier sessions affect later responses
- AC5: "While you were away" summary draws from cross-session memories
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from models import (
    AgentMemory,
    CharacterConfig,
    CharacterFacts,
    DMConfig,
    GameConfig,
    GameState,
    create_character_facts_from_config,
    populate_game_state,
)


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Path:
    """Create a temporary campaigns directory for testing."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    return campaigns_dir


# =============================================================================
# AC1: long_term_summary loaded from previous session on start
# =============================================================================


class TestAC1LongTermSummaryPersistence:
    """AC1: Given a campaign spans multiple sessions,
    When a new session starts,
    Then each agent's long_term_summary is loaded from the previous session (FR14).
    """

    def test_long_term_summary_persists_across_sessions(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that long_term_summary from session 1 is available in session 2."""
        from persistence import (
            initialize_session_with_previous_memories,
            save_checkpoint,
        )

        # Session 1 state with long_term_summary
        session1_state: GameState = {
            "ground_truth_log": ["[dm] The party defeated the goblin king."],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(
                    long_term_summary="The party befriended a goblin named Skrix who now follows them."
                ),
                "rogue": AgentMemory(
                    long_term_summary="I discovered a secret passage and found a magical dagger."
                ),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        # Save session 1 checkpoint
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(session1_state, "001", 20, update_metadata=False)

        # Create fresh session 2 state
        session2_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),  # Fresh, empty
                "rogue": AgentMemory(),  # Fresh, empty
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 2,
            "session_id": "002",
        }

        # Initialize session 2 with memories from session 1
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories(
                "001", "002", session2_state
            )

        # AC1: long_term_summary should be loaded from previous session
        assert "goblin named Skrix" in result["agent_memories"]["dm"].long_term_summary
        assert "magical dagger" in result["agent_memories"]["rogue"].long_term_summary

    def test_short_term_buffer_starts_empty_in_new_session(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that short_term_buffer is cleared when starting new session."""
        from persistence import (
            initialize_session_with_previous_memories,
            save_checkpoint,
        )

        session1_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(
                    long_term_summary="Previous story",
                    short_term_buffer=["Old event 1", "Old event 2"],
                ),
                "rogue": AgentMemory(
                    short_term_buffer=["Rogue old event"],
                ),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(session1_state, "001", 15, update_metadata=False)

        session2_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 2,
            "session_id": "002",
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories(
                "001", "002", session2_state
            )

        # Short-term buffer should be empty in new session
        assert result["agent_memories"]["dm"].short_term_buffer == []
        assert result["agent_memories"]["rogue"].short_term_buffer == []
        # But long-term summary should be preserved
        assert result["agent_memories"]["dm"].long_term_summary == "Previous story"


# =============================================================================
# AC2: Agents can reference events from previous sessions
# =============================================================================


class TestAC2AgentCanReferencePreviousSessions:
    """AC2: Given the long_term_summary contains specific events,
    When those events are relevant,
    Then an agent might reference them (via context inclusion).
    """

    def test_dm_context_includes_long_term_summary_with_skrix(self) -> None:
        """Test DM context includes long_term_summary mentioning Skrix."""
        from agents import _build_dm_context

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(
                    long_term_summary="The party befriended a goblin named Skrix. "
                    "Skrix knows the secret entrance to the mountain fortress."
                ),
                "rogue": AgentMemory(),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 2,
            "session_id": "002",
        }

        with patch("streamlit.session_state", {}):
            context = _build_dm_context(state)

        # DM context should include information about Skrix
        assert "Skrix" in context
        assert "mountain fortress" in context or "goblin" in context

    def test_pc_context_includes_own_long_term_summary(self) -> None:
        """Test PC agent can reference their own previous session memories."""
        from agents import _build_pc_context

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "rogue",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(
                    long_term_summary="In session 1, I made a deal with the thieves guild. "
                    "Their leader, Vex, owes me a favor."
                ),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 2,
            "session_id": "002",
        }

        context = _build_pc_context(state, "rogue")

        # PC should see their own memories from previous sessions
        assert "thieves guild" in context
        assert "Vex" in context


# =============================================================================
# AC3: Character facts persist across sessions and are included in context
# =============================================================================


class TestAC3CharacterFactsPersistence:
    """AC3: Given character facts (name, class, key traits, relationships),
    When stored in AgentMemory,
    Then they persist across sessions (FR15)
    And are always included in the agent's context.
    """

    def test_character_facts_serialize_and_deserialize(self) -> None:
        """Test CharacterFacts survive JSON roundtrip (persistence mechanism)."""
        from persistence import deserialize_game_state, serialize_game_state

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sardonic wit", "Trust issues"],
            relationships={"Theros": "Trusted ally"},
            notable_events=["Stole the enchanted dagger"],
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(
                    long_term_summary="My journey",
                    character_facts=facts,
                ),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        # Serialize and deserialize
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        # Character facts should be fully restored
        restored_facts = restored["agent_memories"]["rogue"].character_facts
        assert restored_facts is not None
        assert restored_facts.name == "Shadowmere"
        assert restored_facts.character_class == "Rogue"
        assert "Sardonic wit" in restored_facts.key_traits
        assert "Theros" in restored_facts.relationships
        assert "Stole the enchanted dagger" in restored_facts.notable_events

    def test_character_facts_persist_through_checkpoint_cycle(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test CharacterFacts persist through save/load checkpoint cycle."""
        from persistence import load_checkpoint, save_checkpoint

        facts = CharacterFacts(
            name="Theros",
            character_class="Fighter",
            key_traits=["Brave", "Honorable"],
            relationships={"Shadowmere": "Fellow adventurer"},
            notable_events=["Defended the village gate alone"],
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "fighter": AgentMemory(character_facts=facts),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 5, update_metadata=False)
            loaded = load_checkpoint("001", 5)

        assert loaded is not None
        loaded_facts = loaded["agent_memories"]["fighter"].character_facts
        assert loaded_facts is not None
        assert loaded_facts.name == "Theros"
        assert loaded_facts.relationships.get("Shadowmere") == "Fellow adventurer"

    def test_character_facts_included_in_pc_context(self) -> None:
        """Test CharacterFacts are always included in PC's context."""
        from agents import _build_pc_context

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sardonic wit", "Trust issues", "Observant"],
            relationships={"Marcus": "Rival merchant"},
            notable_events=["Found the hidden passage"],
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "rogue",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(character_facts=facts),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        context = _build_pc_context(state, "rogue")

        # Character facts should be in context
        assert "Shadowmere" in context
        assert "Rogue" in context
        assert "Sardonic wit" in context
        assert "Marcus" in context

    def test_all_character_facts_included_in_dm_context(self) -> None:
        """Test DM context includes CharacterFacts for ALL party members."""
        from agents import _build_dm_context

        rogue_facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            relationships={"Theros": "Ally"},
        )
        fighter_facts = CharacterFacts(
            name="Theros",
            character_class="Fighter",
            relationships={"Shadowmere": "Fellow adventurer"},
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue", "fighter"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(character_facts=rogue_facts),
                "fighter": AgentMemory(character_facts=fighter_facts),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        with patch("streamlit.session_state", {}):
            context = _build_dm_context(state)

        # DM should see all characters' facts
        assert "Shadowmere" in context
        assert "Theros" in context
        assert "Rogue" in context
        assert "Fighter" in context


# =============================================================================
# AC4: Relationships established in earlier sessions affect later responses
# =============================================================================


class TestAC4RelationshipsAffectFutureSessions:
    """AC4: Given the rogue established a rivalry with a merchant in session 2,
    When that merchant appears in session 5,
    Then the rogue's response reflects that history.
    """

    def test_relationship_persists_across_sessions(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that relationship from session 2 is available in session 5."""
        from persistence import (
            initialize_session_with_previous_memories,
            save_checkpoint,
        )

        # Session 2 state: Rogue establishes rivalry with Marcus
        session2_facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            relationships={"Marcus the Merchant": "Rival - tried to cheat me"},
        )

        session2_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(character_facts=session2_facts),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 2,
            "session_id": "002",
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(session2_state, "002", 10, update_metadata=False)

        # Session 5 state: Fresh start
        session5_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 5,
            "session_id": "005",
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories(
                "002", "005", session5_state
            )

        # In session 5, the rogue should know about Marcus rivalry
        facts = result["agent_memories"]["rogue"].character_facts
        assert facts is not None
        assert "Marcus the Merchant" in facts.relationships
        assert "Rival" in facts.relationships["Marcus the Merchant"]

    def test_relationship_appears_in_pc_context_for_future_sessions(self) -> None:
        """Test that established relationships appear in PC's context."""
        from agents import _build_pc_context

        # Rogue with relationship from previous session
        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            relationships={
                "Marcus the Merchant": "Rival - tried to cheat me in session 2"
            },
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "rogue",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(character_facts=facts),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 5,
            "session_id": "005",
        }

        context = _build_pc_context(state, "rogue")

        # The relationship with Marcus should be visible in context
        assert "Marcus" in context
        assert "Rival" in context or "cheat" in context


# =============================================================================
# AC5: "While you were away" draws from cross-session memories
# =============================================================================


class TestAC5RecapIncludesCrossSessionMemories:
    """AC5: Given cross-session memory loading,
    When a session resumes,
    Then the "While you were away..." summary draws from these memories
    And agents can reference past sessions naturally.
    """

    def test_recap_includes_long_term_summary(self, temp_campaigns_dir: Path) -> None:
        """Test recap summary includes long_term_summary from previous session."""
        from persistence import generate_recap_summary, save_checkpoint

        state: GameState = {
            "ground_truth_log": ["[dm] The adventure continues."],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(
                    long_term_summary="Last session: The party defeated the goblin king and befriended Skrix."
                ),
                "rogue": AgentMemory(),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 2,
            "session_id": "002",
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "002", 1, update_metadata=False)
            recap = generate_recap_summary("002", include_cross_session=True)

        assert recap is not None
        # Recap should include story context
        assert "goblin king" in recap or "Skrix" in recap or "Story So Far" in recap

    def test_recap_includes_character_relationships(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test recap includes character relationships from CharacterFacts."""
        from persistence import generate_recap_summary, save_checkpoint

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            relationships={
                "Theros": "Trusted ally who saved my life",
                "Lord Blackwood": "Enemy - I stole from him",
            },
        )

        state: GameState = {
            "ground_truth_log": ["[dm] A new day dawns."],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(character_facts=facts),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 5, update_metadata=False)
            recap = generate_recap_summary("001", include_cross_session=True)

        assert recap is not None
        # Recap should include relationships
        assert "Theros" in recap or "Lord Blackwood" in recap


# =============================================================================
# Edge Cases and Additional Acceptance Tests
# =============================================================================


class TestEdgeCases:
    """Edge case tests for Story 5.4."""

    def test_first_session_has_no_previous_memories(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test first session works correctly with no previous memories."""
        from persistence import initialize_session_with_previous_memories

        first_session_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="Fresh game"),
                "rogue": AgentMemory(),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        # No previous session exists
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories(
                "nonexistent", "001", first_session_state
            )

        # State should be returned unchanged
        assert result["agent_memories"]["dm"].long_term_summary == "Fresh game"

    def test_new_session_populates_character_facts(self) -> None:
        """Test that populate_game_state creates CharacterFacts for all characters."""
        state = populate_game_state(include_sample_messages=False)

        # Each PC should have CharacterFacts
        for char_name in state["characters"]:
            memory = state["agent_memories"][char_name]
            assert memory.character_facts is not None
            char_config = state["characters"][char_name]
            assert memory.character_facts.name == char_config.name
            assert memory.character_facts.character_class == char_config.character_class

        # DM should not have CharacterFacts
        assert state["agent_memories"]["dm"].character_facts is None

    def test_create_character_facts_from_config_function(self) -> None:
        """Test create_character_facts_from_config creates proper facts."""
        config = CharacterConfig(
            name="Lyra",
            character_class="Wizard",
            personality="Curious and analytical",
            color="#7B68B8",
        )

        facts = create_character_facts_from_config(config)

        assert facts.name == "Lyra"
        assert facts.character_class == "Wizard"
        assert facts.key_traits == []  # Initially empty
        assert facts.relationships == {}  # Initially empty
        assert facts.notable_events == []  # Initially empty

    def test_corrupted_previous_session_returns_new_state_unchanged(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that corrupted previous session data returns new state unchanged."""

        from persistence import (
            ensure_session_dir,
            get_checkpoint_path,
            initialize_session_with_previous_memories,
        )

        # Create a corrupted checkpoint file
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            ensure_session_dir("001")
            checkpoint_path = get_checkpoint_path("001", 5)
            # Write invalid JSON
            checkpoint_path.write_text("{ invalid json }", encoding="utf-8")

        # New session state
        new_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="New session"),
                "rogue": AgentMemory(),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 2,
            "session_id": "002",
            "summarization_in_progress": False,
        }

        # Should return new_state unchanged (graceful degradation)
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories("001", "002", new_state)

        # State should be unchanged - corrupted data doesn't propagate
        assert result["agent_memories"]["dm"].long_term_summary == "New session"
        assert result["agent_memories"]["rogue"].character_facts is None
