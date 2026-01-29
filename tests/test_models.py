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

    def test_character_config_invalid_provider(self) -> None:
        """Test CharacterConfig raises ValidationError for unsupported provider."""
        from models import CharacterConfig

        with pytest.raises(ValidationError) as exc_info:
            CharacterConfig(
                name="Test",
                character_class="Rogue",
                personality="Sneaky",
                color="#6B8E6B",
                provider="openai",  # Not a supported provider
            )
        errors = exc_info.value.errors()
        assert any("provider" in str(e).lower() for e in errors)

    def test_character_config_provider_normalized_to_lowercase(self) -> None:
        """Test CharacterConfig normalizes provider to lowercase."""
        from models import CharacterConfig

        config = CharacterConfig(
            name="Test",
            character_class="Rogue",
            personality="Test",
            color="#6B8E6B",
            provider="CLAUDE",
        )
        assert config.provider == "claude"

    def test_character_config_all_supported_providers(self) -> None:
        """Test CharacterConfig accepts all supported providers."""
        from models import CharacterConfig

        for provider in ["gemini", "claude", "ollama"]:
            config = CharacterConfig(
                name="Test",
                character_class="Rogue",
                personality="Test",
                color="#6B8E6B",
                provider=provider,
            )
            assert config.provider == provider

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


