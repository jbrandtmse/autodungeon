"""Tests for Story 11-4: Callback Detection.

Tests the CallbackEntry and CallbackLog models, detection logic,
integration with extraction pipeline, agent turn propagation,
and persistence round-trip.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from models import (
    AgentMemory,
    CallbackEntry,
    CallbackLog,
    CharacterConfig,
    DMConfig,
    GameState,
    NarrativeElement,
    NarrativeElementStore,
    create_callback_entry,
    create_initial_game_state,
    create_narrative_element,
)
from persistence import (
    deserialize_game_state,
    serialize_game_state,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_element(
    name: str = "Skrix the Goblin",
    element_type: str = "character",
    description: str = "Befriended by party, promised cave information",
    turn_introduced: int = 5,
    session_introduced: int = 1,
    characters_involved: list[str] | None = None,
    resolved: bool = False,
    last_referenced_turn: int | None = None,
    turns_referenced: list[int] | None = None,
) -> NarrativeElement:
    """Create a test NarrativeElement."""
    elem = create_narrative_element(
        element_type=element_type,  # type: ignore[arg-type]
        name=name,
        description=description,
        turn_introduced=turn_introduced,
        session_introduced=session_introduced,
        characters_involved=characters_involved or ["Shadowmere"],
    )
    if resolved:
        elem.resolved = True
    if last_referenced_turn is not None:
        elem.last_referenced_turn = last_referenced_turn
    if turns_referenced is not None:
        elem.turns_referenced = turns_referenced
    return elem


def _make_callback_entry(
    element_id: str = "abc123",
    element_name: str = "Skrix the Goblin",
    element_type: str = "character",
    turn_detected: int = 30,
    turn_gap: int = 25,
    match_type: str = "name_exact",
    match_context: str = "...Skrix the Goblin waving...",
    is_story_moment: bool = True,
    session_detected: int = 1,
) -> CallbackEntry:
    """Create a test CallbackEntry."""
    import uuid

    return CallbackEntry(
        id=uuid.uuid4().hex,
        element_id=element_id,
        element_name=element_name,
        element_type=element_type,
        turn_detected=turn_detected,
        turn_gap=turn_gap,
        match_type=match_type,  # type: ignore[arg-type]
        match_context=match_context,
        is_story_moment=is_story_moment,
        session_detected=session_detected,
    )


def _make_game_state(**overrides: object) -> GameState:
    """Create a minimal GameState for testing."""
    base = create_initial_game_state()
    for key, value in overrides.items():
        base[key] = value  # type: ignore[literal-required]
    return base


# =============================================================================
# Task 28: CallbackEntry Model Tests
# =============================================================================


class TestCallbackEntryModel:
    """Tests for the CallbackEntry Pydantic model."""

    def test_valid_construction_all_fields(self) -> None:
        """Test CallbackEntry can be created with all fields."""
        entry = CallbackEntry(
            id="abc123",
            element_id="elem456",
            element_name="Skrix the Goblin",
            element_type="character",
            turn_detected=30,
            turn_gap=25,
            match_type="name_exact",
            match_context="...Skrix waving...",
            is_story_moment=True,
            session_detected=1,
        )
        assert entry.id == "abc123"
        assert entry.element_id == "elem456"
        assert entry.element_name == "Skrix the Goblin"
        assert entry.element_type == "character"
        assert entry.turn_detected == 30
        assert entry.turn_gap == 25
        assert entry.match_type == "name_exact"
        assert entry.match_context == "...Skrix waving..."
        assert entry.is_story_moment is True
        assert entry.session_detected == 1

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        entry = CallbackEntry(
            id="abc123",
            element_id="elem456",
            element_name="Test",
            element_type="item",
            turn_detected=5,
            turn_gap=3,
            match_type="name_fuzzy",
        )
        assert entry.is_story_moment is False
        assert entry.match_context == ""
        assert entry.session_detected == 1

    def test_turn_detected_ge_zero(self) -> None:
        """Test turn_detected must be >= 0."""
        with pytest.raises(ValidationError):
            CallbackEntry(
                id="abc123",
                element_id="elem456",
                element_name="Test",
                element_type="item",
                turn_detected=-1,
                turn_gap=0,
                match_type="name_exact",
            )

    def test_turn_gap_ge_zero(self) -> None:
        """Test turn_gap must be >= 0."""
        with pytest.raises(ValidationError):
            CallbackEntry(
                id="abc123",
                element_id="elem456",
                element_name="Test",
                element_type="item",
                turn_detected=5,
                turn_gap=-1,
                match_type="name_exact",
            )

    def test_match_type_literal_restriction(self) -> None:
        """Test match_type must be one of the valid literal values."""
        with pytest.raises(ValidationError):
            CallbackEntry(
                id="abc123",
                element_id="elem456",
                element_name="Test",
                element_type="item",
                turn_detected=5,
                turn_gap=3,
                match_type="invalid_type",  # type: ignore[arg-type]
            )

    def test_all_match_types_valid(self) -> None:
        """Test all three valid match types."""
        for match_type in ("name_exact", "name_fuzzy", "description_keyword"):
            entry = CallbackEntry(
                id="abc123",
                element_id="elem456",
                element_name="Test",
                element_type="item",
                turn_detected=5,
                turn_gap=3,
                match_type=match_type,  # type: ignore[arg-type]
            )
            assert entry.match_type == match_type

    def test_session_detected_ge_one(self) -> None:
        """Test session_detected must be >= 1."""
        with pytest.raises(ValidationError):
            CallbackEntry(
                id="abc123",
                element_id="elem456",
                element_name="Test",
                element_type="item",
                turn_detected=5,
                turn_gap=3,
                match_type="name_exact",
                session_detected=0,
            )


# =============================================================================
# Task 29: CallbackLog Model Tests
# =============================================================================


class TestCallbackLogModel:
    """Tests for the CallbackLog Pydantic model."""

    def test_empty_log(self) -> None:
        """Test empty CallbackLog has empty entries list."""
        log = CallbackLog()
        assert log.entries == []
        assert log.get_by_element("any") == []
        assert log.get_story_moments() == []
        assert log.get_by_turn(5) == []
        assert log.get_recent() == []

    def test_add_entry(self) -> None:
        """Test add_entry appends to entries list."""
        log = CallbackLog()
        entry = _make_callback_entry()
        log.add_entry(entry)
        assert len(log.entries) == 1
        assert log.entries[0] is entry

    def test_get_by_element(self) -> None:
        """Test get_by_element filters by element_id."""
        log = CallbackLog()
        entry1 = _make_callback_entry(element_id="elem1")
        entry2 = _make_callback_entry(element_id="elem2")
        entry3 = _make_callback_entry(element_id="elem1")
        log.add_entry(entry1)
        log.add_entry(entry2)
        log.add_entry(entry3)

        results = log.get_by_element("elem1")
        assert len(results) == 2
        assert all(e.element_id == "elem1" for e in results)

        results = log.get_by_element("elem2")
        assert len(results) == 1

        results = log.get_by_element("nonexistent")
        assert len(results) == 0

    def test_get_story_moments(self) -> None:
        """Test get_story_moments returns only entries with is_story_moment=True."""
        log = CallbackLog()
        entry1 = _make_callback_entry(is_story_moment=True, turn_gap=25)
        entry2 = _make_callback_entry(is_story_moment=False, turn_gap=5)
        entry3 = _make_callback_entry(is_story_moment=True, turn_gap=30)
        log.add_entry(entry1)
        log.add_entry(entry2)
        log.add_entry(entry3)

        moments = log.get_story_moments()
        assert len(moments) == 2
        assert all(m.is_story_moment for m in moments)

    def test_get_by_turn(self) -> None:
        """Test get_by_turn filters by turn_detected."""
        log = CallbackLog()
        entry1 = _make_callback_entry(turn_detected=10)
        entry2 = _make_callback_entry(turn_detected=15)
        entry3 = _make_callback_entry(turn_detected=10)
        log.add_entry(entry1)
        log.add_entry(entry2)
        log.add_entry(entry3)

        results = log.get_by_turn(10)
        assert len(results) == 2

        results = log.get_by_turn(15)
        assert len(results) == 1

        results = log.get_by_turn(99)
        assert len(results) == 0

    def test_get_recent_default_limit(self) -> None:
        """Test get_recent returns most recent with default limit of 10."""
        log = CallbackLog()
        for i in range(15):
            log.add_entry(_make_callback_entry(turn_detected=i))

        recent = log.get_recent()
        assert len(recent) == 10
        # Should be sorted by turn_detected descending
        assert recent[0].turn_detected == 14
        assert recent[-1].turn_detected == 5

    def test_get_recent_custom_limit(self) -> None:
        """Test get_recent with custom limit."""
        log = CallbackLog()
        for i in range(5):
            log.add_entry(_make_callback_entry(turn_detected=i))

        recent = log.get_recent(limit=3)
        assert len(recent) == 3
        assert recent[0].turn_detected == 4

    def test_story_moment_threshold(self) -> None:
        """Test STORY_MOMENT_THRESHOLD class constant."""
        assert CallbackLog.STORY_MOMENT_THRESHOLD == 20


# =============================================================================
# Task 30: create_callback_entry Factory Tests
# =============================================================================


class TestCreateCallbackEntry:
    """Tests for the create_callback_entry factory function."""

    def test_generates_unique_id(self) -> None:
        """Test that each entry gets a unique UUID id."""
        element = _make_element()
        entry1 = create_callback_entry(
            element=element,
            turn_detected=30,
            match_type="name_exact",
            match_context="test",
            session_detected=1,
        )
        entry2 = create_callback_entry(
            element=element,
            turn_detected=31,
            match_type="name_exact",
            match_context="test",
            session_detected=1,
        )
        assert entry1.id != entry2.id
        assert len(entry1.id) == 32  # UUID hex is 32 chars

    def test_computes_turn_gap_correctly(self) -> None:
        """Test turn_gap = turn_detected - element.last_referenced_turn."""
        element = _make_element(turn_introduced=5, last_referenced_turn=10)
        entry = create_callback_entry(
            element=element,
            turn_detected=30,
            match_type="name_exact",
            match_context="test",
            session_detected=1,
        )
        assert entry.turn_gap == 20  # 30 - 10

    def test_story_moment_flagged_ge_20(self) -> None:
        """Test is_story_moment=True when turn_gap >= 20."""
        element = _make_element(turn_introduced=5, last_referenced_turn=5)
        entry = create_callback_entry(
            element=element,
            turn_detected=25,
            match_type="name_exact",
            match_context="test",
            session_detected=1,
        )
        assert entry.turn_gap == 20
        assert entry.is_story_moment is True

    def test_story_moment_not_flagged_lt_20(self) -> None:
        """Test is_story_moment=False when turn_gap < 20."""
        element = _make_element(turn_introduced=5, last_referenced_turn=10)
        entry = create_callback_entry(
            element=element,
            turn_detected=29,
            match_type="name_exact",
            match_context="test",
            session_detected=1,
        )
        assert entry.turn_gap == 19
        assert entry.is_story_moment is False

    def test_denormalizes_element_name_and_type(self) -> None:
        """Test element_name and element_type are copied from element."""
        element = _make_element(
            name="Crystal Shard of Binding",
            element_type="item",
        )
        entry = create_callback_entry(
            element=element,
            turn_detected=30,
            match_type="name_exact",
            match_context="test",
            session_detected=1,
        )
        assert entry.element_name == "Crystal Shard of Binding"
        assert entry.element_type == "item"
        assert entry.element_id == element.id

    def test_turn_gap_never_negative(self) -> None:
        """Test turn_gap is clamped to 0 even if turn_detected < last_referenced."""
        element = _make_element(turn_introduced=30, last_referenced_turn=30)
        entry = create_callback_entry(
            element=element,
            turn_detected=25,  # Earlier than last_referenced
            match_type="name_exact",
            match_context="test",
            session_detected=1,
        )
        assert entry.turn_gap == 0


# =============================================================================
# Task 31: _normalize_text Tests
# =============================================================================


class TestNormalizeText:
    """Tests for the _normalize_text helper."""

    def test_lowercase(self) -> None:
        """Test text is lowercased."""
        from memory import _normalize_text

        assert _normalize_text("Hello WORLD") == "hello world"

    def test_punctuation_stripped(self) -> None:
        """Test punctuation is replaced with spaces."""
        from memory import _normalize_text

        result = _normalize_text("Hello, world! How's it going?")
        assert "," not in result
        assert "!" not in result
        assert "'" not in result
        assert "?" not in result

    def test_whitespace_collapsed(self) -> None:
        """Test multiple whitespace characters are collapsed."""
        from memory import _normalize_text

        result = _normalize_text("hello   world\t\ntest")
        assert result == "hello world test"

    def test_empty_string(self) -> None:
        """Test empty string returns empty string."""
        from memory import _normalize_text

        assert _normalize_text("") == ""


# =============================================================================
# Task 32: _extract_match_context Tests
# =============================================================================


class TestExtractMatchContext:
    """Tests for the _extract_match_context helper."""

    def test_centered_extraction(self) -> None:
        """Test context is centered around match position."""
        from memory import _extract_match_context

        content = "A" * 50 + "MATCH" + "B" * 50
        context = _extract_match_context(content, 50, max_length=30)
        assert "MATCH" in context
        assert len(context) <= 40  # 30 + ellipses overhead

    def test_respects_max_length(self) -> None:
        """Test context does not exceed max_length (plus ellipsis)."""
        from memory import _extract_match_context

        content = "X" * 1000
        context = _extract_match_context(content, 500, max_length=50)
        # The raw excerpt is max 50 chars, plus up to 6 chars of "..." on each side
        assert len(context) <= 56

    def test_ellipsis_when_truncated_start(self) -> None:
        """Test ellipsis added when match is not at the beginning."""
        from memory import _extract_match_context

        content = "X" * 200 + "MATCH" + "Y" * 200
        context = _extract_match_context(content, 200, max_length=50)
        assert context.startswith("...")

    def test_ellipsis_when_truncated_end(self) -> None:
        """Test ellipsis added when match is not at the end."""
        from memory import _extract_match_context

        content = "X" * 200 + "MATCH" + "Y" * 200
        context = _extract_match_context(content, 200, max_length=50)
        assert context.endswith("...")

    def test_no_ellipsis_at_beginning(self) -> None:
        """Test no leading ellipsis when match is at the beginning."""
        from memory import _extract_match_context

        content = "MATCH" + "X" * 200
        context = _extract_match_context(content, 0, max_length=50)
        assert not context.startswith("...")

    def test_no_ellipsis_at_end(self) -> None:
        """Test no trailing ellipsis when match is near the end."""
        from memory import _extract_match_context

        content = "X" * 10 + "MATCH"
        context = _extract_match_context(content, 10, max_length=200)
        assert not context.endswith("...")

    def test_short_content(self) -> None:
        """Test short content without truncation."""
        from memory import _extract_match_context

        content = "short text"
        context = _extract_match_context(content, 0, max_length=200)
        assert context == "short text"


# =============================================================================
# Task 33: _detect_name_match Tests
# =============================================================================


class TestDetectNameMatch:
    """Tests for the _detect_name_match function."""

    def test_exact_match_case_insensitive(self) -> None:
        """Test exact name match is case-insensitive."""
        from memory import _detect_name_match, _normalize_text

        element = _make_element(name="Skrix the Goblin")
        content = "The party spots Skrix the Goblin near the cave."
        normalized = _normalize_text(content)

        result = _detect_name_match(element, normalized, content)
        assert result is not None
        match_type, match_context = result
        assert match_type == "name_exact"
        assert "Skrix" in match_context

    def test_fuzzy_match_distinctive_word(self) -> None:
        """Test fuzzy match on longest distinctive word."""
        from memory import _detect_name_match, _normalize_text

        element = _make_element(name="Skrix the Goblin")
        content = "They remember Skrix from the last encounter."
        normalized = _normalize_text(content)

        result = _detect_name_match(element, normalized, content)
        assert result is not None
        match_type, match_context = result
        # "Skrix" is most distinctive word (not "the" or "goblin" which would also match)
        # But "Skrix" as standalone word should match via fuzzy
        # Actually "skrix the goblin" won't be in normalized content exactly,
        # but "skrix" as distinctive word should match
        assert match_type in ("name_exact", "name_fuzzy")

    def test_short_name_skipped(self) -> None:
        """Test names shorter than 3 chars are skipped."""
        from memory import _detect_name_match, _normalize_text

        element = _make_element(name="Bo")
        content = "Bo was standing near the door."
        normalized = _normalize_text(content)

        result = _detect_name_match(element, normalized, content)
        assert result is None

    def test_name_not_present_returns_none(self) -> None:
        """Test no match when name is not in content."""
        from memory import _detect_name_match, _normalize_text

        element = _make_element(name="Skrix the Goblin")
        content = "The party explores the dark cavern."
        normalized = _normalize_text(content)

        result = _detect_name_match(element, normalized, content)
        assert result is None

    def test_multiword_distinctive_word_match(self) -> None:
        """Test multi-word name matches on distinctive word."""
        from memory import _detect_name_match, _normalize_text

        element = _make_element(name="Moonweaver the Enchantress")
        content = "They recall the teachings of Moonweaver."
        normalized = _normalize_text(content)

        result = _detect_name_match(element, normalized, content)
        assert result is not None
        match_type, _ = result
        assert match_type in ("name_exact", "name_fuzzy")

    def test_returns_correct_match_type_and_context(self) -> None:
        """Test return value has correct structure."""
        from memory import _detect_name_match, _normalize_text

        element = _make_element(name="Crystal Shard")
        content = "She picks up the Crystal Shard from the altar."
        normalized = _normalize_text(content)

        result = _detect_name_match(element, normalized, content)
        assert result is not None
        match_type, match_context = result
        assert match_type == "name_exact"
        assert isinstance(match_context, str)
        assert len(match_context) > 0


# =============================================================================
# Task 34: _detect_description_match Tests
# =============================================================================


class TestDetectDescriptionMatch:
    """Tests for the _detect_description_match function."""

    def test_two_plus_keywords_match(self) -> None:
        """Test match when 2+ significant keywords appear in content."""
        from memory import _detect_description_match, _normalize_text

        element = _make_element(
            name="Hidden Cave",
            description="Ancient underground sanctuary guarded by stone golems",
        )
        content = "The stone guardians stand before the ancient sanctuary."
        normalized = _normalize_text(content)

        result = _detect_description_match(element, normalized, content)
        assert result is not None
        match_type, _ = result
        assert match_type == "description_keyword"

    def test_one_keyword_no_match(self) -> None:
        """Test no match when only 1 keyword appears."""
        from memory import _detect_description_match, _normalize_text

        element = _make_element(
            name="Hidden Cave",
            description="Ancient underground sanctuary guarded by stone golems",
        )
        content = "The stone walls echo with emptiness."
        normalized = _normalize_text(content)

        result = _detect_description_match(element, normalized, content)
        assert result is None

    def test_stop_words_excluded(self) -> None:
        """Test stop words are excluded from keyword extraction."""
        from memory import _detect_description_match, _normalize_text

        element = _make_element(
            name="Test Element",
            description="They have been there with their party character",
        )
        content = "They have been there with their party character."
        normalized = _normalize_text(content)

        # All words in description are stop words, so no keywords extracted
        result = _detect_description_match(element, normalized, content)
        assert result is None

    def test_empty_description_returns_none(self) -> None:
        """Test empty description returns None."""
        from memory import _detect_description_match, _normalize_text

        element = _make_element(name="Test", description="")
        content = "Some content here."
        normalized = _normalize_text(content)

        result = _detect_description_match(element, normalized, content)
        assert result is None

    def test_short_description_no_keywords(self) -> None:
        """Test description too short for significant keywords."""
        from memory import _detect_description_match, _normalize_text

        element = _make_element(name="Test", description="is a cat")
        content = "is a cat appears"
        normalized = _normalize_text(content)

        result = _detect_description_match(element, normalized, content)
        assert result is None

    def test_returns_description_keyword_type(self) -> None:
        """Test match_type is always 'description_keyword'."""
        from memory import _detect_description_match, _normalize_text

        element = _make_element(
            name="Artifact",
            description="Powerful magical crystal embedded with arcane runes",
        )
        content = "The crystal glows with arcane energy and ancient runes."
        normalized = _normalize_text(content)

        result = _detect_description_match(element, normalized, content)
        assert result is not None
        assert result[0] == "description_keyword"


# =============================================================================
# Task 35: detect_callbacks Tests
# =============================================================================


class TestDetectCallbacks:
    """Tests for the detect_callbacks function."""

    def test_name_based_callback_detected(self) -> None:
        """Test detection of name-based callback on active element."""
        from memory import detect_callbacks

        element = _make_element(name="Skrix the Goblin", turn_introduced=5)
        store = NarrativeElementStore(elements=[element])

        callbacks = detect_callbacks(
            "The party spots Skrix the Goblin near the cave entrance.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        assert len(callbacks) == 1
        assert callbacks[0].match_type == "name_exact"
        assert callbacks[0].element_name == "Skrix the Goblin"

    def test_description_keyword_callback_detected(self) -> None:
        """Test detection of description-keyword callback."""
        from memory import detect_callbacks

        element = _make_element(
            name="Unknown Entity",
            description="Ancient underground sanctuary guarded by stone golems",
            turn_introduced=5,
        )
        store = NarrativeElementStore(elements=[element])

        callbacks = detect_callbacks(
            "The stone guardians protect the ancient sanctuary entrance.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        assert len(callbacks) == 1
        assert callbacks[0].match_type == "description_keyword"

    def test_skips_resolved_elements(self) -> None:
        """Test resolved elements are not detected."""
        from memory import detect_callbacks

        element = _make_element(name="Skrix the Goblin", turn_introduced=5, resolved=True)
        store = NarrativeElementStore(elements=[element])

        callbacks = detect_callbacks(
            "Skrix the Goblin appears again.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        assert len(callbacks) == 0

    def test_skips_self_reference(self) -> None:
        """Test elements introduced on current turn are skipped."""
        from memory import detect_callbacks

        element = _make_element(name="Skrix the Goblin", turn_introduced=30)
        store = NarrativeElementStore(elements=[element])

        callbacks = detect_callbacks(
            "Skrix the Goblin appears for the first time.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        assert len(callbacks) == 0

    def test_skips_already_referenced_turn(self) -> None:
        """Test elements already referenced on this turn are skipped."""
        from memory import detect_callbacks

        element = _make_element(
            name="Skrix the Goblin",
            turn_introduced=5,
            turns_referenced=[5, 30],
        )
        store = NarrativeElementStore(elements=[element])

        callbacks = detect_callbacks(
            "Skrix the Goblin appears again.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        assert len(callbacks) == 0

    def test_name_match_priority_no_duplicates(self) -> None:
        """Test name match takes priority, no duplicate per element."""
        from memory import detect_callbacks

        element = _make_element(
            name="Skrix the Goblin",
            description="A goblin befriended by the party near the entrance",
            turn_introduced=5,
        )
        store = NarrativeElementStore(elements=[element])

        callbacks = detect_callbacks(
            "Skrix the Goblin stands near the entrance, the goblin looks happy.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        # Only one detection per element per turn
        assert len(callbacks) == 1
        assert callbacks[0].match_type == "name_exact"

    def test_story_moment_flagged_for_20_plus_gap(self) -> None:
        """Test story moment flagged when turn_gap >= 20."""
        from memory import detect_callbacks

        element = _make_element(
            name="Skrix the Goblin",
            turn_introduced=5,
            last_referenced_turn=5,
        )
        store = NarrativeElementStore(elements=[element])

        callbacks = detect_callbacks(
            "Skrix the Goblin appears at the gate.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        assert len(callbacks) == 1
        assert callbacks[0].is_story_moment is True
        assert callbacks[0].turn_gap == 25

    def test_story_moment_not_flagged_for_small_gap(self) -> None:
        """Test story moment not flagged when turn_gap < 20."""
        from memory import detect_callbacks

        element = _make_element(
            name="Skrix the Goblin",
            turn_introduced=5,
            last_referenced_turn=20,
        )
        store = NarrativeElementStore(elements=[element])

        callbacks = detect_callbacks(
            "Skrix the Goblin appears at the gate.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        assert len(callbacks) == 1
        assert callbacks[0].is_story_moment is False
        assert callbacks[0].turn_gap == 10

    def test_empty_content_returns_empty(self) -> None:
        """Test empty content returns empty list."""
        from memory import detect_callbacks

        element = _make_element()
        store = NarrativeElementStore(elements=[element])

        assert detect_callbacks("", 30, 1, store) == []
        assert detect_callbacks("   ", 30, 1, store) == []

    def test_empty_database_returns_empty(self) -> None:
        """Test empty callback_database returns empty list."""
        from memory import detect_callbacks

        store = NarrativeElementStore()
        callbacks = detect_callbacks("Some content", 30, 1, store)
        assert callbacks == []

    def test_graceful_degradation_on_error(self) -> None:
        """Test detection returns empty list on error, no exception."""
        from memory import detect_callbacks

        # Pass a broken store that will cause an error
        bad_store = MagicMock()
        bad_store.get_active.side_effect = RuntimeError("test error")

        callbacks = detect_callbacks("test content", 30, 1, bad_store)
        assert callbacks == []


# =============================================================================
# Task 36: extract_narrative_elements Integration Tests
# =============================================================================


class TestExtractNarrativeElementsIntegration:
    """Tests for callback detection integration in extract_narrative_elements."""

    @patch("memory._extractor_cache", {})
    @patch("memory.get_config")
    def test_extraction_result_includes_callback_log(
        self, mock_config: MagicMock
    ) -> None:
        """Test extraction result includes updated callback_log."""
        # Setup mock config
        mock_cfg = MagicMock()
        mock_cfg.agents.extractor.provider = "gemini"
        mock_cfg.agents.extractor.model = "gemini-1.5-flash"
        mock_config.return_value = mock_cfg

        # Create element in callback_database
        element = _make_element(
            name="Skrix the Goblin",
            turn_introduced=5,
            last_referenced_turn=5,
        )
        callback_db = NarrativeElementStore(elements=[element])

        state = _make_game_state(
            callback_database=callback_db,
            callback_log=CallbackLog(),
        )

        # Mock the extractor to return empty (no new elements)
        with patch.object(
            __import__("memory").NarrativeElementExtractor,
            "extract_elements",
            return_value=[],
        ):
            from memory import extract_narrative_elements

            result = extract_narrative_elements(
                state,
                "The party spots Skrix the Goblin near the cave.",
                turn_number=30,
            )

        assert "callback_log" in result
        assert isinstance(result["callback_log"], CallbackLog)
        assert len(result["callback_log"].entries) == 1
        assert result["callback_log"].entries[0].element_name == "Skrix the Goblin"

    @patch("memory._extractor_cache", {})
    @patch("memory.get_config")
    def test_record_reference_called_for_detected_callbacks(
        self, mock_config: MagicMock
    ) -> None:
        """Test record_reference is called on callback_database for detected callbacks."""
        mock_cfg = MagicMock()
        mock_cfg.agents.extractor.provider = "gemini"
        mock_cfg.agents.extractor.model = "gemini-1.5-flash"
        mock_config.return_value = mock_cfg

        element = _make_element(
            name="Skrix the Goblin",
            turn_introduced=5,
            last_referenced_turn=5,
        )
        callback_db = NarrativeElementStore(elements=[element])

        state = _make_game_state(
            callback_database=callback_db,
            callback_log=CallbackLog(),
        )

        with patch.object(
            __import__("memory").NarrativeElementExtractor,
            "extract_elements",
            return_value=[],
        ):
            from memory import extract_narrative_elements

            result = extract_narrative_elements(
                state,
                "The party spots Skrix the Goblin near the cave.",
                turn_number=30,
            )

        # The callback_database in result should have recorded the reference
        updated_db = result["callback_database"]
        elem = updated_db.find_by_name("Skrix the Goblin")
        assert elem is not None
        assert 30 in elem.turns_referenced

    @patch("memory._extractor_cache", {})
    @patch("memory.get_config")
    def test_detection_failure_does_not_block_extraction(
        self, mock_config: MagicMock
    ) -> None:
        """Test that callback detection failure doesn't block extraction."""
        mock_cfg = MagicMock()
        mock_cfg.agents.extractor.provider = "gemini"
        mock_cfg.agents.extractor.model = "gemini-1.5-flash"
        mock_config.return_value = mock_cfg

        state = _make_game_state(
            callback_log=CallbackLog(),
        )

        with patch.object(
            __import__("memory").NarrativeElementExtractor,
            "extract_elements",
            return_value=[],
        ):
            with patch("memory.detect_callbacks", side_effect=RuntimeError("boom")):
                from memory import extract_narrative_elements

                result = extract_narrative_elements(
                    state, "Some content", turn_number=10
                )

        # Should still return a valid result
        assert "callback_log" in result
        assert isinstance(result["callback_log"], CallbackLog)


