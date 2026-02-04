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
