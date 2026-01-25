"""Tests for game state models."""

import json

import pytest
from pydantic import ValidationError


class TestAgentMemory:
    """Tests for AgentMemory model."""

    def test_agent_memory_creation_with_defaults(self) -> None:
        """Test AgentMemory can be created with default values."""
        from models import AgentMemory

        memory = AgentMemory()
        assert memory.long_term_summary == ""
        assert memory.short_term_buffer == []
        assert memory.token_limit == 8000

    def test_agent_memory_creation_with_values(self) -> None:
        """Test AgentMemory can be created with custom values."""
        from models import AgentMemory

        memory = AgentMemory(
            long_term_summary="The party entered the dungeon",
            short_term_buffer=["Turn 1: Fighter attacks", "Turn 2: Rogue hides"],
            token_limit=4000,
        )
        assert memory.long_term_summary == "The party entered the dungeon"
        assert len(memory.short_term_buffer) == 2
        assert memory.token_limit == 4000

    def test_agent_memory_json_serialization(self) -> None:
        """Test AgentMemory can serialize to JSON via model_dump_json()."""
        from models import AgentMemory

        memory = AgentMemory(
            long_term_summary="Test summary",
            short_term_buffer=["Event 1", "Event 2"],
            token_limit=6000,
        )

        json_str = memory.model_dump_json()
        data = json.loads(json_str)

        assert data["long_term_summary"] == "Test summary"
        assert data["short_term_buffer"] == ["Event 1", "Event 2"]
        assert data["token_limit"] == 6000

    def test_agent_memory_json_roundtrip(self) -> None:
        """Test AgentMemory serialization roundtrip works correctly."""
        from models import AgentMemory

        original = AgentMemory(
            long_term_summary="Original summary",
            short_term_buffer=["Event A", "Event B"],
            token_limit=5000,
        )

        json_str = original.model_dump_json()
        restored = AgentMemory.model_validate_json(json_str)

        assert restored.long_term_summary == original.long_term_summary
        assert restored.short_term_buffer == original.short_term_buffer
        assert restored.token_limit == original.token_limit

    def test_agent_memory_zero_token_limit_validation_error(self) -> None:
        """Test AgentMemory raises ValidationError for token_limit=0."""
        from models import AgentMemory

        with pytest.raises(ValidationError) as exc_info:
            AgentMemory(token_limit=0)
        errors = exc_info.value.errors()
        assert any("token_limit" in str(e).lower() for e in errors)

    def test_agent_memory_negative_token_limit_validation_error(self) -> None:
        """Test AgentMemory raises ValidationError for negative token_limit."""
        from models import AgentMemory

        with pytest.raises(ValidationError) as exc_info:
            AgentMemory(token_limit=-100)
        errors = exc_info.value.errors()
        assert any("token_limit" in str(e).lower() for e in errors)


class TestCharacterConfig:
    """Tests for CharacterConfig model."""

    def test_character_config_creation_with_required_fields(self) -> None:
        """Test CharacterConfig can be created with required fields."""
        from models import CharacterConfig

        config = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sardonic wit, trust issues",
            color="#6B8E6B",
        )
        assert config.name == "Shadowmere"
        assert config.character_class == "Rogue"
        assert config.personality == "Sardonic wit, trust issues"
        assert config.color == "#6B8E6B"
        # Check defaults
        assert config.provider == "gemini"
        assert config.model == "gemini-1.5-flash"
        assert config.token_limit == 4000

    def test_character_config_creation_with_all_fields(self) -> None:
        """Test CharacterConfig can be created with all fields."""
        from models import CharacterConfig

        config = CharacterConfig(
            name="Thaldric",
            character_class="Fighter",
            personality="Honorable, brave",
            color="#C45C4A",
            provider="claude",
            model="claude-3-haiku-20240307",
            token_limit=8000,
        )
        assert config.name == "Thaldric"
        assert config.provider == "claude"
        assert config.model == "claude-3-haiku-20240307"
        assert config.token_limit == 8000

    def test_character_config_empty_name_validation_error(self) -> None:
        """Test CharacterConfig raises ValidationError for empty name."""
        from models import CharacterConfig

        with pytest.raises(ValidationError) as exc_info:
            CharacterConfig(
                name="",
                character_class="Rogue",
                personality="Sneaky",
                color="#6B8E6B",
            )
        errors = exc_info.value.errors()
        assert any("name" in str(e).lower() for e in errors)

    def test_character_config_invalid_color_format(self) -> None:
        """Test CharacterConfig raises ValidationError for invalid color format."""
        from models import CharacterConfig

        with pytest.raises(ValidationError) as exc_info:
            CharacterConfig(
                name="Test",
                character_class="Rogue",
                personality="Sneaky",
                color="red",  # Should be hex format
            )
        errors = exc_info.value.errors()
        assert any("color" in str(e).lower() for e in errors)

    def test_character_config_negative_token_limit(self) -> None:
        """Test CharacterConfig raises ValidationError for negative token_limit."""
        from models import CharacterConfig

        with pytest.raises(ValidationError) as exc_info:
            CharacterConfig(
                name="Test",
                character_class="Rogue",
                personality="Sneaky",
                color="#6B8E6B",
                token_limit=-100,
            )
        errors = exc_info.value.errors()
        assert any("token_limit" in str(e).lower() for e in errors)

    def test_character_config_json_serialization(self) -> None:
        """Test CharacterConfig can serialize to JSON."""
        from models import CharacterConfig

        config = CharacterConfig(
            name="Test",
            character_class="Wizard",
            personality="Curious",
            color="#7B68B8",
        )

        json_str = config.model_dump_json()
        data = json.loads(json_str)

        assert data["name"] == "Test"
        assert data["character_class"] == "Wizard"

    def test_character_config_json_roundtrip(self) -> None:
        """Test CharacterConfig serialization roundtrip works correctly."""
        from models import CharacterConfig

        original = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sardonic wit, trust issues",
            color="#6B8E6B",
            provider="claude",
            model="claude-3-haiku-20240307",
            token_limit=6000,
        )

        json_str = original.model_dump_json()
        restored = CharacterConfig.model_validate_json(json_str)

        assert restored.name == original.name
        assert restored.character_class == original.character_class
        assert restored.personality == original.personality
        assert restored.color == original.color
        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.token_limit == original.token_limit