# =============================================================================
# Task 37-38: Agent Turn Propagation Tests
# =============================================================================


class TestDmTurnCallbackLogPropagation:
    """Tests for dm_turn propagating callback_log."""

    @patch("agents.create_dm_agent")
    @patch("agents._build_dm_context")
    @patch("agents.extract_narrative_elements", create=True)
    def test_callback_log_in_returned_state(
        self,
        mock_extract: MagicMock,
        mock_context: MagicMock,
        mock_agent: MagicMock,
    ) -> None:
        """Test callback_log is included in returned GameState from dm_turn."""
        from agents import dm_turn

        # Set up mock agent
        mock_response = MagicMock()
        mock_response.content = "The adventure continues."
        mock_response.tool_calls = None
        mock_agent.return_value.invoke.return_value = mock_response
        mock_context.return_value = "context"

        # Set up extraction result with a callback log
        test_log = CallbackLog()
        test_log.add_entry(_make_callback_entry())

        mock_extract.return_value = {
            "narrative_elements": {},
            "callback_database": NarrativeElementStore(),
            "callback_log": test_log,
        }

        state = _make_game_state(
            agent_memories={"dm": AgentMemory()},
            dm_config=DMConfig(),
            characters={},
            callback_log=CallbackLog(),
        )

        with patch("memory.extract_narrative_elements", mock_extract):
            result = dm_turn(state)

        assert "callback_log" in result
        assert isinstance(result["callback_log"], CallbackLog)
        assert len(result["callback_log"].entries) == 1

    @patch("agents.create_dm_agent")
    @patch("agents._build_dm_context")
    def test_extraction_failure_fallback_includes_callback_log(
        self,
        mock_context: MagicMock,
        mock_agent: MagicMock,
    ) -> None:
        """Test extraction failure uses existing callback_log from state."""
        from agents import dm_turn

        mock_response = MagicMock()
        mock_response.content = "The adventure continues."
        mock_response.tool_calls = None
        mock_agent.return_value.invoke.return_value = mock_response
        mock_context.return_value = "context"

        existing_log = CallbackLog()
        existing_log.add_entry(_make_callback_entry(element_name="Existing"))

        state = _make_game_state(
            agent_memories={"dm": AgentMemory()},
            dm_config=DMConfig(),
            characters={},
            callback_log=existing_log,
        )

        with patch(
            "memory.extract_narrative_elements",
            side_effect=RuntimeError("extraction error"),
        ):
            result = dm_turn(state)

        assert "callback_log" in result
        # Falls back to existing log
        assert len(result["callback_log"].entries) == 1
        assert result["callback_log"].entries[0].element_name == "Existing"


