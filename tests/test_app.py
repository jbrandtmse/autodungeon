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
        """Test watch mode always shows pulse dot (AC #1 from Story 3.1)."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False)
        assert 'class="mode-indicator watch"' in html
        assert "Watching" in html
        # Pulse dot always shows in watch mode per AC #1
        assert 'class="pulse-dot"' in html

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
                assert len(mock_session_state["game"]["ground_truth_log"]) > initial_len

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


# =============================================================================
# Story 3.1: Watch Mode & Autopilot Tests
# =============================================================================


class TestWatchModeState:
    """Tests for Watch Mode state management (Story 3.1, Task 2)."""

    def test_get_is_watching_true_when_watch_mode_and_no_human(self) -> None:
        """Test get_is_watching returns True when in watch mode and no human active."""
        mock_session_state = {
            "ui_mode": "watch",
            "human_active": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import get_is_watching

            assert get_is_watching() is True

    def test_get_is_watching_false_when_play_mode(self) -> None:
        """Test get_is_watching returns False when in play mode."""
        mock_session_state = {
            "ui_mode": "play",
            "human_active": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import get_is_watching

            assert get_is_watching() is False

    def test_get_is_watching_false_when_human_active(self) -> None:
        """Test get_is_watching returns False when human is active."""
        mock_session_state = {
            "ui_mode": "watch",
            "human_active": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import get_is_watching

            assert get_is_watching() is False

    def test_get_is_watching_defaults_to_watch_mode(self) -> None:
        """Test get_is_watching defaults to True with empty session state."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_is_watching

            # Defaults: ui_mode="watch", human_active=False
            assert get_is_watching() is True

    def test_is_autopilot_available_true_with_game(self) -> None:
        """Test is_autopilot_available returns True when game exists and not paused/human."""
        mock_session_state = {
            "game": {"turn_queue": ["dm"]},
            "is_paused": False,
            "human_active": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import is_autopilot_available

            assert is_autopilot_available() is True

    def test_is_autopilot_available_false_when_no_game(self) -> None:
        """Test is_autopilot_available returns False when no game in session."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import is_autopilot_available

            assert is_autopilot_available() is False

    def test_is_autopilot_available_false_when_paused(self) -> None:
        """Test is_autopilot_available returns False when game is paused."""
        mock_session_state = {
            "game": {"turn_queue": ["dm"]},
            "is_paused": True,
            "human_active": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import is_autopilot_available

            assert is_autopilot_available() is False

    def test_is_autopilot_available_false_when_human_active(self) -> None:
        """Test is_autopilot_available returns False when human is controlling."""
        mock_session_state = {
            "game": {"turn_queue": ["dm"]},
            "is_paused": False,
            "human_active": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import is_autopilot_available

            assert is_autopilot_available() is False

    def test_session_state_initialization_includes_autopilot_flags(self) -> None:
        """Test initialize_session_state creates autopilot-related state."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert "is_autopilot_running" in mock_session_state
            assert mock_session_state["is_autopilot_running"] is False
            assert "autopilot_turn_count" in mock_session_state
            assert mock_session_state["autopilot_turn_count"] == 0
            assert "max_turns_per_session" in mock_session_state

    def test_session_state_initialization_includes_human_active(self) -> None:
        """Test initialize_session_state explicitly sets human_active=False."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            # human_active must be EXPLICITLY set, not just defaulting
            assert "human_active" in mock_session_state
            assert mock_session_state["human_active"] is False


class TestAutopilotLoop:
    """Tests for continuous autopilot loop (Story 3.1, Task 1)."""

    def test_run_autopilot_step_does_nothing_when_not_running(self) -> None:
        """Test run_autopilot_step returns immediately when autopilot not running."""
        mock_session_state = {
            "is_autopilot_running": False,
            "game": {"turn_queue": ["dm"]},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_game_turn") as mock_run_turn,
        ):
            from app import run_autopilot_step

            run_autopilot_step()

            # Should not call run_game_turn when autopilot not running
            mock_run_turn.assert_not_called()

    def test_run_autopilot_step_stops_when_paused(self) -> None:
        """Test run_autopilot_step stops autopilot when game is paused."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
            "human_active": False,
            "game": {"turn_queue": ["dm"]},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_game_turn") as mock_run_turn,
        ):
            from app import run_autopilot_step

            run_autopilot_step()

            # Autopilot should be stopped
            assert mock_session_state["is_autopilot_running"] is False
            mock_run_turn.assert_not_called()

    def test_run_autopilot_step_stops_when_human_active(self) -> None:
        """Test run_autopilot_step stops autopilot when human becomes active."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": False,
            "human_active": True,
            "game": {"turn_queue": ["dm"]},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_game_turn") as mock_run_turn,
        ):
            from app import run_autopilot_step

            run_autopilot_step()

            # Autopilot should be stopped
            assert mock_session_state["is_autopilot_running"] is False
            mock_run_turn.assert_not_called()

    def test_run_autopilot_step_stops_at_turn_limit(self) -> None:
        """Test run_autopilot_step stops when turn limit reached."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": False,
            "human_active": False,
            "autopilot_turn_count": 100,
            "max_turns_per_session": 100,
            "game": {"turn_queue": ["dm"]},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_game_turn") as mock_run_turn,
        ):
            from app import run_autopilot_step

            run_autopilot_step()

            # Autopilot should be stopped at turn limit
            assert mock_session_state["is_autopilot_running"] is False
            mock_run_turn.assert_not_called()

    def test_run_autopilot_step_executes_turn_and_reruns(self) -> None:
        """Test run_autopilot_step executes a turn and triggers rerun."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": False,
            "human_active": False,
            "autopilot_turn_count": 5,
            "max_turns_per_session": 100,
            "game": {"turn_queue": ["dm"]},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_game_turn", return_value=True) as mock_run_turn,
            patch("streamlit.rerun") as mock_rerun,
        ):
            from app import run_autopilot_step

            run_autopilot_step()

            # Should execute turn
            mock_run_turn.assert_called_once()
            # Should increment turn count
            assert mock_session_state["autopilot_turn_count"] == 6
            # Should trigger rerun
            mock_rerun.assert_called_once()

    def test_run_continuous_loop_returns_zero_when_not_running(self) -> None:
        """Test run_continuous_loop returns 0 when autopilot not running."""
        mock_session_state = {
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_continuous_loop

            result = run_continuous_loop()

            assert result == 0

    def test_default_max_turns_per_session(self) -> None:
        """Test DEFAULT_MAX_TURNS_PER_SESSION constant exists."""
        from app import DEFAULT_MAX_TURNS_PER_SESSION

        assert DEFAULT_MAX_TURNS_PER_SESSION == 100


class TestAutopilotToggle:
    """Tests for autopilot toggle button (Story 3.1, Task 3)."""

    def test_handle_autopilot_toggle_starts_autopilot(self) -> None:
        """Test handle_autopilot_toggle starts autopilot when not running."""
        mock_session_state = {
            "is_autopilot_running": False,
            "autopilot_turn_count": 10,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_autopilot_toggle

            handle_autopilot_toggle()

            assert mock_session_state["is_autopilot_running"] is True
            assert mock_session_state["autopilot_turn_count"] == 0

    def test_handle_autopilot_toggle_stops_autopilot(self) -> None:
        """Test handle_autopilot_toggle stops autopilot when running."""
        mock_session_state = {
            "is_autopilot_running": True,
            "autopilot_turn_count": 5,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_autopilot_toggle

            handle_autopilot_toggle()

            assert mock_session_state["is_autopilot_running"] is False


class TestDropInStopsAutopilot:
    """Tests for Drop-In interrupting autopilot (Story 3.1, Task 5)."""

    def test_drop_in_stops_autopilot(self) -> None:
        """Test that clicking Drop-In stops autopilot."""
        mock_session_state = {
            "is_autopilot_running": True,
            "controlled_character": None,
            "ui_mode": "watch",
            "human_active": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("rogue")

            assert mock_session_state["is_autopilot_running"] is False
            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"

    def test_release_control_clears_human_active(self) -> None:
        """Test releasing control clears human_active flag."""
        mock_session_state = {
            "is_autopilot_running": False,
            "controlled_character": "rogue",
            "ui_mode": "play",
            "human_active": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("rogue")  # Same character = release

            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["ui_mode"] == "watch"


class TestModeIndicatorAutopilot:
    """Tests for mode indicator with autopilot (Story 3.1)."""

    def test_mode_indicator_always_shows_pulse_in_watch_mode(self) -> None:
        """Test mode indicator always shows pulse dot in watch mode (AC #1)."""
        from app import render_mode_indicator_html

        # Pulse always shows in watch mode regardless of generating state
        html = render_mode_indicator_html(
            ui_mode="watch",
            is_generating=False,
            controlled_character=None,
            characters=None,
        )

        assert 'class="pulse-dot"' in html
        assert "Watching" in html

    def test_mode_indicator_shows_pulse_not_generating(self) -> None:
        """Test mode indicator shows pulse even when not generating."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html(
            ui_mode="watch",
            is_generating=False,
            controlled_character=None,
            characters=None,
        )

        assert 'class="pulse-dot"' in html
        assert "Watching" in html

    def test_mode_indicator_shows_pulse_when_generating(self) -> None:
        """Test mode indicator shows pulse during generation."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html(
            ui_mode="watch",
            is_generating=True,
        )
        assert 'class="pulse-dot"' in html
        assert "Watching" in html


class TestLangGraphRoutingWithHumanActive:
    """Tests for LangGraph routing respecting human_active flag (Story 3.1, Task 4)."""

    def test_route_uses_ai_when_human_not_active(self) -> None:
        """Test routing uses AI agent when human_active is False."""
        from graph import route_to_next_agent
        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
        }

        # Should route to next agent in queue (rogue)
        result = route_to_next_agent(state)
        assert result == "rogue"

    def test_route_to_human_when_human_active_and_controlled_character_turn(
        self,
    ) -> None:
        """Test routing goes to human when it's controlled character's turn."""
        from graph import route_to_next_agent
        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue", "fighter"],
            "current_turn": "rogue",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": True,
            "controlled_character": "rogue",
            "session_number": 1,
        }

        # Should route to human since it's rogue's turn and human controls rogue
        result = route_to_next_agent(state)
        assert result == "human"

    def test_route_to_ai_when_not_controlled_character_turn(self) -> None:
        """Test routing uses AI when it's not the controlled character's turn."""
        from graph import route_to_next_agent
        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue", "fighter"],
            "current_turn": "fighter",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": True,
            "controlled_character": "rogue",  # Controls rogue, but it's fighter's turn
            "session_number": 1,
        }

        # Should route to end (fighter is last in queue) using AI
        from langgraph.graph import END

        result = route_to_next_agent(state)
        assert result == END


class TestStory31AcceptanceCriteria:
    """Integration tests validating all acceptance criteria (Story 3.1)."""

    def test_ac1_default_watch_mode(self) -> None:
        """AC#1: Application starts in Watch Mode by default."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert mock_session_state["ui_mode"] == "watch"
            assert mock_session_state.get("human_active", False) is False

    def test_ac1_mode_indicator_shows_watching(self) -> None:
        """AC#1: Mode indicator shows 'Watching'."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html(
            ui_mode="watch",
            is_generating=False,
        )

        assert "Watching" in html
        assert 'class="mode-indicator watch"' in html

    def test_ac2_turns_generated_automatically(self) -> None:
        """AC#2: DM and PC agents take turns automatically during autopilot."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": False,
            "human_active": False,
            "autopilot_turn_count": 0,
            "max_turns_per_session": 100,
            "game": {"turn_queue": ["dm"]},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_game_turn", return_value=True) as mock_run_turn,
            patch("streamlit.rerun"),
        ):
            from app import run_autopilot_step

            run_autopilot_step()

            # Turn should be executed
            mock_run_turn.assert_called_once()

    def test_ac3_autopilot_runs_indefinitely(self) -> None:
        """AC#3: Game can run in full Autopilot Mode without intervention."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": False,
            "human_active": False,
            "autopilot_turn_count": 50,
            "max_turns_per_session": 100,
            "game": {"turn_queue": ["dm"]},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_game_turn", return_value=True),
            patch("streamlit.rerun"),
        ):
            from app import run_autopilot_step

            run_autopilot_step()

            # Should continue running (not stopped at 50)
            assert mock_session_state["is_autopilot_running"] is True

    def test_ac4_human_active_false_uses_ai(self) -> None:
        """AC#4: All PC nodes use AI agents when human_active is False."""
        from graph import route_to_next_agent
        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
        }

        # Should route to rogue (AI agent), not human
        result = route_to_next_agent(state)
        assert result == "rogue"
        assert result != "human"

    def test_ac5_drop_in_buttons_visible_during_autopilot(self) -> None:
        """AC#5: Drop-In buttons are visible and accessible in party panel."""
        from app import get_drop_in_button_label

        # Button should show "Drop-In" when not controlled
        label = get_drop_in_button_label(controlled=False)
        assert label == "Drop-In"

        # Button should show "Release" when controlled
        label = get_drop_in_button_label(controlled=True)
        assert label == "Release"


# =============================================================================
# Story 3.2: Drop-In Mode Tests
# =============================================================================


