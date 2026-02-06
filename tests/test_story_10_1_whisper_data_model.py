"""Tests for Story 10-1: Whisper Data Model.

Tests the Whisper and AgentSecrets models for the DM whisper system,
including validation, serialization, and checkpoint integration.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from models import (
    AgentSecrets,
    Whisper,
    create_initial_game_state,
    create_whisper,
    populate_game_state,
)
from persistence import (
    deserialize_game_state,
    load_checkpoint,
    save_checkpoint,
    serialize_game_state,
)

# =============================================================================
# Whisper Model Tests
# =============================================================================


class TestWhisperModel:
    """Tests for the Whisper Pydantic model."""

    def test_whisper_creation_with_required_fields(self) -> None:
        """Test Whisper can be created with all required fields."""
        whisper = Whisper(
            id="abc123",
            from_agent="dm",
            to_agent="fighter",
            content="A secret message",
            turn_created=5,
        )

        assert whisper.id == "abc123"
        assert whisper.from_agent == "dm"
        assert whisper.to_agent == "fighter"
        assert whisper.content == "A secret message"
        assert whisper.turn_created == 5
        assert whisper.revealed is False
        assert whisper.turn_revealed is None

    def test_whisper_creation_with_revealed(self) -> None:
        """Test Whisper can be created with revealed status."""
        whisper = Whisper(
            id="abc123",
            from_agent="dm",
            to_agent="rogue",
            content="The treasure is hidden",
            turn_created=3,
            revealed=True,
            turn_revealed=7,
        )

        assert whisper.revealed is True
        assert whisper.turn_revealed == 7

    def test_whisper_from_agent_dm_valid(self) -> None:
        """Test Whisper accepts 'dm' as from_agent."""
        whisper = Whisper(
            id="test",
            from_agent="dm",
            to_agent="wizard",
            content="Secret info",
            turn_created=1,
        )
        assert whisper.from_agent == "dm"

    def test_whisper_from_agent_human_valid(self) -> None:
        """Test Whisper accepts 'human' as from_agent."""
        whisper = Whisper(
            id="test",
            from_agent="human",
            to_agent="wizard",
            content="Player hint",
            turn_created=1,
        )
        assert whisper.from_agent == "human"

    def test_whisper_from_agent_normalized_lowercase(self) -> None:
        """Test Whisper normalizes from_agent to lowercase."""
        whisper = Whisper(
            id="test",
            from_agent="DM",
            to_agent="wizard",
            content="Secret",
            turn_created=1,
        )
        assert whisper.from_agent == "dm"

        whisper2 = Whisper(
            id="test",
            from_agent="HUMAN",
            to_agent="wizard",
            content="Secret",
            turn_created=1,
        )
        assert whisper2.from_agent == "human"

    def test_whisper_from_agent_invalid_raises(self) -> None:
        """Test Whisper rejects invalid from_agent values."""
        with pytest.raises(ValidationError) as exc_info:
            Whisper(
                id="test",
                from_agent="player",  # Invalid
                to_agent="wizard",
                content="Secret",
                turn_created=1,
            )
        errors = exc_info.value.errors()
        assert any("from_agent" in str(e).lower() for e in errors)

    def test_whisper_empty_id_raises(self) -> None:
        """Test Whisper rejects empty id."""
        with pytest.raises(ValidationError):
            Whisper(
                id="",
                from_agent="dm",
                to_agent="wizard",
                content="Secret",
                turn_created=1,
            )

    def test_whisper_empty_to_agent_raises(self) -> None:
        """Test Whisper rejects empty to_agent."""
        with pytest.raises(ValidationError):
            Whisper(
                id="test",
                from_agent="dm",
                to_agent="",
                content="Secret",
                turn_created=1,
            )

    def test_whisper_to_agent_normalized_lowercase(self) -> None:
        """Test Whisper normalizes to_agent to lowercase."""
        whisper = Whisper(
            id="test",
            from_agent="dm",
            to_agent="WIZARD",
            content="Secret",
            turn_created=1,
        )
        assert whisper.to_agent == "wizard"

        whisper2 = Whisper(
            id="test",
            from_agent="dm",
            to_agent="Fighter",
            content="Secret",
            turn_created=1,
        )
        assert whisper2.to_agent == "fighter"

    def test_whisper_empty_content_raises(self) -> None:
        """Test Whisper rejects empty content."""
        with pytest.raises(ValidationError):
            Whisper(
                id="test",
                from_agent="dm",
                to_agent="wizard",
                content="",
                turn_created=1,
            )

    def test_whisper_whitespace_only_content_raises(self) -> None:
        """Test Whisper rejects whitespace-only content."""
        with pytest.raises(ValidationError) as exc_info:
            Whisper(
                id="test",
                from_agent="dm",
                to_agent="wizard",
                content="   ",
                turn_created=1,
            )
        errors = exc_info.value.errors()
        assert any("whitespace" in str(e).lower() for e in errors)

    def test_whisper_negative_turn_created_raises(self) -> None:
        """Test Whisper rejects negative turn_created."""
        with pytest.raises(ValidationError):
            Whisper(
                id="test",
                from_agent="dm",
                to_agent="wizard",
                content="Secret",
                turn_created=-1,
            )

    def test_whisper_turn_created_zero_valid(self) -> None:
        """Test Whisper accepts turn_created=0 (game start)."""
        whisper = Whisper(
            id="test",
            from_agent="dm",
            to_agent="wizard",
            content="Secret",
            turn_created=0,
        )
        assert whisper.turn_created == 0

    def test_whisper_revealed_without_turn_revealed_raises(self) -> None:
        """Test Whisper rejects revealed=True without turn_revealed."""
        with pytest.raises(ValidationError) as exc_info:
            Whisper(
                id="test",
                from_agent="dm",
                to_agent="wizard",
                content="Secret",
                turn_created=1,
                revealed=True,
                turn_revealed=None,  # Missing when revealed=True
            )
        errors = exc_info.value.errors()
        assert any("turn_revealed must be set" in str(e) for e in errors)

    def test_whisper_turn_revealed_without_revealed_raises(self) -> None:
        """Test Whisper rejects turn_revealed set when revealed=False."""
        with pytest.raises(ValidationError) as exc_info:
            Whisper(
                id="test",
                from_agent="dm",
                to_agent="wizard",
                content="Secret",
                turn_created=1,
                revealed=False,
                turn_revealed=5,  # Should be None when revealed=False
            )
        errors = exc_info.value.errors()
        assert any("turn_revealed must be None" in str(e) for e in errors)

    def test_whisper_turn_revealed_before_turn_created_raises(self) -> None:
        """Test Whisper rejects turn_revealed < turn_created."""
        with pytest.raises(ValidationError) as exc_info:
            Whisper(
                id="test",
                from_agent="dm",
                to_agent="wizard",
                content="Secret",
                turn_created=10,
                revealed=True,
                turn_revealed=5,  # Before creation
            )
        errors = exc_info.value.errors()
        assert any("cannot be before" in str(e) for e in errors)

    def test_whisper_turn_revealed_equals_turn_created_valid(self) -> None:
        """Test Whisper accepts turn_revealed == turn_created (immediate reveal)."""
        whisper = Whisper(
            id="test",
            from_agent="dm",
            to_agent="wizard",
            content="Secret",
            turn_created=5,
            revealed=True,
            turn_revealed=5,  # Same turn - immediate reveal
        )
        assert whisper.turn_revealed == 5

    def test_whisper_json_serialization(self) -> None:
        """Test Whisper can serialize to JSON."""
        whisper = Whisper(
            id="test123",
            from_agent="dm",
            to_agent="rogue",
            content="The trap is ahead",
            turn_created=3,
        )

        json_str = whisper.model_dump_json()
        data = json.loads(json_str)

        assert data["id"] == "test123"
        assert data["from_agent"] == "dm"
        assert data["to_agent"] == "rogue"
        assert data["content"] == "The trap is ahead"
        assert data["turn_created"] == 3
        assert data["revealed"] is False
        assert data["turn_revealed"] is None

    def test_whisper_json_roundtrip(self) -> None:
        """Test Whisper survives JSON roundtrip."""
        original = Whisper(
            id="roundtrip",
            from_agent="dm",
            to_agent="wizard",
            content="Magic secrets",
            turn_created=5,
            revealed=True,
            turn_revealed=10,
        )

        json_str = original.model_dump_json()
        restored = Whisper.model_validate_json(json_str)

        assert restored.id == original.id
        assert restored.from_agent == original.from_agent
        assert restored.to_agent == original.to_agent
        assert restored.content == original.content
        assert restored.turn_created == original.turn_created
        assert restored.revealed == original.revealed
        assert restored.turn_revealed == original.turn_revealed


class TestCreateWhisperFactory:
    """Tests for the create_whisper factory function."""

    def test_create_whisper_generates_uuid(self) -> None:
        """Test create_whisper generates a unique UUID id."""
        whisper1 = create_whisper("dm", "fighter", "Message 1", 1)
        whisper2 = create_whisper("dm", "fighter", "Message 2", 1)

        assert whisper1.id != whisper2.id
        assert len(whisper1.id) == 32  # UUID hex is 32 chars

    def test_create_whisper_sets_defaults(self) -> None:
        """Test create_whisper sets default values correctly."""
        whisper = create_whisper("dm", "rogue", "A secret", 5)

        assert whisper.from_agent == "dm"
        assert whisper.to_agent == "rogue"
        assert whisper.content == "A secret"
        assert whisper.turn_created == 5
        assert whisper.revealed is False
        assert whisper.turn_revealed is None

    def test_create_whisper_from_human(self) -> None:
        """Test create_whisper with human source."""
        whisper = create_whisper("human", "wizard", "Player hint", 3)

        assert whisper.from_agent == "human"
        assert whisper.to_agent == "wizard"

    def test_create_whisper_normalizes_to_agent(self) -> None:
        """Test create_whisper normalizes to_agent to lowercase."""
        whisper = create_whisper("dm", "FIGHTER", "Secret message", 1)

        assert whisper.to_agent == "fighter"

    def test_create_whisper_normalizes_from_agent(self) -> None:
        """Test create_whisper normalizes from_agent to lowercase."""
        whisper = create_whisper("DM", "fighter", "Secret message", 1)

        assert whisper.from_agent == "dm"


class TestWhisperExports:
    """Tests for Whisper exports in __all__."""

    def test_whisper_in_all_exports(self) -> None:
        """Test Whisper is exported in models.__all__."""
        import models

        assert "Whisper" in models.__all__

    def test_create_whisper_in_all_exports(self) -> None:
        """Test create_whisper is exported in models.__all__."""
        import models

        assert "create_whisper" in models.__all__


# =============================================================================
# AgentSecrets Model Tests
# =============================================================================


class TestAgentSecretsModel:
    """Tests for the AgentSecrets Pydantic model."""

    def test_agent_secrets_creation_empty(self) -> None:
        """Test AgentSecrets can be created with empty whispers."""
        secrets = AgentSecrets()

        assert secrets.whispers == []

    def test_agent_secrets_creation_with_whispers(self) -> None:
        """Test AgentSecrets can be created with whispers list."""
        whisper = Whisper(
            id="test",
            from_agent="dm",
            to_agent="fighter",
            content="Secret",
            turn_created=1,
        )
        secrets = AgentSecrets(whispers=[whisper])

        assert len(secrets.whispers) == 1
        assert secrets.whispers[0].id == "test"

    def test_agent_secrets_active_whispers_all_active(self) -> None:
        """Test active_whispers returns all when none revealed."""
        whispers = [
            Whisper(
                id=f"w{i}",
                from_agent="dm",
                to_agent="fighter",
                content=f"Secret {i}",
                turn_created=i,
            )
            for i in range(3)
        ]
        secrets = AgentSecrets(whispers=whispers)

        active = secrets.active_whispers()

        assert len(active) == 3

    def test_agent_secrets_active_whispers_filters_revealed(self) -> None:
        """Test active_whispers excludes revealed whispers."""
        whispers = [
            Whisper(
                id="active1",
                from_agent="dm",
                to_agent="fighter",
                content="Active secret 1",
                turn_created=1,
                revealed=False,
            ),
            Whisper(
                id="revealed",
                from_agent="dm",
                to_agent="fighter",
                content="Revealed secret",
                turn_created=2,
                revealed=True,
                turn_revealed=5,
            ),
            Whisper(
                id="active2",
                from_agent="dm",
                to_agent="fighter",
                content="Active secret 2",
                turn_created=3,
                revealed=False,
            ),
        ]
        secrets = AgentSecrets(whispers=whispers)

        active = secrets.active_whispers()

        assert len(active) == 2
        assert all(w.id.startswith("active") for w in active)

    def test_agent_secrets_active_whispers_empty(self) -> None:
        """Test active_whispers returns empty when all revealed."""
        whispers = [
            Whisper(
                id=f"w{i}",
                from_agent="dm",
                to_agent="fighter",
                content=f"Secret {i}",
                turn_created=i,
                revealed=True,
                turn_revealed=i + 1,
            )
            for i in range(3)
        ]
        secrets = AgentSecrets(whispers=whispers)

        active = secrets.active_whispers()

        assert len(active) == 0

    def test_agent_secrets_json_serialization(self) -> None:
        """Test AgentSecrets can serialize to JSON."""
        whisper = Whisper(
            id="test",
            from_agent="dm",
            to_agent="fighter",
            content="Secret",
            turn_created=1,
        )
        secrets = AgentSecrets(whispers=[whisper])

        json_str = secrets.model_dump_json()
        data = json.loads(json_str)

        assert "whispers" in data
        assert len(data["whispers"]) == 1
        assert data["whispers"][0]["id"] == "test"

    def test_agent_secrets_json_roundtrip(self) -> None:
        """Test AgentSecrets survives JSON roundtrip."""
        whispers = [
            Whisper(
                id="w1",
                from_agent="dm",
                to_agent="fighter",
                content="Secret 1",
                turn_created=1,
            ),
            Whisper(
                id="w2",
                from_agent="dm",
                to_agent="fighter",
                content="Secret 2",
                turn_created=2,
                revealed=True,
                turn_revealed=5,
            ),
        ]
        original = AgentSecrets(whispers=whispers)

        json_str = original.model_dump_json()
        restored = AgentSecrets.model_validate_json(json_str)

        assert len(restored.whispers) == 2
        assert restored.whispers[0].id == "w1"
        assert restored.whispers[1].revealed is True


class TestAgentSecretsExports:
    """Tests for AgentSecrets exports in __all__."""

    def test_agent_secrets_in_all_exports(self) -> None:
        """Test AgentSecrets is exported in models.__all__."""
        import models

        assert "AgentSecrets" in models.__all__


# =============================================================================
# GameState Integration Tests
# =============================================================================


class TestGameStateWithSecrets:
    """Tests for GameState with agent_secrets field."""

    def test_create_initial_game_state_has_agent_secrets(self) -> None:
        """Test create_initial_game_state initializes agent_secrets."""
        state = create_initial_game_state()

        assert "agent_secrets" in state
        assert state["agent_secrets"] == {}

    def test_populate_game_state_initializes_agent_secrets(self) -> None:
        """Test populate_game_state creates AgentSecrets for each agent."""
        state = populate_game_state(include_sample_messages=False)

        assert "agent_secrets" in state
        assert len(state["agent_secrets"]) > 0

        # Should have secrets for DM and all PCs
        assert "dm" in state["agent_secrets"]
        for char_name in state["characters"]:
            assert char_name in state["agent_secrets"]

    def test_populate_game_state_secrets_are_empty(self) -> None:
        """Test populate_game_state creates empty AgentSecrets."""
        state = populate_game_state(include_sample_messages=False)

        for _agent_name, secrets in state["agent_secrets"].items():
            assert isinstance(secrets, AgentSecrets)
            assert secrets.whispers == []

    def test_game_state_secrets_can_be_modified(self) -> None:
        """Test agent_secrets can be modified after creation."""
        state = populate_game_state(include_sample_messages=False)

        whisper = create_whisper("dm", "dm", "DM note to self", 1)
        state["agent_secrets"]["dm"].whispers.append(whisper)

        assert len(state["agent_secrets"]["dm"].whispers) == 1


# =============================================================================
# Serialization/Deserialization Tests
# =============================================================================


class TestSecretsSerialization:
    """Tests for agent_secrets serialization/deserialization."""

    def test_serialize_game_state_includes_agent_secrets(self) -> None:
        """Test serialize_game_state includes agent_secrets field."""
        state = create_initial_game_state()
        state["agent_secrets"]["test"] = AgentSecrets()

        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        assert "agent_secrets" in data
        assert "test" in data["agent_secrets"]

    def test_serialize_game_state_with_whispers(self) -> None:
        """Test serialize_game_state serializes whispers correctly."""
        state = create_initial_game_state()

        whisper = Whisper(
            id="serialize_test",
            from_agent="dm",
            to_agent="wizard",
            content="Serialize this",
            turn_created=5,
        )
        state["agent_secrets"]["wizard"] = AgentSecrets(whispers=[whisper])

        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        assert len(data["agent_secrets"]["wizard"]["whispers"]) == 1
        assert data["agent_secrets"]["wizard"]["whispers"][0]["id"] == "serialize_test"

    def test_deserialize_game_state_restores_agent_secrets(self) -> None:
        """Test deserialize_game_state restores AgentSecrets correctly."""
        state = create_initial_game_state()
        state["agent_secrets"]["test"] = AgentSecrets()

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        assert "agent_secrets" in restored
        assert "test" in restored["agent_secrets"]
        assert isinstance(restored["agent_secrets"]["test"], AgentSecrets)

    def test_deserialize_game_state_restores_whispers(self) -> None:
        """Test deserialize_game_state restores Whisper objects correctly."""
        state = create_initial_game_state()

        whisper = Whisper(
            id="deserialize_test",
            from_agent="dm",
            to_agent="rogue",
            content="Deserialize this",
            turn_created=3,
            revealed=True,
            turn_revealed=7,
        )
        state["agent_secrets"]["rogue"] = AgentSecrets(whispers=[whisper])

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        rogue_secrets = restored["agent_secrets"]["rogue"]
        assert len(rogue_secrets.whispers) == 1

        restored_whisper = rogue_secrets.whispers[0]
        assert isinstance(restored_whisper, Whisper)
        assert restored_whisper.id == "deserialize_test"
        assert restored_whisper.from_agent == "dm"
        assert restored_whisper.to_agent == "rogue"
        assert restored_whisper.content == "Deserialize this"
        assert restored_whisper.turn_created == 3
        assert restored_whisper.revealed is True
        assert restored_whisper.turn_revealed == 7

    def test_serialization_roundtrip(self) -> None:
        """Test complete serialization roundtrip with multiple agents and whispers."""
        state = populate_game_state(include_sample_messages=False)

        # Add whispers to multiple agents
        state["agent_secrets"]["dm"].whispers.append(
            create_whisper("human", "dm", "Human to DM message", 1)
        )

        # Get first agent name
        first_agent = list(state["characters"].keys())[0]
        state["agent_secrets"][first_agent].whispers.extend(
            [
                create_whisper("dm", first_agent, "First secret", 2),
                create_whisper("dm", first_agent, "Second secret", 3),
            ]
        )

        # Roundtrip
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        # Verify
        assert len(restored["agent_secrets"]["dm"].whispers) == 1
        assert len(restored["agent_secrets"][first_agent].whispers) == 2

        # Verify active_whispers still works
        assert len(restored["agent_secrets"][first_agent].active_whispers()) == 2

    def test_backward_compatibility_no_agent_secrets(self) -> None:
        """Test deserialize handles old checkpoints without agent_secrets."""
        # Simulate old checkpoint JSON without agent_secrets field
        old_json = json.dumps(
            {
                "ground_truth_log": [],
                "turn_queue": ["dm"],
                "current_turn": "dm",
                "agent_memories": {},
                "game_config": {
                    "combat_mode": "Narrative",
                    "summarizer_provider": "gemini",
                    "summarizer_model": "gemini-1.5-flash",
                    "party_size": 4,
                },
                "dm_config": {
                    "name": "Dungeon Master",
                    "provider": "gemini",
                    "model": "gemini-1.5-flash",
                    "token_limit": 8000,
                    "color": "#D4A574",
                },
                "characters": {},
                "whisper_queue": [],
                "human_active": False,
                "controlled_character": None,
                "session_number": 1,
                "session_id": "001",
                "summarization_in_progress": False,
                "selected_module": None,
                "character_sheets": {},
                # No agent_secrets field - old checkpoint
            }
        )

        restored = deserialize_game_state(old_json)

        # Should have empty agent_secrets
        assert "agent_secrets" in restored
        assert restored["agent_secrets"] == {}


# =============================================================================
# Checkpoint Integration Tests
# =============================================================================


class TestCheckpointWithSecrets:
    """Tests for checkpoint save/load with agent_secrets."""

    @pytest.fixture
    def temp_campaigns_dir(self, tmp_path: Path):
        """Create a temporary campaigns directory for testing."""
        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns):
            yield temp_campaigns

    def test_save_checkpoint_includes_secrets(self, temp_campaigns_dir: Path) -> None:
        """Test save_checkpoint persists agent_secrets."""
        state = populate_game_state(include_sample_messages=False)

        # Add a whisper
        first_agent = list(state["characters"].keys())[0]
        whisper = create_whisper("dm", first_agent, "Checkpoint test", 5)
        state["agent_secrets"][first_agent].whispers.append(whisper)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(state, "001", 1)

        # Verify file contains agent_secrets
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        assert "agent_secrets" in data
        assert first_agent in data["agent_secrets"]
        assert len(data["agent_secrets"][first_agent]["whispers"]) == 1

    def test_load_checkpoint_restores_secrets(self, temp_campaigns_dir: Path) -> None:
        """Test load_checkpoint restores agent_secrets correctly."""
        state = populate_game_state(include_sample_messages=False)

        # Add whispers
        dm_whisper = create_whisper("human", "dm", "From human", 1)
        state["agent_secrets"]["dm"].whispers.append(dm_whisper)

        first_agent = list(state["characters"].keys())[0]
        pc_whisper = create_whisper("dm", first_agent, "From DM", 2)
        state["agent_secrets"][first_agent].whispers.append(pc_whisper)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            restored = load_checkpoint("001", 1)

        assert restored is not None

        # Verify DM whisper
        assert len(restored["agent_secrets"]["dm"].whispers) == 1
        assert restored["agent_secrets"]["dm"].whispers[0].from_agent == "human"

        # Verify PC whisper
        assert len(restored["agent_secrets"][first_agent].whispers) == 1
        assert restored["agent_secrets"][first_agent].whispers[0].from_agent == "dm"

    def test_checkpoint_roundtrip_with_revealed_whisper(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test checkpoint roundtrip preserves revealed whisper state."""
        state = populate_game_state(include_sample_messages=False)

        first_agent = list(state["characters"].keys())[0]
        revealed_whisper = Whisper(
            id="revealed_checkpoint",
            from_agent="dm",
            to_agent=first_agent,
            content="Was revealed",
            turn_created=1,
            revealed=True,
            turn_revealed=5,
        )
        state["agent_secrets"][first_agent].whispers.append(revealed_whisper)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            restored = load_checkpoint("001", 1)

        assert restored is not None

        whisper = restored["agent_secrets"][first_agent].whispers[0]
        assert whisper.revealed is True
        assert whisper.turn_revealed == 5

        # active_whispers should not include revealed
        assert len(restored["agent_secrets"][first_agent].active_whispers()) == 0
