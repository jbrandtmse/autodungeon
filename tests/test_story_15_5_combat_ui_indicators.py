"""Tests for Story 15.5: Combat UI Indicators.

Tests for render_combat_banner_html(), render_combat_banner(),
render_initiative_order_html(), render_initiative_order(),
and their integration into render_main_content() / render_sidebar().
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app import (
    render_combat_banner,
    render_combat_banner_html,
    render_initiative_order,
    render_initiative_order_html,
)
from models import CharacterConfig, CombatState, NpcProfile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_character(
    name: str = "Theron",
    character_class: str = "Fighter",
    color: str = "#C45C4A",
) -> CharacterConfig:
    return CharacterConfig(
        name=name,
        character_class=character_class,
        personality="Brave and stoic",
        color=color,
    )


def _make_combat_state(
    active: bool = True,
    round_number: int = 1,
    initiative_order: list[str] | None = None,
    initiative_rolls: dict[str, int] | None = None,
    npc_profiles: dict[str, NpcProfile] | None = None,
) -> CombatState:
    return CombatState(
        active=active,
        round_number=round_number,
        initiative_order=initiative_order or [],
        initiative_rolls=initiative_rolls or {},
        npc_profiles=npc_profiles or {},
    )


def _make_game_state(
    combat_state: CombatState | None = None,
    current_turn: str = "",
    characters: dict[str, CharacterConfig] | None = None,
) -> dict:
    game: dict = {
        "ground_truth_log": [],
        "session_number": 1,
        "current_turn": current_turn,
        "characters": characters or {},
    }
    if combat_state is not None:
        game["combat_state"] = combat_state
    return game


# ===========================================================================
# TestRenderCombatBannerHtml
# ===========================================================================


class TestRenderCombatBannerHtml:
    """Test render_combat_banner_html() HTML generation."""

    def test_returns_html_for_round_1(self) -> None:
        html = render_combat_banner_html(1)
        assert "combat-banner" in html
        assert "Round 1" in html

    def test_returns_html_for_round_5(self) -> None:
        html = render_combat_banner_html(5)
        assert "Round 5" in html

    def test_returns_html_for_round_10(self) -> None:
        html = render_combat_banner_html(10)
        assert "Round 10" in html

    def test_contains_combat_banner_css_class(self) -> None:
        html = render_combat_banner_html(1)
        assert 'class="combat-banner"' in html

    def test_contains_combat_banner_label(self) -> None:
        html = render_combat_banner_html(1)
        assert "combat-banner-label" in html
        assert "COMBAT" in html

    def test_contains_combat_banner_round(self) -> None:
        html = render_combat_banner_html(3)
        assert "combat-banner-round" in html
        assert "Round 3" in html

    def test_returns_empty_string_for_round_zero(self) -> None:
        assert render_combat_banner_html(0) == ""

    def test_returns_empty_string_for_negative_round(self) -> None:
        assert render_combat_banner_html(-1) == ""
        assert render_combat_banner_html(-10) == ""


# ===========================================================================
# TestRenderInitiativeOrderHtml
# ===========================================================================


class TestRenderInitiativeOrderHtml:
    """Test render_initiative_order_html() HTML generation."""

    def test_renders_pc_entries_with_character_names(self) -> None:
        combat = _make_combat_state(
            initiative_order=["theron"],
            initiative_rolls={"theron": 18},
        )
        chars = {"theron": _make_character("Theron", "Fighter")}
        html = render_initiative_order_html(combat, "", chars)
        assert "Theron" in html
        assert "initiative-pc" in html
        assert "fighter" in html

    def test_renders_pc_with_class_slug(self) -> None:
        combat = _make_combat_state(
            initiative_order=["shadowmere"],
            initiative_rolls={"shadowmere": 15},
        )
        chars = {"shadowmere": _make_character("Shadowmere", "Rogue")}
        html = render_initiative_order_html(combat, "", chars)
        assert "rogue" in html

    def test_renders_npc_entries_with_profile_names(self) -> None:
        combat = _make_combat_state(
            initiative_order=["dm:goblin_1"],
            initiative_rolls={"dm:goblin_1": 12},
            npc_profiles={"goblin_1": NpcProfile(name="Goblin 1")},
        )
        html = render_initiative_order_html(combat, "", {})
        assert "Goblin 1" in html
        assert "initiative-npc" in html

    def test_skips_dm_bookend_entry(self) -> None:
        combat = _make_combat_state(
            initiative_order=["dm", "theron", "dm:goblin_1"],
            initiative_rolls={"theron": 18, "dm:goblin_1": 12},
            npc_profiles={"goblin_1": NpcProfile(name="Goblin 1")},
        )
        chars = {"theron": _make_character()}
        html = render_initiative_order_html(combat, "", chars)
        # Should have entries for theron and goblin but not a standalone "dm" entry
        entries = html.count("initiative-entry")
        assert entries == 2

    def test_highlights_current_turn_with_active_class(self) -> None:
        combat = _make_combat_state(
            initiative_order=["theron", "shadowmere"],
            initiative_rolls={"theron": 18, "shadowmere": 15},
        )
        chars = {
            "theron": _make_character("Theron", "Fighter"),
            "shadowmere": _make_character("Shadowmere", "Rogue"),
        }
        html = render_initiative_order_html(combat, "theron", chars)
        # Theron's entry should have initiative-active
        assert "initiative-active" in html
        # Check that only one entry has it (Theron, not Shadowmere)
        # Split on initiative-entry to analyze individual entries
        parts = html.split("initiative-entry")
        active_count = sum(1 for p in parts if "initiative-active" in p)
        assert active_count == 1

    def test_displays_initiative_rolls(self) -> None:
        combat = _make_combat_state(
            initiative_order=["theron"],
            initiative_rolls={"theron": 18},
        )
        chars = {"theron": _make_character()}
        html = render_initiative_order_html(combat, "", chars)
        assert "18" in html
        assert "initiative-roll" in html

    def test_falls_back_to_raw_npc_key_when_profile_missing(self) -> None:
        combat = _make_combat_state(
            initiative_order=["dm:unknown_npc"],
            initiative_rolls={"dm:unknown_npc": 8},
            npc_profiles={},  # No profile for unknown_npc
        )
        html = render_initiative_order_html(combat, "", {})
        assert "unknown_npc" in html

    def test_falls_back_to_raw_pc_key_when_character_missing(self) -> None:
        combat = _make_combat_state(
            initiative_order=["unknown_pc"],
            initiative_rolls={"unknown_pc": 10},
        )
        html = render_initiative_order_html(combat, "", {})
        assert "unknown_pc" in html

    def test_escapes_html_in_character_names(self) -> None:
        combat = _make_combat_state(
            initiative_order=["xss_pc"],
            initiative_rolls={"xss_pc": 10},
        )
        chars = {
            "xss_pc": _make_character('<script>alert("xss")</script>', "Fighter")
        }
        html = render_initiative_order_html(combat, "", chars)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_escapes_html_in_npc_names(self) -> None:
        combat = _make_combat_state(
            initiative_order=["dm:evil"],
            initiative_rolls={"dm:evil": 10},
            npc_profiles={
                "evil": NpcProfile(name='<img src=x onerror="alert(1)">')
            },
        )
        html = render_initiative_order_html(combat, "", {})
        assert "<img" not in html
        assert "&lt;img" in html

    def test_empty_initiative_order_returns_empty_container(self) -> None:
        combat = _make_combat_state(initiative_order=[])
        html = render_initiative_order_html(combat, "", {})
        assert 'class="initiative-order"' in html
        assert "initiative-entry" not in html

    def test_initiative_order_with_only_pcs(self) -> None:
        combat = _make_combat_state(
            initiative_order=["theron", "shadowmere"],
            initiative_rolls={"theron": 18, "shadowmere": 15},
        )
        chars = {
            "theron": _make_character("Theron", "Fighter"),
            "shadowmere": _make_character("Shadowmere", "Rogue"),
        }
        html = render_initiative_order_html(combat, "", chars)
        assert "initiative-pc" in html
        assert "initiative-npc" not in html

    def test_initiative_order_with_only_npcs(self) -> None:
        combat = _make_combat_state(
            initiative_order=["dm:goblin_1", "dm:goblin_2"],
            initiative_rolls={"dm:goblin_1": 12, "dm:goblin_2": 8},
            npc_profiles={
                "goblin_1": NpcProfile(name="Goblin 1"),
                "goblin_2": NpcProfile(name="Goblin 2"),
            },
        )
        html = render_initiative_order_html(combat, "", {})
        assert "initiative-npc" in html
        assert "initiative-pc" not in html

    def test_initiative_order_with_mixed_pcs_and_npcs(self) -> None:
        combat = _make_combat_state(
            initiative_order=["dm", "theron", "dm:goblin_1", "shadowmere"],
            initiative_rolls={
                "theron": 18,
                "dm:goblin_1": 12,
                "shadowmere": 15,
            },
            npc_profiles={"goblin_1": NpcProfile(name="Goblin 1")},
        )
        chars = {
            "theron": _make_character("Theron", "Fighter"),
            "shadowmere": _make_character("Shadowmere", "Rogue"),
        }
        html = render_initiative_order_html(combat, "", chars)
        assert "initiative-pc" in html
        assert "initiative-npc" in html
        assert "Theron" in html
        assert "Goblin 1" in html
        assert "Shadowmere" in html

    def test_roll_defaults_to_zero_when_missing(self) -> None:
        combat = _make_combat_state(
            initiative_order=["theron"],
            initiative_rolls={},  # No roll for theron
        )
        chars = {"theron": _make_character()}
        html = render_initiative_order_html(combat, "", chars)
        assert ">0<" in html


# ===========================================================================
# TestRenderCombatBanner
# ===========================================================================


class TestRenderCombatBanner:
    """Test render_combat_banner() Streamlit wrapper."""

    @patch("app.st")
    def test_calls_markdown_when_combat_active(self, mock_st: MagicMock) -> None:
        combat = _make_combat_state(active=True, round_number=2)
        mock_st.session_state = {"game": _make_game_state(combat_state=combat)}
        render_combat_banner()
        mock_st.markdown.assert_called_once()
        call_args = mock_st.markdown.call_args
        assert "combat-banner" in call_args[0][0]
        assert "Round 2" in call_args[0][0]
        assert call_args[1]["unsafe_allow_html"] is True

    @patch("app.st")
    def test_renders_nothing_when_combat_inactive(self, mock_st: MagicMock) -> None:
        combat = _make_combat_state(active=False, round_number=0)
        mock_st.session_state = {"game": _make_game_state(combat_state=combat)}
        render_combat_banner()
        mock_st.markdown.assert_not_called()

    @patch("app.st")
    def test_renders_nothing_when_game_state_missing(
        self, mock_st: MagicMock
    ) -> None:
        mock_st.session_state = {}
        render_combat_banner()
        mock_st.markdown.assert_not_called()

    @patch("app.st")
    def test_renders_nothing_when_combat_state_missing(
        self, mock_st: MagicMock
    ) -> None:
        mock_st.session_state = {"game": _make_game_state()}
        render_combat_banner()
        mock_st.markdown.assert_not_called()


# ===========================================================================
# TestRenderInitiativeOrder
# ===========================================================================


class TestRenderInitiativeOrder:
    """Test render_initiative_order() Streamlit wrapper."""

    @patch("app.st")
    def test_calls_markdown_when_combat_active(self, mock_st: MagicMock) -> None:
        combat = _make_combat_state(
            active=True,
            round_number=1,
            initiative_order=["theron"],
            initiative_rolls={"theron": 18},
        )
        chars = {"theron": _make_character()}
        mock_st.session_state = {
            "game": _make_game_state(
                combat_state=combat,
                current_turn="theron",
                characters=chars,
            )
        }
        render_initiative_order()
        # Should have 3 markdown calls: "---", "### Initiative", and the HTML
        assert mock_st.markdown.call_count == 3

    @patch("app.st")
    def test_renders_nothing_when_combat_inactive(
        self, mock_st: MagicMock
    ) -> None:
        combat = _make_combat_state(active=False)
        mock_st.session_state = {"game": _make_game_state(combat_state=combat)}
        render_initiative_order()
        mock_st.markdown.assert_not_called()

    @patch("app.st")
    def test_renders_nothing_when_game_state_missing(
        self, mock_st: MagicMock
    ) -> None:
        mock_st.session_state = {}
        render_initiative_order()
        mock_st.markdown.assert_not_called()

    @patch("app.st")
    def test_renders_initiative_heading(self, mock_st: MagicMock) -> None:
        combat = _make_combat_state(
            active=True,
            round_number=1,
            initiative_order=["theron"],
            initiative_rolls={"theron": 18},
        )
        chars = {"theron": _make_character()}
        mock_st.session_state = {
            "game": _make_game_state(
                combat_state=combat,
                current_turn="theron",
                characters=chars,
            )
        }
        render_initiative_order()
        # Check that "### Initiative" was rendered
        calls = [str(c) for c in mock_st.markdown.call_args_list]
        assert any("### Initiative" in c for c in calls)


# ===========================================================================
# TestCombatBannerIntegration
# ===========================================================================


class TestCombatBannerIntegration:
    """Test render_main_content() calls render_combat_banner()."""

    @patch("app.render_combat_banner")
    @patch("app.inject_auto_scroll_script")
    @patch("app.render_auto_scroll_indicator")
    @patch("app.render_narrative_messages")
    @patch("app.render_human_input_area")
    @patch("app.render_error_panel")
    @patch("app.load_fork_registry")
    @patch("app.st")
    def test_render_main_content_calls_combat_banner(
        self,
        mock_st: MagicMock,
        mock_fork_reg: MagicMock,
        mock_error: MagicMock,
        mock_input: MagicMock,
        mock_narrative: MagicMock,
        mock_scroll_ind: MagicMock,
        mock_scroll_js: MagicMock,
        mock_combat_banner: MagicMock,
    ) -> None:
        from app import render_main_content

        mock_st.session_state = {"game": _make_game_state()}
        render_main_content()
        mock_combat_banner.assert_called_once()


# ===========================================================================
# TestInitiativeOrderIntegration
# ===========================================================================


class TestInitiativeOrderIntegration:
    """Test render_sidebar() calls render_initiative_order()."""

    @patch("app.handle_back_to_sessions_click")
    @patch("app.render_configure_button")
    @patch("app.validate_api_keys", return_value=[])
    @patch("app.get_api_key_status", return_value="OK")
    @patch("app.render_fork_controls")
    @patch("app.render_story_threads")
    @patch("app.render_human_whisper_input")
    @patch("app.render_nudge_input")
    @patch("app.render_export_transcript_button")
    @patch("app.render_initiative_order")
    @patch("app.render_keyboard_shortcuts_help")
    @patch("app.render_character_card")
    @patch("app.render_game_controls")
    @patch("app.render_session_controls")
    @patch("app.render_checkpoint_browser")
    @patch("app.st")
    def test_render_sidebar_calls_initiative_order(
        self,
        mock_st: MagicMock,
        mock_checkpoint: MagicMock,
        mock_session_ctrl: MagicMock,
        mock_game_ctrl: MagicMock,
        mock_char_card: MagicMock,
        mock_shortcuts: MagicMock,
        mock_initiative: MagicMock,
        mock_export: MagicMock,
        mock_nudge: MagicMock,
        mock_whisper: MagicMock,
        mock_threads: MagicMock,
        mock_fork: MagicMock,
        mock_api_status: MagicMock,
        mock_validate: MagicMock,
        mock_configure: MagicMock,
        mock_back: MagicMock,
    ) -> None:
        from app import render_sidebar
        from config import AppConfig

        combat = _make_combat_state(active=True, round_number=1)
        chars = {"theron": _make_character()}
        mock_st.session_state = {
            "game": _make_game_state(
                combat_state=combat,
                current_turn="theron",
                characters=chars,
            ),
            "ui_mode": "watch",
            "is_generating": False,
            "is_paused": False,
            "controlled_character": None,
        }
        mock_st.sidebar.__enter__ = MagicMock(return_value=None)
        mock_st.sidebar.__exit__ = MagicMock(return_value=False)

        config = MagicMock(spec=AppConfig)
        render_sidebar(config)
        mock_initiative.assert_called_once()

    @patch("app.handle_back_to_sessions_click")
    @patch("app.render_configure_button")
    @patch("app.validate_api_keys", return_value=[])
    @patch("app.get_api_key_status", return_value="OK")
    @patch("app.render_fork_controls")
    @patch("app.render_story_threads")
    @patch("app.render_human_whisper_input")
    @patch("app.render_nudge_input")
    @patch("app.render_export_transcript_button")
    @patch("app.render_initiative_order")
    @patch("app.render_keyboard_shortcuts_help")
    @patch("app.render_character_card")
    @patch("app.render_game_controls")
    @patch("app.render_session_controls")
    @patch("app.render_checkpoint_browser")
    @patch("app.st")
    def test_render_sidebar_no_initiative_when_no_combat(
        self,
        mock_st: MagicMock,
        mock_checkpoint: MagicMock,
        mock_session_ctrl: MagicMock,
        mock_game_ctrl: MagicMock,
        mock_char_card: MagicMock,
        mock_shortcuts: MagicMock,
        mock_initiative: MagicMock,
        mock_export: MagicMock,
        mock_nudge: MagicMock,
        mock_whisper: MagicMock,
        mock_threads: MagicMock,
        mock_fork: MagicMock,
        mock_api_status: MagicMock,
        mock_validate: MagicMock,
        mock_configure: MagicMock,
        mock_back: MagicMock,
    ) -> None:
        """render_initiative_order is always called but it internally checks combat state."""
        from app import render_sidebar
        from config import AppConfig

        mock_st.session_state = {
            "game": _make_game_state(),
            "ui_mode": "watch",
            "is_generating": False,
            "is_paused": False,
            "controlled_character": None,
        }
        mock_st.sidebar.__enter__ = MagicMock(return_value=None)
        mock_st.sidebar.__exit__ = MagicMock(return_value=False)

        config = MagicMock(spec=AppConfig)
        render_sidebar(config)
        # render_initiative_order is called but internally renders nothing
        mock_initiative.assert_called_once()


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    """Edge case tests for combat UI indicators."""

    @patch("app.st")
    def test_combat_state_as_plain_dict_renders_nothing(
        self, mock_st: MagicMock
    ) -> None:
        """A plain dict (not CombatState instance) should be ignored."""
        game = _make_game_state()
        game["combat_state"] = {"active": True, "round_number": 1}
        mock_st.session_state = {"game": game}
        render_combat_banner()
        mock_st.markdown.assert_not_called()

    @patch("app.st")
    def test_combat_state_inactive_produces_no_banner(
        self, mock_st: MagicMock
    ) -> None:
        combat = _make_combat_state(active=False, round_number=0)
        mock_st.session_state = {"game": _make_game_state(combat_state=combat)}
        render_combat_banner()
        mock_st.markdown.assert_not_called()

    @patch("app.st")
    def test_combat_state_inactive_produces_no_initiative(
        self, mock_st: MagicMock
    ) -> None:
        combat = _make_combat_state(active=False)
        mock_st.session_state = {"game": _make_game_state(combat_state=combat)}
        render_initiative_order()
        mock_st.markdown.assert_not_called()

    def test_npc_key_with_underscores_displays_correctly(self) -> None:
        combat = _make_combat_state(
            initiative_order=["dm:goblin_archer_1"],
            initiative_rolls={"dm:goblin_archer_1": 14},
            npc_profiles={
                "goblin_archer_1": NpcProfile(name="Goblin Archer 1")
            },
        )
        html = render_initiative_order_html(combat, "", {})
        assert "Goblin Archer 1" in html

    def test_very_long_initiative_order_renders_all(self) -> None:
        order = [f"pc_{i}" for i in range(12)]
        rolls = {f"pc_{i}": 20 - i for i in range(12)}
        combat = _make_combat_state(
            initiative_order=order,
            initiative_rolls=rolls,
        )
        chars = {
            f"pc_{i}": _make_character(f"Hero {i}", "Fighter")
            for i in range(12)
        }
        html = render_initiative_order_html(combat, "", chars)
        for i in range(12):
            assert f"Hero {i}" in html

    def test_current_turn_matches_npc_entry(self) -> None:
        combat = _make_combat_state(
            initiative_order=["dm:goblin_1", "theron"],
            initiative_rolls={"dm:goblin_1": 16, "theron": 12},
            npc_profiles={"goblin_1": NpcProfile(name="Goblin 1")},
        )
        chars = {"theron": _make_character()}
        html = render_initiative_order_html(combat, "dm:goblin_1", chars)
        # The goblin's entry should have the active class
        # Split entries and check
        assert "initiative-active" in html
        # Find the NPC entry with active class
        assert 'initiative-npc initiative-active' in html

    def test_current_turn_is_dm_bookend_no_highlight(self) -> None:
        """When current_turn is 'dm' (bookend), no entry is highlighted."""
        combat = _make_combat_state(
            initiative_order=["dm", "theron", "dm:goblin_1"],
            initiative_rolls={"theron": 18, "dm:goblin_1": 12},
            npc_profiles={"goblin_1": NpcProfile(name="Goblin 1")},
        )
        chars = {"theron": _make_character()}
        html = render_initiative_order_html(combat, "dm", chars)
        assert "initiative-active" not in html

    @patch("app.st")
    def test_combat_state_plain_dict_initiative_renders_nothing(
        self, mock_st: MagicMock
    ) -> None:
        """A plain dict (not CombatState instance) should be ignored for initiative."""
        game = _make_game_state()
        game["combat_state"] = {"active": True, "round_number": 1}
        mock_st.session_state = {"game": game}
        render_initiative_order()
        mock_st.markdown.assert_not_called()

    def test_npc_fallback_when_profile_not_found_uses_raw_key(self) -> None:
        """When NPC profile is not found, display the raw NPC key."""
        combat = _make_combat_state(
            initiative_order=["dm:mysterious_villain"],
            initiative_rolls={"dm:mysterious_villain": 20},
            npc_profiles={},
        )
        html = render_initiative_order_html(combat, "", {})
        assert "mysterious_villain" in html
