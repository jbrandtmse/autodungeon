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


class TestAcceptanceCriteria:
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