class TestPcTurnCallbackLogPropagation:
    """Tests for pc_turn propagating callback_log."""

    @patch("agents.create_pc_agent")
    @patch("agents._build_pc_context")
    @patch("agents.build_pc_system_prompt")
    def test_callback_log_in_returned_state(
        self,
        mock_prompt: MagicMock,
        mock_context: MagicMock,
        mock_agent: MagicMock,
    ) -> None:
        """Test callback_log is included in returned GameState from pc_turn."""
        from agents import pc_turn

        mock_response = MagicMock()
        mock_response.content = "I draw my sword."
        mock_response.tool_calls = None
        mock_agent.return_value.invoke.return_value = mock_response
        mock_context.return_value = "context"
        mock_prompt.return_value = "prompt"

        test_log = CallbackLog()
        test_log.add_entry(_make_callback_entry())

        mock_extract = MagicMock(return_value={
            "narrative_elements": {},
            "callback_database": NarrativeElementStore(),
            "callback_log": test_log,
        })

        char_config = CharacterConfig(
            name="TestChar",
            character_class="Fighter",
            personality="brave",
            color="#FF0000",
            provider="gemini",
            model="gemini-1.5-flash",
        )

        state = _make_game_state(
            agent_memories={"testchar": AgentMemory()},
            characters={"testchar": char_config},
            callback_log=CallbackLog(),
        )

        with patch("memory.extract_narrative_elements", mock_extract):
            result = pc_turn(state, "testchar")

        assert "callback_log" in result
        assert isinstance(result["callback_log"], CallbackLog)
        assert len(result["callback_log"].entries) == 1

    @patch("agents.create_pc_agent")
    @patch("agents._build_pc_context")
    @patch("agents.build_pc_system_prompt")
    def test_extraction_failure_fallback(
        self,
        mock_prompt: MagicMock,
        mock_context: MagicMock,
        mock_agent: MagicMock,
    ) -> None:
        """Test extraction failure uses existing callback_log from state."""
        from agents import pc_turn

        mock_response = MagicMock()
        mock_response.content = "I draw my sword."
        mock_response.tool_calls = None
        mock_agent.return_value.invoke.return_value = mock_response
        mock_context.return_value = "context"
        mock_prompt.return_value = "prompt"

        existing_log = CallbackLog()
        existing_log.add_entry(_make_callback_entry(element_name="Existing"))

        char_config = CharacterConfig(
            name="TestChar",
            character_class="Fighter",
            personality="brave",
            color="#FF0000",
            provider="gemini",
            model="gemini-1.5-flash",
        )

        state = _make_game_state(
            agent_memories={"testchar": AgentMemory()},
            characters={"testchar": char_config},
            callback_log=existing_log,
        )

        with patch(
            "memory.extract_narrative_elements",
            side_effect=RuntimeError("extraction error"),
        ):
            result = pc_turn(state, "testchar")

        assert "callback_log" in result
        assert len(result["callback_log"].entries) == 1
        assert result["callback_log"].entries[0].element_name == "Existing"


