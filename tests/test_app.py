"""Tests for Streamlit app entry point."""

import os
from pathlib import Path
from unittest.mock import patch


class TestAppEntryPoint:
    """Tests for app.py functionality."""

    def test_app_loads_config(self) -> None:
        """Test that the app module can load configuration."""
        from config import get_config

        config = get_config()
        assert config is not None
        assert hasattr(config, "default_provider")

    def test_get_api_key_status_all_missing(self) -> None:
        """Test API key status when all keys are missing."""
        with patch.dict(os.environ, {}, clear=True):
            from app import get_api_key_status
            from config import AppConfig

            config = AppConfig()
            status = get_api_key_status(config)

            assert "Gemini" in status
            assert "Claude" in status
            assert "Ollama" in status
            # All should show as not configured or available (Ollama has default URL)

    def test_get_api_key_status_with_keys(self) -> None:
        """Test API key status when keys are set."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_KEY": "test-google-key",
                "ANTHROPIC_API_KEY": "test-anthropic-key",
            },
            clear=False,
        ):
            from app import get_api_key_status
            from config import AppConfig

            config = AppConfig()
            status = get_api_key_status(config)

            # Should indicate keys are configured
            assert "Gemini" in status
            assert "Claude" in status


class TestCSSThemeFile:
    """Tests for CSS theme file (Task 5.1)."""

    def test_css_file_exists(self) -> None:
        """Test that styles/theme.css exists."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        assert css_path.exists(), f"CSS file not found at {css_path}"

    def test_css_contains_required_variables(self) -> None:
        """Test that CSS file contains required CSS variables."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Background colors from UX spec
        assert "--bg-primary: #1A1612" in css_content
        assert "--bg-secondary: #2D2520" in css_content
        assert "--bg-message: #3D3530" in css_content

        # Text colors
        assert "--text-primary: #F5E6D3" in css_content
        assert "--text-secondary: #B8A896" in css_content

        # Accent
        assert "--accent-warm: #E8A849" in css_content

        # Character identity colors
        assert "--color-dm: #D4A574" in css_content
        assert "--color-fighter: #C45C4A" in css_content
        assert "--color-rogue: #6B8E6B" in css_content
        assert "--color-wizard: #7B68B8" in css_content
        assert "--color-cleric: #4A90A4" in css_content

        # Font stacks
        assert "--font-narrative:" in css_content
        assert "'Lora'" in css_content
        assert "--font-ui:" in css_content
        assert "'Inter'" in css_content
        assert "--font-mono:" in css_content

        # Font sizes
        assert "--text-dm: 18px" in css_content
        assert "--text-pc: 17px" in css_content
        assert "--text-name: 14px" in css_content
        assert "--text-ui: 14px" in css_content
        assert "--text-system: 13px" in css_content

    def test_css_contains_sidebar_width(self) -> None:
        """Test that CSS file contains 240px sidebar width rule (Task 5.3)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check for sidebar width variable
        assert "--sidebar-width: 240px" in css_content

        # Check for actual usage in sidebar styling
        assert "width: var(--sidebar-width)" in css_content

    def test_css_contains_viewport_warning(self) -> None:
        """Test that CSS file contains viewport warning styles for <1024px."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check for viewport warning class
        assert ".viewport-warning" in css_content

        # Check for media query at 1023px breakpoint
        assert "@media (max-width: 1023px)" in css_content


class TestLoadCss:
    """Tests for load_css function."""

    def test_load_css_returns_content(self) -> None:
        """Test that load_css returns CSS content when file exists."""
        from app import load_css

        css = load_css()
        assert css, "CSS content should not be empty"
        assert "--bg-primary" in css, "CSS should contain CSS variables"

    def test_load_css_empty_when_no_file(self) -> None:
        """Test that load_css returns empty string when file doesn't exist."""
        from app import load_css

        with patch("pathlib.Path.exists", return_value=False):
            css = load_css()
            assert css == "", "Should return empty string when file not found"


class TestSessionStateInitialization:
    """Tests for session state initialization (Task 5.2)."""

    def test_initialize_session_state_creates_game(self) -> None:
        """Test that initialize_session_state creates GameState."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert "game" in mock_session_state
            game = mock_session_state["game"]

            # Verify GameState structure
            assert "ground_truth_log" in game
            assert "turn_queue" in game
            assert "current_turn" in game
            assert "agent_memories" in game
            assert "game_config" in game
            assert "dm_config" in game
            assert "characters" in game
            assert "human_active" in game
            assert "controlled_character" in game

    def test_initialize_session_state_sets_ui_mode(self) -> None:
        """Test that initialize_session_state sets ui_mode to 'watch'."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert mock_session_state["ui_mode"] == "watch"

    def test_initialize_session_state_sets_controlled_character(self) -> None:
        """Test that initialize_session_state sets controlled_character to None."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert mock_session_state["controlled_character"] is None

    def test_initialize_session_state_idempotent(self) -> None:
        """Test that initialize_session_state doesn't overwrite existing game."""
        mock_session_state = {"game": {"existing": True}}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            # Should NOT overwrite existing game
            assert mock_session_state["game"] == {"existing": True}

    def test_populate_game_state_loads_characters(self) -> None:
        """Test that populate_game_state loads characters from config."""
        from models import populate_game_state

        game = populate_game_state()

        # Should have DM in turn_queue
        assert "dm" in game["turn_queue"]

        # Should have agent memories for DM
        assert "dm" in game["agent_memories"]

        # Current turn should start with DM
        assert game["current_turn"] == "dm"


class TestDMMessageStyling:
    """Tests for DM message CSS styling (Story 2.2, Task 1)."""

    def test_dm_message_class_exists(self) -> None:
        """Test that .dm-message class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".dm-message" in css_content

    def test_dm_message_has_gold_border(self) -> None:
        """Test that DM message has gold border-left."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check DM message uses --color-dm variable for border
        assert "var(--color-dm)" in css_content

    def test_dm_message_has_italic_text(self) -> None:
        """Test that DM message uses italic font style."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "font-style: italic" in css_content

    def test_dm_message_uses_lora_font(self) -> None:
        """Test that DM message uses Lora font for narrative feel."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check dm-message section uses font-narrative (Lora)
        assert "var(--font-narrative)" in css_content

    def test_dm_message_border_width_is_4px(self) -> None:
        """Test that DM message has 4px border-left per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Find the .dm-message block and verify 4px border
        assert "border-left: 4px solid var(--color-dm)" in css_content

    def test_dm_message_p_has_italic_and_justify(self) -> None:
        """Test that .dm-message p has italic text and justify alignment."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Verify both properties exist (they should be in .dm-message p block)
        assert "font-style: italic" in css_content
        assert "text-align: justify" in css_content


class TestPCMessageStyling:
    """Tests for PC message CSS styling (Story 2.2, Task 1)."""

    def test_pc_message_class_exists(self) -> None:
        """Test that .pc-message class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".pc-message" in css_content

    def test_pc_message_character_classes_exist(self) -> None:
        """Test that PC message classes exist for all characters."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".pc-message.{char}" in css_content, f"Missing .pc-message.{char}"

    def test_pc_attribution_class_exists(self) -> None:
        """Test that .pc-attribution class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".pc-attribution" in css_content

    def test_pc_attribution_character_classes_exist(self) -> None:
        """Test that PC attribution classes exist for all characters."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".pc-attribution.{char}" in css_content, (
                f"Missing .pc-attribution.{char}"
            )

    def test_action_text_class_exists(self) -> None:
        """Test that action text styling class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".action-text" in css_content


class TestSessionHeaderStyling:
    """Tests for session header CSS styling (Story 2.2, Task 2)."""

    def test_session_title_class_exists(self) -> None:
        """Test that .session-title class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".session-title" in css_content

    def test_session_subtitle_class_exists(self) -> None:
        """Test that .session-subtitle class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".session-subtitle" in css_content

    def test_session_title_has_gold_color(self) -> None:
        """Test that session title uses DM gold color per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Session title should use --color-dm (gold)
        assert "color: var(--color-dm)" in css_content

    def test_session_title_has_24px_font(self) -> None:
        """Test that session title uses 24px font size per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "font-size: 24px" in css_content

    def test_session_header_has_border_bottom(self) -> None:
        """Test that session header has border-bottom separator."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "border-bottom: 1px solid var(--bg-secondary)" in css_content