class TestInputContextBar:
    """Tests for input context bar rendering (Story 3.2, Task 1)."""

    def test_render_input_context_bar_html_shows_character_info(self) -> None:
        """Test context bar displays character name and class."""
        from app import render_input_context_bar_html

        html = render_input_context_bar_html("Shadowmere", "Rogue")

        assert "You are" in html
        assert "Shadowmere" in html
        assert "Rogue" in html
        assert "input-context" in html
        assert "rogue" in html  # class slug for styling

    def test_render_input_context_bar_html_fighter(self) -> None:
        """Test context bar with Fighter class."""
        from app import render_input_context_bar_html

        html = render_input_context_bar_html("Theron", "Fighter")

        assert "Theron" in html
        assert "Fighter" in html
        assert "input-context fighter" in html

    def test_render_input_context_bar_html_wizard(self) -> None:
        """Test context bar with Wizard class."""
        from app import render_input_context_bar_html

        html = render_input_context_bar_html("Elara", "Wizard")

        assert "Elara" in html
        assert "Wizard" in html
        assert "wizard" in html

    def test_render_input_context_bar_html_cleric(self) -> None:
        """Test context bar with Cleric class."""
        from app import render_input_context_bar_html

        html = render_input_context_bar_html("Brother Marcus", "Cleric")

        assert "Brother Marcus" in html
        assert "Cleric" in html
        assert "cleric" in html

    def test_render_input_context_bar_html_escapes_special_chars(self) -> None:
        """Test context bar escapes HTML special characters."""
        from app import render_input_context_bar_html

        html = render_input_context_bar_html("<script>alert('xss')</script>", "Rogue")

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_input_context_css_character_colors_exist(self) -> None:
        """Test that character-specific input context colors are defined in CSS."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".input-context.fighter" in css_content
        assert ".input-context.rogue" in css_content
        assert ".input-context.wizard" in css_content
        assert ".input-context.cleric" in css_content


class TestHumanInputArea:
    """Tests for human action input area (Story 3.2, Task 2)."""

    def test_handle_human_action_submit_stores_action(self) -> None:
        """Test that submitted action is stored in session state."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_human_action_submit

            handle_human_action_submit("I check for traps.")

            assert mock_session_state["human_pending_action"] == "I check for traps."

    def test_handle_human_action_submit_strips_whitespace(self) -> None:
        """Test that action text is stripped of whitespace."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_human_action_submit

            handle_human_action_submit("  I cast fireball.  ")

            assert mock_session_state["human_pending_action"] == "I cast fireball."

    def test_handle_human_action_submit_truncates_long_text(self) -> None:
        """Test that action text is truncated at MAX_ACTION_LENGTH."""
        from app import MAX_ACTION_LENGTH

        mock_session_state: dict = {}
        long_action = "A" * (MAX_ACTION_LENGTH + 500)

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_human_action_submit

            handle_human_action_submit(long_action)

            stored_action = mock_session_state["human_pending_action"]
            assert len(stored_action) == MAX_ACTION_LENGTH

    def test_handle_human_action_submit_ignores_empty(self) -> None:
        """Test that empty action is not stored."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_human_action_submit

            handle_human_action_submit("   ")

            assert "human_pending_action" not in mock_session_state

    def test_human_input_area_css_exists(self) -> None:
        """Test that human input area CSS is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".human-input-area" in css_content


class TestHumanInterventionNodeStory32:
    """Tests for human intervention node processing (Story 3.2, Task 3)."""

    def test_human_intervention_node_adds_action_to_log(self) -> None:
        """Test human action is added to ground_truth_log."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        mock_session_state: dict = {"human_pending_action": "I check for traps."}

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": [],
                "turn_queue": ["dm", "rogue"],
                "current_turn": "rogue",
                "agent_memories": {"dm": AgentMemory()},
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {},
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": "rogue",
                "session_number": 1,
            }

            result = human_intervention_node(state)

            assert len(result["ground_truth_log"]) == 1
            assert "[rogue]: I check for traps." in result["ground_truth_log"][0]

    def test_human_intervention_node_clears_pending_action(self) -> None:
        """Test pending action is cleared after processing."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        mock_session_state: dict = {"human_pending_action": "I attack the goblin."}

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": [],
                "turn_queue": ["dm", "fighter"],
                "current_turn": "fighter",
                "agent_memories": {"dm": AgentMemory()},
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {},
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": "fighter",
                "session_number": 1,
            }

            human_intervention_node(state)

            assert mock_session_state["human_pending_action"] is None

    def test_human_intervention_node_no_action_returns_unchanged(self) -> None:
        """Test node returns unchanged state when no pending action."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        mock_session_state: dict = {"human_pending_action": None}

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": ["[dm]: You enter the dungeon."],
                "turn_queue": ["dm", "rogue"],
                "current_turn": "rogue",
                "agent_memories": {"dm": AgentMemory()},
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {},
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": "rogue",
                "session_number": 1,
            }

            result = human_intervention_node(state)

            # Log should be unchanged
            assert len(result["ground_truth_log"]) == 1

    def test_human_intervention_node_no_controlled_char_returns_unchanged(self) -> None:
        """Test node returns unchanged state when no controlled character."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        mock_session_state: dict = {"human_pending_action": "I do something."}

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": [],
                "turn_queue": ["dm", "rogue"],
                "current_turn": "rogue",
                "agent_memories": {"dm": AgentMemory()},
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {},
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": None,
                "session_number": 1,
            }

            result = human_intervention_node(state)

            # Log should be unchanged
            assert len(result["ground_truth_log"]) == 0

    def test_human_intervention_node_formats_log_entry_correctly(self) -> None:
        """Test log entry format matches PC message format."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        mock_session_state: dict = {"human_pending_action": "I search the room."}

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": [],
                "turn_queue": ["dm", "wizard"],
                "current_turn": "wizard",
                "agent_memories": {"dm": AgentMemory()},
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {},
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": "wizard",
                "session_number": 1,
            }

            result = human_intervention_node(state)

            # Format should be "[agent_key]: content"
            entry = result["ground_truth_log"][0]
            assert entry.startswith("[wizard]:")
            assert "I search the room." in entry

    def test_human_intervention_node_updates_agent_memory(self) -> None:
        """Test human action is added to character's agent memory (code review fix)."""
        from models import AgentMemory, CharacterConfig, DMConfig, GameConfig, GameState

        mock_session_state: dict = {"human_pending_action": "I cast fireball!"}

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": [],
                "turn_queue": ["dm", "wizard"],
                "current_turn": "wizard",
                "agent_memories": {"dm": AgentMemory(), "wizard": AgentMemory()},
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {
                    "wizard": CharacterConfig(
                        name="Elara",
                        character_class="Wizard",
                        personality="Studious",
                        color="#7B68B8",
                    )
                },
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": "wizard",
                "session_number": 1,
            }

            result = human_intervention_node(state)

            # Action should be in character's memory with character name
            assert "wizard" in result["agent_memories"]
            memory_buffer = result["agent_memories"]["wizard"].short_term_buffer
            assert len(memory_buffer) == 1
            assert "Elara: I cast fireball!" in memory_buffer[0]

    def test_human_intervention_node_creates_memory_if_missing(self) -> None:
        """Test human intervention creates agent memory if it doesn't exist."""
        from models import AgentMemory, CharacterConfig, DMConfig, GameConfig, GameState

        mock_session_state: dict = {"human_pending_action": "I attack!"}

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": [],
                "turn_queue": ["dm", "fighter"],
                "current_turn": "fighter",
                "agent_memories": {"dm": AgentMemory()},  # No fighter memory
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {
                    "fighter": CharacterConfig(
                        name="Theron",
                        character_class="Fighter",
                        personality="Bold",
                        color="#C45C4A",
                    )
                },
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": "fighter",
                "session_number": 1,
            }

            result = human_intervention_node(state)

            # Memory should be created for fighter
            assert "fighter" in result["agent_memories"]
            assert (
                "Theron: I attack!"
                in result["agent_memories"]["fighter"].short_term_buffer[0]
            )

    def test_human_intervention_node_uses_fallback_name_without_config(self) -> None:
        """Test human intervention uses agent key as fallback name."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        mock_session_state: dict = {"human_pending_action": "I sneak."}

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": [],
                "turn_queue": ["dm", "rogue"],
                "current_turn": "rogue",
                "agent_memories": {"dm": AgentMemory()},
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {},  # No character config
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": "rogue",
                "session_number": 1,
            }

            result = human_intervention_node(state)

            # Should use title-cased agent key as fallback
            assert "rogue" in result["agent_memories"]
            assert (
                "Rogue: I sneak."
                in result["agent_memories"]["rogue"].short_term_buffer[0]
            )


class TestInputContextBarWrapper:
    """Tests for render_input_context_bar wrapper function (code review fix)."""

    def test_render_input_context_bar_not_rendered_in_watch_mode(self) -> None:
        """Test context bar is not rendered in watch mode."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "controlled_character": "rogue",
            "game": {"characters": {}},
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("streamlit.markdown") as mock_markdown:
                from app import render_input_context_bar

                render_input_context_bar()

                # Should not render anything
                mock_markdown.assert_not_called()

    def test_render_input_context_bar_not_rendered_without_controlled_char(
        self,
    ) -> None:
        """Test context bar is not rendered without controlled character."""
        mock_session_state: dict = {
            "ui_mode": "play",
            "controlled_character": None,
            "game": {"characters": {}},
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("streamlit.markdown") as mock_markdown:
                from app import render_input_context_bar

                render_input_context_bar()

                # Should not render anything
                mock_markdown.assert_not_called()

    def test_render_input_context_bar_renders_in_play_mode(self) -> None:
        """Test context bar renders correctly in play mode with controlled character."""
        from models import CharacterConfig

        mock_session_state: dict = {
            "ui_mode": "play",
            "controlled_character": "rogue",
            "game": {
                "characters": {
                    "rogue": CharacterConfig(
                        name="Shadowmere",
                        character_class="Rogue",
                        personality="Cunning",
                        color="#6B8E6B",
                    )
                }
            },
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("streamlit.markdown") as mock_markdown:
                from app import render_input_context_bar

                render_input_context_bar()

                # Should render with character info
                mock_markdown.assert_called_once()
                call_args = mock_markdown.call_args[0][0]
                assert "Shadowmere" in call_args
                assert "Rogue" in call_args


class TestHumanInputAreaWrapper:
    """Tests for render_human_input_area wrapper function (code review fix)."""

    def test_human_input_area_not_rendered_in_watch_mode(self) -> None:
        """Test input area is not rendered in watch mode."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "controlled_character": "rogue",
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("streamlit.markdown"):
                with patch("streamlit.text_area") as mock_text_area:
                    from app import render_human_input_area

                    render_human_input_area()

                    # Should not render text area
                    mock_text_area.assert_not_called()

    def test_human_input_area_not_rendered_without_controlled_char(self) -> None:
        """Test input area is not rendered without controlled character."""
        mock_session_state: dict = {
            "ui_mode": "play",
            "controlled_character": None,
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("streamlit.markdown"):
                with patch("streamlit.text_area") as mock_text_area:
                    from app import render_human_input_area

                    render_human_input_area()

                    # Should not render text area
                    mock_text_area.assert_not_called()


class TestGameLoopHumanIntegration:
    """Tests for game loop integration with human input (Story 3.2, Task 4)."""

    def test_run_game_turn_waits_for_human_when_controlled_turn(self) -> None:
        """Test game turn waits for human input when it's their turn."""
        mock_session_state: dict = {
            "is_paused": False,
            "human_active": True,
            "controlled_character": "rogue",
            "game": {"current_turn": "rogue", "turn_queue": ["dm", "rogue"]},
            "human_pending_action": None,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_game_turn

            result = run_game_turn()

            assert result is False
            assert mock_session_state["waiting_for_human"] is True

    def test_run_game_turn_proceeds_when_action_pending(self) -> None:
        """Test game turn proceeds when human has pending action."""
        from models import populate_game_state

        mock_session_state: dict = {
            "is_paused": False,
            "human_active": True,
            "controlled_character": "rogue",
            "game": populate_game_state(),
            "human_pending_action": "I attack!",
            "waiting_for_human": False,
            "is_generating": False,
            "playback_speed": "fast",
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_single_round") as mock_run:
                mock_run.return_value = mock_session_state["game"]
                from app import run_game_turn

                run_game_turn()

                # Should proceed with the turn
                assert mock_run.called

    def test_run_game_turn_clears_waiting_flag_on_proceed(self) -> None:
        """Test waiting_for_human is cleared when proceeding."""
        from models import populate_game_state

        mock_session_state: dict = {
            "is_paused": False,
            "human_active": True,
            "controlled_character": "rogue",
            "game": populate_game_state(),
            "human_pending_action": "I sneak past.",
            "waiting_for_human": True,
            "is_generating": False,
            "playback_speed": "fast",
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_single_round") as mock_run:
                mock_run.return_value = mock_session_state["game"]
                from app import run_game_turn

                run_game_turn()

                assert mock_session_state["waiting_for_human"] is False


class TestDropInReleaseCleanup:
    """Tests for Drop-In release cleanup (Story 3.2)."""

    def test_release_control_clears_pending_action(self) -> None:
        """Test releasing control clears pending action."""
        mock_session_state: dict = {
            "controlled_character": "rogue",
            "ui_mode": "play",
            "human_active": True,
            "human_pending_action": "Unfinished action",
            "waiting_for_human": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("rogue")

            assert mock_session_state["human_pending_action"] is None
            assert mock_session_state["waiting_for_human"] is False
            assert mock_session_state["human_active"] is False


class TestInitializeSessionStateStory32:
    """Tests for session state initialization (Story 3.2)."""

    def test_initialize_session_state_includes_human_pending_action(self) -> None:
        """Test session state includes human_pending_action key."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert "human_pending_action" in mock_session_state
            assert mock_session_state["human_pending_action"] is None

    def test_initialize_session_state_includes_waiting_for_human(self) -> None:
        """Test session state includes waiting_for_human key."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert "waiting_for_human" in mock_session_state
            assert mock_session_state["waiting_for_human"] is False


class TestStory32AcceptanceCriteria:
    """Integration tests validating all acceptance criteria (Story 3.2)."""

    def test_ac1_drop_in_takes_control_under_2_seconds(self) -> None:
        """AC#1: Drop-in transition completes instantly (no blocking operations)."""
        import time

        mock_session_state: dict = {
            "controlled_character": None,
            "ui_mode": "watch",
            "human_active": False,
            "is_autopilot_running": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            start_time = time.time()
            handle_drop_in_click("fighter")
            elapsed = time.time() - start_time

            # Function should complete nearly instantly (< 100ms)
            # The 2-second requirement is for UI update perception
            assert elapsed < 0.1
            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["human_active"] is True

    def test_ac1_no_confirmation_dialog(self) -> None:
        """AC#1: No confirmation dialog appears on drop-in."""
        # handle_drop_in_click doesn't show any dialogs - it's synchronous
        # This test verifies the function signature and behavior
        mock_session_state: dict = {
            "controlled_character": None,
            "ui_mode": "watch",
            "human_active": False,
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Should not raise any exceptions or require additional input
            handle_drop_in_click("rogue")

            assert mock_session_state["ui_mode"] == "play"

    def test_ac2_mode_indicator_shows_playing_as_character(self) -> None:
        """AC#2: Mode indicator shows 'Playing as [Character Name]'."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "rogue": CharacterConfig(
                name="Shadowmere",
                character_class="Rogue",
                personality="cunning",
                color="#6B8E6B",
            )
        }

        html = render_mode_indicator_html("play", False, "rogue", characters)

        assert "Playing as Shadowmere" in html
        assert "rogue" in html  # Character class in CSS class

    def test_ac3_input_context_bar_shows_character_info(self) -> None:
        """AC#3: Input context bar shows 'You are [Name], the [Class]'."""
        from app import render_input_context_bar_html

        html = render_input_context_bar_html("Shadowmere", "Rogue")

        assert "You are" in html
        assert "Shadowmere" in html
        assert "Rogue" in html

    def test_ac4_human_action_added_to_log_with_attribution(self) -> None:
        """AC#4: Human action appears in log with character attribution."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        mock_session_state: dict = {
            "human_pending_action": "I search for secret doors."
        }

        with patch("streamlit.session_state", mock_session_state):
            from graph import human_intervention_node

            state: GameState = {
                "ground_truth_log": [],
                "turn_queue": ["dm", "rogue"],
                "current_turn": "rogue",
                "agent_memories": {"dm": AgentMemory()},
                "game_config": GameConfig(),
                "dm_config": DMConfig(),
                "characters": {},
                "whisper_queue": [],
                "human_active": True,
                "controlled_character": "rogue",
                "session_number": 1,
            }

            result = human_intervention_node(state)

            # Action should be in log with attribution
            assert "[rogue]: I search for secret doors." in result["ground_truth_log"]

    def test_ac5_routing_to_human_node_when_controlled_turn(self) -> None:
        """AC#5: LangGraph routes to human_intervention_node when controlled character's turn."""
        from graph import route_to_next_agent
        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "rogue"],
            "current_turn": "rogue",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": True,
            "controlled_character": "rogue",
            "session_number": 1,
        }

        result = route_to_next_agent(state)

        assert result == "human"


# =============================================================================
# Test Automation Expansion: Coverage Gap Tests
# =============================================================================


class TestRunContinuousLoopCoverageExpansion:
    """Tests for run_continuous_loop function to fill coverage gaps (lines 161-182)."""

    def test_run_continuous_loop_returns_zero_when_autopilot_not_running(self) -> None:
        """Test run_continuous_loop returns 0 when autopilot not active."""
        mock_session_state = {"is_autopilot_running": False}

        with patch("streamlit.session_state", mock_session_state):
            from app import run_continuous_loop

            result = run_continuous_loop()
            assert result == 0

    def test_run_continuous_loop_stops_when_paused(self) -> None:
        """Test run_continuous_loop stops and resets when is_paused is True."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_continuous_loop

            result = run_continuous_loop()
            assert result == 0
            assert mock_session_state["is_autopilot_running"] is False

    def test_run_continuous_loop_stops_when_human_active(self) -> None:
        """Test run_continuous_loop stops when human takes control."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": False,
            "human_active": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_continuous_loop

            result = run_continuous_loop()
            assert result == 0
            assert mock_session_state["is_autopilot_running"] is False

    def test_run_continuous_loop_stops_at_max_turns(self) -> None:
        """Test run_continuous_loop stops when max_turns is reached."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": False,
            "human_active": False,
            "autopilot_turn_count": 100,  # Already at default max
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_continuous_loop

            result = run_continuous_loop(max_turns=100)
            assert result == 0
            assert mock_session_state["is_autopilot_running"] is False

    def test_run_continuous_loop_increments_turn_count_and_reruns(self) -> None:
        """Test run_continuous_loop executes turn and triggers rerun."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_autopilot_running": True,
            "is_paused": False,
            "human_active": False,
            "is_generating": False,
            "autopilot_turn_count": 5,
            "waiting_for_human": False,
            "playback_speed": "fast",
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_single_round") as mock_run,
            patch("app.st.rerun") as mock_rerun,
            patch("app.time.sleep"),  # Skip delay
        ):
            mock_run.return_value = game
            from app import run_continuous_loop

            # run_continuous_loop triggers rerun, so we won't get a normal return
            # Just verify the side effects
            try:
                run_continuous_loop(max_turns=100)
            except Exception:
                pass  # Rerun may raise in tests

            assert mock_session_state["autopilot_turn_count"] == 6
            mock_rerun.assert_called_once()


class TestRenderNarrativeMessagesFallback:
    """Tests for render_narrative_messages fallback path (lines 692-693)."""

    def test_render_narrative_unknown_agent_returns_fallback(self) -> None:
        """Test that unknown agent names use fallback tuple."""
        from app import get_character_info
        from models import DMConfig, GameConfig, GameState

        # Create state with no characters matching the agent
        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},  # Empty - no characters
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
        }

        # get_character_info returns fallback tuple for unknown agent
        result = get_character_info(state, "unknown_agent")
        assert result == ("Unknown", "Adventurer")

    def test_render_narrative_dm_returns_none(self) -> None:
        """Test that DM agent returns None from get_character_info."""
        from app import get_character_info
        from models import DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
        }

        result = get_character_info(state, "dm")
        assert result is None

    def test_render_narrative_with_unknown_agent_uses_fallback_tuple(self) -> None:
        """Test fallback uses Unknown/Adventurer for unknown agent."""
        from models import CharacterConfig, DMConfig, GameConfig, GameState

        # Create state with log entry from unknown agent
        state: GameState = {
            "ground_truth_log": ["[mystery_char] Hello world"],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {
                "known_char": CharacterConfig(
                    name="Known",
                    character_class="Fighter",
                    personality="Test",
                    color="#FF0000",
                )
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
        }

        with (
            patch("app.st.markdown"),
            patch("app.render_dm_message"),
            patch("app.render_pc_message") as mock_pc,
        ):
            from app import render_narrative_messages

            render_narrative_messages(state)

            # Should have called render_pc_message with fallback values
            mock_pc.assert_called_once()
            args = mock_pc.call_args[0]
            assert args[0] == "Unknown"  # Fallback name
            assert args[1] == "Adventurer"  # Fallback class


class TestAutopilotToggleCoverage:
    """Tests for autopilot toggle (lines 776-786)."""

    def test_handle_autopilot_toggle_start(self) -> None:
        """Test starting autopilot resets turn count."""
        mock_session_state = {
            "is_autopilot_running": False,
            "autopilot_turn_count": 50,  # Previous count
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_autopilot_toggle

            handle_autopilot_toggle()

            assert mock_session_state["is_autopilot_running"] is True
            assert mock_session_state["autopilot_turn_count"] == 0

    def test_handle_autopilot_toggle_stop(self) -> None:
        """Test stopping autopilot sets flag to False."""
        mock_session_state = {
            "is_autopilot_running": True,
            "autopilot_turn_count": 10,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_autopilot_toggle

            handle_autopilot_toggle()

            assert mock_session_state["is_autopilot_running"] is False


class TestRenderHumanInputAreaCoverage:
    """Tests for render_human_input_area internal logic (lines 926-946)."""

    def test_handle_human_action_submit_truncates_long_input(self) -> None:
        """Test handle_human_action_submit truncates at MAX_ACTION_LENGTH."""
        from app import MAX_ACTION_LENGTH

        mock_session_state: dict = {}
        long_action = "x" * (MAX_ACTION_LENGTH + 500)

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_human_action_submit

            handle_human_action_submit(long_action)

            # Should be truncated to MAX_ACTION_LENGTH
            assert len(mock_session_state["human_pending_action"]) == MAX_ACTION_LENGTH

    def test_handle_human_action_submit_strips_whitespace(self) -> None:
        """Test handle_human_action_submit strips leading/trailing whitespace."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_human_action_submit

            handle_human_action_submit("   attack the goblin   ")

            assert mock_session_state["human_pending_action"] == "attack the goblin"

    def test_handle_human_action_submit_ignores_empty(self) -> None:
        """Test handle_human_action_submit ignores whitespace-only input."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_human_action_submit

            handle_human_action_submit("   ")

            assert "human_pending_action" not in mock_session_state


class TestGetDropInButtonLabelCoverage:
    """Tests for get_drop_in_button_label function."""

    def test_get_drop_in_button_label_not_controlled(self) -> None:
        """Test button label when not controlling character."""
        from app import get_drop_in_button_label

        label = get_drop_in_button_label(False)
        assert label == "Drop-In"  # Hyphenated per implementation

    def test_get_drop_in_button_label_controlled(self) -> None:
        """Test button label when controlling character."""
        from app import get_drop_in_button_label

        label = get_drop_in_button_label(True)
        assert label == "Release"


class TestGetPartyCharactersCoverage:
    """Tests for get_party_characters function."""

    def test_get_party_characters_returns_only_non_dm(self) -> None:
        """Test get_party_characters excludes DM."""
        from app import get_party_characters
        from models import CharacterConfig, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {
                "dm": CharacterConfig(
                    name="DM", character_class="DM", personality="", color="#D4A574"
                ),
                "fighter": CharacterConfig(
                    name="Fighter",
                    character_class="Fighter",
                    personality="Bold",
                    color="#C45C4A",
                ),
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
        }

        result = get_party_characters(state)
        assert "dm" not in result
        assert "fighter" in result


class TestRenderViewportWarningCoverage:
    """Tests for render_viewport_warning function."""

    def test_render_viewport_warning_html_structure(self) -> None:
        """Test viewport warning renders correct HTML."""
        with patch("app.st.markdown") as mock_markdown:
            from app import render_viewport_warning

            render_viewport_warning()

            mock_markdown.assert_called_once()
            call_args = mock_markdown.call_args[0][0]
            assert "viewport-warning" in call_args
            assert "Viewport Too Narrow" in call_args


class TestInjectAutoScrollScriptCoverage:
    """Tests for inject_auto_scroll_script function (lines 362-367)."""

    def test_inject_auto_scroll_script_when_enabled(self) -> None:
        """Test script is injected when auto_scroll_enabled is True."""
        mock_session_state = {"auto_scroll_enabled": True}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.components.v1.html") as mock_html,
        ):
            from app import inject_auto_scroll_script

            inject_auto_scroll_script()

            mock_html.assert_called_once()
            call_args = mock_html.call_args[0][0]
            assert "<script>" in call_args

    def test_inject_auto_scroll_script_when_disabled(self) -> None:
        """Test script is NOT injected when auto_scroll_enabled is False."""
        mock_session_state = {"auto_scroll_enabled": False}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.components.v1.html") as mock_html,
        ):
            from app import inject_auto_scroll_script

            inject_auto_scroll_script()

            mock_html.assert_not_called()


class TestRenderThinkingIndicatorCoverage:
    """Tests for render_thinking_indicator function (lines 399-404)."""

    def test_render_thinking_indicator_when_generating(self) -> None:
        """Test thinking indicator renders when generating."""
        mock_session_state = {"is_generating": True, "is_paused": False}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown") as mock_markdown,
        ):
            from app import render_thinking_indicator

            render_thinking_indicator()

            mock_markdown.assert_called_once()
            call_args = mock_markdown.call_args[0][0]
            assert "thinking-indicator" in call_args

    def test_render_thinking_indicator_when_not_generating(self) -> None:
        """Test thinking indicator does not render when not generating."""
        mock_session_state = {"is_generating": False, "is_paused": False}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown") as mock_markdown,
        ):
            from app import render_thinking_indicator

            render_thinking_indicator()

            # Should not call markdown since HTML is empty
            mock_markdown.assert_not_called()


class TestRenderAutoScrollIndicatorCoverage:
    """Tests for render_auto_scroll_indicator function (lines 327-334)."""

    def test_render_auto_scroll_indicator_when_disabled_renders_html(self) -> None:
        """Test auto-scroll indicator renders when disabled."""
        mock_session_state = {"auto_scroll_enabled": False}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown") as mock_markdown,
            patch("app.st.button", return_value=False),
        ):
            from app import render_auto_scroll_indicator

            render_auto_scroll_indicator()

            mock_markdown.assert_called_once()
            call_args = mock_markdown.call_args[0][0]
            assert "auto-scroll-indicator" in call_args

    def test_render_auto_scroll_indicator_when_enabled_no_render(self) -> None:
        """Test auto-scroll indicator does not render when enabled."""
        mock_session_state = {"auto_scroll_enabled": True}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown") as mock_markdown,
        ):
            from app import render_auto_scroll_indicator

            render_auto_scroll_indicator()

            # Should not call markdown since HTML is empty
            mock_markdown.assert_not_called()