# =============================================================================
# Task 39: Persistence Round-Trip Tests
# =============================================================================


class TestPersistenceRoundTrip:
    """Tests for callback_log serialization/deserialization."""

    def test_serialize_deserialize_preserves_all_fields(self) -> None:
        """Test round-trip preserves all CallbackEntry fields."""
        state = _make_game_state()
        log = CallbackLog()
        log.add_entry(
            _make_callback_entry(
                element_id="elem1",
                element_name="Skrix the Goblin",
                element_type="character",
                turn_detected=30,
                turn_gap=25,
                match_type="name_exact",
                match_context="...Skrix appears...",
                is_story_moment=True,
                session_detected=2,
            )
        )
        log.add_entry(
            _make_callback_entry(
                element_id="elem2",
                element_name="Crystal Shard",
                element_type="item",
                turn_detected=35,
                turn_gap=10,
                match_type="description_keyword",
                match_context="...crystal glows...",
                is_story_moment=False,
                session_detected=2,
            )
        )
        state["callback_log"] = log

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        restored_log = restored["callback_log"]
        assert isinstance(restored_log, CallbackLog)
        assert len(restored_log.entries) == 2

        entry1 = restored_log.entries[0]
        assert entry1.element_id == "elem1"
        assert entry1.element_name == "Skrix the Goblin"
        assert entry1.element_type == "character"
        assert entry1.turn_detected == 30
        assert entry1.turn_gap == 25
        assert entry1.match_type == "name_exact"
        assert entry1.match_context == "...Skrix appears..."
        assert entry1.is_story_moment is True
        assert entry1.session_detected == 2

        entry2 = restored_log.entries[1]
        assert entry2.element_id == "elem2"
        assert entry2.element_name == "Crystal Shard"
        assert entry2.match_type == "description_keyword"
        assert entry2.is_story_moment is False

    def test_backward_compatibility_no_callback_log(self) -> None:
        """Test old checkpoints without callback_log get empty CallbackLog."""
        state = _make_game_state()
        json_str = serialize_game_state(state)

        # Remove callback_log from JSON to simulate old checkpoint
        data = json.loads(json_str)
        if "callback_log" in data:
            del data["callback_log"]
        old_json = json.dumps(data)

        restored = deserialize_game_state(old_json)
        assert "callback_log" in restored
        assert isinstance(restored["callback_log"], CallbackLog)
        assert len(restored["callback_log"].entries) == 0