class TestCharacterCardEnhancement:
    """Tests for enhanced character card CSS styling (Story 2.2, Task 3)."""

    def test_character_card_character_classes_exist(self) -> None:
        """Test that character card classes exist for all characters."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".character-card.{char}" in css_content, (
                f"Missing .character-card.{char}"
            )

    def test_character_card_controlled_state(self) -> None:
        """Test that controlled state class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card.controlled" in css_content

    def test_character_name_class_exists(self) -> None:
        """Test that .character-name class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-name" in css_content


class TestDropInButtonStyling:
    """Tests for Drop-In button CSS styling (Story 2.2, Task 4)."""

    def test_drop_in_button_class_exists(self) -> None:
        """Test that .drop-in-button class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".drop-in-button" in css_content

    def test_drop_in_button_hover_state(self) -> None:
        """Test that Drop-In button has hover state."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".drop-in-button:hover" in css_content

    def test_drop_in_button_active_state(self) -> None:
        """Test that Drop-In button has active state."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".drop-in-button.active" in css_content

    def test_drop_in_button_character_classes(self) -> None:
        """Test that Drop-In button has character-specific classes."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".drop-in-button.{char}" in css_content, (
                f"Missing .drop-in-button.{char}"
            )


class TestModeIndicatorEnhancement:
    """Tests for enhanced mode indicator CSS styling (Story 2.2, Task 5)."""

    def test_mode_indicator_watch_class(self) -> None:
        """Test that .mode-indicator.watch class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.watch" in css_content

    def test_mode_indicator_play_class(self) -> None:
        """Test that .mode-indicator.play class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.play" in css_content

    def test_pulse_animation_defined(self) -> None:
        """Test that pulse animation keyframes are defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "@keyframes pulse" in css_content

    def test_pulse_dot_class_exists(self) -> None:
        """Test that .pulse-dot class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".pulse-dot" in css_content

    def test_mode_indicator_watch_has_green_background(self) -> None:
        """Test that watch mode has green-tinted background per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Watch mode should use green (rogue color) with transparency
        assert "rgba(107, 142, 107, 0.2)" in css_content

    def test_mode_indicator_play_has_amber_background(self) -> None:
        """Test that play mode has amber-tinted background per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Play mode should use amber with transparency
        assert "rgba(232, 168, 73, 0.2)" in css_content

    def test_pulse_dot_uses_animation(self) -> None:
        """Test that pulse-dot uses the pulse animation."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "animation: pulse 2s ease-in-out infinite" in css_content


class TestStreamlitWidgetOverrides:
    """Tests for Streamlit widget theme overrides (Story 2.2, Task 6)."""

    def test_text_input_styling(self) -> None:
        """Test that text input styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".stTextInput" in css_content

    def test_text_area_styling(self) -> None:
        """Test that text area styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".stTextArea" in css_content

    def test_button_styling(self) -> None:
        """Test that button styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".stButton" in css_content

    def test_selectbox_styling(self) -> None:
        """Test that selectbox styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".stSelectbox" in css_content

    def test_expander_styling(self) -> None:
        """Test that expander styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "expanderHeader" in css_content


class TestFontsImport:
    """Tests for font imports (Story 2.2, Task 7)."""

    def test_lora_font_imported(self) -> None:
        """Test that Lora font is imported."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "Lora" in css_content
        assert "@import" in css_content
        assert "fonts.googleapis.com" in css_content

    def test_inter_font_imported(self) -> None:
        """Test that Inter font is imported."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "Inter" in css_content


# =============================================================================
# Story 2.3: Narrative Message Display Tests
# =============================================================================


class TestNarrativeMessageModel:
    """Tests for NarrativeMessage Pydantic model (Story 2.3, Task 1.1-1.2)."""

    def test_narrative_message_creation(self) -> None:
        """Test basic NarrativeMessage creation."""
        from models import NarrativeMessage

        msg = NarrativeMessage(agent="dm", content="The tavern is quiet.")
        assert msg.agent == "dm"
        assert msg.content == "The tavern is quiet."
        assert msg.timestamp is None

    def test_narrative_message_with_timestamp(self) -> None:
        """Test NarrativeMessage with optional timestamp."""
        from models import NarrativeMessage

        msg = NarrativeMessage(
            agent="fighter", content="I draw my sword.", timestamp="2026-01-27T12:00:00"
        )
        assert msg.timestamp == "2026-01-27T12:00:00"

    def test_message_type_dm_narration(self) -> None:
        """Test message_type property returns dm_narration for dm agent."""
        from models import NarrativeMessage

        msg = NarrativeMessage(agent="dm", content="test")
        assert msg.message_type == "dm_narration"

    def test_message_type_pc_dialogue(self) -> None:
        """Test message_type property returns pc_dialogue for PC agents."""
        from models import NarrativeMessage

        for agent in ["fighter", "rogue", "wizard", "cleric"]:
            msg = NarrativeMessage(agent=agent, content="test")
            assert msg.message_type == "pc_dialogue", f"Failed for agent: {agent}"


class TestParseLogEntry:
    """Tests for parse_log_entry function (Story 2.3, Task 5.2)."""

    def test_parse_dm_entry(self) -> None:
        """Test parsing DM log entry."""
        from models import parse_log_entry

        entry = "[dm] The tavern falls silent."
        msg = parse_log_entry(entry)
        assert msg.agent == "dm"
        assert msg.content == "The tavern falls silent."
        assert msg.message_type == "dm_narration"

    def test_parse_pc_entry(self) -> None:
        """Test parsing PC log entry."""
        from models import parse_log_entry

        entry = '[fighter] "Stand ready!" *He draws his sword.*'
        msg = parse_log_entry(entry)
        assert msg.agent == "fighter"
        assert msg.content == '"Stand ready!" *He draws his sword.*'
        assert msg.message_type == "pc_dialogue"

    def test_parse_entry_without_brackets(self) -> None:
        """Test entry without brackets is treated as DM narration."""
        from models import parse_log_entry

        entry = "The adventure begins..."
        msg = parse_log_entry(entry)
        assert msg.agent == "dm"
        assert msg.content == "The adventure begins..."

    def test_parse_entry_with_empty_brackets(self) -> None:
        """Test entry with empty brackets uses fallback agent."""
        from models import parse_log_entry

        # LOG_ENTRY_PATTERN requires \w+ so [] won't match - treated as no-bracket
        entry = "[] Some text"
        msg = parse_log_entry(entry)
        assert msg.agent == "dm"  # Falls back to dm for non-matching entries
        assert msg.content == "[] Some text"

    def test_parse_entry_with_brackets_in_content(self) -> None:
        """Test that only first [agent] is parsed, brackets in content preserved."""
        from models import parse_log_entry

        entry = "[rogue] I found a [locked] chest!"
        msg = parse_log_entry(entry)
        assert msg.agent == "rogue"
        assert msg.content == "I found a [locked] chest!"

    def test_parse_entry_with_space_in_agent_name(self) -> None:
        """Test parsing entry with space in agent name (e.g., 'brother aldric')."""
        from models import parse_log_entry

        entry = '[brother aldric] "Peace, friends." *He raises a calming hand.*'
        msg = parse_log_entry(entry)
        assert msg.agent == "brother aldric"
        assert msg.content == '"Peace, friends." *He raises a calming hand.*'
        assert msg.message_type == "pc_dialogue"


class TestParseMessageContent:
    """Tests for parse_message_content function (Story 2.3, Task 1.3)."""

    def test_parse_plain_narration(self) -> None:
        """Test parsing plain narration without special markers."""
        from models import parse_message_content

        segments = parse_message_content("The tavern is quiet.")
        assert len(segments) == 1
        assert segments[0].segment_type == "narration"
        assert segments[0].text == "The tavern is quiet."

    def test_parse_action_only(self) -> None:
        """Test parsing action text wrapped in asterisks."""
        from models import parse_message_content

        segments = parse_message_content("*draws his sword*")
        assert len(segments) == 1
        assert segments[0].segment_type == "action"
        assert segments[0].text == "draws his sword"

    def test_parse_dialogue_only(self) -> None:
        """Test parsing dialogue text wrapped in quotes."""
        from models import parse_message_content

        segments = parse_message_content('"Stand ready!"')
        assert len(segments) == 1
        assert segments[0].segment_type == "dialogue"
        assert segments[0].text == "Stand ready!"

    def test_parse_mixed_content(self) -> None:
        """Test parsing mixed dialogue and action content."""
        from models import parse_message_content

        content = '"Stand ready," *Theron mutters, drawing his sword.*'
        segments = parse_message_content(content)

        assert len(segments) == 3
        assert segments[0].segment_type == "dialogue"
        assert segments[0].text == "Stand ready,"
        assert segments[1].segment_type == "narration"
        assert segments[1].text == " "
        assert segments[2].segment_type == "action"
        assert segments[2].text == "Theron mutters, drawing his sword."

    def test_parse_action_dialogue_action(self) -> None:
        """Test parsing action-dialogue-action sequence."""
        from models import parse_message_content

        content = '*She whispers,* "Follow me." *and moves to the door.*'
        segments = parse_message_content(content)

        assert len(segments) == 5
        assert segments[0].segment_type == "action"
        assert segments[0].text == "She whispers,"
        assert segments[1].segment_type == "narration"
        assert segments[1].text == " "
        assert segments[2].segment_type == "dialogue"
        assert segments[2].text == "Follow me."
        assert segments[3].segment_type == "narration"
        assert segments[3].text == " "
        assert segments[4].segment_type == "action"
        assert segments[4].text == "and moves to the door."

    def test_parse_unclosed_asterisk(self) -> None:
        """Test unclosed asterisk is treated as narration."""
        from models import parse_message_content

        segments = parse_message_content("*draws his sword")
        assert len(segments) == 1
        assert segments[0].segment_type == "narration"
        assert segments[0].text == "*draws his sword"

    def test_parse_unclosed_quote(self) -> None:
        """Test unclosed quote is treated as narration."""
        from models import parse_message_content

        segments = parse_message_content('"Stand ready')
        assert len(segments) == 1
        assert segments[0].segment_type == "narration"
        assert segments[0].text == '"Stand ready'

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string returns empty list."""
        from models import parse_message_content

        segments = parse_message_content("")
        assert len(segments) == 0

    def test_parse_double_asterisks_filters_empty(self) -> None:
        """Test that double asterisks don't create empty segments."""
        from models import parse_message_content

        segments = parse_message_content("**double asterisk**")
        # Should filter out empty action segments
        assert all(s.text for s in segments), "No empty segments should exist"
        # Should have the narration content
        texts = [s.text for s in segments]
        assert "double asterisk" in texts


