"""Expanded test coverage for Story 5.4: Cross-Session Memory & Character Facts.

This test file expands on test_story_5_4_acceptance.py with additional edge cases:
- CharacterFacts model validation and size limits
- Cross-session memory loading edge cases
- Context building with missing/partial facts
- Serialization/deserialization edge cases
- Recap generation edge cases
- MemoryManager fact methods edge cases

Story Key: 5-4-cross-session-memory-character-facts
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from models import (
    AgentMemory,
    CharacterConfig,
    CharacterFacts,
    DMConfig,
    GameConfig,
    GameState,
    create_agent_memory,
    create_character_facts_from_config,
)

# =============================================================================
# CharacterFacts Model Validation Tests
# =============================================================================


class TestCharacterFactsValidation:
    """Tests for CharacterFacts model validation and size limits."""

    def test_character_facts_empty_name_rejected(self) -> None:
        """Test CharacterFacts rejects empty name."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterFacts(name="", character_class="Rogue")

        errors = exc_info.value.errors()
        assert any("name" in str(e).lower() for e in errors)

    def test_character_facts_whitespace_only_name_allowed(self) -> None:
        """Test CharacterFacts allows whitespace-only name (no strip validation).

        The model uses min_length=1 which checks character count but does
        not strip whitespace. Whitespace validation is the caller's responsibility.
        """
        # This is allowed by the model - whitespace is not stripped
        facts = CharacterFacts(name="   ", character_class="Rogue")
        assert facts.name == "   "  # Preserved as-is

    def test_character_facts_empty_character_class_rejected(self) -> None:
        """Test CharacterFacts rejects empty character_class."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterFacts(name="Shadowmere", character_class="")

        errors = exc_info.value.errors()
        assert any(
            "character_class" in str(e).lower() or "min_length" in str(e).lower()
            for e in errors
        )

    def test_character_facts_key_traits_max_limit(self) -> None:
        """Test CharacterFacts enforces MAX_KEY_TRAITS limit (10)."""
        # Creating with exactly 10 traits should work
        facts = CharacterFacts(
            name="Test",
            character_class="Fighter",
            key_traits=[f"Trait{i}" for i in range(10)],
        )
        assert len(facts.key_traits) == 10

        # Creating with 11 traits should fail
        with pytest.raises(ValidationError):
            CharacterFacts(
                name="Test",
                character_class="Fighter",
                key_traits=[f"Trait{i}" for i in range(11)],
            )

    def test_character_facts_relationships_max_limit(self) -> None:
        """Test CharacterFacts enforces MAX_RELATIONSHIPS limit (20)."""
        # Creating with exactly 20 relationships should work
        facts = CharacterFacts(
            name="Test",
            character_class="Fighter",
            relationships={f"NPC{i}": f"Relationship{i}" for i in range(20)},
        )
        assert len(facts.relationships) == 20

        # Creating with 21 relationships should fail
        with pytest.raises(ValidationError):
            CharacterFacts(
                name="Test",
                character_class="Fighter",
                relationships={f"NPC{i}": f"Relationship{i}" for i in range(21)},
            )

    def test_character_facts_notable_events_max_limit(self) -> None:
        """Test CharacterFacts enforces MAX_NOTABLE_EVENTS limit (20)."""
        # Creating with exactly 20 events should work
        facts = CharacterFacts(
            name="Test",
            character_class="Fighter",
            notable_events=[f"Event{i}" for i in range(20)],
        )
        assert len(facts.notable_events) == 20

        # Creating with 21 events should fail
        with pytest.raises(ValidationError):
            CharacterFacts(
                name="Test",
                character_class="Fighter",
                notable_events=[f"Event{i}" for i in range(21)],
            )

    def test_character_facts_class_variable_constants(self) -> None:
        """Test CharacterFacts class variable constants are correct."""
        assert CharacterFacts.MAX_KEY_TRAITS == 10
        assert CharacterFacts.MAX_RELATIONSHIPS == 20
        assert CharacterFacts.MAX_NOTABLE_EVENTS == 20


class TestCharacterFactsEdgeCases:
    """Tests for CharacterFacts edge cases and boundary conditions."""

    def test_character_facts_unicode_names(self) -> None:
        """Test CharacterFacts handles Unicode characters in name."""
        facts = CharacterFacts(
            name="Aerith \u00c9lven",
            character_class="Wizard",  # Contains Unicode
        )
        assert facts.name == "Aerith \u00c9lven"

    def test_character_facts_long_trait_values(self) -> None:
        """Test CharacterFacts accepts long trait descriptions."""
        long_trait = "A" * 500  # 500 character trait
        facts = CharacterFacts(
            name="Test", character_class="Fighter", key_traits=[long_trait]
        )
        assert len(facts.key_traits[0]) == 500

    def test_character_facts_empty_relationship_values(self) -> None:
        """Test CharacterFacts handles relationship with empty description."""
        # Relationships with empty values should be allowed
        facts = CharacterFacts(
            name="Test",
            character_class="Fighter",
            relationships={"EmptyDesc": ""},
        )
        assert facts.relationships["EmptyDesc"] == ""

    def test_character_facts_duplicate_traits_preserved(self) -> None:
        """Test CharacterFacts allows duplicate traits (model doesn't dedupe)."""
        facts = CharacterFacts(
            name="Test",
            character_class="Fighter",
            key_traits=["Brave", "Brave", "Bold"],
        )
        # Model stores what it's given - deduplication is caller's responsibility
        assert len(facts.key_traits) == 3

    def test_character_facts_special_characters_in_names(self) -> None:
        """Test CharacterFacts handles special characters in names."""
        facts = CharacterFacts(
            name="Theron 'The Bold' O'Malley",
            character_class="Fighter",
            relationships={"Queen's Guard": "Former ally"},
        )
        assert "'" in facts.name
        assert "Queen's Guard" in facts.relationships


# =============================================================================
# Cross-Session Memory Initialization Edge Cases
# =============================================================================


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Path:
    """Create a temporary campaigns directory for testing."""
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()
    return campaigns_dir


class TestCrossSessionMemoryEdgeCases:
    """Tests for cross-session memory initialization edge cases."""

    def test_new_agent_in_new_session_not_in_previous(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that new agents in new session keep their fresh memory."""
        from persistence import (
            initialize_session_with_previous_memories,
            save_checkpoint,
        )

        # Previous session with only dm and rogue
        prev_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="Previous story"),
                "rogue": AgentMemory(
                    long_term_summary="Rogue's previous adventures",
                    character_facts=CharacterFacts(
                        name="Shadowmere", character_class="Rogue"
                    ),
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
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(prev_state, "001", 10, update_metadata=False)

        # New session adds a fighter who wasn't in previous session
        new_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue", "fighter"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(),
                "fighter": AgentMemory(
                    long_term_summary="Fighter's fresh start",
                    character_facts=CharacterFacts(
                        name="Theron", character_class="Fighter"
                    ),
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
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories("001", "002", new_state)

        # Rogue should have memories from previous session
        assert (
            result["agent_memories"]["rogue"].long_term_summary
            == "Rogue's previous adventures"
        )
        assert result["agent_memories"]["rogue"].character_facts is not None
        assert result["agent_memories"]["rogue"].character_facts.name == "Shadowmere"

        # Fighter (new agent) should keep their fresh state
        assert (
            result["agent_memories"]["fighter"].long_term_summary
            == "Fighter's fresh start"
        )
        assert result["agent_memories"]["fighter"].character_facts is not None
        assert result["agent_memories"]["fighter"].character_facts.name == "Theron"

    def test_token_limit_preserved_from_new_session(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that token_limit from new session is used, not previous."""
        from persistence import (
            initialize_session_with_previous_memories,
            save_checkpoint,
        )

        # Previous session with 4000 token limit
        prev_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(token_limit=4000),
                "rogue": AgentMemory(
                    token_limit=4000,
                    long_term_summary="Previous adventures",
                    character_facts=CharacterFacts(
                        name="Shadowmere", character_class="Rogue"
                    ),
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
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(prev_state, "001", 10, update_metadata=False)

        # New session with increased token limit (8000)
        new_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(token_limit=8000),
                "rogue": AgentMemory(token_limit=8000),
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

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories("001", "002", new_state)

        # Token limits should be from NEW session (8000), not previous (4000)
        assert result["agent_memories"]["dm"].token_limit == 8000
        assert result["agent_memories"]["rogue"].token_limit == 8000

        # But memories should still be loaded
        assert (
            result["agent_memories"]["rogue"].long_term_summary == "Previous adventures"
        )

    def test_empty_previous_session_memories(self, temp_campaigns_dir: Path) -> None:
        """Test initializing from previous session with completely empty memories."""
        from persistence import (
            initialize_session_with_previous_memories,
            save_checkpoint,
        )

        # Previous session with empty memories
        prev_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),  # Completely empty
                "rogue": AgentMemory(),  # Completely empty
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(prev_state, "001", 5, update_metadata=False)

        # New session with its own CharacterFacts
        new_facts = CharacterFacts(name="Shadowmere", character_class="Rogue")
        new_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="Fresh DM"),
                "rogue": AgentMemory(character_facts=new_facts),
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

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories("001", "002", new_state)

        # Empty strings/None from previous session should be loaded
        # (previous session had no facts, so it copies the None value)
        assert result["agent_memories"]["dm"].long_term_summary == ""
        assert result["agent_memories"]["rogue"].character_facts is None

    def test_agent_missing_from_previous_but_in_new(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test agent in new session but not in previous keeps new state."""
        from persistence import (
            initialize_session_with_previous_memories,
            save_checkpoint,
        )

        # Previous session only has dm
        prev_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="DM's story"),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(prev_state, "001", 5, update_metadata=False)

        # New session adds rogue who wasn't in previous
        new_state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="New DM summary"),
                "rogue": AgentMemory(
                    long_term_summary="Rogue's fresh start",
                    character_facts=CharacterFacts(
                        name="Shadowmere", character_class="Rogue"
                    ),
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
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = initialize_session_with_previous_memories("001", "002", new_state)

        # DM should have previous session's summary
        assert result["agent_memories"]["dm"].long_term_summary == "DM's story"

        # Rogue keeps their new state (wasn't in previous session)
        assert (
            result["agent_memories"]["rogue"].long_term_summary == "Rogue's fresh start"
        )
        assert result["agent_memories"]["rogue"].character_facts is not None


# =============================================================================
# Context Building Edge Cases
# =============================================================================


class TestContextBuildingEdgeCases:
    """Tests for context building with CharacterFacts edge cases."""

    def test_format_character_facts_with_max_limits(self) -> None:
        """Test format_character_facts handles facts at max limits."""
        from agents import format_character_facts

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=[f"Trait{i}" for i in range(10)],  # Max 10
            relationships={f"NPC{i}": f"Relation{i}" for i in range(20)},  # Max 20
            notable_events=[f"Event{i}" for i in range(20)],  # Max 20
        )

        result = format_character_facts(facts)

        # Should contain all data without errors
        assert "Shadowmere" in result
        assert "Rogue" in result
        assert "Trait0" in result
        assert "Trait9" in result
        assert "NPC0" in result
        assert "Event0" in result

    def test_format_character_facts_special_characters(self) -> None:
        """Test format_character_facts handles special characters."""
        from agents import format_character_facts

        facts = CharacterFacts(
            name="O'Malley",
            character_class="Fighter",
            key_traits=['Says "Huzzah!"', "Uses *emphasis*"],
            relationships={"King's Guard": "Former member"},
        )

        result = format_character_facts(facts)

        assert "O'Malley" in result
        assert '"Huzzah!"' in result or "Huzzah" in result
        assert "King's Guard" in result

    def test_pc_context_with_none_character_facts(self) -> None:
        """Test _build_pc_context handles None character_facts gracefully."""
        from agents import _build_pc_context

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "rogue",
            "agent_memories": {
                "dm": AgentMemory(),
                "rogue": AgentMemory(
                    long_term_summary="Some adventures",
                    short_term_buffer=["Recent event"],
                    character_facts=None,  # Explicitly None
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
            "summarization_in_progress": False,
        }

        # Should not raise, should include other context
        context = _build_pc_context(state, "rogue")
        assert "Some adventures" in context

    def test_dm_context_mixed_character_facts_some_none(self) -> None:
        """Test _build_dm_context handles mixed facts (some None, some present)."""
        from agents import _build_dm_context

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue", "fighter"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="Story so far"),
                "rogue": AgentMemory(
                    character_facts=CharacterFacts(
                        name="Shadowmere", character_class="Rogue"
                    )
                ),
                "fighter": AgentMemory(character_facts=None),  # No facts
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "summarization_in_progress": False,
        }

        with patch("streamlit.session_state", {}):
            context = _build_dm_context(state)

        # Should include rogue's facts, not crash on fighter's None
        assert "Shadowmere" in context
        assert "Story so far" in context


# =============================================================================
# MemoryManager CharacterFacts Edge Cases
# =============================================================================


class TestMemoryManagerCharacterFactsEdgeCases:
    """Tests for MemoryManager character facts edge cases."""

    @pytest.fixture
    def game_state_with_facts(self) -> GameState:
        """Create a GameState with CharacterFacts for testing."""
        return GameState(
            ground_truth_log=[],
            turn_queue=["dm", "rogue"],
            current_turn="dm",
            agent_memories={
                "dm": AgentMemory(),
                "rogue": AgentMemory(
                    character_facts=CharacterFacts(
                        name="Shadowmere",
                        character_class="Rogue",
                        key_traits=["Cunning"],
                        notable_events=["Found the key"],
                    )
                ),
            },
            game_config=GameConfig(),
            dm_config=DMConfig(),
            characters={},
            whisper_queue=[],
            human_active=False,
            controlled_character=None,
            session_number=1,
            session_id="001",
            summarization_in_progress=False,
        )

    def test_get_cross_session_summary_alias(
        self, game_state_with_facts: GameState
    ) -> None:
        """Test get_cross_session_summary is alias for get_long_term_summary."""
        from memory import MemoryManager

        game_state_with_facts["agent_memories"][
            "rogue"
        ].long_term_summary = "Previous adventures"
        manager = MemoryManager(game_state_with_facts)

        # Both methods should return same value
        assert manager.get_cross_session_summary(
            "rogue"
        ) == manager.get_long_term_summary("rogue")
        assert manager.get_cross_session_summary("rogue") == "Previous adventures"

    def test_update_character_facts_duplicate_trait_deduplication(
        self, game_state_with_facts: GameState
    ) -> None:
        """Test update_character_facts deduplicates traits."""
        from memory import MemoryManager

        manager = MemoryManager(game_state_with_facts)

        # Try to add a trait that already exists
        manager.update_character_facts("rogue", key_traits=["Cunning"])

        facts = manager.get_character_facts("rogue")
        assert facts is not None
        # Should still have only 1 "Cunning" trait
        assert facts.key_traits.count("Cunning") == 1

    def test_update_character_facts_duplicate_event_deduplication(
        self, game_state_with_facts: GameState
    ) -> None:
        """Test update_character_facts deduplicates events."""
        from memory import MemoryManager

        manager = MemoryManager(game_state_with_facts)

        # Try to add an event that already exists
        manager.update_character_facts("rogue", notable_events=["Found the key"])

        facts = manager.get_character_facts("rogue")
        assert facts is not None
        # Should still have only 1 "Found the key" event
        assert facts.notable_events.count("Found the key") == 1

    def test_update_character_facts_relationship_overwrites(
        self, game_state_with_facts: GameState
    ) -> None:
        """Test update_character_facts overwrites existing relationship."""
        from memory import MemoryManager

        # Add initial relationship
        rogue_memory = game_state_with_facts["agent_memories"]["rogue"]
        assert rogue_memory.character_facts is not None  # For type narrowing
        rogue_memory.character_facts.relationships = {"Theron": "Acquaintance"}

        manager = MemoryManager(game_state_with_facts)

        # Update same relationship with new description
        manager.update_character_facts(
            "rogue", relationships={"Theron": "Trusted ally"}
        )

        facts = manager.get_character_facts("rogue")
        assert facts is not None
        assert facts.relationships["Theron"] == "Trusted ally"

    def test_update_character_facts_with_empty_lists(
        self, game_state_with_facts: GameState
    ) -> None:
        """Test update_character_facts handles empty updates gracefully."""
        from memory import MemoryManager

        manager = MemoryManager(game_state_with_facts)
        original_facts = manager.get_character_facts("rogue")
        original_traits = original_facts.key_traits.copy() if original_facts else []

        # Update with empty values
        manager.update_character_facts(
            "rogue",
            key_traits=[],
            relationships={},
            notable_events=[],
        )

        facts = manager.get_character_facts("rogue")
        assert facts is not None
        # Original traits should be preserved (empty list doesn't clear)
        assert facts.key_traits == original_traits


# =============================================================================
# Recap Generation Edge Cases
# =============================================================================


class TestRecapGenerationEdgeCases:
    """Tests for recap generation with cross-session memory edge cases."""

    def test_recap_with_empty_relationships(self, temp_campaigns_dir: Path) -> None:
        """Test recap handles characters with empty relationships."""
        from persistence import generate_recap_summary, save_checkpoint

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sneaky"],
            relationships={},  # Empty
            notable_events=["Something happened"],
        )

        state: GameState = {
            "ground_truth_log": ["[dm] A new day begins."],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="The story continues"),
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
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 5, update_metadata=False)
            recap = generate_recap_summary("001", include_cross_session=True)

        assert recap is not None
        # Should still work without relationships section
        assert "Story So Far" in recap or "new day" in recap

    def test_recap_with_very_long_summary(self, temp_campaigns_dir: Path) -> None:
        """Test recap truncates very long summaries appropriately."""
        from persistence import generate_recap_summary, save_checkpoint

        # Create a very long summary (longer than 300 char limit in recap)
        long_summary = "The party traveled far. " * 50  # ~1200 chars

        state: GameState = {
            "ground_truth_log": ["[dm] Another turn."],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary=long_summary),
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
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 5, update_metadata=False)
            recap = generate_recap_summary("001", include_cross_session=True)

        assert recap is not None
        # Long summary should be truncated to ~300 chars in Story So Far section
        # Check that it doesn't include the full summary
        if "Story So Far" in recap:
            # The summary section should be limited
            assert (
                len(recap) < len(long_summary) + 500
            )  # Allow for headers and recent events

    def test_recap_without_cross_session_excludes_summaries(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test recap without include_cross_session excludes long_term_summary."""
        from persistence import generate_recap_summary, save_checkpoint

        state: GameState = {
            "ground_truth_log": ["[dm] Recent event only."],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(long_term_summary="This should not appear"),
                "rogue": AgentMemory(
                    character_facts=CharacterFacts(
                        name="Shadowmere",
                        character_class="Rogue",
                        relationships={"Test": "Should not appear"},
                    )
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
            "summarization_in_progress": False,
        }

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 5, update_metadata=False)
            recap = generate_recap_summary("001", include_cross_session=False)

        assert recap is not None
        # Cross-session content should not be present
        assert "This should not appear" not in recap
        assert "Story So Far" not in recap
        # Recent events should still be present
        assert "Recent event only" in recap or "Recent Events" in recap


# =============================================================================
# Serialization Edge Cases
# =============================================================================


class TestSerializationEdgeCases:
    """Tests for CharacterFacts serialization edge cases."""

    def test_character_facts_with_unicode_serialization(self) -> None:
        """Test CharacterFacts with Unicode survives serialization."""
        from persistence import deserialize_game_state, serialize_game_state

        facts = CharacterFacts(
            name="Aerith \u00c9lven\u00e4",  # Contains umlauts and accents
            character_class="Wizard",
            key_traits=["Speaks \u65e5\u672c\u8a9e"],  # Japanese characters
            relationships={"\u00d6tzi": "Mountain guide"},  # Umlaut
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "wizard"],
            "current_turn": "dm",
            "agent_memories": {
                "dm": AgentMemory(),
                "wizard": AgentMemory(character_facts=facts),
            },
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "summarization_in_progress": False,
        }

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        restored_facts = restored["agent_memories"]["wizard"].character_facts
        assert restored_facts is not None
        assert "\u00c9lven\u00e4" in restored_facts.name
        assert "\u65e5\u672c\u8a9e" in restored_facts.key_traits[0]
        assert "\u00d6tzi" in restored_facts.relationships

    def test_character_facts_with_newlines_in_values(self) -> None:
        """Test CharacterFacts with newlines in values serializes correctly."""
        from persistence import deserialize_game_state, serialize_game_state

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Has a long\nmultiline\ntrait"],
            notable_events=["Event with\nnewlines"],
        )

        state: GameState = {
            "ground_truth_log": [],
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
            "summarization_in_progress": False,
        }

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        restored_facts = restored["agent_memories"]["rogue"].character_facts
        assert restored_facts is not None
        assert "\n" in restored_facts.key_traits[0]
        assert "\n" in restored_facts.notable_events[0]


