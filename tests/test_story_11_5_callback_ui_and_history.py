"""Tests for Story 11.5: Callback UI & History.

Tests HTML rendering functions for the Story Threads sidebar panel,
including summary, element cards, detail views, callback timelines,
helper functions, and sidebar integration.

FR80: User can view callback history and track unresolved narrative threads.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app import (
    _get_element_type_icon,
    _get_element_type_label,
    render_callback_timeline_html,
    render_story_element_card_html,
    render_story_element_detail_html,
    render_story_threads,
    render_story_threads_summary_html,
)
from models import (
    CallbackEntry,
    CallbackLog,
    NarrativeElement,
    NarrativeElementStore,
    create_narrative_element,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def active_character_element() -> NarrativeElement:
    """Active character element with multiple references."""
    return create_narrative_element(
        element_type="character",
        name="Skrix the Goblin",
        description="Befriended by party, promised cave information",
        turn_introduced=5,
        session_introduced=1,
        characters_involved=["Shadowmere", "Eldric"],
        potential_callbacks=["Could return as ally", "Might betray party"],
    )


@pytest.fixture()
def dormant_item_element() -> NarrativeElement:
    """Dormant item element."""
    elem = create_narrative_element(
        element_type="item",
        name="Cursed Amulet",
        description="Found in the ruins, glowing faintly",
        turn_introduced=3,
        session_introduced=1,
        characters_involved=["Eldric"],
    )
    elem.dormant = True
    elem.times_referenced = 2
    return elem


@pytest.fixture()
def resolved_event_element() -> NarrativeElement:
    """Resolved event element."""
    elem = create_narrative_element(
        element_type="event",
        name="Tavern Brawl",
        description="Bar fight that started the quest",
        turn_introduced=1,
        session_introduced=1,
    )
    elem.resolved = True
    return elem


@pytest.fixture()
def story_moment_callback(active_character_element: NarrativeElement) -> CallbackEntry:
    """Callback entry flagged as a story moment."""
    return CallbackEntry(
        id="cb001",
        element_id=active_character_element.id,
        element_name=active_character_element.name,
        element_type=active_character_element.element_type,
        turn_detected=30,
        turn_gap=25,
        match_type="name_exact",
        match_context="Skrix appeared from the shadows, remembering the party",
        is_story_moment=True,
        session_detected=2,
    )


@pytest.fixture()
def regular_callback(active_character_element: NarrativeElement) -> CallbackEntry:
    """Regular callback entry (not a story moment)."""
    return CallbackEntry(
        id="cb002",
        element_id=active_character_element.id,
        element_name=active_character_element.name,
        element_type=active_character_element.element_type,
        turn_detected=10,
        turn_gap=5,
        match_type="name_fuzzy",
        match_context="Someone mentioned the goblin from earlier",
        is_story_moment=False,
        session_detected=1,
    )


@pytest.fixture()
def keyword_callback(active_character_element: NarrativeElement) -> CallbackEntry:
    """Callback entry with keyword match type."""
    return CallbackEntry(
        id="cb003",
        element_id=active_character_element.id,
        element_name=active_character_element.name,
        element_type=active_character_element.element_type,
        turn_detected=15,
        turn_gap=10,
        match_type="description_keyword",
        match_context="The cave information proved valuable",
        is_story_moment=False,
        session_detected=1,
    )


# =============================================================================
# Tests: render_story_threads_summary_html()
# =============================================================================


class TestRenderStoryThreadsSummaryHtml:
    """Tests for the summary statistics HTML rendering."""

    def test_all_zeros_shows_no_elements_message(self) -> None:
        """All zeros returns 'No narrative elements tracked yet'."""
        html = render_story_threads_summary_html(0, 0, 0)
        assert "No narrative elements tracked yet" in html
        assert "story-threads-summary" in html

    def test_active_only(self) -> None:
        """Active count only renders correctly."""
        html = render_story_threads_summary_html(3, 0, 0)
        assert "3 active" in html
        assert "dormant" not in html
        assert "story moment" not in html

    def test_dormant_only(self) -> None:
        """Dormant count only renders correctly."""
        html = render_story_threads_summary_html(0, 2, 0)
        assert "2 dormant" in html
        assert "active" not in html

    def test_story_moments_only(self) -> None:
        """Story moment count only renders correctly."""
        html = render_story_threads_summary_html(1, 0, 1)
        assert "1 story moment" in html
        assert "story moments" not in html  # singular

    def test_story_moments_plural(self) -> None:
        """Multiple story moments use plural."""
        html = render_story_threads_summary_html(1, 0, 3)
        assert "3 story moments" in html

    def test_mixed_counts(self) -> None:
        """Mixed counts render all parts."""
        html = render_story_threads_summary_html(5, 2, 1)
        assert "5 active" in html
        assert "2 dormant" in html
        assert "1 story moment" in html

    def test_css_class_present(self) -> None:
        """CSS class story-threads-summary is present in output."""
        html = render_story_threads_summary_html(1, 0, 0)
        assert 'class="story-threads-summary"' in html

    def test_zero_active_zero_dormant_nonzero_moments(self) -> None:
        """When active and dormant are both 0, shows no elements message."""
        html = render_story_threads_summary_html(0, 0, 5)
        assert "No narrative elements tracked yet" in html


# =============================================================================
# Tests: render_story_element_card_html()
# =============================================================================


class TestRenderStoryElementCardHtml:
    """Tests for element card HTML rendering."""

    def test_active_element_basic(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Active element shows name, type class, and metadata."""
        html = render_story_element_card_html(active_character_element, [])
        assert "Skrix the Goblin" in html
        assert "story-element-card" in html
        assert "type-character" in html
        assert "Turn 5" in html
        assert "Session 1" in html
        assert "NPC" in html  # type icon

    def test_dormant_element_has_dormant_class(
        self, dormant_item_element: NarrativeElement
    ) -> None:
        """Dormant element has 'dormant' CSS class."""
        html = render_story_element_card_html(dormant_item_element, [])
        assert "dormant" in html
        assert "dormant-badge" in html

    def test_resolved_element_has_resolved_class(
        self, resolved_event_element: NarrativeElement
    ) -> None:
        """Resolved element has 'resolved' CSS class."""
        html = render_story_element_card_html(resolved_event_element, [])
        assert "resolved" in html

    def test_element_with_one_reference_no_badge(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Element with 1 reference does not show 'referenced X times' badge."""
        # Default times_referenced is 1
        html = render_story_element_card_html(active_character_element, [])
        assert "referenced" not in html

    def test_element_with_multiple_references_shows_badge(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Element with 5 references shows 'referenced 5 times' badge."""
        active_character_element.times_referenced = 5
        html = render_story_element_card_html(active_character_element, [])
        assert "referenced 5 times" in html
        assert "story-element-badge" in html

    def test_element_with_story_moment_callback(
        self,
        active_character_element: NarrativeElement,
        story_moment_callback: CallbackEntry,
    ) -> None:
        """Element with story moment callbacks shows story-moment badge."""
        html = render_story_element_card_html(
            active_character_element, [story_moment_callback]
        )
        assert "story-moment" in html
        assert "story moment" in html  # badge text

    def test_type_specific_css_classes(self) -> None:
        """Each element type gets correct CSS class."""
        for etype in ["character", "item", "location", "event", "promise", "threat"]:
            elem = create_narrative_element(
                element_type=etype,  # type: ignore[arg-type]
                name=f"Test {etype}",
                turn_introduced=1,
            )
            html = render_story_element_card_html(elem, [])
            assert f"type-{etype}" in html

    def test_html_escaped_name(self) -> None:
        """Element names are HTML-escaped for XSS prevention."""
        elem = create_narrative_element(
            element_type="character",
            name='<script>alert("xss")</script>',
            turn_introduced=1,
        )
        html = render_story_element_card_html(elem, [])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_item_type_icon(self) -> None:
        """Item type shows ITEM icon."""
        elem = create_narrative_element(
            element_type="item", name="Magic Sword", turn_introduced=1
        )
        html = render_story_element_card_html(elem, [])
        assert "ITEM" in html

    def test_location_type_icon(self) -> None:
        """Location type shows LOC icon."""
        elem = create_narrative_element(
            element_type="location", name="Dark Forest", turn_introduced=1
        )
        html = render_story_element_card_html(elem, [])
        assert "LOC" in html


# =============================================================================
# Tests: render_story_element_detail_html()
# =============================================================================


class TestRenderStoryElementDetailHtml:
    """Tests for element detail HTML rendering."""

    def test_element_with_description(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Element with description renders in italic."""
        html = render_story_element_detail_html(active_character_element, [])
        assert "story-element-description" in html
        assert "Befriended by party" in html

    def test_element_with_characters_involved(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Element with characters_involved lists them."""
        html = render_story_element_detail_html(active_character_element, [])
        assert "Characters:" in html
        assert "Shadowmere" in html
        assert "Eldric" in html

    def test_element_with_potential_callbacks(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Element with potential_callbacks lists them."""
        html = render_story_element_detail_html(active_character_element, [])
        assert "Potential callbacks:" in html
        assert "Could return as ally" in html
        assert "Might betray party" in html

    def test_element_with_no_detail(self) -> None:
        """Element with no description/characters/callbacks returns minimal HTML."""
        elem = create_narrative_element(
            element_type="event", name="Minimal Event", turn_introduced=1
        )
        html = render_story_element_detail_html(elem, [])
        # Should still have timeline at minimum
        assert "Timeline:" in html

    def test_element_with_callback_entries(
        self,
        active_character_element: NarrativeElement,
        regular_callback: CallbackEntry,
    ) -> None:
        """Element with callback entries includes timeline section."""
        html = render_story_element_detail_html(
            active_character_element, [regular_callback]
        )
        assert "Callback Timeline:" in html

    def test_html_escaped_description(self) -> None:
        """Description text is HTML-escaped."""
        elem = create_narrative_element(
            element_type="character",
            name="Test",
            description='Has a <b>bold</b> description & "quotes"',
            turn_introduced=1,
        )
        html = render_story_element_detail_html(elem, [])
        assert "<b>" not in html
        assert "&lt;b&gt;" in html
        assert "&amp;" in html

    def test_html_escaped_characters(self) -> None:
        """Character names are HTML-escaped."""
        elem = create_narrative_element(
            element_type="character",
            name="Test",
            turn_introduced=1,
            characters_involved=["<script>evil</script>"],
        )
        html = render_story_element_detail_html(elem, [])
        assert "<script>" not in html

    def test_html_escaped_potential_callbacks(self) -> None:
        """Potential callback text is HTML-escaped."""
        elem = create_narrative_element(
            element_type="character",
            name="Test",
            turn_introduced=1,
            potential_callbacks=["<img src=x onerror=alert(1)>"],
        )
        html = render_story_element_detail_html(elem, [])
        assert "<img" not in html


# =============================================================================
# Tests: render_callback_timeline_html()
# =============================================================================


class TestRenderCallbackTimelineHtml:
    """Tests for callback timeline HTML rendering."""

    def test_no_callbacks_shows_introduction_only(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Element with no callbacks shows just introduction entry."""
        html = render_callback_timeline_html(active_character_element, [])
        assert "introduced" in html
        assert "Introduced in Turn 5" in html
        assert "Session 1" in html
        assert "Timeline:" in html
        assert "Callback Timeline:" not in html

    def test_with_callbacks_shows_callback_timeline_header(
        self,
        active_character_element: NarrativeElement,
        regular_callback: CallbackEntry,
    ) -> None:
        """Element with callbacks shows 'Callback Timeline:' header."""
        html = render_callback_timeline_html(
            active_character_element, [regular_callback]
        )
        assert "Callback Timeline:" in html

    def test_callback_entries_sorted_by_turn(
        self,
        active_character_element: NarrativeElement,
        regular_callback: CallbackEntry,
        keyword_callback: CallbackEntry,
        story_moment_callback: CallbackEntry,
    ) -> None:
        """Callback entries are sorted chronologically by turn_detected."""
        # Pass in unsorted order
        html = render_callback_timeline_html(
            active_character_element,
            [story_moment_callback, regular_callback, keyword_callback],
        )
        # Find positions of turn numbers
        pos_10 = html.find("Turn 10")
        pos_15 = html.find("Turn 15")
        pos_30 = html.find("Turn 30")
        assert pos_10 < pos_15 < pos_30

    def test_story_moment_has_css_class(
        self,
        active_character_element: NarrativeElement,
        story_moment_callback: CallbackEntry,
    ) -> None:
        """Story moment entry has 'story-moment' CSS class."""
        html = render_callback_timeline_html(
            active_character_element, [story_moment_callback]
        )
        assert "story-moment" in html

    def test_story_moment_shows_turn_gap(
        self,
        active_character_element: NarrativeElement,
        story_moment_callback: CallbackEntry,
    ) -> None:
        """Story moment shows turn gap label."""
        html = render_callback_timeline_html(
            active_character_element, [story_moment_callback]
        )
        assert "25 turn gap!" in html

    def test_introduction_entry_has_introduced_class(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Introduction entry has 'introduced' CSS class."""
        html = render_callback_timeline_html(active_character_element, [])
        assert 'class="callback-timeline-entry introduced"' in html

    def test_match_context_included(
        self,
        active_character_element: NarrativeElement,
        regular_callback: CallbackEntry,
    ) -> None:
        """Match context excerpt is included in entry."""
        html = render_callback_timeline_html(
            active_character_element, [regular_callback]
        )
        assert "goblin from earlier" in html

    def test_match_context_truncated_at_80_chars(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Long match context is truncated at 80 characters."""
        long_context = "A" * 100
        entry = CallbackEntry(
            id="cb_long",
            element_id=active_character_element.id,
            element_name=active_character_element.name,
            element_type="character",
            turn_detected=20,
            turn_gap=5,
            match_type="name_exact",
            match_context=long_context,
            is_story_moment=False,
            session_detected=1,
        )
        html = render_callback_timeline_html(active_character_element, [entry])
        assert "A" * 80 in html
        assert "A" * 81 not in html
        assert "..." in html

    def test_match_type_labels(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Match types are converted to human-readable labels."""
        for match_type, expected_label in [
            ("name_exact", "exact name match"),
            ("name_fuzzy", "fuzzy name match"),
            ("description_keyword", "keyword match"),
        ]:
            entry = CallbackEntry(
                id=f"cb_{match_type}",
                element_id=active_character_element.id,
                element_name=active_character_element.name,
                element_type="character",
                turn_detected=20,
                turn_gap=5,
                match_type=match_type,  # type: ignore[arg-type]
                match_context="test",
                is_story_moment=False,
                session_detected=1,
            )
            html = render_callback_timeline_html(active_character_element, [entry])
            assert expected_label in html

    def test_callback_timeline_css_class(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Timeline has callback-timeline CSS class."""
        html = render_callback_timeline_html(active_character_element, [])
        assert "callback-timeline" in html

    def test_match_context_html_escaped(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Match context is HTML-escaped."""
        entry = CallbackEntry(
            id="cb_xss",
            element_id=active_character_element.id,
            element_name=active_character_element.name,
            element_type="character",
            turn_detected=20,
            turn_gap=5,
            match_type="name_exact",
            match_context='<img src="x" onerror="alert(1)">',
            is_story_moment=False,
            session_detected=1,
        )
        html = render_callback_timeline_html(active_character_element, [entry])
        assert "<img" not in html
        assert "&lt;img" in html


# =============================================================================
# Tests: _get_element_type_label() and _get_element_type_icon()
# =============================================================================


class TestElementTypeHelpers:
    """Tests for type label and icon helper functions."""

    @pytest.mark.parametrize(
        "element_type,expected_label",
        [
            ("character", "Character"),
            ("item", "Item"),
            ("location", "Location"),
            ("event", "Event"),
            ("promise", "Promise"),
            ("threat", "Threat"),
        ],
    )
    def test_type_labels(self, element_type: str, expected_label: str) -> None:
        """All 6 element types return correct labels."""
        assert _get_element_type_label(element_type) == expected_label

    def test_unknown_type_label_fallback(self) -> None:
        """Unknown type returns title-cased type string."""
        assert _get_element_type_label("mystery") == "Mystery"
        assert _get_element_type_label("custom_type") == "Custom_Type"

    @pytest.mark.parametrize(
        "element_type,expected_icon",
        [
            ("character", "NPC"),
            ("item", "ITEM"),
            ("location", "LOC"),
            ("event", "EVT"),
            ("promise", "VOW"),
            ("threat", "RISK"),
        ],
    )
    def test_type_icons(self, element_type: str, expected_icon: str) -> None:
        """All 6 element types return correct icons."""
        assert _get_element_type_icon(element_type) == expected_icon

    def test_unknown_type_icon_fallback(self) -> None:
        """Unknown type returns uppercased first 4 chars."""
        assert _get_element_type_icon("mystery") == "MYST"
        assert _get_element_type_icon("ab") == "AB"


# =============================================================================
# Tests: render_story_threads() integration
# =============================================================================


class TestRenderStoryThreads:
    """Integration tests for the Story Threads sidebar render function."""

    @patch("app.st")
    def test_no_game_state_renders_nothing(self, mock_st: MagicMock) -> None:
        """No game state renders nothing (no error)."""
        mock_st.session_state = {}
        render_story_threads()
        # Should not call expander
        mock_st.expander.assert_not_called()

    @patch("app.st")
    def test_game_with_no_callback_database(self, mock_st: MagicMock) -> None:
        """Game with no callback_database renders nothing."""
        mock_st.session_state = {"game": {}}
        render_story_threads()
        mock_st.expander.assert_not_called()

    @patch("app.st")
    def test_game_with_empty_callback_database(self, mock_st: MagicMock) -> None:
        """Game with empty callback_database renders nothing."""
        mock_st.session_state = {
            "game": {
                "callback_database": NarrativeElementStore(elements=[]),
                "callback_log": CallbackLog(),
            }
        }
        render_story_threads()
        mock_st.expander.assert_not_called()

    @patch("app.st")
    def test_game_with_active_elements(self, mock_st: MagicMock) -> None:
        """Game with active elements renders element list with expanders."""
        elem = create_narrative_element(
            element_type="character",
            name="Test NPC",
            turn_introduced=5,
            session_introduced=1,
        )
        store = NarrativeElementStore(elements=[elem])
        mock_st.session_state = {
            "game": {
                "callback_database": store,
                "callback_log": CallbackLog(),
            }
        }

        # Set up context managers for expanders
        outer_expander = MagicMock()
        inner_expander = MagicMock()
        mock_st.expander.side_effect = [outer_expander, inner_expander]

        render_story_threads()

        # Should have called expander for the outer Story Threads section
        mock_st.expander.assert_any_call("Story Threads (1)", expanded=False)

    @patch("app.st")
    def test_game_with_dormant_elements(self, mock_st: MagicMock) -> None:
        """Game with dormant elements shows dormant section."""
        elem = create_narrative_element(
            element_type="item",
            name="Old Ring",
            turn_introduced=1,
            session_introduced=1,
        )
        elem.dormant = True
        store = NarrativeElementStore(elements=[elem])
        mock_st.session_state = {
            "game": {
                "callback_database": store,
                "callback_log": CallbackLog(),
            }
        }

        outer_expander = MagicMock()
        inner_expander = MagicMock()
        mock_st.expander.side_effect = [outer_expander, inner_expander]

        render_story_threads()

        # Should have called expander with count including dormant
        mock_st.expander.assert_any_call("Story Threads (1)", expanded=False)

    @patch("app.st")
    def test_game_with_story_moments(self, mock_st: MagicMock) -> None:
        """Game with story moments includes count in summary."""
        elem = create_narrative_element(
            element_type="character",
            name="Ancient NPC",
            turn_introduced=1,
            session_introduced=1,
        )
        entry = CallbackEntry(
            id="sm1",
            element_id=elem.id,
            element_name=elem.name,
            element_type="character",
            turn_detected=25,
            turn_gap=24,
            match_type="name_exact",
            match_context="Ancient NPC returned",
            is_story_moment=True,
            session_detected=2,
        )
        store = NarrativeElementStore(elements=[elem])
        log = CallbackLog(entries=[entry])

        mock_st.session_state = {
            "game": {
                "callback_database": store,
                "callback_log": log,
            }
        }

        outer_expander = MagicMock()
        inner_expander = MagicMock()
        mock_st.expander.side_effect = [outer_expander, inner_expander]

        render_story_threads()

        # Story moments count should be in the summary
        mock_st.expander.assert_any_call("Story Threads (1)", expanded=False)

    @patch("app.st")
    def test_callback_log_none_defaults_to_empty(self, mock_st: MagicMock) -> None:
        """When callback_log is None, defaults to empty CallbackLog."""
        elem = create_narrative_element(
            element_type="character",
            name="Test NPC",
            turn_introduced=5,
            session_introduced=1,
        )
        store = NarrativeElementStore(elements=[elem])
        mock_st.session_state = {
            "game": {
                "callback_database": store,
                "callback_log": None,
            }
        }

        outer_expander = MagicMock()
        inner_expander = MagicMock()
        mock_st.expander.side_effect = [outer_expander, inner_expander]

        # Should not raise
        render_story_threads()

        mock_st.expander.assert_any_call("Story Threads (1)", expanded=False)


# =============================================================================
# Tests: Sidebar integration
# =============================================================================


class TestSidebarIntegration:
    """Tests for Story Threads integration into render_sidebar()."""

    def test_render_story_threads_called_in_sidebar(self) -> None:
        """render_sidebar() includes render_story_threads() call."""
        import inspect

        from app import render_sidebar

        source = inspect.getsource(render_sidebar)
        assert "render_story_threads()" in source

    def test_story_threads_after_whisper_before_llm_status(self) -> None:
        """Story Threads section appears after whisper and before LLM status."""
        import inspect

        from app import render_sidebar

        source = inspect.getsource(render_sidebar)
        whisper_pos = source.find("render_human_whisper_input()")
        story_threads_pos = source.find("render_story_threads()")
        llm_status_pos = source.find("LLM Status")

        assert whisper_pos > 0, "whisper input not found in render_sidebar"
        assert story_threads_pos > 0, "story threads not found in render_sidebar"
        assert llm_status_pos > 0, "LLM Status not found in render_sidebar"
        assert whisper_pos < story_threads_pos < llm_status_pos


# =============================================================================
# Tests: Edge cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_element_card_with_empty_callbacks_list(self) -> None:
        """Empty callback list does not cause errors."""
        elem = create_narrative_element(
            element_type="promise",
            name="A Vow",
            turn_introduced=10,
        )
        html = render_story_element_card_html(elem, [])
        assert "story-element-card" in html
        assert "type-promise" in html
        assert "VOW" in html

    def test_detail_html_empty_when_no_content(self) -> None:
        """Detail HTML with no description/characters/callbacks just has timeline."""
        elem = create_narrative_element(
            element_type="threat",
            name="Empty Threat",
            turn_introduced=1,
        )
        html = render_story_element_detail_html(elem, [])
        # Should have at least the timeline with introduction
        assert "Timeline:" in html
        assert "Introduced in Turn 1" in html

    def test_summary_html_with_only_dormant(self) -> None:
        """Summary with only dormant elements."""
        html = render_story_threads_summary_html(0, 3, 0)
        assert "3 dormant" in html
        assert "active" not in html

    def test_card_with_both_dormant_and_resolved(self) -> None:
        """Element that is both dormant and resolved gets both classes."""
        elem = create_narrative_element(
            element_type="event",
            name="Past Event",
            turn_introduced=1,
        )
        elem.dormant = True
        elem.resolved = True
        html = render_story_element_card_html(elem, [])
        assert "dormant" in html
        assert "resolved" in html

    def test_timeline_with_empty_match_context(
        self, active_character_element: NarrativeElement
    ) -> None:
        """Callback entry with empty match_context does not show context snippet."""
        entry = CallbackEntry(
            id="cb_empty",
            element_id=active_character_element.id,
            element_name=active_character_element.name,
            element_type="character",
            turn_detected=20,
            turn_gap=5,
            match_type="name_exact",
            match_context="",
            is_story_moment=False,
            session_detected=1,
        )
        html = render_callback_timeline_html(active_character_element, [entry])
        assert "callback-context-snippet" not in html