# =============================================================================
# Task 40: Cross-Session Carry-Over Tests
# =============================================================================


class TestCrossSessionCarryOver:
    """Tests for callback_log carry-over across sessions."""

    def test_initialize_session_carries_over_callback_log(self, tmp_path: object) -> None:
        """Test initialize_session_with_previous_memories carries over callback_log."""
        from persistence import (
            initialize_session_with_previous_memories,
            save_checkpoint,
        )

        # Create previous session state with callback_log
        prev_state = _make_game_state(session_id="001", session_number=1)
        prev_log = CallbackLog()
        prev_log.add_entry(
            _make_callback_entry(element_name="Ancient Artifact", turn_detected=25)
        )
        prev_state["callback_log"] = prev_log

        # Save the previous session checkpoint
        with patch("persistence.CAMPAIGNS_DIR", tmp_path):
            save_checkpoint(prev_state, "001", 25, update_metadata=False)

            # Create new session state
            new_state = _make_game_state(session_id="002", session_number=2)

            # Initialize with previous memories
            result = initialize_session_with_previous_memories("001", "002", new_state)

        # callback_log should be carried over
        assert "callback_log" in result
        assert len(result["callback_log"].entries) == 1
        assert result["callback_log"].entries[0].element_name == "Ancient Artifact"