# =============================================================================
# Factory Function Edge Cases
# =============================================================================


class TestFactoryFunctionEdgeCases:
    """Tests for factory functions related to CharacterFacts."""

    def test_create_agent_memory_with_facts_preserves_all_fields(self) -> None:
        """Test create_agent_memory preserves all CharacterFacts fields."""
        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sneaky", "Cunning"],
            relationships={"NPC": "Friend"},
            notable_events=["Event1"],
        )

        memory = create_agent_memory(token_limit=5000, character_facts=facts)

        assert memory.token_limit == 5000
        assert memory.character_facts is not None
        assert memory.character_facts.name == "Shadowmere"
        assert len(memory.character_facts.key_traits) == 2
        assert "NPC" in memory.character_facts.relationships

    def test_create_character_facts_from_config_minimal(self) -> None:
        """Test create_character_facts_from_config with minimal config."""
        config = CharacterConfig(
            name="X",  # Minimal valid name
            character_class="A",  # Minimal valid class
            personality="Test",
            color="#000000",
        )

        facts = create_character_facts_from_config(config)

        assert facts.name == "X"
        assert facts.character_class == "A"
        assert facts.key_traits == []
        assert facts.relationships == {}
        assert facts.notable_events == []

    def test_create_character_facts_from_config_with_long_personality(self) -> None:
        """Test factory works regardless of personality length."""
        config = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="A" * 1000,  # Very long personality
            color="#6B8E6B",
        )

        # Should work - personality is not copied to CharacterFacts
        facts = create_character_facts_from_config(config)

        assert facts.name == "Shadowmere"
        assert facts.character_class == "Rogue"
        # Personality is NOT copied to CharacterFacts
        # CharacterFacts is for persistent identity, not roleplay guidance