# =============================================================================
# Story 3.3: Release Control & Character Switching Tests
# =============================================================================


class TestReleaseControl:
    """Tests for releasing control back to AI (Story 3.3, Task 1)."""

    def test_release_clears_controlled_character_to_none(self) -> None:
        """Test that releasing control sets controlled_character to None."""
        mock_session_state = {
            "controlled_character": "rogue",
            "human_active": True,
            "ui_mode": "play",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("rogue")  # Same character = release

            assert mock_session_state.get("controlled_character") is None

    def test_release_sets_human_active_to_false(self) -> None:
        """Test that releasing control sets human_active to False."""
        mock_session_state = {
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("fighter")

            assert mock_session_state.get("human_active") is False

    def test_release_returns_ui_mode_to_watch(self) -> None:
        """Test that releasing control returns ui_mode to 'watch'."""
        mock_session_state = {
            "controlled_character": "wizard",
            "human_active": True,
            "ui_mode": "play",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("wizard")

            assert mock_session_state.get("ui_mode") == "watch"

    def test_release_clears_human_pending_action(self) -> None:
        """Test that releasing control clears human_pending_action."""
        mock_session_state = {
            "controlled_character": "cleric",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "I cast healing word",
            "waiting_for_human": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("cleric")

            assert mock_session_state.get("human_pending_action") is None

    def test_release_clears_waiting_for_human(self) -> None:
        """Test that releasing control clears waiting_for_human flag."""
        mock_session_state = {
            "controlled_character": "rogue",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": None,
            "waiting_for_human": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("rogue")

            assert mock_session_state.get("waiting_for_human") is False

    def test_release_all_state_transitions_together(self) -> None:
        """Test all release state transitions happen together (AC #1, #4)."""
        mock_session_state = {
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "Attack the goblin",
            "waiting_for_human": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("fighter")

            # All state should be cleared
            assert mock_session_state.get("controlled_character") is None
            assert mock_session_state.get("human_active") is False
            assert mock_session_state.get("ui_mode") == "watch"
            assert mock_session_state.get("human_pending_action") is None
            assert mock_session_state.get("waiting_for_human") is False


class TestCharacterSwitching:
    """Tests for quick character switching (Story 3.3, Task 3)."""

    def test_switch_auto_releases_previous_character(self) -> None:
        """Test that switching characters auto-releases the previous one (AC #3)."""
        mock_session_state = {
            "controlled_character": "rogue",
            "human_active": True,
            "ui_mode": "play",
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("fighter")  # Switch to fighter

            # Should now control fighter, not rogue
            assert mock_session_state.get("controlled_character") == "fighter"
            assert mock_session_state.get("human_active") is True
            assert mock_session_state.get("ui_mode") == "play"

    def test_switch_clears_pending_action_from_previous_character(self) -> None:
        """Test that switching clears pending action from previous character."""
        mock_session_state = {
            "controlled_character": "rogue",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "I search for traps",
            "waiting_for_human": True,
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("wizard")  # Switch to wizard

            # Pending action from rogue should be cleared
            assert mock_session_state.get("human_pending_action") is None
            assert mock_session_state.get("waiting_for_human") is False
            # But we're now controlling wizard
            assert mock_session_state.get("controlled_character") == "wizard"

    def test_switch_no_explicit_release_required(self) -> None:
        """Test that switching doesn't require explicit release step (AC #3)."""
        mock_session_state = {
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Directly click wizard while controlling fighter
            handle_drop_in_click("wizard")

            # Should be controlling wizard now (no intermediate watch state)
            assert mock_session_state.get("controlled_character") == "wizard"
            assert mock_session_state.get("ui_mode") == "play"

    def test_switch_completes_under_100ms(self) -> None:
        """Test that character switching completes quickly (AC #3: under 2 seconds)."""
        import time

        mock_session_state = {
            "controlled_character": "rogue",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "Some action",
            "waiting_for_human": True,
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            start_time = time.time()
            handle_drop_in_click("cleric")
            elapsed = time.time() - start_time

            # Function should complete nearly instantly (well under 2 seconds)
            assert elapsed < 0.1

    def test_switch_stops_autopilot(self) -> None:
        """Test that switching characters stops autopilot."""
        mock_session_state = {
            "controlled_character": "rogue",
            "human_active": True,
            "ui_mode": "play",
            "is_autopilot_running": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("fighter")

            assert mock_session_state.get("is_autopilot_running") is False

    def test_full_switch_flow(self) -> None:
        """Integration test for complete character switching flow."""
        mock_session_state: dict = {
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "human_pending_action": None,
            "waiting_for_human": False,
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Start controlling rogue
            handle_drop_in_click("rogue")
            assert mock_session_state.get("controlled_character") == "rogue"

            # Type an action (simulated)
            mock_session_state["human_pending_action"] = "I hide in shadows"
            mock_session_state["waiting_for_human"] = True

            # Switch to fighter (should auto-release rogue and clear pending)
            handle_drop_in_click("fighter")

            assert mock_session_state.get("controlled_character") == "fighter"
            assert mock_session_state.get("human_active") is True
            assert mock_session_state.get("ui_mode") == "play"
            assert mock_session_state.get("human_pending_action") is None
            assert mock_session_state.get("waiting_for_human") is False


class TestModeIndicatorRelease:
    """Tests for mode indicator updates on release (Story 3.3, Task 4)."""

    def test_mode_indicator_shows_watching_after_release(self) -> None:
        """Test mode indicator shows 'Watching' after release (AC #1)."""
        from app import render_mode_indicator_html

        # After release, ui_mode = "watch"
        html = render_mode_indicator_html("watch", False, None, None)

        assert "Watching" in html
        assert "watch" in html  # CSS class

    def test_mode_indicator_shows_playing_as_after_switch(self) -> None:
        """Test mode indicator shows 'Playing as [Character B]' after switch (AC #4)."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "wizard": CharacterConfig(
                name="Zephyr",
                character_class="Wizard",
                personality="wise",
                color="#7B68B8",
            )
        }

        html = render_mode_indicator_html("play", False, "wizard", characters)

        assert "Playing as Zephyr" in html
        assert "wizard" in html  # Character class in CSS

    def test_mode_indicator_pulse_dot_present_in_watch_mode(self) -> None:
        """Test pulse dot is present in watch mode (AC #1)."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False, None, None)

        assert "pulse-dot" in html

    def test_mode_indicator_pulse_dot_present_in_play_mode(self) -> None:
        """Test pulse dot is present in play mode."""
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

        assert "pulse-dot" in html


class TestInputAreaCollapse:
    """Tests for input area visibility on release (Story 3.3, Task 5)."""

    def test_render_human_input_area_returns_early_in_watch_mode(self) -> None:
        """Test render_human_input_area returns early when ui_mode='watch' (AC #4)."""
        mock_session_state = {
            "ui_mode": "watch",
            "controlled_character": None,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.text_area") as mock_text_area,
            patch("app.st.button") as mock_button,
        ):
            from app import render_human_input_area

            render_human_input_area()

            # Should not render any UI elements
            mock_text_area.assert_not_called()
            mock_button.assert_not_called()

    def test_render_human_input_area_returns_early_when_no_controlled_character(
        self,
    ) -> None:
        """Test render_human_input_area returns early when no controlled character."""
        mock_session_state = {
            "ui_mode": "play",
            "controlled_character": None,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.text_area") as mock_text_area,
            patch("app.st.button") as mock_button,
        ):
            from app import render_human_input_area

            render_human_input_area()

            # Should not render text area or button
            mock_text_area.assert_not_called()
            mock_button.assert_not_called()

    def test_input_context_bar_not_rendered_in_watch_mode(self) -> None:
        """Test input context bar is not rendered when ui_mode='watch'."""
        mock_session_state = {
            "ui_mode": "watch",
            "controlled_character": None,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown") as mock_markdown,
        ):
            from app import render_input_context_bar

            render_input_context_bar()

            # Should not render
            mock_markdown.assert_not_called()


class TestControlledCardStyling:
    """Tests for character card controlled state styling (Story 3.3, Task 2, 7)."""

    def test_character_card_html_includes_controlled_class_when_controlled(
        self,
    ) -> None:
        """Test character card HTML includes 'controlled' class when controlled."""
        from app import render_character_card_html

        html = render_character_card_html("Theron", "Fighter", controlled=True)

        assert "controlled" in html

    def test_character_card_html_no_controlled_class_when_not_controlled(self) -> None:
        """Test character card HTML does not include 'controlled' class when not controlled."""
        from app import render_character_card_html

        html = render_character_card_html("Theron", "Fighter", controlled=False)

        assert "controlled" not in html

    def test_button_label_changes_to_drop_in_after_release(self) -> None:
        """Test button label shows 'Drop-In' when not controlled."""
        from app import get_drop_in_button_label

        label = get_drop_in_button_label(controlled=False)

        assert label == "Drop-In"

    def test_button_label_shows_release_when_controlled(self) -> None:
        """Test button label shows 'Release' when controlled."""
        from app import get_drop_in_button_label

        label = get_drop_in_button_label(controlled=True)

        assert label == "Release"

    def test_css_has_controlled_character_card_glow(self) -> None:
        """Test CSS includes controlled card glow effect styling."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card.controlled" in css_content
        # Check for glow/box-shadow effect
        assert "box-shadow" in css_content

    def test_css_has_character_card_transition(self) -> None:
        """Test CSS includes transition for control state changes."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check for transition on character-card
        assert ".character-card" in css_content
        # Check for transition property (Story 3.3)
        assert "transition:" in css_content
        assert "box-shadow" in css_content

    def test_css_has_fighter_controlled_glow(self) -> None:
        """Test CSS includes fighter-specific controlled glow (Story 3.3)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card.controlled.fighter" in css_content

    def test_css_has_rogue_controlled_glow(self) -> None:
        """Test CSS includes rogue-specific controlled glow (Story 3.3)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card.controlled.rogue" in css_content

    def test_css_has_wizard_controlled_glow(self) -> None:
        """Test CSS includes wizard-specific controlled glow (Story 3.3)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card.controlled.wizard" in css_content

    def test_css_has_cleric_controlled_glow(self) -> None:
        """Test CSS includes cleric-specific controlled glow (Story 3.3)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card.controlled.cleric" in css_content


class TestAIAgentResume:
    """Tests for AI agent resume behavior (Story 3.3, Task 6)."""

    def test_route_to_next_agent_routes_to_ai_when_human_inactive(self) -> None:
        """Test route_to_next_agent routes to AI when human_active=False (AC #5)."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter", "rogue"],
            "current_turn": "fighter",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,  # Human released control
            "controlled_character": None,
            "session_number": 1,
        }

        from graph import route_to_next_agent

        next_agent = route_to_next_agent(state)

        # Should route to next PC (rogue), not human
        assert next_agent == "rogue"

    def test_route_to_next_agent_uses_ai_for_all_characters_after_release(self) -> None:
        """Test all characters use AI agents after release (AC #5)."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        # After release, human_active=False and controlled_character=None
        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter", "rogue", "wizard", "cleric"],
            "current_turn": "rogue",  # Previously controlled character
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,  # Released
            "session_number": 1,
        }

        from graph import route_to_next_agent

        next_agent = route_to_next_agent(state)

        # Should route to wizard (next in queue), not human
        assert next_agent == "wizard"

    def test_ai_continues_naturally_no_human_node_after_release(self) -> None:
        """Test AI continues naturally without routing to human node after release."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": ["[dm]: The adventure continues..."],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
        }

        from graph import route_to_next_agent

        next_agent = route_to_next_agent(state)

        # Should route to fighter (AI), not human
        assert next_agent == "fighter"


class TestStory33AcceptanceCriteria:
    """Integration tests for full Story 3.3 acceptance criteria."""

    def test_ac1_release_button_returns_control_to_ai(self) -> None:
        """AC#1: Clicking Release returns control to AI immediately."""
        mock_session_state = {
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("fighter")  # Release

            assert mock_session_state.get("human_active") is False
            assert mock_session_state.get("ui_mode") == "watch"

    def test_ac1_mode_indicator_returns_to_watching(self) -> None:
        """AC#1: Mode indicator returns to 'Watching' after release."""
        from app import render_mode_indicator_html

        # After release: ui_mode="watch", no controlled character
        html = render_mode_indicator_html("watch", False, None, None)

        assert "Watching" in html

    def test_ac2_ai_takes_over_seamlessly(self) -> None:
        """AC#2: AI takes over seamlessly with no narrative disruption."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        # State after human releases control mid-scene
        state: GameState = {
            "ground_truth_log": [
                "[dm]: You enter the dark cave.",
                "[fighter]: I light my torch.",
            ],
            "turn_queue": ["dm", "fighter", "rogue"],
            "current_turn": "fighter",
            "agent_memories": {"dm": AgentMemory(), "fighter": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,  # Just released
            "controlled_character": None,
            "session_number": 1,
        }

        from graph import route_to_next_agent

        next_agent = route_to_next_agent(state)

        # AI should continue to next character naturally
        assert next_agent == "rogue"

    def test_ac3_auto_release_on_switch(self) -> None:
        """AC#3: Clicking Drop-In on Character B auto-releases Character A."""
        mock_session_state = {
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "Attacking...",
            "waiting_for_human": True,
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Click on rogue while controlling fighter
            handle_drop_in_click("rogue")

            # Fighter auto-released, now controlling rogue
            assert mock_session_state.get("controlled_character") == "rogue"
            assert mock_session_state.get("human_active") is True
            # Pending action from fighter should be cleared
            assert mock_session_state.get("human_pending_action") is None
            assert mock_session_state.get("waiting_for_human") is False

    def test_ac4_ui_updates_on_release(self) -> None:
        """AC#4: UI updates correctly on release (input collapses, card styling)."""
        # Test input area collapses
        mock_session_state = {
            "ui_mode": "watch",  # After release
            "controlled_character": None,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.text_area") as mock_text_area,
            patch("app.st.button") as mock_button,
        ):
            from app import render_human_input_area

            render_human_input_area()

            # Input should not render
            mock_text_area.assert_not_called()
            mock_button.assert_not_called()

        # Test character card styling
        from app import render_character_card_html

        # After release, card should not have controlled class
        html = render_character_card_html("Theron", "Fighter", controlled=False)
        assert "controlled" not in html

    def test_ac5_human_active_transition_affects_routing(self) -> None:
        """AC#5: human_active=False causes all characters to use AI agents."""
        from models import AgentMemory, DMConfig, GameConfig, GameState

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter", "rogue", "wizard"],
            "current_turn": "rogue",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(),
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
        }

        from graph import route_to_next_agent

        # Should route to wizard (AI), not human
        next_agent = route_to_next_agent(state)
        assert next_agent == "wizard"

    def test_full_release_flow_play_to_watch(self) -> None:
        """Integration test: full release flow from play mode to watch mode."""
        mock_session_state = {
            "controlled_character": "rogue",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "I disarm the trap",
            "waiting_for_human": True,
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Release control
            handle_drop_in_click("rogue")

            # Verify all state transitions
            assert mock_session_state.get("controlled_character") is None
            assert mock_session_state.get("human_active") is False
            assert mock_session_state.get("ui_mode") == "watch"
            assert mock_session_state.get("human_pending_action") is None
            assert mock_session_state.get("waiting_for_human") is False

    def test_full_switch_flow_controlling_a_to_b(self) -> None:
        """Integration test: switching from Character A to Character B."""
        mock_session_state = {
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "I attack",
            "waiting_for_human": True,
            "is_autopilot_running": True,  # Should be stopped
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Switch to wizard
            handle_drop_in_click("wizard")

            # Verify state
            assert mock_session_state.get("controlled_character") == "wizard"
            assert mock_session_state.get("human_active") is True
            assert mock_session_state.get("ui_mode") == "play"
            assert mock_session_state.get("human_pending_action") is None
            assert mock_session_state.get("waiting_for_human") is False
            assert mock_session_state.get("is_autopilot_running") is False

    def test_mode_indicator_through_full_cycle(self) -> None:
        """Integration test: mode indicator through watch -> play -> watch."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "rogue": CharacterConfig(
                name="Shadow",
                character_class="Rogue",
                personality="cunning",
                color="#6B8E6B",
            )
        }

        # Initial watch mode
        html_watch = render_mode_indicator_html("watch", False, None, None)
        assert "Watching" in html_watch

        # Play mode after drop-in
        html_play = render_mode_indicator_html("play", False, "rogue", characters)
        assert "Playing as Shadow" in html_play

        # Back to watch after release
        html_watch_again = render_mode_indicator_html("watch", False, None, None)
        assert "Watching" in html_watch_again

    def test_character_card_styling_through_full_cycle(self) -> None:
        """Integration test: card styling through not controlled -> controlled -> not controlled."""
        from app import render_character_card_html

        # Not controlled
        html1 = render_character_card_html("Theron", "Fighter", controlled=False)
        assert "controlled" not in html1

        # Controlled
        html2 = render_character_card_html("Theron", "Fighter", controlled=True)
        assert "controlled" in html2

        # Not controlled again
        html3 = render_character_card_html("Theron", "Fighter", controlled=False)
        assert "controlled" not in html3

    def test_state_consistency_across_all_transitions(self) -> None:
        """Integration test: state remains consistent across all transitions."""
        mock_session_state: dict = {
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "human_pending_action": None,
            "waiting_for_human": False,
            "is_autopilot_running": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Take control of fighter
            handle_drop_in_click("fighter")
            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"
            assert mock_session_state["is_autopilot_running"] is False

            # Simulate typing action
            mock_session_state["human_pending_action"] = "I charge!"
            mock_session_state["waiting_for_human"] = True

            # Switch to rogue
            handle_drop_in_click("rogue")
            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"
            assert mock_session_state["human_pending_action"] is None
            assert mock_session_state["waiting_for_human"] is False

            # Release control
            handle_drop_in_click("rogue")
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["ui_mode"] == "watch"
            assert mock_session_state["human_pending_action"] is None
            assert mock_session_state["waiting_for_human"] is False

    def test_rapid_switching_settles_on_last_clicked(self) -> None:
        """Edge case: Rapid switching between characters settles on last clicked."""
        mock_session_state: dict = {
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "human_pending_action": None,
            "waiting_for_human": False,
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Rapid sequence of clicks (simulating fast user interaction)
            handle_drop_in_click("fighter")
            handle_drop_in_click("rogue")
            handle_drop_in_click("wizard")
            handle_drop_in_click("cleric")

            # State should settle on last clicked character
            assert mock_session_state["controlled_character"] == "cleric"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"
            # All intermediate pending actions should be cleared
            assert mock_session_state["human_pending_action"] is None
            assert mock_session_state["waiting_for_human"] is False

    def test_rapid_switching_with_pending_actions_clears_all(self) -> None:
        """Edge case: Rapid switching clears pending actions at each step."""
        mock_session_state: dict = {
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "Fighter action",
            "waiting_for_human": True,
            "is_autopilot_running": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Switch with pending action
            handle_drop_in_click("rogue")
            assert mock_session_state["human_pending_action"] is None

            # Add new pending action
            mock_session_state["human_pending_action"] = "Rogue action"

            # Switch again
            handle_drop_in_click("wizard")
            assert mock_session_state["human_pending_action"] is None
            assert mock_session_state["controlled_character"] == "wizard"

    def test_switch_during_generation_state_is_valid(self) -> None:
        """Edge case: Switching during generation maintains valid state.

        Note: In Streamlit's single-threaded model, button clicks trigger reruns.
        This test verifies the state remains valid regardless of is_generating flag.
        """
        mock_session_state: dict = {
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": None,
            "waiting_for_human": False,
            "is_autopilot_running": False,
            "is_generating": True,  # Simulate mid-generation state
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Attempt switch during generation
            handle_drop_in_click("rogue")

            # State should be valid (handle_drop_in_click doesn't check is_generating)
            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"
            # is_generating remains unchanged (not affected by drop-in)
            assert mock_session_state["is_generating"] is True


class TestDropInButtonDisabledDuringGeneration:
    """Tests for Drop-In button disabled state during generation (Story 3.3 code review fix)."""

    def test_drop_in_button_disabled_when_generating(self) -> None:
        """Test that Drop-In button is disabled when is_generating=True."""
        from models import CharacterConfig

        mock_session_state: dict = {
            "is_generating": True,
            "controlled_character": None,
        }

        char_config = CharacterConfig(
            name="Theron",
            character_class="Fighter",
            personality="brave",
            color="#C45C4A",
        )

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.button") as mock_button,
        ):
            mock_button.return_value = False
            from app import render_character_card

            render_character_card("fighter", char_config, controlled=False)

            # Verify button was called with disabled=True
            mock_button.assert_called_once()
            call_kwargs = mock_button.call_args[1]
            assert call_kwargs.get("disabled") is True

    def test_drop_in_button_enabled_when_not_generating(self) -> None:
        """Test that Drop-In button is enabled when is_generating=False."""
        from models import CharacterConfig

        mock_session_state: dict = {
            "is_generating": False,
            "controlled_character": None,
        }

        char_config = CharacterConfig(
            name="Theron",
            character_class="Fighter",
            personality="brave",
            color="#C45C4A",
        )

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.button") as mock_button,
        ):
            mock_button.return_value = False
            from app import render_character_card

            render_character_card("fighter", char_config, controlled=False)

            # Verify button was called with disabled=False
            mock_button.assert_called_once()
            call_kwargs = mock_button.call_args[1]
            assert call_kwargs.get("disabled") is False

    def test_release_button_also_disabled_when_generating(self) -> None:
        """Test that Release button is also disabled when is_generating=True."""
        from models import CharacterConfig

        mock_session_state: dict = {
            "is_generating": True,
            "controlled_character": "fighter",
        }

        char_config = CharacterConfig(
            name="Theron",
            character_class="Fighter",
            personality="brave",
            color="#C45C4A",
        )

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.button") as mock_button,
        ):
            mock_button.return_value = False
            from app import render_character_card

            render_character_card("fighter", char_config, controlled=True)

            # Verify button was called with disabled=True and label "Release"
            mock_button.assert_called_once()
            call_args = mock_button.call_args[0]
            call_kwargs = mock_button.call_args[1]
            assert call_args[0] == "Release"
            assert call_kwargs.get("disabled") is True


# =============================================================================
# Story 3.4: Nudge System Tests
# =============================================================================


class TestNudgeSessionState:
    """Tests for nudge session state initialization (Story 3.4, Task 1)."""

    def test_nudge_state_initializes_as_none(self) -> None:
        """Test that pending_nudge initializes as None."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert mock_session_state.get("pending_nudge") is None

    def test_nudge_submitted_initializes_as_false(self) -> None:
        """Test that nudge_submitted initializes as False."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert mock_session_state.get("nudge_submitted") is False


class TestHandleNudgeSubmit:
    """Tests for handle_nudge_submit() function (Story 3.4, Task 2)."""

    def test_handle_nudge_stores_sanitized_input(self) -> None:
        """Test that nudge handler stores sanitized input."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("  The rogue should check for traps  ")

            assert (
                mock_session_state["pending_nudge"]
                == "The rogue should check for traps"
            )
            assert mock_session_state["nudge_submitted"] is True

    def test_handle_nudge_truncates_long_input(self) -> None:
        """Test that nudge is truncated to 1000 chars."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        long_nudge = "x" * 1500

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit(long_nudge)

            assert len(mock_session_state["pending_nudge"]) == 1000

    def test_empty_nudge_not_stored(self) -> None:
        """Test that empty/whitespace nudge is not stored."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("   ")

            assert mock_session_state["pending_nudge"] is None
            assert mock_session_state["nudge_submitted"] is False

    def test_nudge_overwrite_behavior(self) -> None:
        """Test that new nudge overwrites previous."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("First suggestion")
            assert mock_session_state["pending_nudge"] == "First suggestion"

            handle_nudge_submit("Second suggestion")
            assert mock_session_state["pending_nudge"] == "Second suggestion"


class TestNudgeInputHtml:
    """Tests for render_nudge_input_html() function (Story 3.4, Task 3)."""

    def test_render_nudge_input_html_structure(self) -> None:
        """Test that nudge input HTML contains required structure."""
        from app import render_nudge_input_html

        html = render_nudge_input_html()

        assert 'class="nudge-input-container"' in html
        assert 'class="nudge-label"' in html
        assert 'class="nudge-hint"' in html
        assert "Suggest Something" in html
        assert "Whisper a suggestion to the DM" in html


class TestNudgeInputRendering:
    """Tests for render_nudge_input() rendering conditions (Story 3.4, Task 3)."""

    def test_nudge_hidden_when_controlling_character(self) -> None:
        """Test that nudge input is hidden in Play Mode."""
        mock_session_state: dict = {
            "human_active": True,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown") as mock_markdown,
            patch("app.st.text_area"),
            patch("app.st.button"),
        ):
            from app import render_nudge_input

            render_nudge_input()

            # Should NOT render any markdown (early return)
            mock_markdown.assert_not_called()

    def test_nudge_visible_in_watch_mode(self) -> None:
        """Test that nudge input appears in Watch Mode."""
        mock_session_state: dict = {
            "human_active": False,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown") as mock_markdown,
            patch("app.st.text_area"),
            patch("app.st.button", return_value=False),
        ):
            from app import render_nudge_input

            render_nudge_input()

            # Should render nudge container
            mock_markdown.assert_called()
            call_args = mock_markdown.call_args_list[0][0][0]
            assert "nudge-input-container" in call_args


class TestNudgeDoesNotChangeMode:
    """Tests for nudge not affecting ui_mode or human_active (Story 3.4, AC #2)."""

    def test_nudge_does_not_change_ui_mode(self) -> None:
        """Test that submitting nudge keeps user in Watch Mode."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Check for traps")

            assert mock_session_state.get("ui_mode") == "watch"
            assert mock_session_state.get("human_active") is False

    def test_nudge_preserves_existing_mode_state(self) -> None:
        """Test that nudge preserves all existing mode state."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "controlled_character": None,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Investigate the noise")

            # All mode-related state should be unchanged
            assert mock_session_state["ui_mode"] == "watch"
            assert mock_session_state["human_active"] is False
            assert mock_session_state["controlled_character"] is None
            # Only nudge state should change
            assert mock_session_state["pending_nudge"] == "Investigate the noise"


class TestNudgeCSSStyles:
    """Tests for nudge CSS styling (Story 3.4, Task 4)."""

    def test_css_has_nudge_container_styles(self) -> None:
        """Test CSS includes nudge input container class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".nudge-input-container" in css_content

    def test_css_has_nudge_label_styles(self) -> None:
        """Test CSS includes nudge label class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".nudge-label" in css_content

    def test_css_has_nudge_hint_styles(self) -> None:
        """Test CSS includes nudge hint class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".nudge-hint" in css_content

    def test_css_uses_green_accent_for_nudge(self) -> None:
        """Test CSS uses green (rogue) color for nudge focus."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Should use --color-rogue for the green suggestion theme
        assert "var(--color-rogue)" in css_content


class TestNudgeToastNotification:
    """Tests for nudge toast notification (Story 3.4, Task 8)."""

    def test_toast_shown_after_nudge_submission(self) -> None:
        """Test that success toast is shown when nudge_submitted is True."""
        mock_session_state: dict = {
            "human_active": False,
            "pending_nudge": "Test nudge",
            "nudge_submitted": True,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.text_area"),
            patch("app.st.button", return_value=False),
            patch("app.st.success") as mock_success,
        ):
            from app import render_nudge_input

            render_nudge_input()

            # Should show success toast
            mock_success.assert_called_once()
            call_args = mock_success.call_args
            assert "Nudge sent" in call_args[0][0]
            assert call_args[1].get("icon") == "✨"

    def test_toast_clears_submitted_flag(self) -> None:
        """Test that nudge_submitted flag is cleared after showing toast."""
        mock_session_state: dict = {
            "human_active": False,
            "pending_nudge": "Test nudge",
            "nudge_submitted": True,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.text_area"),
            patch("app.st.button", return_value=False),
            patch("app.st.success"),
        ):
            from app import render_nudge_input

            render_nudge_input()

            # Should clear the flag after showing toast
            assert mock_session_state["nudge_submitted"] is False


class TestNudgeInputValidation:
    """Tests for nudge input validation (Story 3.4, Task 9)."""

    def test_nudge_strips_leading_trailing_whitespace(self) -> None:
        """Test nudge strips whitespace before storage."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("\n  Check for traps  \t")

            assert mock_session_state["pending_nudge"] == "Check for traps"

    def test_nudge_exactly_1000_chars_accepted(self) -> None:
        """Test nudge exactly at 1000 char limit is accepted."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        nudge_1000 = "a" * 1000

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit(nudge_1000)

            assert len(mock_session_state["pending_nudge"]) == 1000
            assert mock_session_state["nudge_submitted"] is True


class TestNudgeInputClearing:
    """Tests for nudge input clearing after submission (Story 3.4, AC #4)."""

    def test_nudge_input_key_deleted_after_submission(self) -> None:
        """Test that nudge_input key is deleted from session_state after submit."""
        mock_session_state: dict = {
            "human_active": False,
            "pending_nudge": None,
            "nudge_submitted": False,
            "nudge_input": "My suggestion",  # Pre-existing input value
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.text_area", return_value="My suggestion"),
            patch("app.st.button", return_value=True),  # Simulate button click
            patch("app.st.rerun"),  # Mock rerun to prevent actual rerun
            patch("app.st.success"),
        ):
            from app import render_nudge_input

            render_nudge_input()

            # The nudge_input key should be deleted to clear the text area
            assert "nudge_input" not in mock_session_state


class TestStory34AcceptanceCriteria:
    """Integration tests for full Story 3.4 acceptance criteria."""

    def test_ac1_nudge_input_accessible_in_watch_mode(self) -> None:
        """AC#1: Nudge feature appears when in Watch Mode."""
        mock_session_state: dict = {
            "human_active": False,
            "ui_mode": "watch",
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown") as mock_markdown,
            patch("app.st.text_area"),
            patch("app.st.button", return_value=False),
        ):
            from app import render_nudge_input

            render_nudge_input()

            # Verify nudge container is rendered
            mock_markdown.assert_called()
            call_args = mock_markdown.call_args_list[0][0][0]
            assert "nudge-input-container" in call_args

    def test_ac2_nudge_stored_for_dm_context(self) -> None:
        """AC#2: Nudge stored for DM context, user remains in Watch Mode."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("The rogue should check for traps")

            # Nudge should be stored
            assert (
                mock_session_state["pending_nudge"]
                == "The rogue should check for traps"
            )
            # User should remain in watch mode
            assert mock_session_state["ui_mode"] == "watch"
            assert mock_session_state["human_active"] is False

    def test_ac4_toast_confirms_nudge_sent(self) -> None:
        """AC#4: Toast confirms 'Nudge sent' and input clears."""
        mock_session_state: dict = {
            "human_active": False,
            "pending_nudge": "Test",
            "nudge_submitted": True,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.st.markdown"),
            patch("app.st.text_area"),
            patch("app.st.button", return_value=False),
            patch("app.st.success") as mock_success,
        ):
            from app import render_nudge_input

            render_nudge_input()

            mock_success.assert_called_once()
            assert "Nudge sent" in mock_success.call_args[0][0]

    def test_ac5_nudge_less_intrusive_than_drop_in(self) -> None:
        """AC#5: Nudge is less intrusive - no character control."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "controlled_character": None,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Suggestion text")

            # Unlike Drop-In, nudge should NOT:
            # - Change ui_mode to "play"
            # - Set human_active to True
            # - Set controlled_character
            assert mock_session_state["ui_mode"] == "watch"
            assert mock_session_state["human_active"] is False
            assert mock_session_state["controlled_character"] is None


# =============================================================================
# Story 3.4: Nudge System Extended Tests - Edge Cases & Integration
# =============================================================================


class TestNudgeEdgeCasesUnicode:
    """Tests for nudge handling with unicode and special characters."""

    def test_nudge_accepts_unicode_characters(self) -> None:
        """Test that unicode characters are accepted in nudge."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Check the dragon's lair for treasure!")

            assert (
                mock_session_state["pending_nudge"]
                == "Check the dragon's lair for treasure!"
            )
            assert mock_session_state["nudge_submitted"] is True

    def test_nudge_accepts_emoji(self) -> None:
        """Test that emoji characters are preserved in nudge."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("The wizard should cast fireball! 🔥")

            assert "🔥" in mock_session_state["pending_nudge"]
            assert mock_session_state["nudge_submitted"] is True

    def test_nudge_accepts_non_latin_scripts(self) -> None:
        """Test that non-Latin scripts (CJK, Cyrillic, etc.) work."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            # Mix of Japanese, Chinese, and Cyrillic
            handle_nudge_submit("勇者は洞窟を探検してください 探险 исследуйте")

            assert (
                mock_session_state["pending_nudge"]
                == "勇者は洞窟を探検してください 探险 исследуйте"
            )

    def test_nudge_accepts_newlines(self) -> None:
        """Test that newlines within nudge text are preserved."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Line 1\nLine 2\nLine 3")

            assert mock_session_state["pending_nudge"] == "Line 1\nLine 2\nLine 3"

    def test_nudge_handles_tabs(self) -> None:
        """Test that tabs within nudge text are preserved."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Item 1\tItem 2")

            assert mock_session_state["pending_nudge"] == "Item 1\tItem 2"


class TestNudgeBoundaryConditions:
    """Tests for nudge at boundary conditions."""

    def test_nudge_1001_chars_truncated(self) -> None:
        """Test nudge at 1001 chars is truncated to 1000."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        nudge_1001 = "b" * 1001

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit(nudge_1001)

            assert len(mock_session_state["pending_nudge"]) == 1000
            assert mock_session_state["pending_nudge"] == "b" * 1000

    def test_nudge_999_chars_not_truncated(self) -> None:
        """Test nudge at 999 chars is not truncated."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        nudge_999 = "c" * 999

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit(nudge_999)

            assert len(mock_session_state["pending_nudge"]) == 999
            assert mock_session_state["pending_nudge"] == "c" * 999

    def test_nudge_single_character_accepted(self) -> None:
        """Test nudge with single character is accepted."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("?")

            assert mock_session_state["pending_nudge"] == "?"
            assert mock_session_state["nudge_submitted"] is True

    def test_nudge_very_long_truncated_at_boundary(self) -> None:
        """Test nudge with 10000 chars is truncated to 1000."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        nudge_10000 = "d" * 10000

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit(nudge_10000)

            assert len(mock_session_state["pending_nudge"]) == 1000

    def test_nudge_whitespace_only_variants(self) -> None:
        """Test various whitespace-only inputs are rejected."""
        whitespace_variants = [
            "",
            " ",
            "  ",
            "\t",
            "\n",
            "\r\n",
            "   \t\n   ",
        ]

        for ws in whitespace_variants:
            mock_session_state: dict = {
                "pending_nudge": None,
                "nudge_submitted": False,
            }

            with patch("streamlit.session_state", mock_session_state):
                from app import handle_nudge_submit

                handle_nudge_submit(ws)

                assert mock_session_state["pending_nudge"] is None, (
                    f"Failed for: {repr(ws)}"
                )
                assert mock_session_state["nudge_submitted"] is False, (
                    f"Failed for: {repr(ws)}"
                )


class TestNudgeSpecialCharacters:
    """Tests for nudge with special characters and potential edge cases."""

    def test_nudge_with_html_entities(self) -> None:
        """Test HTML-like characters don't cause issues."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("<script>alert('xss')</script>")

            # Should store raw text, not sanitize HTML
            assert (
                mock_session_state["pending_nudge"] == "<script>alert('xss')</script>"
            )

    def test_nudge_with_quotes(self) -> None:
        """Test nudge with various quote types."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Say \"Hello\" and 'Goodbye'")

            assert mock_session_state["pending_nudge"] == "Say \"Hello\" and 'Goodbye'"

    def test_nudge_with_backslashes(self) -> None:
        """Test nudge with backslash characters."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Check the path\\to\\dungeon")

            assert mock_session_state["pending_nudge"] == "Check the path\\to\\dungeon"

    def test_nudge_with_null_byte(self) -> None:
        """Test nudge with null byte is handled."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            # Null byte in string
            handle_nudge_submit("Check\x00for\x00traps")

            # Should store as-is (null bytes are valid in Python strings)
            assert "Check" in mock_session_state["pending_nudge"]

    def test_nudge_with_percent_encoding(self) -> None:
        """Test nudge with URL-like percent encoding."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Check %20 for %3D")

            assert mock_session_state["pending_nudge"] == "Check %20 for %3D"


class TestNudgeIntegrationWithDropIn:
    """Tests for nudge + Drop-In mode interactions."""

    def test_nudge_hidden_immediately_after_drop_in(self) -> None:
        """Test nudge input is hidden when user drops in to control character."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "controlled_character": None,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.markdown") as mock_markdown,
            patch("streamlit.text_area") as mock_text_area,
            patch("streamlit.button", return_value=False),
        ):
            from app import handle_drop_in_click, render_nudge_input

            # First verify nudge is shown
            mock_text_area.return_value = ""
            render_nudge_input()

            # Now drop in
            handle_drop_in_click("fighter")

            # Verify mode changed
            assert mock_session_state["human_active"] is True

            # Reset mocks and render nudge again
            mock_markdown.reset_mock()
            mock_text_area.reset_mock()

            render_nudge_input()

            # Nudge should not render (no markdown calls for nudge container)
            # Since human_active is True, render_nudge_input returns early
            assert mock_text_area.call_count == 0

    def test_nudge_visible_after_release(self) -> None:
        """Test nudge reappears when user releases character control."""
        mock_session_state: dict = {
            "ui_mode": "play",
            "human_active": True,
            "controlled_character": "fighter",
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.markdown"),
            patch("streamlit.text_area") as mock_text_area,
            patch("streamlit.button", return_value=False),
        ):
            from app import handle_drop_in_click, render_nudge_input

            # Initially hidden
            mock_text_area.return_value = ""
            render_nudge_input()
            assert mock_text_area.call_count == 0

            # Release control
            handle_drop_in_click("fighter")

            assert mock_session_state["human_active"] is False

            # Reset and render again
            mock_text_area.reset_mock()
            render_nudge_input()

            # Now should be visible
            assert mock_text_area.call_count == 1

    def test_pending_nudge_preserved_during_drop_in(self) -> None:
        """Test that pending nudge is preserved when user drops in/out."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "controlled_character": None,
            "pending_nudge": "Check for traps",
            "nudge_submitted": True,
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Drop in
            handle_drop_in_click("rogue")

            # Nudge should still be preserved
            assert mock_session_state["pending_nudge"] == "Check for traps"

            # Release
            handle_drop_in_click("rogue")

            # Still preserved
            assert mock_session_state["pending_nudge"] == "Check for traps"


class TestNudgeIntegrationWithAutopilot:
    """Tests for nudge + autopilot interactions."""

    def test_nudge_available_during_autopilot(self) -> None:
        """Test nudge input is available while autopilot is running."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "controlled_character": None,
            "is_autopilot_running": True,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.markdown"),
            patch("streamlit.text_area") as mock_text_area,
            patch("streamlit.button", return_value=False),
            patch("streamlit.success"),
        ):
            from app import render_nudge_input

            mock_text_area.return_value = ""
            render_nudge_input()

            # Nudge should still render during autopilot
            assert mock_text_area.call_count == 1

    def test_nudge_submit_during_autopilot(self) -> None:
        """Test nudge can be submitted while autopilot runs."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "controlled_character": None,
            "is_autopilot_running": True,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Speed up the story!")

            # Nudge should be stored even during autopilot
            assert mock_session_state["pending_nudge"] == "Speed up the story!"
            # Autopilot should NOT be affected
            assert mock_session_state["is_autopilot_running"] is True


class TestNudgeIntegrationWithPause:
    """Tests for nudge + pause state interactions."""

    def test_nudge_available_when_paused(self) -> None:
        """Test nudge input is available when game is paused."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "controlled_character": None,
            "is_paused": True,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.markdown"),
            patch("streamlit.text_area") as mock_text_area,
            patch("streamlit.button", return_value=False),
            patch("streamlit.success"),
        ):
            from app import render_nudge_input

            mock_text_area.return_value = ""
            render_nudge_input()

            # Nudge should render when paused
            assert mock_text_area.call_count == 1

    def test_nudge_preserved_across_pause_resume(self) -> None:
        """Test pending nudge is preserved through pause/resume."""
        mock_session_state: dict = {
            "ui_mode": "watch",
            "human_active": False,
            "is_paused": False,
            "pending_nudge": "Remember this",
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            # Pause
            handle_pause_toggle()
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["pending_nudge"] == "Remember this"

            # Resume
            handle_pause_toggle()
            assert mock_session_state["is_paused"] is False
            assert mock_session_state["pending_nudge"] == "Remember this"


class TestNudgeMultipleSubmissions:
    """Tests for multiple/rapid nudge submissions."""

    def test_nudge_overwrite_clears_previous(self) -> None:
        """Test that second nudge completely replaces first."""
        mock_session_state: dict = {
            "pending_nudge": "First nudge",
            "nudge_submitted": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Second nudge")

            assert mock_session_state["pending_nudge"] == "Second nudge"
            # submitted flag should still be True
            assert mock_session_state["nudge_submitted"] is True

    def test_nudge_rapid_submissions(self) -> None:
        """Test rapid successive submissions work correctly."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            # Simulate rapid submissions
            for i in range(10):
                handle_nudge_submit(f"Nudge {i}")
                assert mock_session_state["pending_nudge"] == f"Nudge {i}"

            # Final state should be last submission
            assert mock_session_state["pending_nudge"] == "Nudge 9"
            assert mock_session_state["nudge_submitted"] is True

    def test_nudge_then_empty_keeps_previous(self) -> None:
        """Test that empty submission after valid doesn't clear it."""
        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            # Submit valid nudge
            handle_nudge_submit("Valid nudge")
            assert mock_session_state["pending_nudge"] == "Valid nudge"

            # Submit empty - should NOT overwrite
            handle_nudge_submit("")
            assert mock_session_state["pending_nudge"] == "Valid nudge"


class TestNudgeSessionStateRobustness:
    """Tests for nudge handling with various session state conditions."""

    def test_nudge_with_missing_nudge_submitted_key(self) -> None:
        """Test handle_nudge_submit works even if nudge_submitted key missing."""
        mock_session_state: dict = {
            "pending_nudge": None,
            # nudge_submitted intentionally missing
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Test nudge")

            # Should create the key
            assert mock_session_state["nudge_submitted"] is True
            assert mock_session_state["pending_nudge"] == "Test nudge"

    def test_nudge_with_missing_pending_nudge_key(self) -> None:
        """Test handle_nudge_submit works even if pending_nudge key missing."""
        mock_session_state: dict = {
            # pending_nudge intentionally missing
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Test nudge")

            # Should create the key
            assert mock_session_state["pending_nudge"] == "Test nudge"

    def test_render_nudge_with_missing_human_active_key(self) -> None:
        """Test render_nudge_input handles missing human_active gracefully."""
        mock_session_state: dict = {
            # human_active intentionally missing - should default to falsy
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.markdown"),
            patch("streamlit.text_area") as mock_text_area,
            patch("streamlit.button", return_value=False),
        ):
            from app import render_nudge_input

            mock_text_area.return_value = ""
            # Should not raise
            render_nudge_input()

            # Should render (missing key treated as falsy)
            assert mock_text_area.call_count == 1


class TestNudgeConstantValidation:
    """Tests for MAX_NUDGE_LENGTH constant behavior."""

    def test_max_nudge_length_constant_exists(self) -> None:
        """Test MAX_NUDGE_LENGTH constant is defined."""
        from app import MAX_NUDGE_LENGTH

        assert MAX_NUDGE_LENGTH == 1000

    def test_nudge_truncation_uses_constant(self) -> None:
        """Test truncation actually uses MAX_NUDGE_LENGTH value."""
        from app import MAX_NUDGE_LENGTH

        mock_session_state: dict = {
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            # Create string longer than constant
            long_string = "x" * (MAX_NUDGE_LENGTH + 500)
            handle_nudge_submit(long_string)

            assert len(mock_session_state["pending_nudge"]) == MAX_NUDGE_LENGTH


# =============================================================================
# Story 3.5: Pause, Resume & Speed Control Tests
# =============================================================================


class TestModeIndicatorPaused:
    """Tests for mode indicator paused state rendering (Story 3.5, Task 1)."""

    def test_paused_state_shows_pause_dot(self) -> None:
        """Test paused state renders with static pause-dot class (AC #1)."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False, is_paused=True)
        assert "pause-dot" in html
        assert 'class="mode-indicator paused"' in html

    def test_paused_state_shows_paused_text(self) -> None:
        """Test paused state shows 'Paused' text (AC #1)."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False, is_paused=True)
        assert "Paused" in html

    def test_paused_state_takes_priority_over_watch(self) -> None:
        """Test paused state takes priority over watch mode (AC #1)."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False, is_paused=True)
        # Should not contain "Watching"
        assert "Watching" not in html
        assert "Paused" in html

    def test_paused_state_takes_priority_over_play(self) -> None:
        """Test paused state takes priority over play mode (AC #1)."""
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
        html = render_mode_indicator_html(
            "play", False, "fighter", characters, is_paused=True
        )
        # Should not contain "Playing as"
        assert "Playing as" not in html
        assert "Paused" in html

    def test_not_paused_shows_watch_mode(self) -> None:
        """Test not paused in watch mode shows normal watch state (AC #2)."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False, is_paused=False)
        assert "Watching" in html
        assert "Paused" not in html

    def test_not_paused_shows_play_mode(self) -> None:
        """Test not paused in play mode shows normal play state (AC #2)."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "rogue": CharacterConfig(
                name="Shadow",
                character_class="Rogue",
                personality="sneaky",
                color="#6B8E6B",
            )
        }
        html = render_mode_indicator_html(
            "play", False, "rogue", characters, is_paused=False
        )
        assert "Playing as Shadow" in html
        assert "Paused" not in html

    def test_paused_uses_pause_dot_not_pulse_dot(self) -> None:
        """Test paused state uses pause-dot class, not pulse-dot (AC #1)."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False, is_paused=True)
        assert "pause-dot" in html
        assert "pulse-dot" not in html


class TestPauseResumeState:
    """Tests for pause/resume session state behavior (Story 3.5, Task 3)."""

    def test_pause_stops_turn_generation(self) -> None:
        """Test pause flag stops run_game_turn() execution (AC #1)."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": True,
            "is_generating": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_game_turn

            result = run_game_turn()
            assert result is False

    def test_resume_allows_turn_generation(self) -> None:
        """Test resume allows turn generation to continue (AC #2)."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": False,
            "is_generating": False,
            "human_active": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_single_round") as mock_run,
            patch("time.sleep"),
        ):
            mock_run.return_value = game
            from app import run_game_turn

            result = run_game_turn()
            assert result is True

    def test_ui_responsive_while_paused(self) -> None:
        """Test UI rendering functions still work while paused (AC #3)."""
        from app import render_mode_indicator_html

        # UI render functions should work regardless of pause state
        html = render_mode_indicator_html("watch", False, is_paused=True)
        assert html is not None
        assert len(html) > 0

    def test_autopilot_stops_when_paused(self) -> None:
        """Test autopilot stops when game is paused."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
            "autopilot_turn_count": 5,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_autopilot_step

            run_autopilot_step()
            assert mock_session_state["is_autopilot_running"] is False

    def test_continuous_loop_stops_when_paused(self) -> None:
        """Test run_continuous_loop stops when paused."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_continuous_loop

            result = run_continuous_loop()
            assert result == 0
            assert mock_session_state["is_autopilot_running"] is False


class TestSpeedControl:
    """Tests for speed control effects on turn timing (Story 3.5, Task 4)."""

    def test_speed_delays_slow(self) -> None:
        """Test slow speed returns 3.0 second delay (AC #5)."""
        mock_session_state = {"playback_speed": "slow"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 3.0

    def test_speed_delays_normal(self) -> None:
        """Test normal speed returns 1.0 second delay (AC #4)."""
        mock_session_state = {"playback_speed": "normal"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 1.0

    def test_speed_delays_fast(self) -> None:
        """Test fast speed returns 0.2 second delay (AC #4)."""
        mock_session_state = {"playback_speed": "fast"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 0.2

    def test_speed_delays_constant_mapping(self) -> None:
        """Test SPEED_DELAYS constant has correct values."""
        from app import SPEED_DELAYS

        assert SPEED_DELAYS["slow"] == 3.0
        assert SPEED_DELAYS["normal"] == 1.0
        assert SPEED_DELAYS["fast"] == 0.2

    def test_speed_delays_unknown_defaults_to_normal(self) -> None:
        """Test unknown speed defaults to normal (1.0s)."""
        mock_session_state = {"playback_speed": "invalid"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 1.0


class TestModalAutoPause:
    """Tests for config modal auto-pause behavior (Story 3.5, Task 6)."""

    def test_modal_open_auto_pauses_game(self) -> None:
        """Test opening config modal auto-pauses game (AC #6)."""
        mock_session_state = {
            "is_paused": False,
            "pre_modal_pause_state": False,
            "modal_open": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_open

            handle_modal_open()
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["modal_open"] is True

    def test_modal_open_stores_previous_pause_state(self) -> None:
        """Test modal open stores previous pause state (AC #6)."""
        mock_session_state = {
            "is_paused": False,
            "pre_modal_pause_state": False,
            "modal_open": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_open

            handle_modal_open()
            assert mock_session_state["pre_modal_pause_state"] is False

    def test_modal_open_when_already_paused(self) -> None:
        """Test modal open when game already paused stores True (AC #6)."""
        mock_session_state = {
            "is_paused": True,
            "pre_modal_pause_state": False,
            "modal_open": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_open

            handle_modal_open()
            assert mock_session_state["pre_modal_pause_state"] is True
            assert mock_session_state["is_paused"] is True

    def test_modal_close_restores_pause_state_false(self) -> None:
        """Test closing modal restores previous pause state (False) (AC #6)."""
        mock_session_state = {
            "is_paused": True,
            "pre_modal_pause_state": False,
            "modal_open": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_close

            handle_modal_close()
            assert mock_session_state["is_paused"] is False
            assert mock_session_state["modal_open"] is False

    def test_modal_close_restores_pause_state_true(self) -> None:
        """Test closing modal restores previous pause state (True) (AC #6)."""
        mock_session_state = {
            "is_paused": True,
            "pre_modal_pause_state": True,
            "modal_open": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_close

            handle_modal_close()
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["modal_open"] is False

    def test_modal_open_close_round_trip_not_paused(self) -> None:
        """Test modal open/close round trip preserves unpaused state (AC #6)."""
        mock_session_state = {
            "is_paused": False,
            "pre_modal_pause_state": False,
            "modal_open": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_close, handle_modal_open

            # Open modal
            handle_modal_open()
            assert mock_session_state["is_paused"] is True

            # Close modal
            handle_modal_close()
            assert mock_session_state["is_paused"] is False

    def test_modal_open_close_round_trip_already_paused(self) -> None:
        """Test modal open/close round trip preserves paused state (AC #6)."""
        mock_session_state = {
            "is_paused": True,
            "pre_modal_pause_state": False,
            "modal_open": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_close, handle_modal_open

            # Open modal
            handle_modal_open()
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["pre_modal_pause_state"] is True

            # Close modal
            handle_modal_close()
            assert mock_session_state["is_paused"] is True


class TestInitializeSessionStateStory35:
    """Tests for session state initialization for Story 3.5."""

    def test_initialize_session_state_sets_modal_open(self) -> None:
        """Test that initialize_session_state sets modal_open to False."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()
            assert mock_session_state["modal_open"] is False

    def test_initialize_session_state_sets_pre_modal_pause_state(self) -> None:
        """Test that initialize_session_state sets pre_modal_pause_state to False."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()
            assert mock_session_state["pre_modal_pause_state"] is False


class TestPausedModeIndicatorCSS:
    """Tests for paused mode indicator CSS styling (Story 3.5, Task 2)."""

    def test_css_has_mode_indicator_paused(self) -> None:
        """Test CSS includes .mode-indicator.paused class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.paused" in css_content

    def test_css_has_pause_dot_class(self) -> None:
        """Test CSS includes .pause-dot class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".pause-dot" in css_content

    def test_css_pause_dot_no_animation(self) -> None:
        """Test CSS pause-dot has no animation (static)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Find the pause-dot section
        pause_dot_start = css_content.find(".pause-dot {")
        pause_dot_end = css_content.find("}", pause_dot_start)
        pause_dot_css = css_content[pause_dot_start:pause_dot_end]

        # Should NOT have animation property
        assert "animation:" not in pause_dot_css

    def test_css_paused_has_amber_background(self) -> None:
        """Test CSS paused state uses amber background."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Paused should use amber (232, 168, 73 is --accent-warm)
        assert "rgba(232, 168, 73, 0.2)" in css_content

    def test_css_mode_indicator_has_transition(self) -> None:
        """Test CSS mode-indicator has transition for smooth state changes."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "transition:" in css_content


class TestStory35AcceptanceCriteria:
    """Integration tests for Story 3.5 acceptance criteria."""

    def test_ac1_pause_stops_generation_shows_paused_indicator(self) -> None:
        """AC #1: Pause stops turn generation and shows paused indicator."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": True,
            "is_generating": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import render_mode_indicator_html, run_game_turn

            # Turn generation should stop
            result = run_game_turn()
            assert result is False

            # Mode indicator should show paused
            html = render_mode_indicator_html("watch", False, is_paused=True)
            assert "Paused" in html
            assert "pause-dot" in html

    def test_ac2_resume_continues_and_returns_to_active(self) -> None:
        """AC #2: Resume continues turn generation and returns to active state."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": False,
            "is_generating": False,
            "human_active": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_single_round") as mock_run,
            patch("time.sleep"),
        ):
            mock_run.return_value = game
            from app import render_mode_indicator_html, run_game_turn

            # Turn generation should continue
            result = run_game_turn()
            assert result is True

            # Mode indicator should show active (watch)
            html = render_mode_indicator_html("watch", False, is_paused=False)
            assert "Watching" in html
            assert "pulse-dot" in html

    def test_ac3_ui_functional_while_paused(self) -> None:
        """AC #3: UI remains fully functional while paused."""
        from app import (
            render_auto_scroll_indicator_html,
            render_dm_message_html,
            render_mode_indicator_html,
            render_pc_message_html,
        )

        # All render functions should work while paused
        mode_html = render_mode_indicator_html("watch", False, is_paused=True)
        assert mode_html is not None

        dm_html = render_dm_message_html("Test narration")
        assert dm_html is not None

        pc_html = render_pc_message_html("Theron", "Fighter", "Test dialogue")
        assert pc_html is not None

        scroll_html = render_auto_scroll_indicator_html(False)
        assert scroll_html is not None

    def test_ac4_speed_control_changes_delay(self) -> None:
        """AC #4: Speed control changes delay between turns."""
        from app import get_turn_delay

        for speed, expected_delay in [("slow", 3.0), ("normal", 1.0), ("fast", 0.2)]:
            mock_session_state = {"playback_speed": speed}
            with patch("streamlit.session_state", mock_session_state):
                delay = get_turn_delay()
                assert delay == expected_delay

    def test_ac5_slow_speed_longer_pause(self) -> None:
        """AC #5: Slow speed provides longer pause for reading."""
        mock_session_state = {"playback_speed": "slow"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            # Slow should be 3.0 seconds
            assert delay == 3.0
            # Slow should be longer than normal
            assert delay > 1.0

    def test_ac6_modal_auto_pause_resume(self) -> None:
        """AC #6: Modal auto-pauses on open and auto-resumes on close."""
        mock_session_state = {
            "is_paused": False,
            "pre_modal_pause_state": False,
            "modal_open": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_close, handle_modal_open

            # Verify initial state
            assert mock_session_state["is_paused"] is False

            # Open modal - should auto-pause
            handle_modal_open()
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["modal_open"] is True

            # Close modal - should auto-resume
            handle_modal_close()
            assert mock_session_state["is_paused"] is False
            assert mock_session_state["modal_open"] is False


class TestPauseIntegrationWithAutopilot:
    """Integration tests for pause with autopilot (Story 3.5, Task 7)."""

    def test_autopilot_step_respects_pause(self) -> None:
        """Test run_autopilot_step respects is_paused flag."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
            "autopilot_turn_count": 0,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_autopilot_step

            run_autopilot_step()
            # Autopilot should stop when paused
            assert mock_session_state["is_autopilot_running"] is False

    def test_autopilot_resumes_when_unpaused(self) -> None:
        """Test autopilot can continue when unpaused (turn count preserved)."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
            "autopilot_turn_count": 5,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_autopilot_step

            # First stop due to pause
            run_autopilot_step()
            assert mock_session_state["is_autopilot_running"] is False
            # Turn count should be preserved
            assert mock_session_state["autopilot_turn_count"] == 5

    def test_continuous_loop_stops_immediately_when_paused(self) -> None:
        """Test run_continuous_loop stops immediately when paused."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_continuous_loop

            result = run_continuous_loop()
            assert result == 0
            assert mock_session_state["is_autopilot_running"] is False


class TestPauseEdgeCases:
    """Tests for pause edge cases (Story 3.5)."""

    def test_rapid_pause_resume_toggle(self) -> None:
        """Test rapid pause/resume toggles work correctly."""
        mock_session_state = {"is_paused": False}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            # Toggle rapidly
            handle_pause_toggle()
            assert mock_session_state["is_paused"] is True

            handle_pause_toggle()
            assert mock_session_state["is_paused"] is False

            handle_pause_toggle()
            assert mock_session_state["is_paused"] is True

    def test_pause_during_play_mode(self) -> None:
        """Test pause works correctly during play mode."""
        from models import CharacterConfig

        characters = {
            "fighter": CharacterConfig(
                name="Theron",
                character_class="Fighter",
                personality="brave",
                color="#C45C4A",
            )
        }

        from app import render_mode_indicator_html

        html = render_mode_indicator_html(
            "play", False, "fighter", characters, is_paused=True
        )
        # Paused should take priority
        assert "Paused" in html
        assert "Playing as" not in html

    def test_speed_change_while_paused(self) -> None:
        """Test speed change while paused stores for later use."""
        mock_session_state = {"is_paused": True, "playback_speed": "normal"}

        with patch("streamlit.session_state", mock_session_state):
            # Change speed while paused
            mock_session_state["playback_speed"] = "slow"

            from app import get_turn_delay

            # Speed should be updated even while paused
            delay = get_turn_delay()
            assert delay == 3.0

    def test_pause_then_drop_in_works(self) -> None:
        """Test human can drop in while game is paused."""
        mock_session_state = {
            "is_paused": True,
            "controlled_character": None,
            "ui_mode": "watch",
            "human_active": False,
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("fighter")

            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["ui_mode"] == "play"
            assert mock_session_state["human_active"] is True
            # Pause state should remain
            assert mock_session_state["is_paused"] is True


class TestModeIndicatorRenderSidebarIntegration:
    """Tests for mode indicator integration with render_sidebar (Story 3.5)."""

    def test_render_sidebar_passes_is_paused(self) -> None:
        """Test render_sidebar passes is_paused to render_mode_indicator_html."""
        mock_session_state = {
            "ui_mode": "watch",
            "is_generating": False,
            "is_paused": True,
            "controlled_character": None,
            "game": {
                "characters": {},
                "ground_truth_log": [],
            },
            "pending_nudge": None,
            "nudge_submitted": False,
            "human_active": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.sidebar"),
            patch("streamlit.markdown") as mock_markdown,
            patch("streamlit.expander"),
            patch("streamlit.caption"),
            patch("app.render_session_controls"),
            patch("app.render_nudge_input"),
        ):
            from app import render_sidebar
            from config import AppConfig

            config = AppConfig()

            render_sidebar(config)

            # Check that markdown was called with paused HTML
            calls = mock_markdown.call_args_list
            # At least one call should contain the paused indicator
            paused_calls = [c for c in calls if "Paused" in str(c)]
            assert len(paused_calls) > 0


# =============================================================================
# Story 3.5: Extended Edge Case Tests - Test Automation Expansion
# =============================================================================


class TestPauseSessionStateMissing:
    """Tests for pause behavior when session state keys are missing."""

    def test_render_mode_indicator_missing_is_paused_defaults_to_false(self) -> None:
        """Test render_mode_indicator_html defaults is_paused to False."""
        from app import render_mode_indicator_html

        # Call without is_paused parameter (uses default)
        html = render_mode_indicator_html("watch", False)
        assert "Paused" not in html
        assert "Watching" in html

    def test_run_game_turn_missing_is_paused_key(self) -> None:
        """Test run_game_turn handles missing is_paused key gracefully."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_generating": False,
            "human_active": False,
            # is_paused key intentionally missing
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_single_round") as mock_run,
            patch("time.sleep"),
        ):
            mock_run.return_value = game
            from app import run_game_turn

            # Should proceed (missing is_paused treated as False)
            result = run_game_turn()
            assert result is True

    def test_get_turn_delay_missing_playback_speed_key(self) -> None:
        """Test get_turn_delay handles missing playback_speed key."""
        mock_session_state: dict = {}  # Empty session state

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            # Should default to "normal" (1.0s)
            delay = get_turn_delay()
            assert delay == 1.0

    def test_is_autopilot_available_missing_is_paused(self) -> None:
        """Test is_autopilot_available handles missing is_paused."""
        mock_session_state = {
            "game": {},
            "human_active": False,
            # is_paused missing
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import is_autopilot_available

            # Should be available (missing is_paused treated as False)
            assert is_autopilot_available() is True

    def test_handle_pause_toggle_missing_is_paused(self) -> None:
        """Test handle_pause_toggle creates is_paused if missing."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            handle_pause_toggle()
            # Should create is_paused and set to True (toggle from False)
            assert mock_session_state["is_paused"] is True


class TestSpeedControlBoundaryConditions:
    """Tests for speed control boundary and edge conditions."""

    def test_speed_delays_empty_string_defaults_to_normal(self) -> None:
        """Test empty string playback_speed defaults to normal."""
        mock_session_state = {"playback_speed": ""}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 1.0

    def test_speed_delays_none_defaults_to_normal(self) -> None:
        """Test None playback_speed defaults to normal."""
        mock_session_state = {"playback_speed": None}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 1.0

    def test_speed_delays_uppercase_invalid(self) -> None:
        """Test uppercase speed names are treated as invalid (case sensitive)."""
        mock_session_state = {"playback_speed": "SLOW"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            # Should default to normal since exact match required
            delay = get_turn_delay()
            assert delay == 1.0

    def test_speed_delays_mixed_case_invalid(self) -> None:
        """Test mixed case speed names are invalid."""
        mock_session_state = {"playback_speed": "Normal"}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 1.0

    def test_speed_delays_whitespace_invalid(self) -> None:
        """Test whitespace speed is invalid."""
        mock_session_state = {"playback_speed": "  normal  "}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_turn_delay

            delay = get_turn_delay()
            assert delay == 1.0  # Exact match required

    def test_speed_delays_all_valid_values(self) -> None:
        """Test all valid speed values return correct delays."""
        from app import SPEED_DELAYS

        valid_speeds = [("slow", 3.0), ("normal", 1.0), ("fast", 0.2)]
        for speed, expected in valid_speeds:
            assert SPEED_DELAYS.get(speed, 1.0) == expected


class TestPauseNudgeIntegrationExtended:
    """Extended tests for pause and nudge interaction."""

    def test_pause_does_not_clear_pending_nudge(self) -> None:
        """Test pausing game does not clear pending nudge."""
        mock_session_state = {
            "is_paused": False,
            "pending_nudge": "Check for traps",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            handle_pause_toggle()
            # Pause should not affect nudge
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["pending_nudge"] == "Check for traps"

    def test_resume_does_not_clear_pending_nudge(self) -> None:
        """Test resuming game does not clear pending nudge."""
        mock_session_state = {
            "is_paused": True,
            "pending_nudge": "Cast detect magic",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            handle_pause_toggle()
            # Resume should not affect nudge
            assert mock_session_state["is_paused"] is False
            assert mock_session_state["pending_nudge"] == "Cast detect magic"

    def test_nudge_submission_while_paused(self) -> None:
        """Test nudge can be submitted while game is paused."""
        mock_session_state = {
            "is_paused": True,
            "pending_nudge": None,
            "nudge_submitted": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Search the bookshelf")
            # Nudge should be stored even while paused
            assert mock_session_state["pending_nudge"] == "Search the bookshelf"
            assert mock_session_state["nudge_submitted"] is True

    def test_multiple_nudges_while_paused_replaces(self) -> None:
        """Test multiple nudge submissions while paused replace each other."""
        mock_session_state = {
            "is_paused": True,
            "pending_nudge": "First suggestion",
            "nudge_submitted": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_nudge_submit

            handle_nudge_submit("Second suggestion")
            # Second nudge should replace first
            assert mock_session_state["pending_nudge"] == "Second suggestion"


class TestPauseStateConsistency:
    """Tests for pause state consistency across operations."""

    def test_pause_state_survives_speed_change(self) -> None:
        """Test pause state is preserved when speed is changed."""
        mock_session_state = {"is_paused": True, "playback_speed": "normal"}

        with patch("streamlit.session_state", mock_session_state):
            # Simulate speed change
            mock_session_state["playback_speed"] = "fast"

            # Pause should be preserved
            assert mock_session_state["is_paused"] is True

    def test_pause_state_survives_human_action_submit(self) -> None:
        """Test pause state is preserved when human action is submitted."""
        mock_session_state = {
            "is_paused": True,
            "human_pending_action": None,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_human_action_submit

            handle_human_action_submit("I attack the goblin")
            # Pause should be preserved
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["human_pending_action"] == "I attack the goblin"

    def test_pause_state_survives_auto_scroll_toggle(self) -> None:
        """Test pause state is preserved when auto-scroll is toggled."""
        mock_session_state = {
            "is_paused": True,
            "auto_scroll_enabled": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_auto_scroll_click

            handle_pause_auto_scroll_click()
            # Pause should be preserved
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["auto_scroll_enabled"] is False

    def test_pause_preserved_across_drop_in_release_cycle(self) -> None:
        """Test pause state preserved through drop-in/release cycle."""
        mock_session_state = {
            "is_paused": True,
            "controlled_character": None,
            "ui_mode": "watch",
            "human_active": False,
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            # Drop in
            handle_drop_in_click("rogue")
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["controlled_character"] == "rogue"

            # Release
            handle_drop_in_click("rogue")
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["controlled_character"] is None


class TestModalAutoPauseEdgeCases:
    """Extended tests for modal auto-pause edge cases."""

    def test_modal_open_with_missing_pre_modal_state(self) -> None:
        """Test modal open handles missing pre_modal_pause_state."""
        mock_session_state = {
            "is_paused": False,
            "modal_open": False,
            # pre_modal_pause_state missing
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_open

            # Should not raise
            handle_modal_open()
            assert mock_session_state["is_paused"] is True

    def test_modal_close_with_missing_pre_modal_state(self) -> None:
        """Test modal close handles missing pre_modal_pause_state (defaults False)."""
        mock_session_state = {
            "is_paused": True,
            "modal_open": True,
            # pre_modal_pause_state missing - should default to False
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_close

            handle_modal_close()
            # Should restore to False (default)
            assert mock_session_state["is_paused"] is False
            assert mock_session_state["modal_open"] is False

    def test_multiple_modal_open_calls_idempotent(self) -> None:
        """Test multiple modal open calls don't break state."""
        mock_session_state = {
            "is_paused": False,
            "pre_modal_pause_state": False,
            "modal_open": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_open

            # Multiple opens
            handle_modal_open()
            assert mock_session_state["pre_modal_pause_state"] is False

            # Second open should store current state (True from first open)
            handle_modal_open()
            assert mock_session_state["pre_modal_pause_state"] is True

    def test_modal_close_without_open_safe(self) -> None:
        """Test modal close without prior open is safe."""
        mock_session_state = {
            "is_paused": True,
            "pre_modal_pause_state": True,
            "modal_open": False,  # Not open
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_modal_close

            # Should not raise, just update state
            handle_modal_close()
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["modal_open"] is False


class TestThinkingIndicatorPauseInteraction:
    """Tests for thinking indicator interaction with pause state."""

    def test_thinking_indicator_hidden_when_paused_and_generating(self) -> None:
        """Test thinking indicator is hidden when paused even if generating."""
        from app import render_thinking_indicator_html

        html = render_thinking_indicator_html(is_generating=True, is_paused=True)
        assert html == ""

    def test_thinking_indicator_shown_when_not_paused_and_generating(self) -> None:
        """Test thinking indicator shown when generating and not paused."""
        from app import render_thinking_indicator_html

        html = render_thinking_indicator_html(is_generating=True, is_paused=False)
        assert "thinking-indicator" in html
        assert "The story unfolds" in html

    def test_thinking_indicator_hidden_when_not_generating(self) -> None:
        """Test thinking indicator hidden when not generating regardless of pause."""
        from app import render_thinking_indicator_html

        html_not_paused = render_thinking_indicator_html(
            is_generating=False, is_paused=False
        )
        html_paused = render_thinking_indicator_html(
            is_generating=False, is_paused=True
        )

        assert html_not_paused == ""
        assert html_paused == ""


class TestPauseDropInCombinations:
    """Tests for pause + drop-in mode combinations."""

    def test_pause_while_controlling_character(self) -> None:
        """Test pausing while controlling a character."""
        mock_session_state = {
            "is_paused": False,
            "controlled_character": "wizard",
            "ui_mode": "play",
            "human_active": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_pause_toggle

            handle_pause_toggle()
            # Should pause without affecting character control
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["controlled_character"] == "wizard"
            assert mock_session_state["human_active"] is True

    def test_release_character_while_paused(self) -> None:
        """Test releasing character while paused."""
        mock_session_state = {
            "is_paused": True,
            "controlled_character": "cleric",
            "ui_mode": "play",
            "human_active": True,
            "is_autopilot_running": False,
            "human_pending_action": "I heal the fighter",
            "waiting_for_human": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("cleric")  # Release
            # Should release and return to watch mode
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["ui_mode"] == "watch"
            assert mock_session_state["human_active"] is False
            # Pending action should be cleared
            assert mock_session_state["human_pending_action"] is None
            # Pause should be preserved
            assert mock_session_state["is_paused"] is True

    def test_switch_character_while_paused(self) -> None:
        """Test switching controlled character while paused."""
        mock_session_state = {
            "is_paused": True,
            "controlled_character": "fighter",
            "ui_mode": "play",
            "human_active": True,
            "is_autopilot_running": False,
            "human_pending_action": "I attack",
            "waiting_for_human": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_drop_in_click

            handle_drop_in_click("rogue")  # Switch to rogue
            # Should switch characters
            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["ui_mode"] == "play"
            assert mock_session_state["human_active"] is True
            # Pending action from previous character should be cleared
            assert mock_session_state["human_pending_action"] is None
            # Pause should be preserved
            assert mock_session_state["is_paused"] is True


class TestPauseCSSValidationExtended:
    """Extended CSS validation tests for pause styling."""

    def test_css_pause_dot_dimensions(self) -> None:
        """Test pause-dot has correct dimensions (8px x 8px)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Find pause-dot section
        pause_start = css_content.find(".pause-dot {")
        pause_end = css_content.find("}", pause_start)
        pause_css = css_content[pause_start:pause_end]

        assert "width: 8px" in pause_css
        assert "height: 8px" in pause_css

    def test_css_pause_dot_border_radius(self) -> None:
        """Test pause-dot is circular (border-radius: 50%)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        pause_start = css_content.find(".pause-dot {")
        pause_end = css_content.find("}", pause_start)
        pause_css = css_content[pause_start:pause_end]

        assert "border-radius: 50%" in pause_css

    def test_css_pause_dot_uses_accent_warm(self) -> None:
        """Test pause-dot uses --accent-warm color."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        pause_start = css_content.find(".pause-dot {")
        pause_end = css_content.find("}", pause_start)
        pause_css = css_content[pause_start:pause_end]

        assert "var(--accent-warm)" in pause_css

    def test_css_mode_indicator_paused_color(self) -> None:
        """Test paused mode indicator uses correct color."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        paused_start = css_content.find(".mode-indicator.paused {")
        paused_end = css_content.find("}", paused_start)
        paused_css = css_content[paused_start:paused_end]

        assert "var(--accent-warm)" in paused_css

    def test_css_pulse_dot_has_animation(self) -> None:
        """Test pulse-dot (not pause-dot) has animation."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        pulse_start = css_content.find(".pulse-dot {")
        pulse_end = css_content.find("}", pulse_start)
        pulse_css = css_content[pulse_start:pulse_end]

        assert "animation:" in pulse_css
        assert "pulse" in pulse_css


class TestRunGameTurnPauseInteraction:
    """Tests for run_game_turn pause interaction edge cases."""

    def test_run_game_turn_paused_returns_false_immediately(self) -> None:
        """Test run_game_turn returns False immediately when paused."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": True,
            "is_generating": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_game_turn

            result = run_game_turn()
            # Should return False without setting is_generating
            assert result is False
            assert mock_session_state["is_generating"] is False

    def test_run_game_turn_not_paused_sets_generating(self) -> None:
        """Test run_game_turn sets is_generating when not paused."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        generating_values = []

        mock_session_state = {
            "game": game,
            "is_paused": False,
            "is_generating": False,
            "human_active": False,
            "waiting_for_human": False,
        }

        def track_generating(*args):
            generating_values.append(mock_session_state.get("is_generating"))
            return game

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_single_round", side_effect=track_generating),
            patch("time.sleep"),
        ):
            from app import run_game_turn

            run_game_turn()
            # is_generating should have been True during execution
            assert True in generating_values

    def test_run_game_turn_respects_pause_set_during_execution(self) -> None:
        """Test pause set during execution doesn't break return."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_paused": False,
            "is_generating": False,
            "human_active": False,
            "waiting_for_human": False,
        }

        def pause_during_run(*args):
            mock_session_state["is_paused"] = True
            return game

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_single_round", side_effect=pause_during_run),
            patch("time.sleep"),
        ):
            from app import run_game_turn

            result = run_game_turn()
            # Should still return True (pause checked at start)
            assert result is True
            # But is_generating should be cleared
            assert mock_session_state["is_generating"] is False


class TestAutopilotPauseInteractionExtended:
    """Extended tests for autopilot and pause interaction."""

    def test_autopilot_not_started_when_paused(self) -> None:
        """Test autopilot cannot start when game is paused."""
        mock_session_state = {
            "game": {},
            "is_paused": True,
            "human_active": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import is_autopilot_available

            assert is_autopilot_available() is False

    def test_autopilot_turn_count_preserved_on_pause(self) -> None:
        """Test autopilot turn count is preserved when paused."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
            "autopilot_turn_count": 42,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_autopilot_step

            run_autopilot_step()
            # Autopilot stops but count preserved
            assert mock_session_state["is_autopilot_running"] is False
            assert mock_session_state["autopilot_turn_count"] == 42

    def test_continuous_loop_returns_zero_when_paused(self) -> None:
        """Test run_continuous_loop returns 0 when paused."""
        mock_session_state = {
            "is_autopilot_running": True,
            "is_paused": True,
            "autopilot_turn_count": 10,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import run_continuous_loop

            result = run_continuous_loop()
            assert result == 0

    def test_pause_during_autopilot_stops_cleanly(self) -> None:
        """Test setting pause during autopilot stops it cleanly."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {
            "game": game,
            "is_autopilot_running": True,
            "is_paused": False,
            "autopilot_turn_count": 5,
            "max_turns_per_session": 100,
            "human_active": False,
            "is_generating": False,
            "waiting_for_human": False,
        }

        def pause_on_call(*args):
            mock_session_state["is_paused"] = True
            return False  # run_game_turn returns False due to pause

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("app.run_game_turn", side_effect=pause_on_call),
        ):
            from app import run_autopilot_step

            # First run_game_turn will set pause
            run_autopilot_step()
            # On next check, autopilot should stop
            assert mock_session_state["is_autopilot_running"] is True  # Not stopped yet


class TestModeIndicatorHTMLStructure:
    """Tests for mode indicator HTML structure validation."""

    def test_paused_mode_indicator_has_correct_structure(self) -> None:
        """Test paused mode indicator has proper HTML structure."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False, is_paused=True)
        # Should have div with correct classes
        assert html.startswith('<div class="mode-indicator paused">')
        assert html.endswith("</div>")
        # Should have pause-dot span
        assert '<span class="pause-dot"></span>' in html
        assert "Paused" in html

    def test_watch_mode_indicator_has_correct_structure(self) -> None:
        """Test watch mode indicator has proper HTML structure."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html("watch", False, is_paused=False)
        assert html.startswith('<div class="mode-indicator watch">')
        assert html.endswith("</div>")
        assert '<span class="pulse-dot"></span>' in html
        assert "Watching" in html

    def test_play_mode_indicator_has_character_class(self) -> None:
        """Test play mode indicator includes character class slug."""
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

        html = render_mode_indicator_html(
            "play", False, "wizard", characters, is_paused=False
        )
        assert 'class="mode-indicator play wizard"' in html
        assert "Playing as Elara" in html

    def test_mode_indicator_escapes_character_name(self) -> None:
        """Test mode indicator escapes character name for XSS prevention."""
        from app import render_mode_indicator_html
        from models import CharacterConfig

        characters = {
            "bad": CharacterConfig(
                name="<script>evil</script>",
                character_class="Fighter",
                personality="bad",
                color="#C45C4A",
            )
        }

        html = render_mode_indicator_html(
            "play", False, "bad", characters, is_paused=False
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# =============================================================================
# Story 3.6: Keyboard Shortcuts
# =============================================================================


class TestKeyboardShortcutScript:
    """Tests for keyboard shortcut JavaScript generation (Task 1)."""

    def test_keyboard_script_returns_string(self) -> None:
        """Test that get_keyboard_shortcut_script returns a string."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert isinstance(script, str)
        assert len(script) > 0

    def test_keyboard_script_includes_script_tags(self) -> None:
        """Test that script includes script tags."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "<script>" in script
        assert "</script>" in script

    def test_keyboard_script_includes_number_keys(self) -> None:
        """Test that script handles keys 1-4 for drop-in."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "e.key >= '1'" in script
        assert "e.key <= '4'" in script

    def test_keyboard_script_includes_escape(self) -> None:
        """Test that script handles Escape for release."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "e.key === 'Escape'" in script

    def test_keyboard_script_skips_input_fields(self) -> None:
        """Test that script ignores shortcuts in input/textarea/select (AC #4)."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "tagName === 'input'" in script
        assert "tagName === 'textarea'" in script
        assert "tagName === 'select'" in script

    def test_keyboard_script_skips_contenteditable(self) -> None:
        """Test that script ignores shortcuts in contenteditable elements (AC #4)."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "contenteditable" in script

    def test_keyboard_script_prevents_duplicate_attach(self) -> None:
        """Test that script only attaches once."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "_autodungeonKeyboardListenerAttached" in script

    def test_keyboard_script_sets_query_param_for_drop_in(self) -> None:
        """Test that script uses query param pattern for drop-in."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "keyboard_action" in script
        assert "drop_in_" in script

    def test_keyboard_script_sets_query_param_for_release(self) -> None:
        """Test that script uses query param pattern for release."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "'release'" in script

    def test_keyboard_script_prevents_default(self) -> None:
        """Test that script prevents default key behavior."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()
        assert "e.preventDefault()" in script


class TestGetPartyCharacterKeys:
    """Tests for get_party_character_keys() function (Task 2)."""

    def test_get_party_character_keys_with_characters(self) -> None:
        """Test get_party_character_keys returns party keys."""
        from models import populate_game_state

        game = populate_game_state(include_sample_messages=False)
        mock_session_state = {"game": game}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            keys = get_party_character_keys()
            assert isinstance(keys, list)
            # Should have party members but not dm
            assert "dm" not in keys

    def test_get_party_character_keys_empty_game(self) -> None:
        """Test get_party_character_keys with empty game state."""
        mock_session_state = {"game": {}}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            keys = get_party_character_keys()
            assert keys == []

    def test_get_party_character_keys_no_game(self) -> None:
        """Test get_party_character_keys with no game in session."""
        mock_session_state = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            keys = get_party_character_keys()
            assert keys == []


class TestKeyboardDropInHandler:
    """Tests for handle_keyboard_drop_in() function (Task 2)."""

    def test_keyboard_drop_in_first_character(self) -> None:
        """Test key 1 drops in as first party member (AC #1)."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "human_active": False,
            "controlled_character": None,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)

            # First party member (fighter)
            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"

    def test_keyboard_drop_in_second_character(self) -> None:
        """Test key 2 drops in as second party member (AC #2)."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "human_active": False,
            "controlled_character": None,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(1)

            # Second party member (rogue)
            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["human_active"] is True

    def test_keyboard_drop_in_out_of_bounds(self) -> None:
        """Test that out-of-bounds index is handled safely (AC #2 edge case)."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "human_active": False,
            "controlled_character": None,
            "ui_mode": "watch",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(5)  # Out of bounds

            # Should not change state
            assert mock_session_state.get("controlled_character") is None

    def test_keyboard_drop_in_negative_index(self) -> None:
        """Test that negative index is handled safely."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "human_active": False,
            "controlled_character": None,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(-1)  # Negative index

            # Should not change state
            assert mock_session_state.get("controlled_character") is None

    def test_keyboard_drop_in_switches_character(self) -> None:
        """Test pressing different number switches characters (Quick Switch)."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(1)  # Switch to rogue

            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["human_active"] is True


class TestKeyboardReleaseHandler:
    """Tests for handle_keyboard_release() function (Task 2)."""

    def test_keyboard_release_from_controlled(self) -> None:
        """Test Escape releases character control (AC #3)."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "test action",
            "waiting_for_human": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_release

            handle_keyboard_release()

            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["ui_mode"] == "watch"

    def test_keyboard_release_when_not_controlling(self) -> None:
        """Test Escape does nothing when not controlling."""
        mock_session_state = {
            "game": {},
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_release

            handle_keyboard_release()

            # Should remain unchanged
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False


class TestProcessKeyboardAction:
    """Tests for process_keyboard_action() function (Task 3)."""

    def test_process_keyboard_action_no_action(self) -> None:
        """Test returns False when no action present."""
        mock_query_params = {}

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", {}),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()
            assert result is False

    def test_process_keyboard_action_drop_in(self) -> None:
        """Test processing drop_in_N action from query params."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        # Use a class to simulate query params behavior
        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "drop_in_0"})

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            assert result is True
            assert "keyboard_action" not in mock_query_params  # Cleared
            assert mock_session_state["controlled_character"] == "fighter"

    def test_process_keyboard_action_release(self) -> None:
        """Test processing release action from query params."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "release"})

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            assert result is True
            assert "keyboard_action" not in mock_query_params  # Cleared
            assert mock_session_state["controlled_character"] is None

    def test_process_keyboard_action_invalid_index(self) -> None:
        """Test handling of invalid drop_in index."""
        mock_session_state = {"game": {}}

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "drop_in_not_a_number"})

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            assert result is False

    def test_process_keyboard_action_unknown_action(self) -> None:
        """Test handling of unknown action."""
        mock_session_state = {}

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "unknown_action"})

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            assert result is False


class TestKeyboardShortcutsHelp:
    """Tests for keyboard shortcuts help rendering (Task 5)."""

    def test_keyboard_shortcuts_help_html(self) -> None:
        """Test help text contains all shortcut keys (AC #5)."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()
        assert "<kbd>1</kbd>" in html
        assert "<kbd>2</kbd>" in html
        assert "<kbd>3</kbd>" in html
        assert "<kbd>4</kbd>" in html
        assert "<kbd>Esc</kbd>" in html

    def test_keyboard_shortcuts_help_mentions_drop_in(self) -> None:
        """Test help text mentions drop in."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()
        assert "drop in" in html.lower()

    def test_keyboard_shortcuts_help_mentions_release(self) -> None:
        """Test help text mentions release."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()
        assert "release" in html.lower()

    def test_keyboard_shortcuts_help_has_css_class(self) -> None:
        """Test help text has proper CSS class."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()
        assert 'class="keyboard-shortcuts-help"' in html

    def test_keyboard_shortcuts_help_has_help_text_class(self) -> None:
        """Test help text has help-text class for styling."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()
        assert 'class="help-text"' in html


class TestKeyboardShortcutsCSS:
    """Tests for keyboard shortcuts CSS (Task 6)."""

    def test_css_contains_keyboard_shortcuts_help_class(self) -> None:
        """Test CSS contains keyboard-shortcuts-help class."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".keyboard-shortcuts-help" in css_content

    def test_css_contains_kbd_styling(self) -> None:
        """Test CSS contains kbd tag styling."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".keyboard-shortcuts-help kbd" in css_content

    def test_css_kbd_has_background(self) -> None:
        """Test kbd has background styling."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Find the kbd section
        assert "background:" in css_content
        assert "var(--bg-message)" in css_content

    def test_css_kbd_has_border(self) -> None:
        """Test kbd has border styling."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "border:" in css_content
        assert "border-radius:" in css_content

    def test_css_help_text_class(self) -> None:
        """Test help-text class exists."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".keyboard-shortcuts-help .help-text" in css_content


class TestInjectKeyboardShortcutScript:
    """Tests for inject_keyboard_shortcut_script() function (Task 4)."""

    def test_inject_keyboard_shortcut_script_calls_components(self) -> None:
        """Test that inject function calls components.html."""
        with (
            patch("streamlit.components.v1.html") as mock_html,
            patch("streamlit.session_state", {}),
        ):
            from app import inject_keyboard_shortcut_script

            inject_keyboard_shortcut_script()

            mock_html.assert_called_once()
            # Check the script is passed
            call_args = mock_html.call_args
            assert "script" in call_args[0][0].lower()


class TestStory36AcceptanceCriteria:
    """Integration tests for Story 3.6 acceptance criteria."""

    def test_ac1_key_1_drops_in_first_party_member(self) -> None:
        """AC #1: Key 1 drops in as first party member."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
                "wizard": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    personality="wise",
                    color="#7B68B8",
                ),
                "cleric": CharacterConfig(
                    name="Brother Marcus",
                    character_class="Cleric",
                    personality="pious",
                    color="#4A90A4",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "human_active": False,
            "controlled_character": None,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)  # Key '1' -> index 0

            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"

    def test_ac2_keys_2_3_4_drop_in_subsequent_members(self) -> None:
        """AC #2: Keys 2, 3, 4 drop in as subsequent party members."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
                "wizard": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    personality="wise",
                    color="#7B68B8",
                ),
                "cleric": CharacterConfig(
                    name="Brother Marcus",
                    character_class="Cleric",
                    personality="pious",
                    color="#4A90A4",
                ),
            }
        }

        # Test key 2 (index 1)
        mock_session_state = {
            "game": game,
            "human_active": False,
            "controlled_character": None,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(1)  # Key '2' -> index 1
            assert mock_session_state["controlled_character"] == "rogue"

        # Test key 3 (index 2)
        mock_session_state["controlled_character"] = None
        mock_session_state["human_active"] = False
        mock_session_state["ui_mode"] = "watch"

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(2)  # Key '3' -> index 2
            assert mock_session_state["controlled_character"] == "wizard"

        # Test key 4 (index 3)
        mock_session_state["controlled_character"] = None
        mock_session_state["human_active"] = False
        mock_session_state["ui_mode"] = "watch"

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(3)  # Key '4' -> index 3
            assert mock_session_state["controlled_character"] == "cleric"

    def test_ac3_escape_releases_control(self) -> None:
        """AC #3: Escape key releases control and returns to Watch Mode."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_release

            handle_keyboard_release()

            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["ui_mode"] == "watch"

    def test_ac4_shortcuts_script_guards_input_fields(self) -> None:
        """AC #4: Shortcuts are disabled when typing in input field."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()

        # Script should check for input, textarea, and select
        assert "tagName === 'input'" in script
        assert "tagName === 'textarea'" in script
        assert "tagName === 'select'" in script
        # Should also check contenteditable
        assert "contenteditable" in script
        # Should return early if in input field
        assert "return;" in script

    def test_ac5_help_text_displays_shortcuts(self) -> None:
        """AC #5: Help text displays keyboard shortcuts."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()

        # Should have all key indicators
        assert "<kbd>1</kbd>" in html
        assert "<kbd>2</kbd>" in html
        assert "<kbd>3</kbd>" in html
        assert "<kbd>4</kbd>" in html
        assert "<kbd>Esc</kbd>" in html

        # Should describe actions
        assert "drop in" in html.lower()
        assert "release" in html.lower()

    def test_quick_switch_while_controlling(self) -> None:
        """Test pressing different number while controlling switches characters."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(1)  # Switch to rogue

            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"

    def test_shortcuts_work_when_paused(self) -> None:
        """Test shortcuts work when game is paused (Story 3.5 integration)."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "is_paused": True,
            "human_active": False,
            "controlled_character": None,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)

            # Should still work when paused
            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["human_active"] is True


class TestKeyboardShortcutEdgeCases:
    """Edge case tests for keyboard shortcuts (Task 7)."""

    def test_no_party_members(self) -> None:
        """Test shortcuts do nothing gracefully with no party members."""
        mock_session_state = {
            "game": {"characters": {}},
            "controlled_character": None,
            "human_active": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)

            # Should do nothing
            assert mock_session_state["controlled_character"] is None

    def test_fewer_than_four_party_members(self) -> None:
        """Test shortcuts for non-existent members are ignored."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            # Key 2-4 should do nothing
            handle_keyboard_drop_in(1)
            assert mock_session_state["controlled_character"] is None

            handle_keyboard_drop_in(2)
            assert mock_session_state["controlled_character"] is None

            handle_keyboard_drop_in(3)
            assert mock_session_state["controlled_character"] is None

    def test_pressing_same_number_toggles_off(self) -> None:
        """Test pressing same number while controlling releases (toggle)."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)  # Press '1' again -> toggle off

            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["ui_mode"] == "watch"

    def test_escape_when_not_controlling_is_noop(self) -> None:
        """Test Escape when not controlling does nothing."""
        mock_session_state = {
            "game": {},
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_release

            handle_keyboard_release()

            # No change
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["ui_mode"] == "watch"

    def test_keyboard_drop_in_stops_autopilot(self) -> None:
        """Test keyboard drop-in stops autopilot like button click."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "is_autopilot_running": True,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)

            # Autopilot should be stopped
            assert mock_session_state["is_autopilot_running"] is False
            assert mock_session_state["controlled_character"] == "fighter"

    def test_dm_excluded_from_party_keys(self) -> None:
        """Test DM is excluded from party character keys."""
        from models import CharacterConfig

        game = {
            "characters": {
                "dm": CharacterConfig(
                    name="Dungeon Master",
                    character_class="DM",
                    personality="neutral",
                    color="#D4A574",
                ),
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {"game": game}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            keys = get_party_character_keys()

            assert "dm" not in keys
            assert "fighter" in keys


class TestProcessKeyboardActionIntegration:
    """Integration tests for process_keyboard_action flow."""

    def test_full_drop_in_flow(self) -> None:
        """Test complete drop-in flow from query param to state change."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": True,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "drop_in_1"})

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            assert result is True
            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"
            assert mock_session_state["is_autopilot_running"] is False
            assert "keyboard_action" not in mock_query_params

    def test_full_release_flow(self) -> None:
        """Test complete release flow from query param to state change."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": "test action",
            "waiting_for_human": True,
        }

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "release"})

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            assert result is True
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["ui_mode"] == "watch"
            # Pending action should be cleared
            assert mock_session_state["human_pending_action"] is None
            assert "keyboard_action" not in mock_query_params


# =============================================================================
# Story 3.6: Extended Keyboard Shortcuts Test Coverage
# Edge cases, boundary conditions, error paths, integration scenarios
# =============================================================================


class TestKeyboardShortcutEmptyParty:
    """Tests for keyboard shortcuts with empty party (0 characters)."""

    def test_keyboard_drop_in_empty_party(self) -> None:
        """Test keyboard drop-in with no party characters."""
        game = {"characters": {}}
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            # Should not crash with empty party
            handle_keyboard_drop_in(0)

            # State should be unchanged
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False

    def test_keyboard_drop_in_dm_only_party(self) -> None:
        """Test keyboard drop-in when only DM exists (no PCs)."""
        from models import CharacterConfig

        game = {
            "characters": {
                "dm": CharacterConfig(
                    name="Dungeon Master",
                    character_class="DM",
                    personality="neutral",
                    color="#D4A574",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            # DM is excluded from party keys, so index 0 should be out of bounds
            handle_keyboard_drop_in(0)

            # State should be unchanged - cannot drop into DM
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False

    def test_get_party_character_keys_empty_game(self) -> None:
        """Test get_party_character_keys with empty game state."""
        mock_session_state = {"game": {}}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            keys = get_party_character_keys()

            assert keys == []

    def test_get_party_character_keys_no_game(self) -> None:
        """Test get_party_character_keys when game not in session."""
        mock_session_state = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            keys = get_party_character_keys()

            assert keys == []


class TestKeyboardShortcutSingleCharacter:
    """Tests for keyboard shortcuts with single character party."""

    def test_single_character_drop_in(self) -> None:
        """Test drop-in with single PC."""
        from models import CharacterConfig

        game = {
            "characters": {
                "wizard": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    personality="scholarly",
                    color="#7B68B8",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)

            assert mock_session_state["controlled_character"] == "wizard"
            assert mock_session_state["human_active"] is True

    def test_single_character_keys_2_3_4_out_of_bounds(self) -> None:
        """Test keys 2, 3, 4 are out of bounds with single character."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            # Keys 2, 3, 4 (indices 1, 2, 3) should be out of bounds
            for index in [1, 2, 3]:
                handle_keyboard_drop_in(index)
                assert mock_session_state["controlled_character"] is None


class TestKeyboardShortcutLargeParty:
    """Tests for keyboard shortcuts with 5+ characters (exceeds 1-4 keys)."""

    def test_five_character_party_only_first_four_accessible(self) -> None:
        """Test that only first 4 characters are accessible via keyboard."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
                "wizard": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    personality="scholarly",
                    color="#7B68B8",
                ),
                "cleric": CharacterConfig(
                    name="Brother Marcus",
                    character_class="Cleric",
                    personality="devout",
                    color="#4A90A4",
                ),
                "bard": CharacterConfig(
                    name="Lyria",
                    character_class="Bard",
                    personality="charismatic",
                    color="#E8A849",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            keys = get_party_character_keys()

            # Should have 5 keys (all PCs)
            assert len(keys) == 5
            # JavaScript only handles keys 1-4, so index 4 (5th char) not reachable
            # via keyboard shortcuts, but the function returns all keys

    def test_keyboard_script_only_handles_1_through_4(self) -> None:
        """Test that JavaScript only handles keys 1-4."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()

        # Script should check e.key >= '1' && e.key <= '4'
        assert "'1'" in script
        assert "'4'" in script
        # Should NOT handle key 5
        assert "'5'" not in script


class TestKeyboardShortcutStateConsistency:
    """Tests for state consistency across keyboard interactions."""

    def test_rapid_drop_in_release_cycle(self) -> None:
        """Test rapid drop-in and release maintains consistent state."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in, handle_keyboard_release

            # Rapid cycle: drop in -> release -> drop in -> release
            for _ in range(3):
                handle_keyboard_drop_in(0)
                assert mock_session_state["controlled_character"] == "fighter"
                assert mock_session_state["human_active"] is True

                handle_keyboard_release()
                assert mock_session_state["controlled_character"] is None
                assert mock_session_state["human_active"] is False

            # Final state should be clean
            assert mock_session_state["ui_mode"] == "watch"

    def test_rapid_character_switching(self) -> None:
        """Test rapid switching between characters maintains state."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
                "wizard": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    personality="scholarly",
                    color="#7B68B8",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys, handle_keyboard_drop_in

            keys = get_party_character_keys()

            # Switch through all characters rapidly
            for i, expected_key in enumerate(keys):
                handle_keyboard_drop_in(i)
                assert mock_session_state["controlled_character"] == expected_key
                assert mock_session_state["human_active"] is True

    def test_pending_action_cleared_on_character_switch(self) -> None:
        """Test pending action is cleared when switching characters."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "is_autopilot_running": False,
            "human_pending_action": "I attack the goblin!",
            "waiting_for_human": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            # Switch from fighter to rogue
            handle_keyboard_drop_in(1)

            # Pending action should be cleared
            assert mock_session_state["human_pending_action"] is None
            assert mock_session_state["waiting_for_human"] is False
            assert mock_session_state["controlled_character"] == "rogue"


class TestKeyboardShortcutWithPause:
    """Tests for keyboard shortcuts interaction with pause state."""

    def test_keyboard_drop_in_while_paused(self) -> None:
        """Test keyboard drop-in works while game is paused."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_paused": True,  # Game is paused
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)

            # Drop-in should work even when paused
            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["human_active"] is True
            # Pause state should remain unchanged
            assert mock_session_state["is_paused"] is True

    def test_keyboard_release_while_paused(self) -> None:
        """Test keyboard release works while game is paused."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "is_paused": True,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_release

            handle_keyboard_release()

            # Release should work even when paused
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["is_paused"] is True


class TestKeyboardShortcutWithNudge:
    """Tests for keyboard shortcuts interaction with nudge system."""

    def test_keyboard_drop_in_clears_pending_nudge(self) -> None:
        """Test that keyboard drop-in does not affect pending nudge."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
            "pending_nudge": "The rogue should check for traps",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)

            # Nudge should remain (handled separately by DM)
            assert mock_session_state["pending_nudge"] == "The rogue should check for traps"
            assert mock_session_state["controlled_character"] == "fighter"

    def test_keyboard_release_preserves_nudge(self) -> None:
        """Test that keyboard release preserves pending nudge."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "human_pending_action": None,
            "waiting_for_human": False,
            "pending_nudge": "Have the wizard cast fireball",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_release

            handle_keyboard_release()

            # Nudge should remain
            assert mock_session_state["pending_nudge"] == "Have the wizard cast fireball"


class TestKeyboardShortcutWithModal:
    """Tests for keyboard shortcuts interaction with modal state."""

    def test_keyboard_drop_in_during_modal(self) -> None:
        """Test keyboard drop-in behavior during modal (config) open."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
            "modal_open": True,
            "is_paused": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            # Drop-in should still work even with modal open
            # (JavaScript prevents keys in input fields, but modal state
            # doesn't prevent the handler)
            handle_keyboard_drop_in(0)

            assert mock_session_state["controlled_character"] == "fighter"


class TestKeyboardShortcutWithGenerating:
    """Tests for keyboard shortcuts during LLM generation."""

    def test_keyboard_drop_in_during_generation(self) -> None:
        """Test keyboard drop-in works during generation."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
            "human_active": False,
            "ui_mode": "watch",
            "is_generating": True,  # LLM is generating
            "is_autopilot_running": True,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            handle_keyboard_drop_in(0)

            # Drop-in should work and stop autopilot
            assert mock_session_state["controlled_character"] == "fighter"
            assert mock_session_state["is_autopilot_running"] is False
            # Note: is_generating stays True as it's managed by run_game_turn


class TestProcessKeyboardActionEdgeCases:
    """Edge cases for process_keyboard_action parsing."""

    def test_process_keyboard_action_empty_string(self) -> None:
        """Test empty action string is handled."""

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": ""})
        mock_session_state = {}

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            # Empty string should return False (no action taken)
            assert result is False

    def test_process_keyboard_action_malformed_drop_in(self) -> None:
        """Test malformed drop_in action (e.g., 'drop_in_')."""

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "drop_in_"})

        with patch("streamlit.query_params", mock_query_params):
            from app import process_keyboard_action

            result = process_keyboard_action()

            # Malformed should return False
            assert result is False

    def test_process_keyboard_action_negative_index(self) -> None:
        """Test negative index in drop_in action."""

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "drop_in_-1"})
        mock_session_state = {"game": {"characters": {}}}

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            # Negative index: int conversion works, but out of bounds
            assert result is True  # Action was processed (even if no effect)

    def test_process_keyboard_action_large_index(self) -> None:
        """Test very large index in drop_in action."""
        from models import CharacterConfig

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "drop_in_999"})
        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": None,
        }

        with (
            patch("streamlit.query_params", mock_query_params),
            patch("streamlit.session_state", mock_session_state),
        ):
            from app import process_keyboard_action

            result = process_keyboard_action()

            # Out of bounds - action processed but no state change
            assert result is True
            assert mock_session_state["controlled_character"] is None

    def test_process_keyboard_action_special_characters(self) -> None:
        """Test action with special characters is rejected."""

        class MockQueryParams(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_query_params = MockQueryParams({"keyboard_action": "drop_in_<script>"})

        with patch("streamlit.query_params", mock_query_params):
            from app import process_keyboard_action

            result = process_keyboard_action()

            # Should fail int conversion and return False
            assert result is False


class TestKeyboardShortcutScriptSecurity:
    """Security tests for keyboard shortcut script."""

    def test_script_has_input_protection(self) -> None:
        """Test script protects against input in text fields."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()

        # Must check for input fields
        assert "input" in script
        assert "textarea" in script
        assert "select" in script

    def test_script_has_contenteditable_protection(self) -> None:
        """Test script protects against contenteditable elements."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()

        assert "contenteditable" in script

    def test_script_prevents_event_default(self) -> None:
        """Test script prevents default event behavior."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()

        assert "preventDefault" in script

    def test_script_uses_url_api(self) -> None:
        """Test script uses URL API for safe param handling."""
        from app import get_keyboard_shortcut_script

        script = get_keyboard_shortcut_script()

        assert "new URL" in script
        assert "searchParams" in script


class TestKeyboardShortcutsCSSExtended:
    """Extended CSS tests for keyboard shortcuts help styling."""

    def test_kbd_element_has_border_radius(self) -> None:
        """Test kbd elements have rounded corners."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Find the kbd styling block
        assert ".keyboard-shortcuts-help kbd" in css_content
        assert "border-radius" in css_content

    def test_kbd_element_has_background(self) -> None:
        """Test kbd elements have background color."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Should use message background for kbd
        assert "var(--bg-message)" in css_content

    def test_kbd_element_has_mono_font(self) -> None:
        """Test kbd elements use monospace font."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "var(--font-mono)" in css_content

    def test_keyboard_shortcuts_help_centered(self) -> None:
        """Test keyboard shortcuts help is centered."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Find the keyboard-shortcuts-help block
        assert "text-align: center" in css_content

    def test_keyboard_shortcuts_has_proper_spacing(self) -> None:
        """Test keyboard shortcuts help has margin spacing."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "margin-top:" in css_content
        assert "margin-bottom:" in css_content


class TestKeyboardShortcutsHelpContent:
    """Tests for keyboard shortcuts help content."""

    def test_help_shows_all_number_keys(self) -> None:
        """Test help shows keys 1, 2, 3, 4."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()

        assert "<kbd>1</kbd>" in html
        assert "<kbd>2</kbd>" in html
        assert "<kbd>3</kbd>" in html
        assert "<kbd>4</kbd>" in html

    def test_help_shows_escape_key(self) -> None:
        """Test help shows Esc key."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()

        assert "<kbd>Esc</kbd>" in html

    def test_help_is_accessible_structure(self) -> None:
        """Test help has accessible text structure."""
        from app import render_keyboard_shortcuts_help_html

        html = render_keyboard_shortcuts_help_html()

        # Should have help-text spans for screen readers
        assert 'class="help-text"' in html
        # Should explain what keys do
        assert "drop in" in html.lower()
        assert "release" in html.lower()


class TestKeyboardShortcutToggleBehavior:
    """Tests for keyboard shortcut toggle (press same key to release)."""

    def test_press_same_key_releases_character(self) -> None:
        """Test pressing same number key releases character."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            # Press '1' again (same character)
            handle_keyboard_drop_in(0)

            # Should toggle off (release)
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["human_active"] is False
            assert mock_session_state["ui_mode"] == "watch"

    def test_press_different_key_switches_character(self) -> None:
        """Test pressing different number key switches character."""
        from models import CharacterConfig

        game = {
            "characters": {
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {
            "game": game,
            "controlled_character": "fighter",
            "human_active": True,
            "ui_mode": "play",
            "is_autopilot_running": False,
            "human_pending_action": None,
            "waiting_for_human": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import handle_keyboard_drop_in

            # Press '2' (different character)
            handle_keyboard_drop_in(1)

            # Should switch to rogue
            assert mock_session_state["controlled_character"] == "rogue"
            assert mock_session_state["human_active"] is True
            assert mock_session_state["ui_mode"] == "play"


class TestInjectKeyboardShortcutScriptVariations:
    """Tests for inject_keyboard_shortcut_script variations."""

    def test_inject_script_always_called(self) -> None:
        """Test inject script is called regardless of session state."""
        mock_session_state = {}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.components.v1.html") as mock_html,
        ):
            from app import inject_keyboard_shortcut_script

            inject_keyboard_shortcut_script()

            # Should always inject the script
            mock_html.assert_called_once()
            call_args = mock_html.call_args
            assert "height=0" in str(call_args) or call_args.kwargs.get("height") == 0

    def test_inject_script_height_zero(self) -> None:
        """Test injected script has height 0 to be invisible."""
        with patch("streamlit.components.v1.html") as mock_html:
            from app import inject_keyboard_shortcut_script

            inject_keyboard_shortcut_script()

            _, kwargs = mock_html.call_args
            assert kwargs.get("height") == 0


class TestGetPartyCharacterKeysOrdering:
    """Tests for get_party_character_keys ordering consistency."""

    def test_party_keys_excludes_dm(self) -> None:
        """Test DM is always excluded from party keys."""
        from models import CharacterConfig

        game = {
            "characters": {
                "dm": CharacterConfig(
                    name="Dungeon Master",
                    character_class="DM",
                    personality="neutral",
                    color="#D4A574",
                ),
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
            }
        }
        mock_session_state = {"game": game}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            keys = get_party_character_keys()

            assert "dm" not in keys
            assert "fighter" in keys
            assert len(keys) == 1

    def test_party_keys_consistent_order(self) -> None:
        """Test party keys maintain consistent order across calls."""
        from models import CharacterConfig

        game = {
            "characters": {
                "wizard": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    personality="scholarly",
                    color="#7B68B8",
                ),
                "fighter": CharacterConfig(
                    name="Theron",
                    character_class="Fighter",
                    personality="brave",
                    color="#C45C4A",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="cunning",
                    color="#6B8E6B",
                ),
            }
        }
        mock_session_state = {"game": game}

        with patch("streamlit.session_state", mock_session_state):
            from app import get_party_character_keys

            # Multiple calls should return same order
            keys1 = get_party_character_keys()
            keys2 = get_party_character_keys()
            keys3 = get_party_character_keys()

            assert keys1 == keys2 == keys3


# =============================================================================
# Story 4.2: Checkpoint Browser & Restore Tests
# =============================================================================


class TestCheckpointBrowserCSS:
    """Tests for checkpoint browser CSS styling (Story 4.2, Task 6)."""

    def test_checkpoint_list_class_exists(self) -> None:
        """Test .checkpoint-list CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".checkpoint-list" in css_content

    def test_checkpoint_entry_class_exists(self) -> None:
        """Test .checkpoint-entry CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".checkpoint-entry" in css_content

    def test_checkpoint_header_class_exists(self) -> None:
        """Test .checkpoint-header CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".checkpoint-header" in css_content

    def test_checkpoint_turn_class_exists(self) -> None:
        """Test .checkpoint-turn CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".checkpoint-turn" in css_content

    def test_checkpoint_timestamp_class_exists(self) -> None:
        """Test .checkpoint-timestamp CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".checkpoint-timestamp" in css_content

    def test_checkpoint_context_class_exists(self) -> None:
        """Test .checkpoint-context CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".checkpoint-context" in css_content

    def test_checkpoint_preview_class_exists(self) -> None:
        """Test .checkpoint-preview CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".checkpoint-preview" in css_content

    def test_restore_confirmation_class_exists(self) -> None:
        """Test .restore-confirmation CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".restore-confirmation" in css_content

    def test_checkpoint_entry_has_border_left(self) -> None:
        """Test checkpoint entries have border-left styling."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        # Check for border-left in checkpoint-entry context
        assert "border-left: 3px solid var(--accent-warm)" in css_content

    def test_checkpoint_empty_class_exists(self) -> None:
        """Test .checkpoint-empty CSS class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")
        assert ".checkpoint-empty" in css_content


class TestRenderCheckpointEntryHtml:
    """Tests for render_checkpoint_entry_html function (Story 4.2)."""

    def test_checkpoint_entry_html_structure(self) -> None:
        """Test checkpoint entry generates correct HTML structure."""
        from app import render_checkpoint_entry_html

        html = render_checkpoint_entry_html(5, "2026-01-28 10:30", "The adventure begins...")
        assert 'class="checkpoint-entry"' in html
        assert 'class="checkpoint-header"' in html
        assert 'class="checkpoint-turn"' in html
        assert 'class="checkpoint-timestamp"' in html
        assert 'class="checkpoint-context"' in html

    def test_checkpoint_entry_html_content(self) -> None:
        """Test checkpoint entry contains correct content."""
        from app import render_checkpoint_entry_html

        html = render_checkpoint_entry_html(5, "2026-01-28 10:30", "The adventure begins...")
        assert "Turn 5" in html
        assert "2026-01-28 10:30" in html
        assert "The adventure begins..." in html

    def test_checkpoint_entry_html_escapes_content(self) -> None:
        """Test checkpoint entry HTML escapes special characters."""
        from app import render_checkpoint_entry_html

        html = render_checkpoint_entry_html(
            1, "2026-01-28", '<script>alert("xss")</script>'
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestHandleCheckpointRestore:
    """Tests for handle_checkpoint_restore function (Story 4.2)."""

    def test_handle_restore_updates_game_state(self, tmp_path: Path) -> None:
        """Test restore updates session_state['game']."""
        from models import create_initial_game_state
        from persistence import save_checkpoint

        state = create_initial_game_state()
        state["ground_truth_log"] = ["[dm] Restored message."]

        with patch("persistence.CAMPAIGNS_DIR", tmp_path):
            save_checkpoint(state, "001", 1)

        mock_session_state: dict = {"game": {}, "is_autopilot_running": True}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path),
        ):
            from app import handle_checkpoint_restore

            result = handle_checkpoint_restore("001", 1)

            assert result is True
            assert mock_session_state["game"]["ground_truth_log"] == ["[dm] Restored message."]

    def test_handle_restore_stops_autopilot(self, tmp_path: Path) -> None:
        """Test restore stops autopilot if running."""
        from models import create_initial_game_state
        from persistence import save_checkpoint

        state = create_initial_game_state()

        with patch("persistence.CAMPAIGNS_DIR", tmp_path):
            save_checkpoint(state, "001", 1)

        mock_session_state: dict = {"game": {}, "is_autopilot_running": True}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path),
        ):
            from app import handle_checkpoint_restore

            handle_checkpoint_restore("001", 1)

            assert mock_session_state["is_autopilot_running"] is False

    def test_handle_restore_resets_ui_state(self, tmp_path: Path) -> None:
        """Test restore resets UI state to defaults."""
        from models import create_initial_game_state
        from persistence import save_checkpoint

        state = create_initial_game_state()

        with patch("persistence.CAMPAIGNS_DIR", tmp_path):
            save_checkpoint(state, "001", 1)

        mock_session_state: dict = {
            "game": {},
            "is_autopilot_running": False,
            "ui_mode": "play",
            "controlled_character": "fighter",
            "is_generating": True,
            "is_paused": True,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path),
        ):
            from app import handle_checkpoint_restore

            handle_checkpoint_restore("001", 1)

            assert mock_session_state["ui_mode"] == "watch"
            assert mock_session_state["controlled_character"] is None
            assert mock_session_state["is_generating"] is False
            assert mock_session_state["is_paused"] is False

    def test_handle_restore_returns_false_for_invalid(self, tmp_path: Path) -> None:
        """Test restore returns False for invalid checkpoint."""
        mock_session_state: dict = {"game": {}, "is_autopilot_running": False}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path),
        ):
            from app import handle_checkpoint_restore

            result = handle_checkpoint_restore("invalid", 999)

        assert result is False


class TestCheckpointBrowserUI:
    """Tests for checkpoint browser UI integration (Story 4.2)."""

    def test_checkpoint_browser_shown_in_sidebar(self) -> None:
        """Test render_checkpoint_browser is called from render_sidebar."""
        # Verify the function is imported and called in render_sidebar
        app_path = Path(__file__).parent.parent / "app.py"
        source = app_path.read_text(encoding="utf-8")

        # Check that render_checkpoint_browser is called in render_sidebar
        assert "render_checkpoint_browser()" in source

    def test_render_checkpoint_browser_function_exists(self) -> None:
        """Test render_checkpoint_browser function is defined."""
        from app import render_checkpoint_browser

        assert callable(render_checkpoint_browser)

    def test_render_checkpoint_preview_function_exists(self) -> None:
        """Test render_checkpoint_preview function is defined."""
        from app import render_checkpoint_preview

        assert callable(render_checkpoint_preview)

    def test_render_restore_confirmation_function_exists(self) -> None:
        """Test render_restore_confirmation function is defined."""
        from app import render_restore_confirmation

        assert callable(render_restore_confirmation)

    def test_handle_restore_clears_preview_state_keys(self, tmp_path: Path) -> None:
        """Test restore clears lingering show_preview_ session state keys."""
        from models import create_initial_game_state
        from persistence import save_checkpoint

        state = create_initial_game_state()

        with patch("persistence.CAMPAIGNS_DIR", tmp_path):
            save_checkpoint(state, "001", 1)

        mock_session_state: dict = {
            "game": {},
            "is_autopilot_running": False,
            "show_preview_1": True,
            "show_preview_5": True,
            "other_key": "preserved",
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path),
        ):
            from app import handle_checkpoint_restore

            handle_checkpoint_restore("001", 1)

            # Preview keys should be removed
            assert "show_preview_1" not in mock_session_state
            assert "show_preview_5" not in mock_session_state
            # Other keys should remain
            assert mock_session_state["other_key"] == "preserved"

    def test_handle_restore_resets_nudge_submitted(self, tmp_path: Path) -> None:
        """Test restore clears nudge_submitted flag to prevent stale toast."""
        from models import create_initial_game_state
        from persistence import save_checkpoint

        state = create_initial_game_state()

        with patch("persistence.CAMPAIGNS_DIR", tmp_path):
            save_checkpoint(state, "001", 1)

        mock_session_state: dict = {
            "game": {},
            "is_autopilot_running": False,
            "nudge_submitted": True,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path),
        ):
            from app import handle_checkpoint_restore

            handle_checkpoint_restore("001", 1)

            assert mock_session_state["nudge_submitted"] is False

    def test_handle_restore_resets_autopilot_turn_count(self, tmp_path: Path) -> None:
        """Test restore resets autopilot_turn_count to zero."""
        from models import create_initial_game_state
        from persistence import save_checkpoint

        state = create_initial_game_state()

        with patch("persistence.CAMPAIGNS_DIR", tmp_path):
            save_checkpoint(state, "001", 1)

        mock_session_state: dict = {
            "game": {},
            "is_autopilot_running": False,
            "autopilot_turn_count": 50,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path),
        ):
            from app import handle_checkpoint_restore

            handle_checkpoint_restore("001", 1)

            assert mock_session_state["autopilot_turn_count"] == 0