class TestDMConfig:
    """Tests for DMConfig model."""

    def test_dm_config_creation_with_defaults(self) -> None:
        """Test DMConfig can be created with default values."""
        from models import DMConfig

        config = DMConfig()
        assert config.name == "Dungeon Master"
        assert config.provider == "gemini"
        assert config.model == "gemini-1.5-flash"
        assert config.token_limit == 8000
        assert config.color == "#D4A574"

    def test_dm_config_creation_with_custom_values(self) -> None:
        """Test DMConfig can be created with custom values."""
        from models import DMConfig

        config = DMConfig(
            name="Game Master",
            provider="claude",
            model="claude-3-sonnet-20240229",
            token_limit=16000,
            color="#FF6B6B",
        )
        assert config.name == "Game Master"
        assert config.provider == "claude"
        assert config.model == "claude-3-sonnet-20240229"
        assert config.token_limit == 16000
        assert config.color == "#FF6B6B"

    def test_dm_config_invalid_color_format(self) -> None:
        """Test DMConfig raises ValidationError for invalid color format."""
        from models import DMConfig

        with pytest.raises(ValidationError) as exc_info:
            DMConfig(color="gold")  # Should be hex format
        errors = exc_info.value.errors()
        assert any("color" in str(e).lower() for e in errors)

    def test_dm_config_invalid_provider(self) -> None:
        """Test DMConfig raises ValidationError for unsupported provider."""
        from models import DMConfig

        with pytest.raises(ValidationError) as exc_info:
            DMConfig(provider="openai")  # Not a supported provider
        errors = exc_info.value.errors()
        assert any("provider" in str(e).lower() for e in errors)

    def test_dm_config_provider_normalized_to_lowercase(self) -> None:
        """Test DMConfig normalizes provider to lowercase."""
        from models import DMConfig

        config = DMConfig(provider="GEMINI")
        assert config.provider == "gemini"

        config = DMConfig(provider="Claude")
        assert config.provider == "claude"

    def test_dm_config_all_supported_providers(self) -> None:
        """Test DMConfig accepts all supported providers."""
        from models import DMConfig

        for provider in ["gemini", "claude", "ollama"]:
            config = DMConfig(provider=provider)
            assert config.provider == provider

    def test_dm_config_negative_token_limit(self) -> None:
        """Test DMConfig raises ValidationError for negative token_limit."""
        from models import DMConfig

        with pytest.raises(ValidationError) as exc_info:
            DMConfig(token_limit=-100)
        errors = exc_info.value.errors()
        assert any("token_limit" in str(e).lower() for e in errors)

    def test_dm_config_json_serialization(self) -> None:
        """Test DMConfig can serialize to JSON."""
        from models import DMConfig

        config = DMConfig(provider="claude", model="claude-3-haiku-20240307")

        json_str = config.model_dump_json()
        data = json.loads(json_str)

        assert data["provider"] == "claude"
        assert data["model"] == "claude-3-haiku-20240307"
        assert data["name"] == "Dungeon Master"

    def test_dm_config_json_roundtrip(self) -> None:
        """Test DMConfig serialization roundtrip works correctly."""
        from models import DMConfig

        original = DMConfig(
            name="Custom DM",
            provider="ollama",
            model="llama3",
            token_limit=4000,
            color="#123456",
        )

        json_str = original.model_dump_json()
        restored = DMConfig.model_validate_json(json_str)

        assert restored.name == original.name
        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.token_limit == original.token_limit
        assert restored.color == original.color

    def test_dm_config_in_all_exports(self) -> None:
        """Test DMConfig is exported in __all__."""
        import models

        assert "DMConfig" in models.__all__


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
        from models import AgentMemory, CharacterConfig, DMConfig, GameConfig, GameState

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
            "dm_config": DMConfig(),
            "characters": {
                "fighter": CharacterConfig(
                    name="Thor",
                    character_class="Fighter",
                    personality="Bold",
                    color="#8B4513",
                ),
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        assert len(state["ground_truth_log"]) == 1
        assert len(state["turn_queue"]) == 3
        assert state["current_turn"] == "dm"
        assert "fighter" in state["agent_memories"]
        assert "fighter" in state["characters"]
        assert state["human_active"] is False
        assert state["controlled_character"] is None
        assert state["dm_config"].name == "Dungeon Master"

    def test_game_state_agent_memories_is_agent_memory_dict(self) -> None:
        """Test that agent_memories contains AgentMemory instances."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        memory = AgentMemory(long_term_summary="Test")
        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {"test_agent": memory},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        assert isinstance(state["agent_memories"]["test_agent"], AgentMemory)
        assert state["agent_memories"]["test_agent"].long_term_summary == "Test"

    def test_game_state_characters_field(self) -> None:
        """Test that characters dict stores CharacterConfig instances."""
        from models import CharacterConfig, DMConfig, GameConfig, GameState

        char_config = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sardonic",
            color="#6B8E6B",
        )
        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {"shadowmere": char_config},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }

        assert "shadowmere" in state["characters"]
        assert isinstance(state["characters"]["shadowmere"], CharacterConfig)
        assert state["characters"]["shadowmere"].name == "Shadowmere"


class TestFactoryFunctions:
    """Tests for state factory functions."""

    def test_create_initial_game_state(self) -> None:
        """Test create_initial_game_state produces valid state."""
        from models import DMConfig, create_initial_game_state

        state = create_initial_game_state()

        assert state["ground_truth_log"] == []
        assert state["turn_queue"] == []
        assert state["current_turn"] == ""
        assert state["agent_memories"] == {}
        assert state["whisper_queue"] == []
        assert state["human_active"] is False
        assert state["controlled_character"] is None
        # Check dm_config is included
        assert isinstance(state["dm_config"], DMConfig)
        assert state["dm_config"].provider == "gemini"

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


class TestGameStateInitialization:
    """Tests for initializing GameState with character configs."""

    def test_initialize_game_state_with_characters(self) -> None:
        """Test populate_game_state initializes characters and turn queue."""
        from models import populate_game_state

        state = populate_game_state()

        # Should have 4 PC characters
        assert len(state["characters"]) == 4

        # DM config should be loaded from YAML
        assert state["dm_config"].name == "Dungeon Master"
        assert state["dm_config"].color == "#D4A574"

        # Turn queue should have dm first, then PCs
        assert state["turn_queue"][0] == "dm"
        assert len(state["turn_queue"]) == 5  # dm + 4 PCs

        # Agent memories should be initialized for all
        assert "dm" in state["agent_memories"]
        for char_name in state["characters"]:
            assert char_name in state["agent_memories"]

    def test_turn_queue_dm_first(self) -> None:
        """Test that DM is always first in turn queue."""
        from models import populate_game_state

        state = populate_game_state()
        assert state["turn_queue"][0] == "dm"

    def test_agent_memories_initialized_with_correct_limits(self) -> None:
        """Test agent memories use token limits from character configs."""
        from models import populate_game_state

        state = populate_game_state()

        # DM should have 8000 (from dm.yaml)
        assert state["agent_memories"]["dm"].token_limit == 8000

        # PC agents should have their configured limits
        for char_name, char_config in state["characters"].items():
            memory = state["agent_memories"][char_name]
            assert memory.token_limit == char_config.token_limit

    def test_current_turn_starts_with_dm(self) -> None:
        """Test that current_turn is initialized to dm."""
        from models import populate_game_state

        state = populate_game_state()
        assert state["current_turn"] == "dm"


# =============================================================================
# Story 4.3: SessionMetadata Model Tests
# =============================================================================


class TestSessionMetadataModel:
    """Tests for SessionMetadata Pydantic model (Story 4.3)."""

    def test_session_metadata_creation_with_required_fields(self) -> None:
        """Test SessionMetadata can be created with required fields."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert metadata.session_id == "001"
        assert metadata.session_number == 1

    def test_session_metadata_creation_with_all_fields(self) -> None:
        """Test SessionMetadata can be created with all fields."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="042",
            session_number=42,
            name="Epic Adventure",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T14:30:00Z",
            character_names=["Theron", "Lyra", "Magnus"],
            turn_count=100,
        )

        assert metadata.session_id == "042"
        assert metadata.session_number == 42
        assert metadata.name == "Epic Adventure"
        assert len(metadata.character_names) == 3
        assert metadata.turn_count == 100

    def test_session_metadata_default_name(self) -> None:
        """Test SessionMetadata defaults name to empty string."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert metadata.name == ""

    def test_session_metadata_default_character_names(self) -> None:
        """Test SessionMetadata defaults character_names to empty list."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert metadata.character_names == []

    def test_session_metadata_default_turn_count(self) -> None:
        """Test SessionMetadata defaults turn_count to 0."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert metadata.turn_count == 0

    def test_session_metadata_rejects_empty_session_id(self) -> None:
        """Test SessionMetadata rejects empty session_id."""
        import pytest
        from pydantic import ValidationError

        from models import SessionMetadata

        with pytest.raises(ValidationError):
            SessionMetadata(
                session_id="",
                session_number=1,
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
            )

    def test_session_metadata_rejects_zero_session_number(self) -> None:
        """Test SessionMetadata rejects session_number < 1."""
        import pytest
        from pydantic import ValidationError

        from models import SessionMetadata

        with pytest.raises(ValidationError):
            SessionMetadata(
                session_id="001",
                session_number=0,
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
            )

    def test_session_metadata_rejects_negative_session_number(self) -> None:
        """Test SessionMetadata rejects negative session_number."""
        import pytest
        from pydantic import ValidationError

        from models import SessionMetadata

        with pytest.raises(ValidationError):
            SessionMetadata(
                session_id="001",
                session_number=-1,
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
            )

    def test_session_metadata_rejects_negative_turn_count(self) -> None:
        """Test SessionMetadata rejects negative turn_count."""
        import pytest
        from pydantic import ValidationError

        from models import SessionMetadata

        with pytest.raises(ValidationError):
            SessionMetadata(
                session_id="001",
                session_number=1,
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
                turn_count=-1,
            )

    def test_session_metadata_in_all_exports(self) -> None:
        """Test SessionMetadata is in module __all__ exports."""
        import models

        assert "SessionMetadata" in models.__all__

    def test_session_metadata_json_serialization(self) -> None:
        """Test SessionMetadata can serialize to JSON."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Test",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T12:00:00Z",
            character_names=["Hero"],
            turn_count=5,
        )

        json_str = metadata.model_dump_json()
        assert "001" in json_str
        assert "Test" in json_str
        assert "Hero" in json_str

    def test_session_metadata_json_roundtrip(self) -> None:
        """Test SessionMetadata survives JSON roundtrip."""
        from models import SessionMetadata

        original = SessionMetadata(
            session_id="042",
            session_number=42,
            name="Roundtrip Test",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T14:00:00Z",
            character_names=["Alpha", "Beta"],
            turn_count=99,
        )

        json_str = original.model_dump_json()
        restored = SessionMetadata.model_validate_json(json_str)

        assert restored.session_id == original.session_id
        assert restored.session_number == original.session_number
        assert restored.name == original.name
        assert restored.character_names == original.character_names
        assert restored.turn_count == original.turn_count

    def test_session_metadata_accepts_boundary_session_number(self) -> None:
        """Test SessionMetadata accepts session_number=1 (boundary)."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert metadata.session_number == 1

    def test_session_metadata_accepts_large_session_number(self) -> None:
        """Test SessionMetadata accepts large session_number."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="9999",
            session_number=9999,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert metadata.session_number == 9999

    def test_session_metadata_accepts_large_turn_count(self) -> None:
        """Test SessionMetadata accepts large turn_count."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
            turn_count=100000,
        )

        assert metadata.turn_count == 100000

    def test_session_metadata_accepts_boundary_turn_count(self) -> None:
        """Test SessionMetadata accepts turn_count=0 (boundary)."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
            turn_count=0,
        )

        assert metadata.turn_count == 0


# =============================================================================
# Story 5.4: CharacterFacts Model Tests
# =============================================================================


class TestCharacterFacts:
    """Tests for CharacterFacts model (Story 5.4, Task 1)."""

    def test_character_facts_creation_with_required_fields(self) -> None:
        """Test CharacterFacts can be created with required fields only."""
        from models import CharacterFacts

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
        )

        assert facts.name == "Shadowmere"
        assert facts.character_class == "Rogue"
        assert facts.key_traits == []
        assert facts.relationships == {}
        assert facts.notable_events == []

    def test_character_facts_creation_with_all_fields(self) -> None:
        """Test CharacterFacts can be created with all fields."""
        from models import CharacterFacts

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sardonic wit", "Trust issues", "Observant"],
            relationships={
                "Theros": "Trusted party member, saved my life in the goblin cave",
                "Marcus the Merchant": "Rival - tried to cheat me in session 2",
            },
            notable_events=[
                "Discovered the hidden passage in Thornwood Tower",
                "Stole the enchanted dagger from Lord Blackwood",
            ],
        )

        assert facts.name == "Shadowmere"
        assert facts.character_class == "Rogue"
        assert len(facts.key_traits) == 3
        assert "Sardonic wit" in facts.key_traits
        assert len(facts.relationships) == 2
        assert "Theros" in facts.relationships
        assert len(facts.notable_events) == 2

    def test_character_facts_json_serialization(self) -> None:
        """Test CharacterFacts can serialize to JSON."""
        from models import CharacterFacts

        facts = CharacterFacts(
            name="Theron",
            character_class="Fighter",
            key_traits=["Brave", "Honorable"],
            relationships={"Shadowmere": "Fellow party member"},
            notable_events=["Defended the village gate"],
        )

        json_str = facts.model_dump_json()
        data = json.loads(json_str)

        assert data["name"] == "Theron"
        assert data["character_class"] == "Fighter"
        assert "Brave" in data["key_traits"]

    def test_character_facts_json_roundtrip(self) -> None:
        """Test CharacterFacts survives JSON roundtrip."""
        from models import CharacterFacts

        original = CharacterFacts(
            name="Lyra",
            character_class="Wizard",
            key_traits=["Curious", "Analytical"],
            relationships={"Master Aldric": "Mentor"},
            notable_events=["Cast first fireball spell"],
        )

        json_str = original.model_dump_json()
        restored = CharacterFacts.model_validate_json(json_str)

        assert restored.name == original.name
        assert restored.character_class == original.character_class
        assert restored.key_traits == original.key_traits
        assert restored.relationships == original.relationships
        assert restored.notable_events == original.notable_events

    def test_character_facts_in_all_exports(self) -> None:
        """Test CharacterFacts is in module __all__ exports."""
        import models

        assert "CharacterFacts" in models.__all__


class TestAgentMemoryWithCharacterFacts:
    """Tests for AgentMemory with character_facts field (Story 5.4, Task 1)."""

    def test_agent_memory_character_facts_default_none(self) -> None:
        """Test AgentMemory defaults character_facts to None."""
        from models import AgentMemory

        memory = AgentMemory()
        assert memory.character_facts is None

    def test_agent_memory_with_character_facts(self) -> None:
        """Test AgentMemory can be created with character_facts."""
        from models import AgentMemory, CharacterFacts

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sardonic wit"],
        )

        memory = AgentMemory(
            long_term_summary="The party explored the dungeon",
            character_facts=facts,
        )

        assert memory.character_facts is not None
        assert memory.character_facts.name == "Shadowmere"
        assert memory.character_facts.character_class == "Rogue"

    def test_agent_memory_with_character_facts_serialization(self) -> None:
        """Test AgentMemory with character_facts serializes correctly."""
        from models import AgentMemory, CharacterFacts

        facts = CharacterFacts(
            name="Theron",
            character_class="Fighter",
            key_traits=["Brave"],
            relationships={"Shadowmere": "Ally"},
        )

        memory = AgentMemory(
            long_term_summary="Test summary",
            character_facts=facts,
            token_limit=6000,
        )

        json_str = memory.model_dump_json()
        data = json.loads(json_str)

        assert "character_facts" in data
        assert data["character_facts"]["name"] == "Theron"
        assert data["character_facts"]["character_class"] == "Fighter"

    def test_agent_memory_with_character_facts_roundtrip(self) -> None:
        """Test AgentMemory with character_facts survives JSON roundtrip."""
        from models import AgentMemory, CharacterFacts

        facts = CharacterFacts(
            name="Lyra",
            character_class="Wizard",
            key_traits=["Curious"],
            relationships={"Master": "Mentor"},
            notable_events=["Learned fireball"],
        )

        original = AgentMemory(
            long_term_summary="Original summary",
            short_term_buffer=["Event 1"],
            character_facts=facts,
            token_limit=5000,
        )

        json_str = original.model_dump_json()
        restored = AgentMemory.model_validate_json(json_str)

        assert restored.character_facts is not None
        assert restored.character_facts.name == "Lyra"
        assert restored.character_facts.key_traits == ["Curious"]
        assert restored.character_facts.relationships == {"Master": "Mentor"}
        assert restored.character_facts.notable_events == ["Learned fireball"]


class TestCreateAgentMemoryWithFacts:
    """Tests for create_agent_memory factory with character_facts (Story 5.4, Task 1)."""

    def test_create_agent_memory_without_facts(self) -> None:
        """Test create_agent_memory works without character_facts."""
        from models import create_agent_memory

        memory = create_agent_memory()
        assert memory.character_facts is None

    def test_create_agent_memory_with_facts(self) -> None:
        """Test create_agent_memory accepts optional character_facts."""
        from models import CharacterFacts, create_agent_memory

        facts = CharacterFacts(name="Test", character_class="Fighter")
        memory = create_agent_memory(token_limit=4000, character_facts=facts)

        assert memory.token_limit == 4000
        assert memory.character_facts is not None
        assert memory.character_facts.name == "Test"


class TestCreateCharacterFactsFromConfig:
    """Tests for create_character_facts_from_config function (Story 5.4, Task 4)."""

    def test_create_character_facts_basic(self) -> None:
        """Test creating CharacterFacts from a CharacterConfig."""
        from models import CharacterConfig, create_character_facts_from_config

        config = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sardonic wit, trust issues",
            color="#6B8E6B",
        )

        facts = create_character_facts_from_config(config)

        assert facts.name == "Shadowmere"
        assert facts.character_class == "Rogue"
        assert facts.key_traits == []  # Initially empty
        assert facts.relationships == {}  # Initially empty
        assert facts.notable_events == []  # Initially empty

    def test_create_character_facts_all_character_classes(self) -> None:
        """Test CharacterFacts creation works for all character classes."""
        from models import CharacterConfig, create_character_facts_from_config

        classes = ["Fighter", "Rogue", "Wizard", "Cleric", "Ranger", "Paladin"]
        for char_class in classes:
            config = CharacterConfig(
                name=f"Test {char_class}",
                character_class=char_class,
                personality="Test personality",
                color="#123456",
            )
            facts = create_character_facts_from_config(config)
            assert facts.character_class == char_class

    def test_create_character_facts_in_all_exports(self) -> None:
        """Test create_character_facts_from_config is in module __all__."""
        import models

        assert "create_character_facts_from_config" in models.__all__


class TestPopulateGameStateWithCharacterFacts:
    """Tests for populate_game_state with CharacterFacts (Story 5.4, Task 4)."""

    def test_populate_game_state_initializes_character_facts(self) -> None:
        """Test populate_game_state creates CharacterFacts for PC agents."""
        from models import CharacterFacts, populate_game_state

        state = populate_game_state(include_sample_messages=False)

        # Each PC agent should have character_facts
        for char_name, char_config in state["characters"].items():
            memory = state["agent_memories"][char_name]
            assert memory.character_facts is not None
            assert isinstance(memory.character_facts, CharacterFacts)
            assert memory.character_facts.name == char_config.name
            assert memory.character_facts.character_class == char_config.character_class

    def test_populate_game_state_dm_has_no_character_facts(self) -> None:
        """Test DM agent does not have character_facts (DM is not a character)."""
        from models import populate_game_state

        state = populate_game_state(include_sample_messages=False)

        dm_memory = state["agent_memories"]["dm"]
        assert dm_memory.character_facts is None