class TestGameConfig:
    """Tests for GameConfig model."""

    def test_game_config_creation_with_defaults(self) -> None:
        """Test GameConfig can be created with default values."""
        from models import GameConfig

        config = GameConfig()
        assert config.combat_mode == "Narrative"
        assert config.summarizer_model == "gemini-1.5-flash"
        assert config.party_size == 4

    def test_game_config_creation_with_values(self) -> None:
        """Test GameConfig can be created with custom values."""
        from models import GameConfig

        config = GameConfig(
            combat_mode="Tactical",
            summarizer_model="claude-3-haiku-20240307",
            party_size=6,
        )
        assert config.combat_mode == "Tactical"
        assert config.summarizer_model == "claude-3-haiku-20240307"
        assert config.party_size == 6

    def test_game_config_invalid_combat_mode(self) -> None:
        """Test GameConfig raises ValidationError for invalid combat_mode."""
        from models import GameConfig

        with pytest.raises(ValidationError):
            GameConfig(combat_mode="InvalidMode")  # type: ignore[arg-type]

    def test_game_config_json_serialization(self) -> None:
        """Test GameConfig can serialize to JSON."""
        from models import GameConfig

        config = GameConfig(
            combat_mode="Tactical",
            summarizer_model="claude-3-haiku-20240307",
            party_size=6,
        )

        json_str = config.model_dump_json()
        data = json.loads(json_str)

        assert data["combat_mode"] == "Tactical"
        assert data["summarizer_model"] == "claude-3-haiku-20240307"
        assert data["party_size"] == 6

    def test_game_config_json_roundtrip(self) -> None:
        """Test GameConfig serialization roundtrip works correctly."""
        from models import GameConfig

        original = GameConfig(
            combat_mode="Tactical",
            summarizer_model="gemini-1.5-pro",
            party_size=5,
        )

        json_str = original.model_dump_json()
        restored = GameConfig.model_validate_json(json_str)

        assert restored.combat_mode == original.combat_mode
        assert restored.summarizer_model == original.summarizer_model
        assert restored.party_size == original.party_size

    def test_game_config_party_size_zero_validation_error(self) -> None:
        """Test GameConfig raises ValidationError for party_size=0."""
        from models import GameConfig

        with pytest.raises(ValidationError) as exc_info:
            GameConfig(party_size=0)
        errors = exc_info.value.errors()
        assert any("party_size" in str(e).lower() for e in errors)

    def test_game_config_party_size_over_max_validation_error(self) -> None:
        """Test GameConfig raises ValidationError for party_size > 8."""
        from models import GameConfig

        with pytest.raises(ValidationError) as exc_info:
            GameConfig(party_size=9)
        errors = exc_info.value.errors()
        assert any("party_size" in str(e).lower() for e in errors)


class TestGameState:
    """Tests for GameState TypedDict."""

    def test_game_state_structure(self) -> None:
        """Test GameState has all required fields with correct types."""
        from models import AgentMemory, GameConfig, GameState

        # Create a valid GameState
        state: GameState = {
            "ground_truth_log": ["Turn 1: Game begins"],
            "turn_queue": ["dm", "fighter", "rogue"],
            "current_turn": "dm",
            "agent_memories": {
                "fighter": AgentMemory(),
                "rogue": AgentMemory(token_limit=4000),
            },
            "game_config": GameConfig(),
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
        }

        assert len(state["ground_truth_log"]) == 1
        assert len(state["turn_queue"]) == 3
        assert state["current_turn"] == "dm"
        assert "fighter" in state["agent_memories"]
        assert state["human_active"] is False
        assert state["controlled_character"] is None

    def test_game_state_agent_memories_is_agent_memory_dict(self) -> None:
        """Test that agent_memories contains AgentMemory instances."""
        from models import AgentMemory, GameConfig, GameState

        memory = AgentMemory(long_term_summary="Test")
        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {"test_agent": memory},
            "game_config": GameConfig(),
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
        }

        assert isinstance(state["agent_memories"]["test_agent"], AgentMemory)
        assert state["agent_memories"]["test_agent"].long_term_summary == "Test"


class TestFactoryFunctions:
    """Tests for state factory functions."""

    def test_create_initial_game_state(self) -> None:
        """Test create_initial_game_state produces valid state."""
        from models import create_initial_game_state

        state = create_initial_game_state()

        assert state["ground_truth_log"] == []
        assert state["turn_queue"] == []
        assert state["current_turn"] == ""
        assert state["agent_memories"] == {}
        assert state["whisper_queue"] == []
        assert state["human_active"] is False
        assert state["controlled_character"] is None

    def test_create_agent_memory(self) -> None:
        """Test create_agent_memory factory function."""
        from models import create_agent_memory

        memory = create_agent_memory()
        assert memory.long_term_summary == ""
        assert memory.short_term_buffer == []
        assert memory.token_limit == 8000

    def test_create_agent_memory_with_custom_limit(self) -> None:
        """Test create_agent_memory with custom token_limit."""
        from models import create_agent_memory

        memory = create_agent_memory(token_limit=4000)
        assert memory.token_limit == 4000
