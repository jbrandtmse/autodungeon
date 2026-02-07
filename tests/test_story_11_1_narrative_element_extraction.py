"""Tests for Story 11-1: Narrative Element Extraction.

Tests the NarrativeElement and NarrativeElementStore models,
the NarrativeElementExtractor class, integration with dm_turn/pc_turn,
and serialization round-trip with persistence.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from models import (
    AgentMemory,
    CharacterConfig,
    DMConfig,
    GameState,
    NarrativeElement,
    NarrativeElementStore,
    create_initial_game_state,
    create_narrative_element,
    populate_game_state,
)
from persistence import (
    deserialize_game_state,
    serialize_game_state,
)

# =============================================================================
# NarrativeElement Model Tests (Tasks 1, 21)
# =============================================================================


class TestNarrativeElementModel:
    """Tests for the NarrativeElement Pydantic model."""

    def test_creation_with_all_fields(self) -> None:
        """Test NarrativeElement can be created with all fields."""
        element = NarrativeElement(
            id="abc123",
            element_type="character",
            name="Skrix the Goblin",
            description="Befriended by party",
            turn_introduced=5,
            session_introduced=1,
            turns_referenced=[5, 8, 12],
            characters_involved=["Shadowmere", "Aldric"],
            resolved=False,
        )

        assert element.id == "abc123"
        assert element.element_type == "character"
        assert element.name == "Skrix the Goblin"
        assert element.description == "Befriended by party"
        assert element.turn_introduced == 5
        assert element.session_introduced == 1
        assert element.turns_referenced == [5, 8, 12]
        assert element.characters_involved == ["Shadowmere", "Aldric"]
        assert element.resolved is False

    def test_default_values(self) -> None:
        """Test NarrativeElement default values: id generation, empty lists, resolved=False."""
        element = NarrativeElement(
            id="test123",
            element_type="item",
            name="Magic Sword",
            turn_introduced=0,
        )

        assert element.description == ""
        assert element.session_introduced == 1
        assert element.turns_referenced == []
        assert element.characters_involved == []
        assert element.resolved is False

    def test_name_must_be_non_empty(self) -> None:
        """Test that name cannot be empty."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            NarrativeElement(
                id="test",
                element_type="character",
                name="",
                turn_introduced=0,
            )

    def test_id_must_be_non_empty(self) -> None:
        """Test that id cannot be empty."""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            NarrativeElement(
                id="",
                element_type="character",
                name="Test",
                turn_introduced=0,
            )

    def test_invalid_element_type_rejected(self) -> None:
        """Test that invalid element_type is rejected."""
        with pytest.raises(ValidationError, match="Input should be"):
            NarrativeElement(
                id="test",
                element_type="invalid_type",  # type: ignore[arg-type]
                name="Test",
                turn_introduced=0,
            )

    def test_turn_introduced_must_be_non_negative(self) -> None:
        """Test that turn_introduced must be >= 0."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            NarrativeElement(
                id="test",
                element_type="event",
                name="Test",
                turn_introduced=-1,
            )

    def test_session_introduced_must_be_positive(self) -> None:
        """Test that session_introduced must be >= 1."""
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            NarrativeElement(
                id="test",
                element_type="event",
                name="Test",
                turn_introduced=0,
                session_introduced=0,
            )

    def test_all_valid_element_types(self) -> None:
        """Test all valid element types are accepted."""
        valid_types = ["character", "item", "location", "event", "promise", "threat"]
        for et in valid_types:
            element = NarrativeElement(
                id="test",
                element_type=et,  # type: ignore[arg-type]
                name="Test",
                turn_introduced=0,
            )
            assert element.element_type == et

    def test_resolved_element(self) -> None:
        """Test element can be marked as resolved."""
        element = NarrativeElement(
            id="test",
            element_type="promise",
            name="Promise to help",
            turn_introduced=3,
            resolved=True,
        )
        assert element.resolved is True


# =============================================================================
# NarrativeElementStore Tests (Tasks 2, 22)
# =============================================================================


class TestNarrativeElementStore:
    """Tests for the NarrativeElementStore model."""

    def _make_element(
        self,
        element_type: str = "character",
        name: str = "Test",
        resolved: bool = False,
    ) -> NarrativeElement:
        """Helper to create a NarrativeElement for tests."""
        return NarrativeElement(
            id=f"id_{name.lower().replace(' ', '_')}",
            element_type=element_type,  # type: ignore[arg-type]
            name=name,
            turn_introduced=0,
            resolved=resolved,
        )

    def test_empty_store(self) -> None:
        """Test empty store returns empty lists."""
        store = NarrativeElementStore()
        assert store.elements == []
        assert store.get_active() == []
        assert store.get_by_type("character") == []
        assert store.find_by_name("anything") is None

    def test_get_active_returns_unresolved(self) -> None:
        """Test get_active returns only unresolved elements."""
        resolved = self._make_element(name="Resolved NPC", resolved=True)
        active1 = self._make_element(name="Active NPC 1")
        active2 = self._make_element(name="Active NPC 2")

        store = NarrativeElementStore(elements=[resolved, active1, active2])
        active = store.get_active()

        assert len(active) == 2
        assert active[0].name == "Active NPC 1"
        assert active[1].name == "Active NPC 2"

    def test_get_by_type_filters_correctly(self) -> None:
        """Test get_by_type returns only matching type."""
        npc = self._make_element(element_type="character", name="NPC")
        item = self._make_element(element_type="item", name="Sword")
        location = self._make_element(element_type="location", name="Cave")

        store = NarrativeElementStore(elements=[npc, item, location])

        characters = store.get_by_type("character")
        assert len(characters) == 1
        assert characters[0].name == "NPC"

        items = store.get_by_type("item")
        assert len(items) == 1
        assert items[0].name == "Sword"

        events = store.get_by_type("event")
        assert len(events) == 0

    def test_find_by_name_case_insensitive(self) -> None:
        """Test find_by_name is case-insensitive."""
        npc = self._make_element(name="Skrix the Goblin")
        store = NarrativeElementStore(elements=[npc])

        # Exact match
        assert store.find_by_name("Skrix the Goblin") is not None
        # Lowercase
        assert store.find_by_name("skrix the goblin") is not None
        # Uppercase
        assert store.find_by_name("SKRIX THE GOBLIN") is not None
        # Mixed case
        assert store.find_by_name("Skrix The GOBLIN") is not None
        # Not found
        assert store.find_by_name("Unknown") is None

    def test_find_by_name_returns_first_match(self) -> None:
        """Test find_by_name returns first matching element."""
        npc1 = self._make_element(name="NPC")
        npc2 = self._make_element(name="npc")  # same name, different case

        store = NarrativeElementStore(elements=[npc1, npc2])
        result = store.find_by_name("npc")
        assert result is not None
        assert result.id == npc1.id  # returns first match


# =============================================================================
# Factory Function Tests (Tasks 7, 23)
# =============================================================================


class TestCreateNarrativeElement:
    """Tests for the create_narrative_element factory function."""

    def test_creates_valid_element(self) -> None:
        """Test factory creates valid NarrativeElement with UUID id."""
        element = create_narrative_element(
            element_type="character",
            name="Goblin King",
            description="Rules the goblin caves",
            turn_introduced=5,
            session_introduced=1,
            characters_involved=["Shadowmere"],
        )

        assert len(element.id) == 32  # UUID hex is 32 chars
        assert element.element_type == "character"
        assert element.name == "Goblin King"
        assert element.description == "Rules the goblin caves"
        assert element.turn_introduced == 5
        assert element.session_introduced == 1
        assert element.characters_involved == ["Shadowmere"]
        assert element.resolved is False

    def test_unique_ids(self) -> None:
        """Test factory generates unique IDs."""
        e1 = create_narrative_element(element_type="item", name="Sword")
        e2 = create_narrative_element(element_type="item", name="Sword")
        assert e1.id != e2.id

    def test_default_values(self) -> None:
        """Test factory defaults."""
        element = create_narrative_element(
            element_type="event",
            name="Discovery",
        )
        assert element.description == ""
        assert element.turn_introduced == 0
        assert element.session_introduced == 1
        assert element.characters_involved == []


# =============================================================================
# GameState Integration Tests (Tasks 3-6)
# =============================================================================


class TestGameStateIntegration:
    """Tests for narrative_elements in GameState."""

    def test_create_initial_game_state_has_narrative_elements(self) -> None:
        """Test create_initial_game_state includes empty narrative_elements."""
        state = create_initial_game_state()
        assert "narrative_elements" in state
        assert state["narrative_elements"] == {}

    @patch("config.load_character_configs")
    @patch("config.load_dm_config")
    def test_populate_game_state_has_narrative_elements(
        self,
        mock_dm_config: MagicMock,
        mock_char_configs: MagicMock,
    ) -> None:
        """Test populate_game_state initializes NarrativeElementStore for session."""
        mock_dm_config.return_value = DMConfig()
        mock_char_configs.return_value = {
            "fighter": CharacterConfig(
                name="Fighter",
                character_class="Fighter",
                personality="Brave",
                color="#FF0000",
            ),
        }

        state = populate_game_state(include_sample_messages=False)
        assert "narrative_elements" in state
        session_id = state["session_id"]
        assert session_id in state["narrative_elements"]
        assert isinstance(state["narrative_elements"][session_id], NarrativeElementStore)
        assert state["narrative_elements"][session_id].elements == []


# =============================================================================
# Extraction Prompt Tests (Task 24)
# =============================================================================


class TestExtractionPrompt:
    """Tests for ELEMENT_EXTRACTION_PROMPT format and content."""

    def test_prompt_exists_and_non_empty(self) -> None:
        """Test the extraction prompt constant exists and has content."""
        from memory import ELEMENT_EXTRACTION_PROMPT

        assert ELEMENT_EXTRACTION_PROMPT
        assert len(ELEMENT_EXTRACTION_PROMPT) > 100

    def test_prompt_mentions_all_element_types(self) -> None:
        """Test prompt references all 6 element types."""
        from memory import ELEMENT_EXTRACTION_PROMPT

        for et in ["character", "item", "location", "event", "promise", "threat"]:
            assert et in ELEMENT_EXTRACTION_PROMPT.lower()

    def test_prompt_requests_json_format(self) -> None:
        """Test prompt requests JSON array response."""
        from memory import ELEMENT_EXTRACTION_PROMPT

        assert "JSON" in ELEMENT_EXTRACTION_PROMPT
        assert "array" in ELEMENT_EXTRACTION_PROMPT.lower()


# =============================================================================
# _parse_extraction_response Tests (Task 25)
# =============================================================================


class TestParseExtractionResponse:
    """Tests for _parse_extraction_response function."""

    def test_valid_json_array(self) -> None:
        """Test parsing a valid JSON array with multiple elements."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {
                "type": "character",
                "name": "Skrix",
                "context": "Goblin ally",
                "characters_involved": ["Shadowmere"],
            },
            {
                "type": "item",
                "name": "Crystal Shard",
                "context": "Glowing fragment found in cave",
                "characters_involved": [],
            },
        ])

        elements = _parse_extraction_response(response, turn_number=5, session_number=1)
        assert len(elements) == 2
        assert elements[0].name == "Skrix"
        assert elements[0].element_type == "character"
        assert elements[0].description == "Goblin ally"
        assert elements[0].turn_introduced == 5
        assert elements[0].session_introduced == 1
        assert elements[0].characters_involved == ["Shadowmere"]
        assert elements[1].name == "Crystal Shard"
        assert elements[1].element_type == "item"

    def test_json_wrapped_in_markdown_code_blocks(self) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""
        from memory import _parse_extraction_response

        response = '```json\n[{"type": "location", "name": "Dark Cave", "context": "Entrance to dungeon"}]\n```'

        elements = _parse_extraction_response(response, turn_number=3, session_number=1)
        assert len(elements) == 1
        assert elements[0].name == "Dark Cave"
        assert elements[0].element_type == "location"

    def test_empty_response_returns_empty_list(self) -> None:
        """Test empty response returns empty list."""
        from memory import _parse_extraction_response

        assert _parse_extraction_response("", turn_number=0, session_number=1) == []
        assert _parse_extraction_response("   ", turn_number=0, session_number=1) == []

    def test_malformed_json_returns_empty_list(self) -> None:
        """Test malformed JSON returns empty list (graceful degradation)."""
        from memory import _parse_extraction_response

        assert _parse_extraction_response(
            "not json at all", turn_number=0, session_number=1
        ) == []
        assert _parse_extraction_response(
            "[{invalid json}]", turn_number=0, session_number=1
        ) == []

    def test_mixed_valid_and_invalid_elements(self) -> None:
        """Test mixed valid and invalid elements: valid kept, invalid skipped."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {
                "type": "character",
                "name": "Valid NPC",
                "context": "A good NPC",
            },
            {
                "type": "character",
                "name": "",  # Empty name - will fail validation
                "context": "Bad element",
            },
            {
                "type": "item",
                "name": "Magic Ring",
                "context": "A ring of power",
            },
        ])

        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        # Valid NPC and Magic Ring should be kept, empty name skipped
        assert len(elements) == 2
        names = [e.name for e in elements]
        assert "Valid NPC" in names
        assert "Magic Ring" in names

    def test_empty_json_array(self) -> None:
        """Test empty JSON array returns empty list."""
        from memory import _parse_extraction_response

        elements = _parse_extraction_response("[]", turn_number=0, session_number=1)
        assert elements == []

    def test_uses_context_field_for_description(self) -> None:
        """Test that 'context' field maps to 'description'."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {
                "type": "event",
                "name": "Battle",
                "context": "Fought the dragon",
            },
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert elements[0].description == "Fought the dragon"

    def test_uses_description_field_as_fallback(self) -> None:
        """Test that 'description' field is used if 'context' is absent."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {
                "type": "event",
                "name": "Discovery",
                "description": "Found a secret door",
            },
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert elements[0].description == "Found a secret door"

    def test_defaults_to_event_type(self) -> None:
        """Test that missing type defaults to 'event'."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {
                "name": "Something Happened",
                "context": "An event occurred",
            },
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert len(elements) == 1
        assert elements[0].element_type == "event"

    def test_type_alias_npc_maps_to_character(self) -> None:
        """Test that LLM type 'npc' is mapped to 'character'."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {"type": "npc", "name": "Barkeep", "context": "Friendly tavern owner"},
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert len(elements) == 1
        assert elements[0].element_type == "character"

    def test_type_alias_place_maps_to_location(self) -> None:
        """Test that LLM type 'place' is mapped to 'location'."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {"type": "place", "name": "Dark Cave", "context": "Entrance to dungeon"},
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert len(elements) == 1
        assert elements[0].element_type == "location"

    def test_unknown_type_defaults_to_event(self) -> None:
        """Test that completely unknown type defaults to 'event'."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {"type": "random_unknown_type", "name": "Test", "context": "test"},
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert len(elements) == 1
        assert elements[0].element_type == "event"

    def test_characters_involved_as_string(self) -> None:
        """Test that characters_involved as a single string is handled."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {
                "type": "event",
                "name": "Battle",
                "context": "Fight occurred",
                "characters_involved": "Shadowmere",
            },
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert len(elements) == 1
        assert elements[0].characters_involved == ["Shadowmere"]

    def test_characters_involved_as_null(self) -> None:
        """Test that characters_involved as null is handled."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {
                "type": "event",
                "name": "Storm",
                "context": "A storm brews",
                "characters_involved": None,
            },
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert len(elements) == 1
        assert elements[0].characters_involved == []

    def test_characters_involved_as_number(self) -> None:
        """Test that characters_involved as a non-list/non-string is handled."""
        from memory import _parse_extraction_response

        response = json.dumps([
            {
                "type": "event",
                "name": "Discovery",
                "context": "Found something",
                "characters_involved": 42,
            },
        ])
        elements = _parse_extraction_response(response, turn_number=1, session_number=1)
        assert len(elements) == 1
        assert elements[0].characters_involved == []


# =============================================================================
# NarrativeElementExtractor Tests (Task 26)
# =============================================================================


class TestNarrativeElementExtractor:
    """Tests for NarrativeElementExtractor.extract_elements() with mocked LLM."""

    def test_successful_extraction(self) -> None:
        """Test successful extraction returns NarrativeElement list."""
        from memory import NarrativeElementExtractor

        extractor = NarrativeElementExtractor(provider="gemini", model="gemini-1.5-flash")

        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {
                "type": "character",
                "name": "Goblin Chief",
                "context": "Leader of the goblin warband",
                "characters_involved": ["Fighter", "Rogue"],
            }
        ])

        with patch.object(extractor, "_get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            elements = extractor.extract_elements(
                turn_content="The goblin chief approaches...",
                turn_number=5,
                session_id="001",
            )

        assert len(elements) == 1
        assert elements[0].name == "Goblin Chief"
        assert elements[0].element_type == "character"
        assert elements[0].turn_introduced == 5
        assert elements[0].session_introduced == 1

    def test_llm_failure_returns_empty_list(self) -> None:
        """Test LLM failure returns empty list (no exception raised)."""
        from memory import NarrativeElementExtractor

        extractor = NarrativeElementExtractor(provider="gemini", model="gemini-1.5-flash")

        with patch.object(extractor, "_get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("API connection failed")
            mock_get_llm.return_value = mock_llm

            elements = extractor.extract_elements(
                turn_content="Some content",
                turn_number=1,
                session_id="001",
            )

        assert elements == []

    def test_empty_content_returns_empty_list(self) -> None:
        """Test empty content returns empty list without calling LLM."""
        from memory import NarrativeElementExtractor

        extractor = NarrativeElementExtractor(provider="gemini", model="gemini-1.5-flash")

        elements = extractor.extract_elements(
            turn_content="",
            turn_number=1,
            session_id="001",
        )
        assert elements == []

    def test_whitespace_only_content_returns_empty_list(self) -> None:
        """Test whitespace-only content returns empty list without calling LLM."""
        from memory import NarrativeElementExtractor

        extractor = NarrativeElementExtractor(provider="gemini", model="gemini-1.5-flash")

        elements = extractor.extract_elements(
            turn_content="   \n  ",
            turn_number=1,
            session_id="001",
        )
        assert elements == []

    def test_content_truncation_at_max_chars(self) -> None:
        """Test content is truncated at MAX_CONTENT_CHARS."""
        from memory import NarrativeElementExtractor

        extractor = NarrativeElementExtractor(provider="gemini", model="gemini-1.5-flash")

        mock_response = MagicMock()
        mock_response.content = "[]"

        long_content = "x" * (extractor.MAX_CONTENT_CHARS + 1000)

        with patch.object(extractor, "_get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            extractor.extract_elements(
                turn_content=long_content,
                turn_number=1,
                session_id="001",
            )

            # Verify LLM was called (content was truncated, not rejected)
            mock_llm.invoke.assert_called_once()
            # Check the content passed to invoke was truncated
            call_args = mock_llm.invoke.call_args[0][0]
            # The messages list contains System + Human message
            human_msg_content = call_args[1].content
            # The human message includes prefix text + truncated content
            assert len(human_msg_content) < len(long_content)

    def test_lazy_llm_initialization(self) -> None:
        """Test LLM is lazily initialized."""
        from memory import NarrativeElementExtractor

        extractor = NarrativeElementExtractor(provider="gemini", model="gemini-1.5-flash")
        assert extractor._llm is None

    def test_session_id_number_parsing(self) -> None:
        """Test session_id is parsed to session_number correctly."""
        from memory import NarrativeElementExtractor

        extractor = NarrativeElementExtractor(provider="gemini", model="gemini-1.5-flash")

        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"type": "event", "name": "Test", "context": "test"}
        ])

        with patch.object(extractor, "_get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            elements = extractor.extract_elements(
                turn_content="Something happened",
                turn_number=1,
                session_id="003",
            )

        assert len(elements) == 1
        assert elements[0].session_introduced == 3


# =============================================================================
# extract_narrative_elements State Integration Tests (Task 27)
# =============================================================================


class TestExtractNarrativeElements:
    """Tests for extract_narrative_elements state integration."""

    def _make_state(self, session_id: str = "001") -> GameState:
        """Helper to create a minimal GameState for testing."""
        state = create_initial_game_state()
        state["session_id"] = session_id
        return state

    @patch("memory._extractor_cache", {})
    @patch("memory.get_config")
    def test_elements_merged_into_existing_store(
        self, mock_config: MagicMock
    ) -> None:
        """Test extracted elements are merged into existing NarrativeElementStore."""
        from memory import NarrativeElementStore, extract_narrative_elements

        # Setup config mock
        mock_cfg = MagicMock()
        mock_cfg.agents.extractor.provider = "gemini"
        mock_cfg.agents.extractor.model = "gemini-1.5-flash"
        mock_config.return_value = mock_cfg

        # Pre-populate store with one existing element
        existing = create_narrative_element(
            element_type="character", name="Old NPC", turn_introduced=1
        )
        state = self._make_state()
        state["narrative_elements"] = {
            "001": NarrativeElementStore(elements=[existing])
        }

        # Mock the extractor to return new elements
        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"type": "item", "name": "New Sword", "context": "Found in chest"}
        ])

        with patch("memory.NarrativeElementExtractor._get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            result = extract_narrative_elements(state, "Found a sword in the chest", 5)

        narr = result["narrative_elements"]
        assert "001" in narr
        assert len(narr["001"].elements) == 2
        assert narr["001"].elements[0].name == "Old NPC"
        assert narr["001"].elements[1].name == "New Sword"

    @patch("memory._extractor_cache", {})
    @patch("memory.get_config")
    def test_new_store_created_if_session_not_present(
        self, mock_config: MagicMock
    ) -> None:
        """Test new NarrativeElementStore is created if session not present."""
        from memory import extract_narrative_elements

        mock_cfg = MagicMock()
        mock_cfg.agents.extractor.provider = "gemini"
        mock_cfg.agents.extractor.model = "gemini-1.5-flash"
        mock_config.return_value = mock_cfg

        state = self._make_state(session_id="002")
        # No narrative_elements at all
        state["narrative_elements"] = {}

        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"type": "location", "name": "Dark Forest", "context": "Entered forest"}
        ])

        with patch("memory.NarrativeElementExtractor._get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            result = extract_narrative_elements(state, "Entered the dark forest", 1)

        narr = result["narrative_elements"]
        assert "002" in narr
        assert len(narr["002"].elements) == 1
        assert narr["002"].elements[0].name == "Dark Forest"


# =============================================================================
# Serialization Round-Trip Tests (Task 28)
# =============================================================================


class TestNarrativeElementSerialization:
    """Tests for serialization/deserialization of narrative_elements."""

    def test_serialize_deserialize_round_trip(self) -> None:
        """Test serialize -> deserialize preserves all NarrativeElement fields."""
        element = NarrativeElement(
            id="abc123hex",
            element_type="character",
            name="Skrix the Goblin",
            description="Befriended by party",
            turn_introduced=5,
            session_introduced=2,
            turns_referenced=[5, 8],
            characters_involved=["Shadowmere", "Aldric"],
            resolved=False,
        )
        store = NarrativeElementStore(elements=[element])

        state = create_initial_game_state()
        state["narrative_elements"] = {"001": store}

        # Serialize
        json_str = serialize_game_state(state)

        # Deserialize
        restored = deserialize_game_state(json_str)

        # Verify
        assert "001" in restored["narrative_elements"]
        restored_store = restored["narrative_elements"]["001"]
        assert len(restored_store.elements) == 1

        restored_el = restored_store.elements[0]
        assert restored_el.id == "abc123hex"
        assert restored_el.element_type == "character"
        assert restored_el.name == "Skrix the Goblin"
        assert restored_el.description == "Befriended by party"
        assert restored_el.turn_introduced == 5
        assert restored_el.session_introduced == 2
        assert restored_el.turns_referenced == [5, 8]
        assert restored_el.characters_involved == ["Shadowmere", "Aldric"]
        assert restored_el.resolved is False

    def test_backward_compatibility_no_narrative_elements(self) -> None:
        """Test backward compatibility with old checkpoints without narrative_elements."""
        # Simulate old checkpoint JSON without narrative_elements key
        old_checkpoint = {
            "ground_truth_log": [],
            "turn_queue": ["dm"],
            "current_turn": "dm",
            "agent_memories": {},
            "game_config": {"combat_mode": "Narrative", "summarizer_provider": "gemini",
                            "summarizer_model": "gemini-1.5-flash", "party_size": 4},
            "dm_config": {"name": "Dungeon Master", "provider": "gemini",
                          "model": "gemini-1.5-flash", "token_limit": 8000,
                          "color": "#D4A574"},
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "summarization_in_progress": False,
            "selected_module": None,
            "character_sheets": {},
            "agent_secrets": {},
            # No narrative_elements key!
        }

        json_str = json.dumps(old_checkpoint)
        state = deserialize_game_state(json_str)

        # Should have empty narrative_elements dict
        assert "narrative_elements" in state
        assert state["narrative_elements"] == {}

    def test_multiple_sessions_serialization(self) -> None:
        """Test serialization with multiple sessions in narrative_elements."""
        el1 = create_narrative_element(
            element_type="character", name="NPC 1", turn_introduced=1
        )
        el2 = create_narrative_element(
            element_type="item", name="Item 1", turn_introduced=5
        )

        state = create_initial_game_state()
        state["narrative_elements"] = {
            "001": NarrativeElementStore(elements=[el1]),
            "002": NarrativeElementStore(elements=[el2]),
        }

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        assert "001" in restored["narrative_elements"]
        assert "002" in restored["narrative_elements"]
        assert len(restored["narrative_elements"]["001"].elements) == 1
        assert len(restored["narrative_elements"]["002"].elements) == 1
        assert restored["narrative_elements"]["001"].elements[0].name == "NPC 1"
        assert restored["narrative_elements"]["002"].elements[0].name == "Item 1"


# =============================================================================
# dm_turn Integration Tests (Task 29)
# =============================================================================


class TestDmTurnNarrativeElements:
    """Integration test for dm_turn producing narrative_elements."""

    @patch("memory.extract_narrative_elements")
    @patch("agents.create_dm_agent")
    def test_dm_turn_calls_extraction(
        self,
        mock_create_dm: MagicMock,
        mock_extract: MagicMock,
    ) -> None:
        """Test dm_turn calls narrative element extraction on response."""
        from agents import dm_turn

        # Setup mock DM agent
        mock_response = MagicMock()
        mock_response.content = "The tavern is dark and smoky."
        mock_response.tool_calls = None
        mock_dm = MagicMock()
        mock_dm.invoke.return_value = mock_response
        mock_create_dm.return_value = mock_dm

        # Setup extraction mock
        extracted_store = NarrativeElementStore(
            elements=[
                create_narrative_element(
                    element_type="location",
                    name="Smoky Tavern",
                    turn_introduced=1,
                )
            ]
        )
        mock_extract.return_value = {
            "narrative_elements": {"001": extracted_store},
            "callback_database": extracted_store,
        }

        # Create minimal state
        state = create_initial_game_state()
        state["dm_config"] = DMConfig()
        state["agent_memories"]["dm"] = AgentMemory(token_limit=8000)

        result = dm_turn(state)

        # Verify extraction was called
        mock_extract.assert_called_once()
        # Verify narrative_elements in returned state
        assert "narrative_elements" in result
        assert "001" in result["narrative_elements"]

    @patch("agents.create_dm_agent")
    def test_dm_turn_extraction_failure_non_blocking(
        self, mock_create_dm: MagicMock
    ) -> None:
        """Test dm_turn continues when extraction fails."""
        from agents import dm_turn

        # Setup mock DM agent
        mock_response = MagicMock()
        mock_response.content = "The adventure continues."
        mock_response.tool_calls = None
        mock_dm = MagicMock()
        mock_dm.invoke.return_value = mock_response
        mock_create_dm.return_value = mock_dm

        # Make extraction raise an exception
        with patch("memory.extract_narrative_elements", side_effect=RuntimeError("boom")):
            state = create_initial_game_state()
            state["dm_config"] = DMConfig()
            state["agent_memories"]["dm"] = AgentMemory(token_limit=8000)

            # Should NOT raise
            result = dm_turn(state)

        # State should still be valid
        assert "[DM]: The adventure continues." in result["ground_truth_log"]


# =============================================================================
# pc_turn Integration Tests (Task 30)
# =============================================================================


class TestPcTurnNarrativeElements:
    """Integration test for pc_turn producing narrative_elements."""

    @patch("memory.extract_narrative_elements")
    @patch("agents.create_pc_agent")
    def test_pc_turn_calls_extraction(
        self,
        mock_create_pc: MagicMock,
        mock_extract: MagicMock,
    ) -> None:
        """Test pc_turn calls narrative element extraction on response."""
        from agents import pc_turn

        # Setup mock PC agent
        mock_response = MagicMock()
        mock_response.content = "I draw my sword and charge."
        mock_response.tool_calls = None
        mock_pc = MagicMock()
        mock_pc.invoke.return_value = mock_response
        mock_create_pc.return_value = mock_pc

        # Setup extraction mock (Story 11.2: returns dict with both keys)
        mock_extract.return_value = {
            "narrative_elements": {"001": NarrativeElementStore()},
            "callback_database": NarrativeElementStore(),
        }

        # Create minimal state with character
        state = create_initial_game_state()
        state["characters"] = {
            "fighter": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                personality="Brave",
                color="#FF0000",
            ),
        }
        state["agent_memories"]["fighter"] = AgentMemory(token_limit=4000)

        result = pc_turn(state, "fighter")

        # Verify extraction was called
        mock_extract.assert_called_once()
        # Verify narrative_elements in returned state
        assert "narrative_elements" in result
        # Verify callback_database in returned state (Story 11.2)
        assert "callback_database" in result

    @patch("agents.create_pc_agent")
    def test_pc_turn_extraction_failure_non_blocking(
        self, mock_create_pc: MagicMock
    ) -> None:
        """Test pc_turn continues when extraction fails."""
        from agents import pc_turn

        # Setup mock PC agent
        mock_response = MagicMock()
        mock_response.content = "I stand ready."
        mock_response.tool_calls = None
        mock_pc = MagicMock()
        mock_pc.invoke.return_value = mock_response
        mock_create_pc.return_value = mock_pc

        with patch("memory.extract_narrative_elements", side_effect=RuntimeError("fail")):
            state = create_initial_game_state()
            state["characters"] = {
                "rogue": CharacterConfig(
                    name="Shadow",
                    character_class="Rogue",
                    personality="Sneaky",
                    color="#00FF00",
                ),
            }
            state["agent_memories"]["rogue"] = AgentMemory(token_limit=4000)

            # Should NOT raise
            result = pc_turn(state, "rogue")

        # State should still be valid
        assert any("Shadow" in entry for entry in result["ground_truth_log"])


# =============================================================================
# Configuration Tests (Task 19-20)
# =============================================================================


class TestExtractorConfig:
    """Tests for extractor configuration in config.py."""

    def test_agents_config_has_extractor(self) -> None:
        """Test AgentsConfig includes extractor field."""
        from config import AgentsConfig

        config = AgentsConfig()
        assert hasattr(config, "extractor")
        assert config.extractor.provider == "gemini"
        assert config.extractor.model == "gemini-1.5-flash"
        assert config.extractor.token_limit == 4000

    def test_app_config_loads_extractor(self) -> None:
        """Test AppConfig.load() includes extractor config."""
        import config as config_module
        from config import get_config

        original_config = config_module._config
        try:
            config_module._config = None

            cfg = get_config()
            assert hasattr(cfg.agents, "extractor")
            assert cfg.agents.extractor.provider == "gemini"
        finally:
            # Always reset singleton, even if test fails
            config_module._config = original_config