class TestMessageSegmentModel:
    """Tests for MessageSegment Pydantic model."""

    def test_message_segment_creation(self) -> None:
        """Test basic MessageSegment creation."""
        from models import MessageSegment

        segment = MessageSegment(segment_type="action", text="draws sword")
        assert segment.segment_type == "action"
        assert segment.text == "draws sword"

    def test_message_segment_types(self) -> None:
        """Test all valid segment types."""
        from models import MessageSegment

        for segment_type in ["dialogue", "action", "narration"]:
            segment = MessageSegment(segment_type=segment_type, text="test")
            assert segment.segment_type == segment_type


class TestDMMessageRendering:
    """Tests for DM message HTML generation (Story 2.3, Task 2)."""

    def test_render_dm_message_html_structure(self) -> None:
        """Test DM message rendering produces correct HTML structure."""
        from app import render_dm_message_html

        html = render_dm_message_html("The tavern is quiet.")
        assert 'class="dm-message"' in html
        assert "<p>" in html
        assert "</p>" in html
        assert "The tavern is quiet." in html

    def test_render_dm_message_html_escapes_content(self) -> None:
        """Test DM message HTML escapes special characters."""
        from app import render_dm_message_html

        html = render_dm_message_html("<script>alert('xss')</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_dm_message_html_preserves_text(self) -> None:
        """Test DM message preserves regular text content."""
        from app import render_dm_message_html

        content = "The tavern falls silent as the stranger enters, her cloak dripping."
        html = render_dm_message_html(content)
        assert content in html

    def test_render_dm_message_html_div_wrapper(self) -> None:
        """Test DM message is wrapped in div with correct class."""
        from app import render_dm_message_html

        html = render_dm_message_html("test")
        assert html.startswith('<div class="dm-message">')
        assert html.endswith("</div>")


class TestPCMessageRendering:
    """Tests for PC message HTML generation (Story 2.3, Task 3)."""

    def test_render_pc_message_html_structure(self) -> None:
        """Test PC message rendering produces correct HTML structure."""
        from app import render_pc_message_html

        html = render_pc_message_html("Theron", "Fighter", "I stand ready.")
        assert 'class="pc-message fighter"' in html
        assert 'class="pc-attribution fighter"' in html
        assert "Theron, the Fighter:" in html
        assert "<p>" in html
        assert "I stand ready." in html

    def test_render_pc_message_fighter(self) -> None:
        """Test PC message rendering for fighter class."""
        from app import render_pc_message_html

        html = render_pc_message_html("Theron", "Fighter", "For glory!")
        assert 'class="pc-message fighter"' in html
        assert 'class="pc-attribution fighter"' in html

    def test_render_pc_message_rogue(self) -> None:
        """Test PC message rendering for rogue class."""
        from app import render_pc_message_html

        html = render_pc_message_html("Shadowmere", "Rogue", "I check for traps.")
        assert 'class="pc-message rogue"' in html
        assert 'class="pc-attribution rogue"' in html

    def test_render_pc_message_wizard(self) -> None:
        """Test PC message rendering for wizard class."""
        from app import render_pc_message_html

        html = render_pc_message_html("Elara", "Wizard", "I cast detect magic.")
        assert 'class="pc-message wizard"' in html
        assert 'class="pc-attribution wizard"' in html

    def test_render_pc_message_cleric(self) -> None:
        """Test PC message rendering for cleric class."""
        from app import render_pc_message_html

        html = render_pc_message_html("Brother Marcus", "Cleric", "Blessings upon you.")
        assert 'class="pc-message cleric"' in html
        assert 'class="pc-attribution cleric"' in html

    def test_render_pc_message_with_action(self) -> None:
        """Test PC message with action text styling."""
        from app import render_pc_message_html

        html = render_pc_message_html(
            "Theron", "Fighter", '*draws his sword* "For glory!"'
        )
        assert 'class="action-text"' in html
        assert "draws his sword" in html
        assert "For glory!" in html

    def test_render_pc_message_escapes_html(self) -> None:
        """Test PC message HTML escapes special characters."""
        from app import render_pc_message_html

        html = render_pc_message_html(
            "Test<Name>", "Test<Class>", "<script>bad</script>"
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "Test&lt;Name&gt;" in html
        assert "Test&lt;Class&gt;" in html


class TestFormatPCContent:
    """Tests for format_pc_content function (Story 2.3, Task 3.4)."""

    def test_format_pc_content_no_action(self) -> None:
        """Test content without action markers passes through."""
        from app import format_pc_content

        result = format_pc_content("I attack the goblin.")
        assert result == "I attack the goblin."

    def test_format_pc_content_single_action(self) -> None:
        """Test single action marker is converted."""
        from app import format_pc_content

        result = format_pc_content("*draws sword*")
        assert result == '<span class="action-text">draws sword</span>'

    def test_format_pc_content_multiple_actions(self) -> None:
        """Test multiple action markers are converted."""
        from app import format_pc_content

        result = format_pc_content("*draws sword* and *charges forward*")
        assert result.count('class="action-text"') == 2
        assert "draws sword" in result
        assert "charges forward" in result

    def test_format_pc_content_mixed(self) -> None:
        """Test mixed dialogue and action content."""
        from app import format_pc_content

        result = format_pc_content('"Stand ready!" *He raises his shield.*')
        # Quotes are escaped to &quot;
        assert "&quot;Stand ready!&quot;" in result
        assert '<span class="action-text">He raises his shield.</span>' in result

    def test_format_pc_content_escapes_html(self) -> None:
        """Test HTML entities are escaped before action parsing."""
        from app import format_pc_content

        result = format_pc_content("*<script>evil</script>*")
        assert "<script>" not in result
        assert "&lt;script&gt;evil&lt;/script&gt;" in result


class TestGetCharacterInfo:
    """Tests for get_character_info function (Story 2.3, Task 5.3)."""

    def test_get_character_info_dm_returns_none(self) -> None:
        """Test that DM agent returns None."""
        from app import get_character_info
        from models import populate_game_state

        state = populate_game_state()
        result = get_character_info(state, "dm")
        assert result is None

    def test_get_character_info_known_character(self) -> None:
        """Test getting info for a known character."""
        from app import get_character_info
        from models import populate_game_state

        state = populate_game_state()
        # Use actual character key (name) - "thorin" is the fighter
        result = get_character_info(state, "thorin")
        assert result is not None
        name, char_class = result
        assert name == "Thorin"
        assert char_class == "Fighter"

    def test_get_character_info_unknown_agent(self) -> None:
        """Test fallback for unknown agent."""
        from app import get_character_info
        from models import populate_game_state

        state = populate_game_state()
        result = get_character_info(state, "unknown_agent")
        assert result == ("Unknown", "Adventurer")

    def test_get_character_info_empty_state(self) -> None:
        """Test with empty state dict."""
        from app import get_character_info

        state = {}  # type: ignore
        result = get_character_info(state, "fighter")
        assert result == ("Unknown", "Adventurer")


class TestNarrativeContainer:
    """Tests for narrative container rendering (Story 2.3, Task 4)."""

    def test_render_narrative_messages_empty_log(self) -> None:
        """Test empty log shows placeholder."""
        from app import render_narrative_messages
        from models import create_initial_game_state

        state = create_initial_game_state()
        # This will render placeholder - we can't easily test Streamlit output
        # but we verify it doesn't raise an error
        with patch("streamlit.markdown") as mock_markdown:
            render_narrative_messages(state)
            # Should have been called with placeholder
            calls = mock_markdown.call_args_list
            assert len(calls) == 1
            assert "narrative-placeholder" in str(calls[0])

    def test_render_narrative_messages_dm_message(self) -> None:
        """Test DM message is rendered correctly."""
        from app import render_narrative_messages
        from models import create_initial_game_state

        state = create_initial_game_state()
        state["ground_truth_log"] = ["[dm] The tavern is quiet."]

        with patch("streamlit.markdown") as mock_markdown:
            render_narrative_messages(state)
            calls = mock_markdown.call_args_list
            assert len(calls) == 1
            html = str(calls[0])
            assert "dm-message" in html
            assert "The tavern is quiet." in html

    def test_render_narrative_messages_pc_message(self) -> None:
        """Test PC message is rendered with character info."""
        from app import render_narrative_messages
        from models import populate_game_state

        state = populate_game_state()
        # Use actual character key (name) from the config
        state["ground_truth_log"] = ["[thorin] I stand ready."]

        with patch("streamlit.markdown") as mock_markdown:
            render_narrative_messages(state)
            calls = mock_markdown.call_args_list
            assert len(calls) == 1
            html = str(calls[0])
            assert "pc-message" in html
            assert "fighter" in html  # CSS class from character_class
            assert "I stand ready." in html
            assert "Thorin" in html  # Character name

    def test_render_narrative_messages_multiple(self) -> None:
        """Test multiple messages are rendered in sequence."""
        from app import render_narrative_messages
        from models import populate_game_state

        state = populate_game_state(include_sample_messages=False)
        # Use actual character names from config
        state["ground_truth_log"] = [
            "[dm] The tavern falls silent.",
            "[thorin] I draw my sword.",
            "[shadowmere] I check for traps.",
        ]

        with patch("streamlit.markdown") as mock_markdown:
            render_narrative_messages(state)
            calls = mock_markdown.call_args_list
            assert len(calls) == 3  # One call per message


class TestSampleMessages:
    """Tests for sample messages feature (Story 2.3, Task 6)."""

    def test_populate_game_state_includes_sample_messages_by_default(self) -> None:
        """Test that populate_game_state includes sample messages by default."""
        from models import populate_game_state

        state = populate_game_state()
        log = state["ground_truth_log"]
        assert len(log) > 0, "Should have sample messages"
        # Should have DM messages
        assert any("[dm]" in entry for entry in log)

    def test_populate_game_state_can_exclude_sample_messages(self) -> None:
        """Test that sample messages can be disabled."""
        from models import populate_game_state

        state = populate_game_state(include_sample_messages=False)
        log = state["ground_truth_log"]
        assert len(log) == 0, "Should have no messages when disabled"

    def test_sample_messages_include_dm_narration(self) -> None:
        """Test sample messages include DM narration entries."""
        from models import populate_game_state

        state = populate_game_state()
        log = state["ground_truth_log"]
        dm_messages = [e for e in log if e.startswith("[dm]")]
        assert len(dm_messages) >= 1, "Should have at least one DM message"

    def test_sample_messages_include_pc_dialogue(self) -> None:
        """Test sample messages include PC dialogue with actions."""
        from models import populate_game_state

        state = populate_game_state()
        log = state["ground_truth_log"]
        # Should have at least some PC messages (not dm)
        pc_messages = [e for e in log if not e.startswith("[dm]")]
        assert len(pc_messages) >= 1, "Should have at least one PC message"

    def test_sample_messages_contain_action_markers(self) -> None:
        """Test sample PC messages contain *action* markers."""
        from models import populate_game_state

        state = populate_game_state()
        log = state["ground_truth_log"]
        # At least one message should have action markers
        has_action = any("*" in entry for entry in log)
        assert has_action, "Should have at least one message with action markers"

    def test_sample_messages_contain_dialogue_quotes(self) -> None:
        """Test sample PC messages contain quoted dialogue."""
        from models import populate_game_state

        state = populate_game_state()
        log = state["ground_truth_log"]
        # At least one message should have quoted dialogue
        has_dialogue = any('"' in entry for entry in log)
        assert has_dialogue, "Should have at least one message with dialogue quotes"


class TestLogEntryEdgeCases:
    """Tests for ground_truth_log parsing edge cases (Story 2.3, Task 5.4)."""

    def test_parse_entry_special_characters_in_content(self) -> None:
        """Test parsing entry with special characters in content."""
        from models import parse_log_entry

        entry = "[dm] The door reads: <DANGER> & [KEEP OUT]"
        msg = parse_log_entry(entry)
        assert msg.agent == "dm"
        assert "<DANGER>" in msg.content
        assert "[KEEP OUT]" in msg.content

    def test_parse_entry_unicode_content(self) -> None:
        """Test parsing entry with unicode characters."""
        from models import parse_log_entry

        entry = "[dm] The sign reads: 「危険」"
        msg = parse_log_entry(entry)
        assert msg.agent == "dm"
        assert "「危険」" in msg.content

    def test_parse_entry_long_content(self) -> None:
        """Test parsing entry with very long content."""
        from models import parse_log_entry

        long_text = "A" * 10000
        entry = f"[dm] {long_text}"
        msg = parse_log_entry(entry)
        assert msg.agent == "dm"
        assert len(msg.content) == 10000

    def test_parse_entry_whitespace_handling(self) -> None:
        """Test parsing entry preserves internal whitespace."""
        from models import parse_log_entry

        entry = "[dm] The door   opens   slowly..."
        msg = parse_log_entry(entry)
        assert "   " in msg.content

    def test_parse_entry_newlines_in_content(self) -> None:
        """Test parsing entry with newlines in content."""
        from models import parse_log_entry

        entry = "[dm] Line one\nLine two"
        msg = parse_log_entry(entry)
        assert "\n" in msg.content


# =============================================================================
# Story 2.4: Party Panel & Character Cards Tests
# =============================================================================


class TestCharacterCardRendering:
    """Tests for character card HTML generation (Story 2.4, Task 4)."""

    def test_render_character_card_html_structure(self) -> None:
        """Test character card rendering produces correct HTML structure."""
        from app import render_character_card_html

        html = render_character_card_html("Theron", "Fighter")
        assert 'class="character-card fighter"' in html
        assert 'class="character-name fighter"' in html
        assert 'class="character-class"' in html
        assert "Theron" in html
        assert "Fighter" in html

    def test_render_character_card_html_each_class(self) -> None:
        """Test each character class gets correct CSS classes."""
        from app import render_character_card_html

        for name, char_class in [
            ("Theron", "Fighter"),
            ("Shadowmere", "Rogue"),
            ("Elara", "Wizard"),
            ("Brother Marcus", "Cleric"),
        ]:
            html = render_character_card_html(name, char_class)
            class_slug = char_class.lower()
            assert f'class="character-card {class_slug}"' in html
            assert f'class="character-name {class_slug}"' in html

    def test_render_character_card_html_controlled_state(self) -> None:
        """Test controlled character has controlled class."""
        from app import render_character_card_html

        html = render_character_card_html("Theron", "Fighter", controlled=True)
        assert 'class="character-card fighter controlled"' in html

    def test_render_character_card_html_not_controlled(self) -> None:
        """Test non-controlled character does not have controlled class."""
        from app import render_character_card_html

        html = render_character_card_html("Theron", "Fighter", controlled=False)
        assert "controlled" not in html

    def test_render_character_card_html_escapes_name(self) -> None:
        """Test character name is HTML escaped."""
        from app import render_character_card_html

        html = render_character_card_html("<script>xss</script>", "Fighter")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_character_card_html_escapes_class(self) -> None:
        """Test character class is HTML escaped."""
        from app import render_character_card_html

        html = render_character_card_html("Theron", "<script>xss</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestDropInButtonFunctionality:
    """Tests for Drop-In/Release button functionality (Story 2.4, Task 2, 3)."""

    def test_get_button_label_not_controlled(self) -> None:
        """Test button label is 'Drop-In' when not controlled."""
        from app import get_drop_in_button_label

        label = get_drop_in_button_label(controlled=False)
        assert label == "Drop-In"

    def test_get_button_label_controlled(self) -> None:
        """Test button label is 'Release' when controlled."""
        from app import get_drop_in_button_label

        label = get_drop_in_button_label(controlled=True)
        assert label == "Release"


class TestPartyPanelRendering:
    """Tests for sidebar party panel rendering (Story 2.4, Task 1)."""

    def test_get_party_characters_excludes_dm(self) -> None:
        """Test get_party_characters excludes DM from party list."""
        from app import get_party_characters
        from models import populate_game_state

        state = populate_game_state()
        characters = get_party_characters(state)

        # Should not include "dm" key
        assert "dm" not in characters
        # Should include PC characters
        assert len(characters) >= 1

    def test_get_party_characters_includes_pcs(self) -> None:
        """Test get_party_characters includes PC characters."""
        from app import get_party_characters
        from models import populate_game_state

        state = populate_game_state()
        characters = get_party_characters(state)

        # Should have character configs
        for _agent_key, char_config in characters.items():
            assert char_config.name
            assert char_config.character_class

    def test_get_party_characters_empty_state(self) -> None:
        """Test get_party_characters with empty state."""
        from app import get_party_characters

        state = {}  # type: ignore
        characters = get_party_characters(state)
        assert characters == {}


class TestHandleDropInClick:
    """Tests for Drop-In button click handler (Story 2.4, Task 2.3, 2.4, 3.4)."""

    def test_handle_drop_in_takes_control(self) -> None:
        """Test clicking Drop-In takes control of character."""
        mock_session_state = {
            "controlled_character": None,
            "ui_mode": "watch",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("fighter")

            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["ui_mode"] == "play"

    def test_handle_drop_in_releases_control(self) -> None:
        """Test clicking Release releases control of character."""
        mock_session_state = {
            "controlled_character": "fighter",
            "ui_mode": "play",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("fighter")  # Same character - toggle off

            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["ui_mode"] == "watch"

    def test_handle_drop_in_switches_character(self) -> None:
        """Test clicking Drop-In on different character switches control."""
        mock_session_state = {
            "controlled_character": "fighter",
            "ui_mode": "play",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("rogue")  # Different character

            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["ui_mode"] == "play"


class TestStreamlitButtonCSS:
    """Tests for Streamlit button CSS styling in character cards (Story 2.4, Task 5)."""

    def test_css_has_character_card_wrapper_styles(self) -> None:
        """Test CSS includes character card wrapper class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card-wrapper" in css_content

    def test_css_has_character_card_button_styles(self) -> None:
        """Test CSS includes Streamlit button overrides for character card wrappers."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card-wrapper .stButton > button" in css_content

    def test_css_has_fighter_button_styles(self) -> None:
        """Test CSS includes fighter character button styles."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card-wrapper.fighter .stButton > button" in css_content
        assert ".character-card-wrapper.fighter .stButton > button:hover" in css_content

    def test_css_has_rogue_button_styles(self) -> None:
        """Test CSS includes rogue character button styles."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card-wrapper.rogue .stButton > button" in css_content
        assert ".character-card-wrapper.rogue .stButton > button:hover" in css_content

    def test_css_has_wizard_button_styles(self) -> None:
        """Test CSS includes wizard character button styles."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card-wrapper.wizard .stButton > button" in css_content
        assert ".character-card-wrapper.wizard .stButton > button:hover" in css_content

    def test_css_has_cleric_button_styles(self) -> None:
        """Test CSS includes cleric character button styles."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card-wrapper.cleric .stButton > button" in css_content
        assert ".character-card-wrapper.cleric .stButton > button:hover" in css_content

    def test_css_has_controlled_button_styles(self) -> None:
        """Test CSS includes controlled state button styles."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card-wrapper.controlled .stButton > button" in css_content
        assert (
            ".character-card-wrapper.controlled .stButton > button:hover" in css_content
        )


class TestPartyPanelIntegration:
    """Integration tests for party panel rendering (Story 2.4, Task 6.5, 6.6)."""

    def test_party_panel_renders_all_pc_characters(self) -> None:
        """Test sidebar party panel renders all 4 PC characters, excluding DM."""
        from app import get_party_characters
        from models import populate_game_state

        state = populate_game_state()
        party = get_party_characters(state)

        # Should have exactly 4 PC characters
        assert len(party) == 4, (
            f"Expected 4 PCs, got {len(party)}: {list(party.keys())}"
        )

        # DM should not be in the party
        assert "dm" not in party

        # Verify each character has required attributes
        for agent_key, char_config in party.items():
            assert char_config.name, f"Character {agent_key} missing name"
            assert char_config.character_class, f"Character {agent_key} missing class"

    def test_party_panel_character_classes_covered(self) -> None:
        """Test all expected character classes are represented."""
        from app import get_party_characters
        from models import populate_game_state

        state = populate_game_state()
        party = get_party_characters(state)

        # Get all character classes (lowercase for comparison)
        classes = {c.character_class.lower() for c in party.values()}

        # Should include the core D&D classes from the default config
        # At minimum, verify we have variety (not all the same class)
        assert len(classes) >= 2, "Party should have diverse character classes"

    def test_controlled_character_state_toggle_cycle(self) -> None:
        """Test full cycle: no control -> take control -> release control."""
        mock_session_state = {
            "controlled_character": None,
            "ui_mode": "watch",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Initial state: no control
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["ui_mode"] == "watch"

            # Take control of fighter
            handle_drop_in_click("fighter")
            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["ui_mode"] == "play"

            # Release control (click same character)
            handle_drop_in_click("fighter")
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["ui_mode"] == "watch"

    def test_quick_switch_between_characters(self) -> None:
        """Test switching control between characters without explicit release."""
        mock_session_state = {
            "controlled_character": "fighter",
            "ui_mode": "play",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Switch directly from fighter to rogue
            handle_drop_in_click("rogue")
            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["ui_mode"] == "play"

            # Switch directly from rogue to wizard
            handle_drop_in_click("wizard")
            assert mock_session_state["controlled_character"] == "wizard"
            assert mock_session_state["ui_mode"] == "play"

            # Switch directly from wizard to cleric
            handle_drop_in_click("cleric")
            assert mock_session_state["controlled_character"] == "cleric"
            assert mock_session_state["ui_mode"] == "play"


# =============================================================================
# Story 2.5: Session Header & Controls Tests
# =============================================================================


class TestRomanNumerals:
    """Tests for int_to_roman conversion (Story 2.5, Task 5.1)."""

    def test_int_to_roman_basic_values(self) -> None:
        """Test basic roman numeral conversion for 1-10."""
        from app import int_to_roman

        assert int_to_roman(1) == "I"
        assert int_to_roman(2) == "II"
        assert int_to_roman(3) == "III"
        assert int_to_roman(4) == "IV"
        assert int_to_roman(5) == "V"
        assert int_to_roman(6) == "VI"
        assert int_to_roman(7) == "VII"
        assert int_to_roman(8) == "VIII"
        assert int_to_roman(9) == "IX"
        assert int_to_roman(10) == "X"

    def test_int_to_roman_tens(self) -> None:
        """Test roman numerals for tens values."""
        from app import int_to_roman

        assert int_to_roman(20) == "XX"
        assert int_to_roman(30) == "XXX"
        assert int_to_roman(40) == "XL"
        assert int_to_roman(50) == "L"

    def test_int_to_roman_complex_values(self) -> None:
        """Test complex roman numeral conversions."""
        from app import int_to_roman

        assert int_to_roman(42) == "XLII"
        assert int_to_roman(99) == "XCIX"
        assert int_to_roman(100) == "C"
        assert int_to_roman(500) == "D"
        assert int_to_roman(1000) == "M"
        assert int_to_roman(1994) == "MCMXCIV"
        assert int_to_roman(2024) == "MMXXIV"
        assert int_to_roman(3999) == "MMMCMXCIX"

    def test_int_to_roman_edge_case_min(self) -> None:
        """Test minimum valid value (1)."""
        from app import int_to_roman

        assert int_to_roman(1) == "I"

    def test_int_to_roman_edge_case_max(self) -> None:
        """Test maximum valid value (3999)."""
        from app import int_to_roman

        assert int_to_roman(3999) == "MMMCMXCIX"

    def test_int_to_roman_invalid_zero(self) -> None:
        """Test that zero raises ValueError."""
        import pytest

        from app import int_to_roman

        with pytest.raises(ValueError, match="out of range"):
            int_to_roman(0)

    def test_int_to_roman_invalid_negative(self) -> None:
        """Test that negative numbers raise ValueError."""
        import pytest

        from app import int_to_roman

        with pytest.raises(ValueError, match="out of range"):
            int_to_roman(-1)

    def test_int_to_roman_invalid_too_large(self) -> None:
        """Test that numbers > 3999 raise ValueError."""
        import pytest

        from app import int_to_roman

        with pytest.raises(ValueError, match="out of range"):
            int_to_roman(4000)


class TestSessionHeader:
    """Tests for session header rendering (Story 2.5, Task 5.2)."""

    def test_render_session_header_html_structure(self) -> None:
        """Test session header produces correct HTML structure."""
        from app import render_session_header_html

        html = render_session_header_html(7, "January 27, 2026")
        assert 'class="session-header"' in html
        assert 'class="session-title"' in html
        assert 'class="session-subtitle"' in html
        assert "Session VII" in html
        assert "January 27, 2026" in html

    def test_render_session_header_html_session_one(self) -> None:
        """Test session header for session 1."""
        from app import render_session_header_html

        html = render_session_header_html(1, "Test subtitle")
        assert "Session I" in html

    def test_render_session_header_html_high_session(self) -> None:
        """Test session header for high session number."""
        from app import render_session_header_html

        html = render_session_header_html(42, "Test subtitle")
        assert "Session XLII" in html

    def test_render_session_header_html_escapes_info(self) -> None:
        """Test session header escapes subtitle text."""
        from app import render_session_header_html

        html = render_session_header_html(1, "<script>xss</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_get_session_subtitle_no_turns(self) -> None:
        """Test session subtitle with no turns shows only date."""
        from app import get_session_subtitle
        from models import create_initial_game_state

        state = create_initial_game_state()
        subtitle = get_session_subtitle(state)
        # Should contain date but not "Turn"
        assert "Turn" not in subtitle
        # Date format check (month name)
        assert any(
            month in subtitle
            for month in [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]
        )

    def test_get_session_subtitle_with_turns(self) -> None:
        """Test session subtitle with turns shows date and turn count."""
        from app import get_session_subtitle
        from models import create_initial_game_state

        state = create_initial_game_state()
        state["ground_truth_log"] = [
            "[dm] Message 1",
            "[dm] Message 2",
            "[dm] Message 3",
        ]
        subtitle = get_session_subtitle(state)
        assert "Turn 3" in subtitle
        assert "•" in subtitle

    def test_session_number_in_game_state(self) -> None:
        """Test that GameState includes session_number field."""
        from models import populate_game_state

        state = populate_game_state()
        assert "session_number" in state
        assert state["session_number"] == 1


class TestModeIndicator:
    """Tests for mode indicator rendering (Story 2.5, Task 5.3, 5.4)."""

    def test_render_mode_indicator_watch_not_generating(self) -> None:
        """Test watch mode without generating shows no pulse dot."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False)
        assert 'class="mode-indicator watch"' in html
        assert "Watching" in html
        assert "pulse-dot" not in html

    def test_render_mode_indicator_watch_generating(self) -> None:
        """Test watch mode with generating shows pulse dot."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", True)
        assert 'class="mode-indicator watch"' in html
        assert "Watching" in html
        assert 'class="pulse-dot"' in html

    def test_render_mode_indicator_play_mode(self) -> None:
        """Test play mode shows 'Playing as' with character name."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "fighter": CharacterConfig(
                name="Theron",
                character_class="Fighter",
                personality="brave",
                color="#C45C4A",
            )
        }
        html = render_mode_indicator_html("play", False, "fighter", characters)
        assert 'class="mode-indicator play fighter"' in html
        assert "Playing as Theron" in html
        assert 'class="pulse-dot"' in html

    def test_render_mode_indicator_play_mode_rogue(self) -> None:
        """Test play mode with rogue character."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "rogue": CharacterConfig(
                name="Shadowmere",
                character_class="Rogue",
                personality="sneaky",
                color="#6B8E6B",
            )
        }
        html = render_mode_indicator_html("play", False, "rogue", characters)
        assert "play rogue" in html
        assert "Playing as Shadowmere" in html

    def test_render_mode_indicator_play_mode_wizard(self) -> None:
        """Test play mode with wizard character."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "wizard": CharacterConfig(
                name="Elara",
                character_class="Wizard",
                personality="wise",
                color="#7B68B8",
            )
        }
        html = render_mode_indicator_html("play", False, "wizard", characters)
        assert "play wizard" in html
        assert "Playing as Elara" in html

    def test_render_mode_indicator_play_mode_cleric(self) -> None:
        """Test play mode with cleric character."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "cleric": CharacterConfig(
                name="Brother Marcus",
                character_class="Cleric",
                personality="devout",
                color="#4A90A4",
            )
        }
        html = render_mode_indicator_html("play", False, "cleric", characters)
        assert "play cleric" in html
        assert "Playing as Brother Marcus" in html

    def test_render_mode_indicator_play_mode_unknown_character(self) -> None:
        """Test play mode with unknown character shows fallback."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("play", False, "unknown_agent", {})
        assert "Playing as unknown_agent" in html

    def test_render_mode_indicator_escapes_character_name(self) -> None:
        """Test play mode escapes character name."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "test": CharacterConfig(
                name="<script>xss</script>",
                character_class="Fighter",
                personality="test",
                color="#C45C4A",
            )
        }
        html = render_mode_indicator_html("play", False, "test", characters)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestSessionControls:
    """Tests for session controls UI (Story 2.5, Task 5.5, 5.6)."""

    def test_pause_toggle_false_to_true(self) -> None:
        """Test pause toggle from false to true."""
        mock_session_state = {"is_paused": False}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            handle_pause_toggle()
            assert mock_session_state["is_paused"] is True

    def test_pause_toggle_true_to_false(self) -> None:
        """Test pause toggle from true to false."""
        mock_session_state = {"is_paused": True}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            handle_pause_toggle()
            assert mock_session_state["is_paused"] is False

    def test_pause_toggle_from_unset(self) -> None:
        """Test pause toggle when is_paused is not set."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            handle_pause_toggle()
            assert mock_session_state["is_paused"] is True

    def test_initialize_session_state_sets_is_generating(self) -> None:
        """Test that initialize_session_state sets is_generating to False."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()
            assert mock_session_state["is_generating"] is False

    def test_initialize_session_state_sets_is_paused(self) -> None:
        """Test that initialize_session_state sets is_paused to False."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()
            assert mock_session_state["is_paused"] is False

    def test_initialize_session_state_sets_playback_speed(self) -> None:
        """Test that initialize_session_state sets playback_speed to 'normal'."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()
            assert mock_session_state["playback_speed"] == "normal"


class TestSessionControlsCSS:
    """Tests for session controls CSS styling (Story 2.5, Task 4)."""

    def test_css_has_session_controls_class(self) -> None:
        """Test CSS includes .session-controls class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".session-controls" in css_content

    def test_css_has_control_button_secondary(self) -> None:
        """Test CSS includes .control-button-secondary class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".control-button-secondary" in css_content

    def test_css_has_speed_select(self) -> None:
        """Test CSS includes .speed-select class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".speed-select" in css_content

    def test_css_has_mode_indicator_play_fighter(self) -> None:
        """Test CSS includes .mode-indicator.play.fighter."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.play.fighter" in css_content

    def test_css_has_mode_indicator_play_rogue(self) -> None:
        """Test CSS includes .mode-indicator.play.rogue."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.play.rogue" in css_content

    def test_css_has_mode_indicator_play_wizard(self) -> None:
        """Test CSS includes .mode-indicator.play.wizard."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.play.wizard" in css_content

    def test_css_has_mode_indicator_play_cleric(self) -> None:
        """Test CSS includes .mode-indicator.play.cleric."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.play.cleric" in css_content


# =============================================================================
# Story 2.6: Real-time Narrative Flow Tests
# =============================================================================


class TestThinkingIndicator:
    """Tests for thinking indicator display (Story 2.6, Task 4)."""

    def test_render_thinking_indicator_html_when_generating(self) -> None:
        """Test thinking indicator HTML is generated when is_generating=True."""
        from app import render_thinking_indicator_html

        html = render_thinking_indicator_html(is_generating=True, is_paused=False)
        assert 'class="thinking-indicator"' in html
        assert 'class="thinking-dot"' in html
        assert 'class="thinking-text"' in html
        assert "The story unfolds..." in html

    def test_render_thinking_indicator_html_not_generating(self) -> None:
        """Test thinking indicator returns empty string when not generating."""
        from app import render_thinking_indicator_html

        html = render_thinking_indicator_html(is_generating=False, is_paused=False)
        assert html == ""

    def test_render_thinking_indicator_html_when_paused(self) -> None:
        """Test thinking indicator returns empty string when paused."""
        from app import render_thinking_indicator_html

        html = render_thinking_indicator_html(is_generating=True, is_paused=True)
        assert html == ""

    def test_render_thinking_indicator_html_structure(self) -> None:
        """Test thinking indicator has correct div wrapper structure."""
        from app import render_thinking_indicator_html

        html = render_thinking_indicator_html(is_generating=True, is_paused=False)
        assert html.startswith('<div class="thinking-indicator">')
        assert html.endswith("</div>")


class TestGameExecution:
    """Tests for game turn execution (Story 2.6, Task 1)."""

    def test_speed_delays_constants(self) -> None:
        """Test speed delay constants are defined correctly."""
        from app import SPEED_DELAYS

        assert SPEED_DELAYS["slow"] == 3.0
        assert SPEED_DELAYS["normal"] == 1.0
        assert SPEED_DELAYS["fast"] == 0.2

    def test_get_turn_delay_normal(self) -> None:
        """Test get_turn_delay returns 1.0 for normal speed."""
        mock_session_state = {"playback_speed": "normal"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 1.0

    def test_get_turn_delay_slow(self) -> None:
        """Test get_turn_delay returns 3.0 for slow speed."""
        mock_session_state = {"playback_speed": "slow"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 3.0

    def test_get_turn_delay_fast(self) -> None:
        """Test get_turn_delay returns 0.2 for fast speed."""
        mock_session_state = {"playback_speed": "fast"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 0.2

    def test_get_turn_delay_default(self) -> None:
        """Test get_turn_delay returns 1.0 when playback_speed not set."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 1.0

    def test_run_game_turn_checks_pause(self) -> None:
        """Test run_game_turn returns early when paused."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": True,
            "is_generating": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_game_turn

            # Should return False (no turn executed) when paused
            result = run_game_turn()
            assert result is False

    def test_run_game_turn_sets_generating_flag(self) -> None:
        """Test run_game_turn sets is_generating flag during execution."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": False,
            "is_generating": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_single_round") as mock_run,
        ):
            mock_run.return_value = game
            from app import run_game_turn

            run_game_turn()
            # After execution, is_generating should be False
            assert mock_session_state["is_generating"] is False


class TestAutoScroll:
    """Tests for auto-scroll behavior (Story 2.6, Task 2)."""

    def test_initialize_session_state_sets_auto_scroll(self) -> None:
        """Test that initialize_session_state sets auto_scroll_enabled to True."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()
            assert mock_session_state["auto_scroll_enabled"] is True

    def test_render_auto_scroll_indicator_html_when_disabled(self) -> None:
        """Test auto-scroll indicator HTML is generated when auto_scroll disabled."""
        from app import render_auto_scroll_indicator_html

        html = render_auto_scroll_indicator_html(auto_scroll_enabled=False)
        assert 'class="auto-scroll-indicator visible"' in html
        assert "Resume auto-scroll" in html

    def test_render_auto_scroll_indicator_html_when_enabled(self) -> None:
        """Test auto-scroll indicator returns empty string when enabled."""
        from app import render_auto_scroll_indicator_html

        html = render_auto_scroll_indicator_html(auto_scroll_enabled=True)
        assert html == ""

    def test_handle_resume_auto_scroll_click(self) -> None:
        """Test clicking resume re-enables auto-scroll."""
        mock_session_state = {"auto_scroll_enabled": False}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_resume_auto_scroll_click

            handle_resume_auto_scroll_click()
            assert mock_session_state["auto_scroll_enabled"] is True

    def test_handle_pause_auto_scroll_click(self) -> None:
        """Test pausing auto-scroll sets flag to False."""
        mock_session_state = {"auto_scroll_enabled": True}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_auto_scroll_click

            handle_pause_auto_scroll_click()
            assert mock_session_state["auto_scroll_enabled"] is False


class TestAutoScrollCSS:
    """Tests for auto-scroll indicator CSS styling (Story 2.6, Task 2.5)."""

    def test_css_has_auto_scroll_indicator_class(self) -> None:
        """Test CSS includes .auto-scroll-indicator class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".auto-scroll-indicator" in css_content

    def test_css_has_auto_scroll_visible_class(self) -> None:
        """Test CSS includes .auto-scroll-indicator.visible class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".auto-scroll-indicator.visible" in css_content

    def test_css_has_narrative_container_scrollable(self) -> None:
        """Test CSS makes narrative container scrollable."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check for overflow-y: auto or scroll
        assert "overflow-y:" in css_content


class TestAutoScrollScript:
    """Tests for auto-scroll JavaScript injection (Story 2.6, Task 2.1)."""

    def test_get_auto_scroll_script_contains_javascript(self) -> None:
        """Test that get_auto_scroll_script returns valid JavaScript."""
        from app import get_auto_scroll_script

        script = get_auto_scroll_script()
        assert "<script>" in script
        assert "</script>" in script
        assert "narrative-container" in script
        assert "scrollTop" in script
        assert "scrollHeight" in script

    def test_get_auto_scroll_script_uses_parent_document(self) -> None:
        """Test that script accesses parent document for iframe compatibility."""
        from app import get_auto_scroll_script

        script = get_auto_scroll_script()
        # st.components.v1.html runs in iframe, so must use parent.document
        assert "parent.document" in script


class TestGameButtons:
    """Tests for Start Game and Next Turn buttons (Story 2.6, Task 5)."""

    def test_get_start_button_label_no_messages(self) -> None:
        """Test button shows 'Start Game' when no messages exist."""
        from app import get_start_button_label
        from models import create_initial_game_state

        game = create_initial_game_state()
        label = get_start_button_label(game)
        assert label == "Start Game"

    def test_get_start_button_label_with_messages(self) -> None:
        """Test button shows 'Next Turn' when messages exist."""
        from app import get_start_button_label
        from models import create_initial_game_state

        game = create_initial_game_state()
        game["ground_truth_log"] = ["[dm] Some message"]
        label = get_start_button_label(game)
        assert label == "Next Turn"

    def test_is_start_button_disabled_when_generating(self) -> None:
        """Test button is disabled when is_generating=True."""
        from app import is_start_button_disabled

        mock_session_state = {"is_generating": True}
        with patch("streamlit.session_state", mock_session_state):
            result = is_start_button_disabled()
            assert result is True

    def test_is_start_button_enabled_when_not_generating(self) -> None:
        """Test button is enabled when is_generating=False."""
        from app import is_start_button_disabled

        mock_session_state = {"is_generating": False}
        with patch("streamlit.session_state", mock_session_state):
            result = is_start_button_disabled()
            assert result is False


class TestCurrentTurnHighlight:
    """Tests for current turn highlighting (Story 2.6, Task 3)."""

    def test_render_dm_message_html_current_turn(self) -> None:
        """Test DM message with current-turn class."""
        from app import render_dm_message_html

        html = render_dm_message_html("The tavern is quiet.", is_current=True)
        assert 'class="dm-message current-turn"' in html

    def test_render_dm_message_html_not_current(self) -> None:
        """Test DM message without current-turn class (default)."""
        from app import render_dm_message_html

        html = render_dm_message_html("The tavern is quiet.")
        assert 'class="dm-message"' in html
        assert "current-turn" not in html

    def test_render_pc_message_html_current_turn(self) -> None:
        """Test PC message with current-turn class."""
        from app import render_pc_message_html

        html = render_pc_message_html("Theron", "Fighter", "I attack!", is_current=True)
        assert 'class="pc-message fighter current-turn"' in html

    def test_render_pc_message_html_not_current(self) -> None:
        """Test PC message without current-turn class (default)."""
        from app import render_pc_message_html

        html = render_pc_message_html("Theron", "Fighter", "I attack!")
        assert 'class="pc-message fighter"' in html
        assert "current-turn" not in html

    def test_narrative_messages_last_message_has_current_turn(self) -> None:
        """Test that render_narrative_messages applies current-turn to last message."""
        from app import render_narrative_messages
        from models import populate_game_state

        state = populate_game_state(include_sample_messages=False)
        state["ground_truth_log"] = [
            "[dm] First message",
            "[dm] Second message",
            "[dm] Last message",
        ]

        with patch("streamlit.markdown") as mock_markdown:
            render_narrative_messages(state)
            calls = mock_markdown.call_args_list

            # Check that only the last call has current-turn
            assert len(calls) == 3
            assert "current-turn" not in str(calls[0])
            assert "current-turn" not in str(calls[1])
            assert "current-turn" in str(calls[2])


class TestCurrentTurnHighlightCSS:
    """Tests for current turn highlight CSS styling (Story 2.6, Task 3.2, 3.4)."""

    def test_css_has_current_turn_dm_class(self) -> None:
        """Test CSS includes .dm-message.current-turn class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".dm-message.current-turn" in css_content

    def test_css_has_current_turn_pc_class(self) -> None:
        """Test CSS includes .pc-message.current-turn class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".pc-message.current-turn" in css_content

    def test_css_has_current_turn_highlight_animation(self) -> None:
        """Test CSS includes @keyframes current-turn-highlight animation."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "@keyframes current-turn-highlight" in css_content

    def test_css_current_turn_animation_duration_3s(self) -> None:
        """Test current turn highlight animation is ~3s for fade-out."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Should have 3s duration for the fade-out effect
        assert "current-turn-highlight 3s" in css_content


class TestThinkingIndicatorCSS:
    """Tests for thinking indicator CSS styling (Story 2.6, Task 4.2, 4.4)."""

    def test_css_has_thinking_indicator_class(self) -> None:
        """Test CSS includes .thinking-indicator class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".thinking-indicator" in css_content

    def test_css_has_thinking_dot_class(self) -> None:
        """Test CSS includes .thinking-dot class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".thinking-dot" in css_content

    def test_css_has_fade_in_delayed_animation(self) -> None:
        """Test CSS includes @keyframes fade-in-delayed for 500ms delay."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "@keyframes fade-in-delayed" in css_content

    def test_css_thinking_indicator_has_500ms_delay(self) -> None:
        """Test CSS thinking indicator has 500ms (0.5s) animation delay."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # The animation should have a 0.5s delay (fade-in-delayed 0.3s ease-in 0.5s forwards)
        assert "0.5s forwards" in css_content


class TestStory26AcceptanceCriteria:
    """Integration tests validating acceptance criteria (Story 2.6)."""

    def test_ac1_new_message_appears_immediately(self) -> None:
        """AC#1: New message appears immediately when generated."""
        from app import run_game_turn
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        initial_len = len(game["ground_truth_log"])

        mock_session_state = {
            "game": game,
            "is_paused": False,
            "is_generating": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_single_round") as mock_run:
                # Simulate adding a message
                updated_game = game.copy()
                updated_game["ground_truth_log"] = game["ground_truth_log"] + [
                    "[dm] New message"
                ]
                mock_run.return_value = updated_game

                result = run_game_turn()

                assert result is True
                assert (
                    len(mock_session_state["game"]["ground_truth_log"]) > initial_len
                )

    def test_ac2_auto_scroll_pause_on_manual_scroll(self) -> None:
        """AC#2: Auto-scroll pauses when user scrolls up, resume indicator appears."""
        from app import (
            handle_pause_auto_scroll_click,
            render_auto_scroll_indicator_html,
        )

        mock_session_state = {"auto_scroll_enabled": True}

        with patch("streamlit.session_state", mock_session_state):
            # User scrolls up
            handle_pause_auto_scroll_click()
            assert mock_session_state["auto_scroll_enabled"] is False

        # Indicator should now be visible
        html = render_auto_scroll_indicator_html(auto_scroll_enabled=False)
        assert "Resume auto-scroll" in html
        assert 'class="auto-scroll-indicator visible"' in html

    def test_ac3_current_turn_highlighted(self) -> None:
        """AC#3: Most recent message has subtle highlight indicator."""
        from app import render_dm_message_html, render_pc_message_html

        # DM message with current turn
        dm_html = render_dm_message_html("DM narration", is_current=True)
        assert "current-turn" in dm_html

        # PC message with current turn
        pc_html = render_pc_message_html("Theron", "Fighter", "Action", is_current=True)
        assert "current-turn" in pc_html

    def test_ac4_full_transcript_scrollable(self) -> None:
        """AC#4: Session history is scrollable for reading full transcript."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Narrative container should be scrollable
        assert ".narrative-container" in css_content
        assert "overflow-y:" in css_content
        assert "max-height:" in css_content

    def test_ac5_thinking_indicator_500ms_delay(self) -> None:
        """AC#5: Thinking indicator appears after 500ms delay when generating."""
        from app import render_thinking_indicator_html

        # When generating and not paused
        html = render_thinking_indicator_html(is_generating=True, is_paused=False)
        assert 'class="thinking-indicator"' in html
        assert "The story unfolds..." in html

        # CSS should have 500ms delay
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert "0.5s forwards" in css_content  # 0.5s delay

        # When not generating, no indicator
        html = render_thinking_indicator_html(is_generating=False, is_paused=False)
        assert html == ""

    def test_pause_prevents_turn_execution(self) -> None:
        """Test pause state prevents game turn execution (related to AC#2)."""
        from app import run_game_turn
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": True,
            "is_generating": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            result = run_game_turn()
            assert result is False  # Turn not executed

    def test_speed_control_values(self) -> None:
        """Test speed control delay values are correctly defined."""
        from app import SPEED_DELAYS

        assert SPEED_DELAYS["slow"] == 3.0
        assert SPEED_DELAYS["normal"] == 1.0
        assert SPEED_DELAYS["fast"] == 0.2


class TestStory23AcceptanceCriteria:
    """Integration tests validating all acceptance criteria (Story 2.3)."""

    def test_ac1_dm_narration_styling(self) -> None:
        """AC#1: DM narration has gold border, italic Lora text, no attribution."""
        from app import render_dm_message_html

        html = render_dm_message_html("The tavern is quiet.")

        # Gold border via dm-message class (CSS has border-left: 4px solid var(--color-dm))
        assert 'class="dm-message"' in html
        # Has paragraph tag for text
        assert "<p>" in html
        # Content is present
        assert "The tavern is quiet." in html
        # No speaker attribution (just content)
        assert "attribution" not in html

    def test_ac2_pc_dialogue_styling(self) -> None:
        """AC#2: PC dialogue has attribution, background, character border."""
        from app import render_pc_message_html

        html = render_pc_message_html("Theron", "Fighter", "I stand ready.")

        # Character-colored class for styling
        assert 'class="pc-message fighter"' in html
        assert 'class="pc-attribution fighter"' in html
        # Attribution line
        assert "Theron, the Fighter:" in html
        # Content present
        assert "I stand ready." in html

    def test_ac3_mixed_dialogue_and_action(self) -> None:
        """AC#3: Mixed content has regular dialogue and italic actions."""
        from app import render_pc_message_html

        content = '"Stand ready!" *He draws his sword.*'
        html = render_pc_message_html("Theron", "Fighter", content)

        # Action text wrapped in action-text span
        assert 'class="action-text"' in html
        assert "He draws his sword." in html
        # Dialogue present (quotes escaped to &quot;)
        assert "&quot;Stand ready!&quot;" in html

    def test_ac4_message_spacing(self) -> None:
        """AC#4: Messages have 16px spacing (via CSS margin-bottom on dm-message/pc-message)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check margin-bottom uses spacing variable (--space-md = 16px)
        assert "margin-bottom: var(--space-md)" in css_content
        # Verify --space-md value
        assert "--space-md: 16px" in css_content

    def test_ac4_text_justified(self) -> None:
        """AC#4: Text is justified for manuscript feel."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # DM messages have justified text
        assert "text-align: justify" in css_content

    def test_dm_message_uses_lora_18px(self) -> None:
        """Verify DM message uses Lora font at 18px per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check for Lora font in --font-narrative
        assert "'Lora'" in css_content
        # Check --text-dm is 18px
        assert "--text-dm: 18px" in css_content

    def test_pc_message_background_color(self) -> None:
        """Verify PC message has #3D3530 background per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check --bg-message variable value
        assert "--bg-message: #3D3530" in css_content

    def test_all_character_classes_have_colors(self) -> None:
        """Verify all character classes have associated colors."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char_class in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".pc-message.{char_class}" in css_content
            assert f".pc-attribution.{char_class}" in css_content

    def test_action_text_secondary_color(self) -> None:
        """Verify action text uses secondary color #B8A896."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check --text-secondary value
        assert "--text-secondary: #B8A896" in css_content
        # Check .action-text uses it
        assert ".action-text" in css_content