# =============================================================================
# Task 41: End-to-End Scenario Test
# =============================================================================


class TestEndToEndCallbackDetection:
    """End-to-end test for the callback detection scenario."""

    def test_full_callback_detection_scenario(self) -> None:
        """Test: create element at turn 5, detect callback at turn 30, verify story moment."""
        from memory import detect_callbacks

        # Create element at turn 5
        element = create_narrative_element(
            element_type="character",
            name="Skrix the Goblin",
            description="Befriended by party, promised cave information",
            turn_introduced=5,
            session_introduced=1,
            characters_involved=["Shadowmere"],
        )
        # last_referenced_turn defaults to turn_introduced (5)

        # Build callback database
        store = NarrativeElementStore(elements=[element])

        # At turn 30, content references the element
        callbacks = detect_callbacks(
            "The party spots Skrix the Goblin waving from the cave entrance.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )

        # Verify callback detected
        assert len(callbacks) == 1
        cb = callbacks[0]
        assert cb.element_name == "Skrix the Goblin"
        assert cb.element_type == "character"
        assert cb.match_type == "name_exact"
        assert cb.turn_detected == 30
        assert cb.turn_gap == 25  # 30 - 5
        assert cb.is_story_moment is True  # 25 >= 20
        assert cb.session_detected == 1

        # Verify reference count can be incremented
        store.record_reference(element.id, 30)
        assert element.times_referenced == 2
        assert 30 in element.turns_referenced
        assert element.last_referenced_turn == 30

    def test_callback_log_accumulation(self) -> None:
        """Test callback log accumulates entries across multiple detections."""
        from memory import detect_callbacks

        elem1 = _make_element(name="Skrix the Goblin", turn_introduced=5)
        elem2 = _make_element(name="Crystal Shard of Doom", turn_introduced=8, element_type="item")
        store = NarrativeElementStore(elements=[elem1, elem2])

        log = CallbackLog()

        # Turn 30: detect Skrix
        cb1 = detect_callbacks(
            "Skrix the Goblin appears at the gate.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        for cb in cb1:
            log.add_entry(cb)
            store.record_reference(cb.element_id, 30)

        # Turn 35: detect Crystal Shard
        cb2 = detect_callbacks(
            "The Crystal Shard of Doom glows with an eerie light.",
            turn_number=35,
            session_number=1,
            callback_database=store,
        )
        for cb in cb2:
            log.add_entry(cb)

        assert len(log.entries) == 2
        assert log.entries[0].element_name == "Skrix the Goblin"
        assert log.entries[1].element_name == "Crystal Shard of Doom"

        # Story moments
        moments = log.get_story_moments()
        assert len(moments) == 2  # Both have gap >= 20

    def test_multiple_elements_detected_same_turn(self) -> None:
        """Test multiple elements can be detected in the same turn content."""
        from memory import detect_callbacks

        elem1 = _make_element(name="Skrix the Goblin", turn_introduced=5)
        elem2 = _make_element(
            name="Crystal Shard",
            element_type="item",
            turn_introduced=8,
        )
        store = NarrativeElementStore(elements=[elem1, elem2])

        callbacks = detect_callbacks(
            "Skrix the Goblin holds the Crystal Shard triumphantly.",
            turn_number=30,
            session_number=1,
            callback_database=store,
        )
        assert len(callbacks) == 2
        names = {cb.element_name for cb in callbacks}
        assert "Skrix the Goblin" in names
        assert "Crystal Shard" in names
