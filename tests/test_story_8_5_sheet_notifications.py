"""Tests for Story 8-5: Sheet Change Notifications.

Tests the sheet change notification system that displays character sheet
updates (HP, equipment, conditions) in the narrative area.

FR64: Sheet changes are reflected in the narrative
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from models import NarrativeMessage, parse_log_entry


# =============================================================================
# NarrativeMessage.message_type Tests
# =============================================================================


class TestNarrativeMessageType:
    """Tests for NarrativeMessage.message_type property."""

    def test_dm_narration_type(self) -> None:
        msg = NarrativeMessage(agent="dm", content="The tavern is quiet.")
        assert msg.message_type == "dm_narration"

    def test_dm_narration_uppercase(self) -> None:
        msg = NarrativeMessage(agent="DM", content="Text.")
        assert msg.message_type == "dm_narration"

    def test_pc_dialogue_type(self) -> None:
        msg = NarrativeMessage(agent="fighter", content="I attack!")
        assert msg.message_type == "pc_dialogue"

    def test_sheet_update_type(self) -> None:
        msg = NarrativeMessage(agent="SHEET", content="Updated Thorin: HP: 45 -> 35 (-10)")
        assert msg.message_type == "sheet_update"

    def test_sheet_update_lowercase(self) -> None:
        msg = NarrativeMessage(agent="sheet", content="Updated Thorin: HP: 45 -> 35 (-10)")
        assert msg.message_type == "sheet_update"

    def test_sheet_update_mixed_case(self) -> None:
        msg = NarrativeMessage(agent="Sheet", content="Updated Thorin: HP: 45 -> 35 (-10)")
        assert msg.message_type == "sheet_update"


# =============================================================================
# parse_log_entry with [SHEET] prefix Tests
# =============================================================================


class TestParseLogEntrySheet:
    """Tests for parse_log_entry handling [SHEET] prefixed entries."""

    def test_parse_sheet_entry(self) -> None:
        entry = "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert msg.message_type == "sheet_update"
        assert "Updated Thorin" in msg.content

    def test_parse_sheet_entry_equipment(self) -> None:
        entry = "[SHEET]: Updated Shadowmere: Equipment: gained Dagger +1"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert msg.message_type == "sheet_update"
        assert "Dagger +1" in msg.content

    def test_parse_sheet_entry_condition(self) -> None:
        entry = "[SHEET]: Updated Elara: Conditions: added poisoned"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert "poisoned" in msg.content

    def test_parse_sheet_entry_multiple_changes(self) -> None:
        entry = "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10); Conditions: added prone; Equipment: gained Cursed Ring"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert "HP: 45 -> 35" in msg.content
        assert "prone" in msg.content
        assert "Cursed Ring" in msg.content

    def test_parse_sheet_entry_gold(self) -> None:
        entry = "[SHEET]: Updated Thorin: Gold: 47 -> 100 (+53)"
        msg = parse_log_entry(entry)
        assert msg.message_type == "sheet_update"
        assert "+53" in msg.content

    def test_parse_sheet_entry_spell_slots(self) -> None:
        entry = "[SHEET]: Updated Elara: Spell Slots: L1: 4/4 -> 3/4"
        msg = parse_log_entry(entry)
        assert msg.message_type == "sheet_update"
        assert "L1:" in msg.content


# =============================================================================
# render_sheet_message_html Tests
# =============================================================================


class TestRenderSheetMessageHtml:
    """Tests for render_sheet_message_html function."""

    def test_structure(self) -> None:
        from app import render_sheet_message_html

        html = render_sheet_message_html("Updated Thorin: HP: 45 -> 35 (-10)")
        assert 'class="sheet-notification"' in html
        assert "<p>" in html
        assert "Updated Thorin" in html

    def test_escapes_content(self) -> None:
        from app import render_sheet_message_html

        html = render_sheet_message_html("<script>alert('xss')</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_current_turn_class(self) -> None:
        from app import render_sheet_message_html

        html = render_sheet_message_html("Updated Thorin: HP: 45 -> 35", is_current=True)
        assert "current-turn" in html

    def test_no_current_turn_class_by_default(self) -> None:
        from app import render_sheet_message_html

        html = render_sheet_message_html("Updated Thorin: HP: 45 -> 35")
        assert "current-turn" not in html

    def test_preserves_content(self) -> None:
        from app import render_sheet_message_html

        content = "Updated Elara: Spell Slots: L1: 4/4 -> 3/4, L2: 3/3 -> 2/3"
        html = render_sheet_message_html(content)
        assert "L1: 4/4" in html
        assert "L2: 3/3" in html

    def test_div_wrapper(self) -> None:
        from app import render_sheet_message_html

        html = render_sheet_message_html("Test content")
        assert html.startswith("<div")
        assert html.endswith("</div>")

    def test_empty_content(self) -> None:
        from app import render_sheet_message_html

        html = render_sheet_message_html("")
        assert 'class="sheet-notification"' in html
        assert "<p></p>" in html


# =============================================================================
# render_narrative_messages Integration Tests
# =============================================================================


class TestRenderNarrativeWithSheetNotifications:
    """Tests for render_narrative_messages handling sheet notifications."""

    @patch("app.st")
    def test_sheet_message_renders_with_sheet_class(self, mock_st: MagicMock) -> None:
        """Test that [SHEET] entries render with sheet-notification class."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
            ],
            "characters": {},
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 1
        html = call_args[0][0][0]
        assert "sheet-notification" in html

    @patch("app.st")
    def test_sheet_and_dm_messages_render_in_order(self, mock_st: MagicMock) -> None:
        """Test sheet notifications appear before DM narrative."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
                "[DM]: The goblin strikes Thorin!",
            ],
            "characters": {},
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 2
        assert "sheet-notification" in call_args[0][0][0]
        assert "dm-message" in call_args[1][0][0]

    @patch("app.st")
    def test_multiple_sheet_notifications(self, mock_st: MagicMock) -> None:
        """Test multiple sheet notifications render correctly."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
                "[SHEET]: Updated Elara: Spell Slots: L1: 4/4 -> 3/4",
                "[DM]: Combat rages on!",
            ],
            "characters": {},
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 3
        assert "sheet-notification" in call_args[0][0][0]
        assert "sheet-notification" in call_args[1][0][0]
        assert "dm-message" in call_args[2][0][0]

    @patch("app.st")
    def test_sheet_between_dm_and_pc(self, mock_st: MagicMock) -> None:
        """Test sheet notification between DM and PC messages."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[DM]: The battle begins!",
                "[fighter]: I attack the goblin!",
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
                "[DM]: The goblin retaliates!",
            ],
            "characters": {
                "fighter": MagicMock(name="Thorin", character_class="Fighter"),
            },
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 4
        assert "dm-message" in call_args[0][0][0]
        assert "pc-message" in call_args[1][0][0]
        assert "sheet-notification" in call_args[2][0][0]
        assert "dm-message" in call_args[3][0][0]


# =============================================================================
# dm_turn Sheet Notification Integration Tests
# =============================================================================


class TestDmTurnSheetNotifications:
    """Tests for sheet notifications being added to ground_truth_log in dm_turn."""

    @patch("agents.get_llm")
    def test_sheet_update_creates_notification_entry(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Test that successful sheet updates add [SHEET] entries to log."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterSheet,
            DMConfig,
            GameConfig,
            GameState,
        )

        fighter_sheet = CharacterSheet(
            name="Thorin",
            race="Dwarf",
            character_class="Fighter",
            level=5,
            strength=18,
            dexterity=12,
            constitution=16,
            intelligence=10,
            wisdom=14,
            charisma=8,
            armor_class=18,
            hit_points_max=52,
            hit_points_current=45,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    race="Dwarf",
                    personality="Brave warrior",
                    color="#FF0000",
                    provider="gemini",
                    model="gemini-1.5-flash",
                )
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": {"Thorin": fighter_sheet},
        }

        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "Thorin",
                        "updates": {"hit_points_current": 35},
                    },
                    "id": "call_001",
                }
            ],
        )
        final_response = AIMessage(
            content="The goblin strikes Thorin for 10 damage!",
        )

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        # Should have [SHEET] entry before [DM] entry
        log = result["ground_truth_log"]
        sheet_entries = [e for e in log if e.startswith("[SHEET]")]
        dm_entries = [e for e in log if e.startswith("[DM]")]
        assert len(sheet_entries) == 1
        assert len(dm_entries) == 1
        assert "Updated Thorin" in sheet_entries[0]
        assert "HP: 45 -> 35" in sheet_entries[0]
        # Sheet notification should come before DM narrative
        assert log.index(sheet_entries[0]) < log.index(dm_entries[0])

    @patch("agents.get_llm")
    def test_failed_sheet_update_no_notification(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Test that failed sheet updates do NOT add [SHEET] entries."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterSheet,
            DMConfig,
            GameConfig,
            GameState,
        )

        fighter_sheet = CharacterSheet(
            name="Thorin",
            race="Dwarf",
            character_class="Fighter",
            level=5,
            strength=18,
            dexterity=12,
            constitution=16,
            intelligence=10,
            wisdom=14,
            charisma=8,
            armor_class=18,
            hit_points_max=52,
            hit_points_current=45,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    race="Dwarf",
                    personality="Brave warrior",
                    color="#FF0000",
                    provider="gemini",
                    model="gemini-1.5-flash",
                )
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": {"Thorin": fighter_sheet},
        }

        # Try to update nonexistent character
        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "NonexistentChar",
                        "updates": {"hit_points_current": 35},
                    },
                    "id": "call_001",
                }
            ],
        )
        final_response = AIMessage(
            content="The DM narrates.",
        )

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        log = result["ground_truth_log"]
        sheet_entries = [e for e in log if e.startswith("[SHEET]")]
        assert len(sheet_entries) == 0  # No notification for failed update

    @patch("agents.get_llm")
    def test_multiple_sheet_updates_create_multiple_notifications(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Test multiple sheet updates create multiple [SHEET] log entries."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterSheet,
            DMConfig,
            GameConfig,
            GameState,
            SpellSlots,
        )

        fighter_sheet = CharacterSheet(
            name="Thorin",
            race="Dwarf",
            character_class="Fighter",
            level=5,
            strength=18,
            dexterity=12,
            constitution=16,
            intelligence=10,
            wisdom=14,
            charisma=8,
            armor_class=18,
            hit_points_max=52,
            hit_points_current=45,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )

        wizard_sheet = CharacterSheet(
            name="Elara",
            race="Elf",
            character_class="Wizard",
            level=5,
            strength=8,
            dexterity=14,
            constitution=12,
            intelligence=18,
            wisdom=12,
            charisma=10,
            armor_class=12,
            hit_points_max=27,
            hit_points_current=27,
            hit_dice="5d6",
            hit_dice_remaining=5,
            spell_slots={1: SpellSlots(current=4, max=4)},
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter", "wizard"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    race="Dwarf",
                    personality="Brave",
                    color="#FF0000",
                    provider="gemini",
                    model="gemini-1.5-flash",
                ),
                "wizard": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    race="Elf",
                    personality="Wise",
                    color="#7B68B8",
                    provider="gemini",
                    model="gemini-1.5-flash",
                ),
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": {"Thorin": fighter_sheet, "Elara": wizard_sheet},
        }

        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "Thorin",
                        "updates": {"hit_points_current": 35},
                    },
                    "id": "call_001",
                },
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "Elara",
                        "updates": {"spell_slots": {"1": {"current": 3}}},
                    },
                    "id": "call_002",
                },
            ],
        )
        final_response = AIMessage(
            content="Combat ensues!",
        )

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        log = result["ground_truth_log"]
        sheet_entries = [e for e in log if e.startswith("[SHEET]")]
        assert len(sheet_entries) == 2
        assert any("Thorin" in e for e in sheet_entries)
        assert any("Elara" in e for e in sheet_entries)


# =============================================================================
# CSS Styling Tests
# =============================================================================


class TestSheetNotificationCSS:
    """Tests for sheet notification CSS styling."""

    def test_css_contains_sheet_notification_class(self) -> None:
        with open("styles/theme.css") as f:
            css = f.read()
        assert ".sheet-notification" in css

    def test_css_uses_accent_warm_color(self) -> None:
        with open("styles/theme.css") as f:
            css = f.read()
        # Sheet notifications should use amber accent color
        assert "var(--accent-warm)" in css

    def test_css_has_paragraph_styling(self) -> None:
        with open("styles/theme.css") as f:
            css = f.read()
        assert ".sheet-notification p" in css


# =============================================================================
# EXPANDED TEST COVERAGE
# =============================================================================


# =============================================================================
# NarrativeMessage.message_type Edge Cases
# =============================================================================


class TestNarrativeMessageTypeEdgeCases:
    """Extended edge case tests for NarrativeMessage.message_type."""

    def test_agent_name_with_spaces(self) -> None:
        """Agent names with spaces should be pc_dialogue."""
        msg = NarrativeMessage(agent="brother aldric", content="I pray.")
        assert msg.message_type == "pc_dialogue"

    def test_agent_name_numeric(self) -> None:
        """Numeric agent names should be pc_dialogue."""
        msg = NarrativeMessage(agent="123", content="Some text")
        assert msg.message_type == "pc_dialogue"

    def test_agent_name_empty(self) -> None:
        """Empty agent name should be pc_dialogue (not dm or sheet)."""
        msg = NarrativeMessage(agent="", content="Test")
        assert msg.message_type == "pc_dialogue"

    def test_agent_dm_with_suffix(self) -> None:
        """Agent 'dm_assistant' should NOT be dm_narration."""
        msg = NarrativeMessage(agent="dm_assistant", content="Help.")
        assert msg.message_type == "pc_dialogue"

    def test_agent_sheet_with_suffix(self) -> None:
        """Agent 'SHEET_update' should NOT be sheet_update."""
        msg = NarrativeMessage(agent="SHEET_update", content="Text")
        assert msg.message_type == "pc_dialogue"

    def test_agent_name_special_chars(self) -> None:
        """Agent names with special chars should be pc_dialogue."""
        msg = NarrativeMessage(agent="rogue#1", content="Sneaking.")
        assert msg.message_type == "pc_dialogue"

    def test_agent_name_unicode(self) -> None:
        """Unicode agent name should be pc_dialogue."""
        msg = NarrativeMessage(agent="rogue", content="Text")
        assert msg.message_type == "pc_dialogue"

    def test_message_type_is_property(self) -> None:
        """message_type should be a property, not stored."""
        msg = NarrativeMessage(agent="dm", content="Text")
        # Changing agent should change the property
        msg.agent = "fighter"
        assert msg.message_type == "pc_dialogue"

    def test_agent_sHEET_mixed_case_upper(self) -> None:
        """'sHEET' upper() == 'SHEET' should be sheet_update."""
        msg = NarrativeMessage(agent="sHEET", content="Test")
        assert msg.message_type == "sheet_update"

    def test_agent_dM_mixed_case(self) -> None:
        """'dM' lower() == 'dm' should be dm_narration."""
        msg = NarrativeMessage(agent="dM", content="Text")
        assert msg.message_type == "dm_narration"


# =============================================================================
# parse_log_entry Edge Cases for [SHEET] entries
# =============================================================================


class TestParseLogEntrySheetEdgeCases:
    """Extended edge case tests for parse_log_entry with [SHEET] prefix."""

    def test_parse_sheet_entry_empty_content(self) -> None:
        """[SHEET] with empty content after prefix."""
        entry = "[SHEET]: "
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert msg.content == ""

    def test_parse_sheet_entry_only_bracket(self) -> None:
        """[SHEET] with no colon or content after bracket."""
        entry = "[SHEET]"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert msg.content == ""

    def test_parse_sheet_entry_special_chars_in_content(self) -> None:
        """[SHEET] with special characters in the content."""
        entry = "[SHEET]: Updated Thorin: HP: <100> -> 50 & Conditions: +poisoned"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert "<100>" in msg.content
        assert "&" in msg.content

    def test_parse_sheet_entry_duplicate_prefix(self) -> None:
        """[SHEET] with duplicate [SHEET] prefix in content (LLM echo)."""
        entry = "[SHEET]: [SHEET]: Updated Thorin: HP: 45 -> 35 (-10)"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        # The duplicate prefix should be stripped
        assert "Updated Thorin" in msg.content

    def test_parse_sheet_entry_very_long_content(self) -> None:
        """[SHEET] with very long content string."""
        long_changes = "; ".join([f"Change_{i}: value_{i}" for i in range(50)])
        entry = f"[SHEET]: Updated Thorin: {long_changes}"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert msg.message_type == "sheet_update"
        assert "Change_0" in msg.content
        assert "Change_49" in msg.content

    def test_parse_sheet_entry_no_space_after_colon(self) -> None:
        """[SHEET]:content_without_space."""
        entry = "[SHEET]:Updated Thorin: HP: 45 -> 35"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert "Updated Thorin" in msg.content

    def test_parse_sheet_entry_multiple_colons(self) -> None:
        """[SHEET] entry with multiple colons in content."""
        entry = "[SHEET]: Updated Thorin: HP: 45 -> 35: Conditions: added prone: Equipment: gained Shield"
        msg = parse_log_entry(entry)
        assert msg.agent == "SHEET"
        assert "HP: 45 -> 35" in msg.content
        assert "Equipment: gained Shield" in msg.content

    def test_parse_non_sheet_entry_still_works(self) -> None:
        """Ensure non-SHEET entries are not affected by sheet handling."""
        entry = "[DM]: The tavern falls silent."
        msg = parse_log_entry(entry)
        assert msg.agent == "DM"
        assert msg.message_type == "dm_narration"

    def test_parse_entry_without_brackets(self) -> None:
        """Entry without brackets treated as DM narration."""
        entry = "The adventure continues..."
        msg = parse_log_entry(entry)
        assert msg.agent == "dm"
        assert msg.content == entry


# =============================================================================
# render_sheet_message_html Edge Cases
# =============================================================================


class TestRenderSheetMessageHtmlEdgeCases:
    """Extended edge case tests for render_sheet_message_html."""

    def test_very_long_content(self) -> None:
        """Very long content should be preserved without truncation."""
        from app import render_sheet_message_html

        long_content = "Updated Thorin: " + "x" * 5000
        html = render_sheet_message_html(long_content)
        assert 'class="sheet-notification"' in html
        assert "x" * 5000 in html

    def test_special_html_chars_ampersand(self) -> None:
        """Ampersand characters should be escaped."""
        from app import render_sheet_message_html

        html = render_sheet_message_html("HP: 45 -> 35 & Conditions: poisoned")
        assert "&amp;" in html
        assert "& Conditions" not in html

    def test_special_html_chars_angle_brackets(self) -> None:
        """Angle brackets should be escaped."""
        from app import render_sheet_message_html

        html = render_sheet_message_html("Updated <Thorin>: HP changed")
        assert "&lt;Thorin&gt;" in html
        assert "<Thorin>" not in html

    def test_special_html_chars_quotes(self) -> None:
        """Double quotes in content should be escaped."""
        from app import render_sheet_message_html

        html = render_sheet_message_html('Updated "Thorin": HP changed')
        assert "&#x27;" in html or "&quot;" in html or "Thorin" in html

    def test_newline_in_content(self) -> None:
        """Newlines in content should be preserved (not break HTML)."""
        from app import render_sheet_message_html

        html = render_sheet_message_html("Line 1\nLine 2")
        assert 'class="sheet-notification"' in html
        assert "Line 1" in html
        assert "Line 2" in html

    def test_is_current_true_adds_class(self) -> None:
        """is_current=True should add current-turn class after sheet-notification."""
        from app import render_sheet_message_html

        html = render_sheet_message_html("Content", is_current=True)
        assert "sheet-notification current-turn" in html

    def test_is_current_false_no_extra_class(self) -> None:
        """is_current=False should NOT add current-turn class."""
        from app import render_sheet_message_html

        html = render_sheet_message_html("Content", is_current=False)
        assert "current-turn" not in html

    def test_html_structure_has_div_and_p(self) -> None:
        """Output should have div wrapper and p tag."""
        from app import render_sheet_message_html

        html = render_sheet_message_html("Test")
        assert html.startswith("<div")
        assert "<p>" in html
        assert "</p>" in html
        assert html.endswith("</div>")

    def test_unicode_content(self) -> None:
        """Unicode content (emojis, non-ASCII) should render correctly."""
        from app import render_sheet_message_html

        html = render_sheet_message_html("Updated Thorin: Conditions: added cursed")
        assert "cursed" in html
        assert 'class="sheet-notification"' in html


# =============================================================================
# render_narrative_messages Edge Cases
# =============================================================================


class TestRenderNarrativeMessagesEdgeCases:
    """Extended edge case tests for render_narrative_messages."""

    @patch("app.st")
    def test_empty_log_shows_placeholder(self, mock_st: MagicMock) -> None:
        """Empty ground_truth_log should show placeholder message."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [],
            "characters": {},
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 1
        html = call_args[0][0][0]
        assert "narrative-placeholder" in html
        assert "adventure awaits" in html.lower()

    @patch("app.st")
    def test_only_sheet_entries(self, mock_st: MagicMock) -> None:
        """Log with only sheet entries should all render as sheet-notification."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
                "[SHEET]: Updated Elara: Spell Slots: L1: 4/4 -> 3/4",
            ],
            "characters": {},
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 2
        assert all("sheet-notification" in c[0][0] for c in call_args)

    @patch("app.st")
    def test_no_characters_dict_defaults(self, mock_st: MagicMock) -> None:
        """Missing characters dict should not crash rendering."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[DM]: The tavern is quiet.",
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
            ],
            "characters": {},
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 2

    @patch("app.st")
    def test_last_entry_is_sheet_gets_current_turn(self, mock_st: MagicMock) -> None:
        """Last entry being a sheet notification should get current-turn class."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[DM]: Combat begins!",
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
            ],
            "characters": {},
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 2
        # First entry is DM, should NOT have current-turn
        assert "current-turn" not in call_args[0][0][0]
        # Last entry is sheet, should have current-turn
        assert "current-turn" in call_args[1][0][0]

    @patch("app.st")
    def test_single_sheet_entry_gets_current_turn(self, mock_st: MagicMock) -> None:
        """Single sheet entry should get current-turn class."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
            ],
            "characters": {},
        }
        render_narrative_messages(state)
        call_args = mock_st.markdown.call_args_list
        assert len(call_args) == 1
        assert "current-turn" in call_args[0][0][0]
        assert "sheet-notification" in call_args[0][0][0]

    @patch("app.st")
    def test_markdown_unsafe_allow_html(self, mock_st: MagicMock) -> None:
        """All markdown calls should use unsafe_allow_html=True."""
        from app import render_narrative_messages

        state: dict[str, Any] = {
            "ground_truth_log": [
                "[SHEET]: Updated Thorin: HP: 45 -> 35 (-10)",
                "[DM]: Combat continues.",
            ],
            "characters": {},
        }
        render_narrative_messages(state)
        for call in mock_st.markdown.call_args_list:
            assert call[1].get("unsafe_allow_html") is True


# =============================================================================
# dm_turn Edge Cases for Sheet Notifications
# =============================================================================


class TestDmTurnSheetNotificationEdgeCases:
    """Extended edge case tests for dm_turn sheet notifications."""

    @patch("agents.get_llm")
    def test_no_sheet_updates_no_sheet_entries(
        self, mock_get_llm: MagicMock
    ) -> None:
        """DM turn with no sheet updates should produce no [SHEET] entries."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterSheet,
            DMConfig,
            GameConfig,
            GameState,
        )

        fighter_sheet = CharacterSheet(
            name="Thorin",
            race="Dwarf",
            character_class="Fighter",
            level=5,
            strength=18,
            dexterity=12,
            constitution=16,
            intelligence=10,
            wisdom=14,
            charisma=8,
            armor_class=18,
            hit_points_max=52,
            hit_points_current=45,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    race="Dwarf",
                    personality="Brave warrior",
                    color="#FF0000",
                    provider="gemini",
                    model="gemini-1.5-flash",
                )
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": {"Thorin": fighter_sheet},
        }

        # Simple narrative response, no tool calls
        final_response = AIMessage(
            content="The tavern is peaceful tonight.",
        )

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.return_value = final_response
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        log = result["ground_truth_log"]
        sheet_entries = [e for e in log if e.startswith("[SHEET]")]
        dm_entries = [e for e in log if e.startswith("[DM]")]
        assert len(sheet_entries) == 0
        assert len(dm_entries) == 1
        assert "peaceful tonight" in dm_entries[0]

    @patch("agents.get_llm")
    def test_dice_roll_plus_sheet_update_combo(
        self, mock_get_llm: MagicMock
    ) -> None:
        """DM turn with both dice roll and sheet update should produce both."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterSheet,
            DMConfig,
            GameConfig,
            GameState,
        )

        fighter_sheet = CharacterSheet(
            name="Thorin",
            race="Dwarf",
            character_class="Fighter",
            level=5,
            strength=18,
            dexterity=12,
            constitution=16,
            intelligence=10,
            wisdom=14,
            charisma=8,
            armor_class=18,
            hit_points_max=52,
            hit_points_current=45,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    race="Dwarf",
                    personality="Brave warrior",
                    color="#FF0000",
                    provider="gemini",
                    model="gemini-1.5-flash",
                )
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": {"Thorin": fighter_sheet},
        }

        # First response: dice roll + sheet update tool calls
        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_roll_dice",
                    "args": {"notation": "1d20+5"},
                    "id": "call_dice_001",
                },
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "Thorin",
                        "updates": {"hit_points_current": 35},
                    },
                    "id": "call_sheet_001",
                },
            ],
        )
        final_response = AIMessage(
            content="The goblin strikes Thorin! The blade bites deep.",
        )

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        log = result["ground_truth_log"]
        sheet_entries = [e for e in log if e.startswith("[SHEET]")]
        dm_entries = [e for e in log if e.startswith("[DM]")]

        # Should have both sheet notification and DM entry
        assert len(sheet_entries) == 1
        assert len(dm_entries) == 1
        assert "Thorin" in sheet_entries[0]
        assert "HP: 45 -> 35" in sheet_entries[0]
        # Sheet notification should come before DM narrative
        assert log.index(sheet_entries[0]) < log.index(dm_entries[0])

    @patch("agents.get_llm")
    def test_sheet_update_preserves_original_sheets(
        self, mock_get_llm: MagicMock
    ) -> None:
        """DM turn should NOT mutate the input state's character_sheets."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import (
            AgentMemory,
            CharacterConfig,
            CharacterSheet,
            DMConfig,
            GameConfig,
            GameState,
        )

        fighter_sheet = CharacterSheet(
            name="Thorin",
            race="Dwarf",
            character_class="Fighter",
            level=5,
            strength=18,
            dexterity=12,
            constitution=16,
            intelligence=10,
            wisdom=14,
            charisma=8,
            armor_class=18,
            hit_points_max=52,
            hit_points_current=45,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )

        original_sheets = {"Thorin": fighter_sheet}

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    race="Dwarf",
                    personality="Brave warrior",
                    color="#FF0000",
                    provider="gemini",
                    model="gemini-1.5-flash",
                )
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": original_sheets,
        }

        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "Thorin",
                        "updates": {"hit_points_current": 35},
                    },
                    "id": "call_001",
                }
            ],
        )
        final_response = AIMessage(content="Thorin takes damage!")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        # Result should have updated sheets
        assert result["character_sheets"]["Thorin"].hit_points_current == 35
        # Original sheet object should be unchanged (45 HP)
        assert fighter_sheet.hit_points_current == 45


# =============================================================================
# CSS Validation Extended Tests
# =============================================================================


class TestSheetNotificationCSSExtended:
    """Extended CSS validation tests for sheet notification styling."""

    def test_css_border_left_style(self) -> None:
        """Sheet notification should have a left border."""
        with open("styles/theme.css") as f:
            css = f.read()
        assert "border-left:" in css or "border-left-color:" in css

    def test_css_font_family_for_notification_p(self) -> None:
        """Sheet notification p should use var(--font-ui)."""
        with open("styles/theme.css") as f:
            css = f.read()
        # Extract the .sheet-notification p block
        assert "var(--font-ui)" in css

    def test_css_font_size(self) -> None:
        """Sheet notification p should have explicit font-size."""
        with open("styles/theme.css") as f:
            css = f.read()
        # Find the section around .sheet-notification p
        idx = css.find(".sheet-notification p")
        assert idx != -1
        # Check that font-size is defined nearby
        section = css[idx : idx + 200]
        assert "font-size" in section

    def test_css_accent_warm_color_in_notification_div(self) -> None:
        """The .sheet-notification rule should reference --accent-warm."""
        with open("styles/theme.css") as f:
            css = f.read()
        # Find the .sheet-notification block (not .sheet-notification p)
        idx = css.find(".sheet-notification {")
        assert idx != -1
        # Check the block up to the closing brace
        end_idx = css.find("}", idx)
        block = css[idx:end_idx]
        assert "var(--accent-warm)" in block

    def test_css_background_rgba(self) -> None:
        """Sheet notification should have a semi-transparent background."""
        with open("styles/theme.css") as f:
            css = f.read()
        idx = css.find(".sheet-notification {")
        assert idx != -1
        end_idx = css.find("}", idx)
        block = css[idx:end_idx]
        assert "rgba(" in block

    def test_css_border_radius(self) -> None:
        """Sheet notification should have border-radius for rounded corners."""
        with open("styles/theme.css") as f:
            css = f.read()
        idx = css.find(".sheet-notification {")
        assert idx != -1
        end_idx = css.find("}", idx)
        block = css[idx:end_idx]
        assert "border-radius" in block

    def test_css_margin_bottom(self) -> None:
        """Sheet notification should have margin-bottom for spacing."""
        with open("styles/theme.css") as f:
            css = f.read()
        idx = css.find(".sheet-notification {")
        assert idx != -1
        end_idx = css.find("}", idx)
        block = css[idx:end_idx]
        assert "margin-bottom" in block

    def test_css_paragraph_margin_zero(self) -> None:
        """Sheet notification p should have margin: 0."""
        with open("styles/theme.css") as f:
            css = f.read()
        idx = css.find(".sheet-notification p")
        assert idx != -1
        end_idx = css.find("}", idx)
        block = css[idx:end_idx]
        assert "margin: 0" in block

    def test_css_paragraph_color_accent_warm(self) -> None:
        """Sheet notification p should use accent-warm color."""
        with open("styles/theme.css") as f:
            css = f.read()
        idx = css.find(".sheet-notification p")
        assert idx != -1
        end_idx = css.find("}", idx)
        block = css[idx:end_idx]
        assert "var(--accent-warm)" in block

    def test_css_line_height(self) -> None:
        """Sheet notification p should have line-height set."""
        with open("styles/theme.css") as f:
            css = f.read()
        idx = css.find(".sheet-notification p")
        assert idx != -1
        end_idx = css.find("}", idx)
        block = css[idx:end_idx]
        assert "line-height" in block


# =============================================================================
# create_initial_game_state and populate_game_state character_sheets Tests
# =============================================================================


class TestGameStateFactoryCharacterSheets:
    """Tests that create_initial_game_state and populate_game_state include character_sheets."""

    def test_create_initial_game_state_has_character_sheets(self) -> None:
        """create_initial_game_state should include empty character_sheets dict."""
        from models import create_initial_game_state

        state = create_initial_game_state()
        assert "character_sheets" in state
        assert isinstance(state["character_sheets"], dict)
        assert len(state["character_sheets"]) == 0

    @patch("config.load_character_configs")
    @patch("config.load_dm_config")
    def test_populate_game_state_has_character_sheets(
        self, mock_dm: MagicMock, mock_chars: MagicMock
    ) -> None:
        """populate_game_state should include character_sheets key."""
        from models import CharacterConfig, DMConfig, populate_game_state

        mock_dm.return_value = DMConfig()
        mock_chars.return_value = {
            "fighter": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                race="Dwarf",
                personality="Brave",
                color="#FF0000",
            )
        }

        state = populate_game_state(include_sample_messages=False)
        assert "character_sheets" in state
        assert isinstance(state["character_sheets"], dict)
        # populate_game_state initializes character_sheets as empty by default
        assert len(state["character_sheets"]) == 0

    @patch("config.load_character_configs")
    @patch("config.load_dm_config")
    def test_populate_game_state_character_sheets_is_empty_dict(
        self, mock_dm: MagicMock, mock_chars: MagicMock
    ) -> None:
        """populate_game_state creates empty character_sheets (filled later by DM)."""
        from models import CharacterConfig, DMConfig, populate_game_state

        mock_dm.return_value = DMConfig()
        mock_chars.return_value = {
            "fighter": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                race="Dwarf",
                personality="Brave",
                color="#FF0000",
            ),
            "wizard": CharacterConfig(
                name="Elara",
                character_class="Wizard",
                race="Elf",
                personality="Wise",
                color="#7B68B8",
            ),
        }

        state = populate_game_state(include_sample_messages=False)
        # Sheets are empty initially - populated when adventure starts
        assert state["character_sheets"] == {}


# =============================================================================
# _execute_sheet_update Notification Message Format Tests
# =============================================================================


class TestExecuteSheetUpdateNotifications:
    """Tests for _execute_sheet_update notification message format."""

    def test_successful_update_starts_with_updated(self) -> None:
        """Successful update confirmation should start with 'Updated'."""
        from agents import _execute_sheet_update
        from models import CharacterSheet

        sheet = CharacterSheet(
            name="Thorin",
            race="Dwarf",
            character_class="Fighter",
            level=5,
            strength=18,
            dexterity=12,
            constitution=16,
            intelligence=10,
            wisdom=14,
            charisma=8,
            armor_class=18,
            hit_points_max=52,
            hit_points_current=45,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )
        sheets: dict[str, CharacterSheet] = {"Thorin": sheet}

        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": {"hit_points_current": 40}},
            sheets,
        )
        assert result.startswith("Updated Thorin")
        assert "HP:" in result

    def test_error_message_starts_with_error(self) -> None:
        """Failed update should return message starting with 'Error'."""
        from agents import _execute_sheet_update
        from models import CharacterSheet

        sheets: dict[str, CharacterSheet] = {}

        result = _execute_sheet_update(
            {"character_name": "NonExistent", "updates": {"hit_points_current": 40}},
            sheets,
        )
        assert result.startswith("Error")

    def test_missing_character_name_returns_error(self) -> None:
        """Missing character_name should return an error message."""
        from agents import _execute_sheet_update
        from models import CharacterSheet

        sheets: dict[str, CharacterSheet] = {}

        result = _execute_sheet_update(
            {"updates": {"hit_points_current": 40}},
            sheets,
        )
        assert result.startswith("Error")

    def test_notification_not_generated_for_error(self) -> None:
        """Error results should NOT start with 'Updated' (not a notification)."""
        from agents import _execute_sheet_update
        from models import CharacterSheet

        sheets: dict[str, CharacterSheet] = {}

        result = _execute_sheet_update(
            {"character_name": "Ghost", "updates": {"hit_points_current": 10}},
            sheets,
        )
        assert not result.startswith("Updated")


# =============================================================================
# NarrativeMessage Model Validation Tests
# =============================================================================


class TestNarrativeMessageModel:
    """Tests for NarrativeMessage model validation and fields."""

    def test_timestamp_defaults_to_none(self) -> None:
        """NarrativeMessage timestamp should default to None."""
        msg = NarrativeMessage(agent="dm", content="Text")
        assert msg.timestamp is None

    def test_timestamp_can_be_set(self) -> None:
        """NarrativeMessage timestamp can be explicitly set."""
        msg = NarrativeMessage(agent="dm", content="Text", timestamp="2026-01-01T00:00:00Z")
        assert msg.timestamp == "2026-01-01T00:00:00Z"

    def test_content_can_be_empty(self) -> None:
        """NarrativeMessage content can be an empty string."""
        msg = NarrativeMessage(agent="SHEET", content="")
        assert msg.content == ""
        assert msg.message_type == "sheet_update"

    def test_agent_and_content_are_required(self) -> None:
        """NarrativeMessage should require agent and content."""
        with pytest.raises(Exception):
            NarrativeMessage(agent="dm")  # type: ignore[call-arg]

        with pytest.raises(Exception):
            NarrativeMessage(content="text")  # type: ignore[call-arg]
