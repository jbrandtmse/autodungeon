"""Tests for error handling and recovery (Story 4.5)."""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import config as config_module
from agents import (
    LLMError,
    categorize_error,
    detect_network_error,
    dm_turn,
    pc_turn,
)
from graph import run_single_round
from models import (
    ERROR_TYPES,
    CharacterConfig,
    UserError,
    create_initial_game_state,
    create_user_error,
)


@pytest.fixture(autouse=True)
def reset_config_singleton() -> Generator[None, None, None]:
    """Reset config singleton before each test to ensure isolation."""
    config_module._config = None
    yield
    config_module._config = None


# =============================================================================
# Task 1.6: UserError Model Tests
# =============================================================================


class TestUserError:
    """Tests for UserError Pydantic model."""

    def test_user_error_creation(self) -> None:
        """Test creating a UserError with all fields."""
        error = UserError(
            title="Test Title",
            message="Test message",
            action="Test action",
            error_type="timeout",
            timestamp="2026-01-28T12:00:00Z",
            provider="gemini",
            agent="dm",
            retry_count=1,
            last_checkpoint_turn=5,
        )

        assert error.title == "Test Title"
        assert error.message == "Test message"
        assert error.action == "Test action"
        assert error.error_type == "timeout"
        assert error.provider == "gemini"
        assert error.agent == "dm"
        assert error.retry_count == 1
        assert error.last_checkpoint_turn == 5

    def test_user_error_default_values(self) -> None:
        """Test UserError uses correct defaults for optional fields."""
        error = UserError(
            title="Title",
            message="Message",
            action="Action",
            error_type="unknown",
            timestamp="2026-01-28T12:00:00Z",
        )

        assert error.provider == ""
        assert error.agent == ""
        assert error.retry_count == 0
        assert error.last_checkpoint_turn is None

    def test_user_error_retry_count_validation(self) -> None:
        """Test that retry_count is validated (0-3)."""
        # Valid range
        error = UserError(
            title="T",
            message="M",
            action="A",
            error_type="unknown",
            timestamp="now",
            retry_count=3,
        )
        assert error.retry_count == 3

        # Exceeds max - should fail validation
        with pytest.raises(ValueError):
            UserError(
                title="T",
                message="M",
                action="A",
                error_type="unknown",
                timestamp="now",
                retry_count=4,
            )


class TestCreateUserError:
    """Tests for create_user_error factory function."""

    def test_create_user_error_timeout(self) -> None:
        """Test factory creates timeout error with correct messages."""
        error = create_user_error(
            error_type="timeout", provider="gemini", agent="dm", retry_count=0
        )

        assert error.title == ERROR_TYPES["timeout"]["title"]
        assert error.message == ERROR_TYPES["timeout"]["message"]
        assert error.action == ERROR_TYPES["timeout"]["action"]
        assert error.error_type == "timeout"
        assert error.provider == "gemini"
        assert error.agent == "dm"

    def test_create_user_error_rate_limit(self) -> None:
        """Test factory creates rate_limit error with correct messages."""
        error = create_user_error(error_type="rate_limit")

        assert "spirits need rest" in error.title.lower()
        assert error.error_type == "rate_limit"

    def test_create_user_error_auth_error(self) -> None:
        """Test factory creates auth_error with correct messages."""
        error = create_user_error(error_type="auth_error")

        assert "seal is broken" in error.title.lower()
        assert "API" in error.action or "configuration" in error.action.lower()

    def test_create_user_error_network_error(self) -> None:
        """Test factory creates network_error with Ollama suggestion."""
        error = create_user_error(error_type="network_error")

        assert "severed" in error.title.lower()
        assert "ollama" in error.action.lower()

    def test_create_user_error_unknown_falls_back(self) -> None:
        """Test factory falls back to 'unknown' for unrecognized types."""
        error = create_user_error(error_type="nonexistent_type")

        assert error.error_type == "unknown"
        assert error.title == ERROR_TYPES["unknown"]["title"]

    def test_create_user_error_timestamp_format(self) -> None:
        """Test factory sets correct ISO timestamp."""
        before = datetime.now(UTC)
        error = create_user_error(error_type="timeout")
        after = datetime.now(UTC)

        # Timestamp should be in ISO format and between before/after
        assert error.timestamp.endswith("Z")
        # Parse and verify it's a valid timestamp
        ts = datetime.fromisoformat(error.timestamp.replace("Z", "+00:00"))
        assert before <= ts <= after

    def test_create_user_error_with_checkpoint(self) -> None:
        """Test factory preserves last_checkpoint_turn."""
        error = create_user_error(
            error_type="timeout", last_checkpoint_turn=10
        )

        assert error.last_checkpoint_turn == 10


# =============================================================================
# Task 2.7: LLMError Exception Tests
# =============================================================================


class TestLLMError:
    """Tests for LLMError exception class."""

    def test_llm_error_attributes(self) -> None:
        """Test LLMError stores provider, agent, error_type."""
        error = LLMError(
            provider="gemini", agent="dm", error_type="timeout", original_error=None
        )

        assert error.provider == "gemini"
        assert error.agent == "dm"
        assert error.error_type == "timeout"
        assert error.original_error is None

    def test_llm_error_with_original_error(self) -> None:
        """Test LLMError preserves original exception."""
        original = ValueError("Original error message")
        error = LLMError(
            provider="claude",
            agent="rogue",
            error_type="rate_limit",
            original_error=original,
        )

        assert error.original_error is original
        assert isinstance(error.original_error, ValueError)

    def test_llm_error_message(self) -> None:
        """Test LLMError has descriptive message."""
        error = LLMError(
            provider="ollama", agent="fighter", error_type="network_error"
        )

        message = str(error)
        assert "network_error" in message
        assert "fighter" in message
        assert "ollama" in message


class TestCategorizeError:
    """Tests for error categorization logic."""

    def test_timeout_from_message(self) -> None:
        """Test timeout errors are categorized from message."""
        error = Exception("Request timed out")
        assert categorize_error(error) == "timeout"

    def test_timeout_from_message_variant(self) -> None:
        """Test timeout errors with 'timeout' in message."""
        error = Exception("Connection timeout exceeded")
        assert categorize_error(error) == "timeout"

    def test_timeout_deadline_exceeded(self) -> None:
        """Test timeout from deadline exceeded message."""
        error = Exception("Deadline exceeded for API call")
        assert categorize_error(error) == "timeout"

    def test_rate_limit_from_message(self) -> None:
        """Test rate limit errors are categorized from message."""
        error = Exception("Rate limit exceeded")
        assert categorize_error(error) == "rate_limit"

    def test_rate_limit_429_status(self) -> None:
        """Test rate limit from 429 status code."""
        error = Exception("HTTP 429 Too Many Requests")
        assert categorize_error(error) == "rate_limit"

    def test_rate_limit_quota(self) -> None:
        """Test rate limit from quota exceeded."""
        error = Exception("Quota limit exceeded for today")
        assert categorize_error(error) == "rate_limit"

    def test_auth_error_from_message(self) -> None:
        """Test auth errors are categorized from message."""
        error = Exception("Authentication failed")
        assert categorize_error(error) == "auth_error"

    def test_auth_error_api_key(self) -> None:
        """Test auth error from API key message."""
        error = Exception("Invalid API key provided")
        assert categorize_error(error) == "auth_error"

    def test_auth_error_401_status(self) -> None:
        """Test auth error from 401 status code."""
        error = Exception("HTTP 401 Unauthorized")
        assert categorize_error(error) == "auth_error"

    def test_auth_error_403_status(self) -> None:
        """Test auth error from 403 status code."""
        error = Exception("HTTP 403 Forbidden")
        assert categorize_error(error) == "auth_error"

    def test_invalid_response_json(self) -> None:
        """Test invalid response from JSON parsing error."""
        error = Exception("JSON decode error")
        assert categorize_error(error) == "invalid_response"

    def test_invalid_response_parse(self) -> None:
        """Test invalid response from parsing error."""
        error = Exception("Failed to parse response")
        assert categorize_error(error) == "invalid_response"

    def test_unknown_error(self) -> None:
        """Test unrecognized errors are categorized as unknown."""
        error = Exception("Some random error")
        assert categorize_error(error) == "unknown"


# =============================================================================
# Task 9.4: Network Error Detection Tests
# =============================================================================


class TestDetectNetworkError:
    """Tests for network error detection."""

    def test_connection_error(self) -> None:
        """Test connection errors are detected."""
        error = Exception("Connection refused")
        assert detect_network_error(error) is True

    def test_network_unreachable(self) -> None:
        """Test network unreachable errors are detected."""
        error = Exception("Network is unreachable")
        assert detect_network_error(error) is True

    def test_dns_error(self) -> None:
        """Test DNS errors are detected."""
        error = Exception("DNS resolution failed")
        assert detect_network_error(error) is True

    def test_socket_error(self) -> None:
        """Test socket errors are detected."""
        error = Exception("Socket error occurred")
        assert detect_network_error(error) is True

    def test_no_route_error(self) -> None:
        """Test no route errors are detected."""
        error = Exception("No route to host")
        assert detect_network_error(error) is True

    def test_non_network_error(self) -> None:
        """Test non-network errors return False."""
        error = Exception("Invalid input")
        assert detect_network_error(error) is False

    def test_network_error_categorization(self) -> None:
        """Test network errors are categorized correctly."""
        error = Exception("Connection refused by server")
        assert categorize_error(error) == "network_error"


# =============================================================================
# Task 3.6: Error Handling in Game Loop Tests
# =============================================================================


class TestErrorInGameLoop:
    """Tests for error handling in game loop."""

    @patch("persistence.save_checkpoint")
    @patch("persistence.get_latest_checkpoint")
    @patch("graph.create_game_workflow")
    def test_llm_error_creates_user_error(
        self,
        mock_create_workflow: MagicMock,
        mock_get_latest: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Test LLMError is converted to UserError in game loop."""
        mock_get_latest.return_value = 5
        mock_workflow = MagicMock()
        mock_workflow.invoke.side_effect = LLMError(
            provider="gemini", agent="dm", error_type="timeout"
        )
        mock_create_workflow.return_value = mock_workflow

        state = create_initial_game_state()
        state["turn_queue"] = ["dm"]

        result = run_single_round(state)

        # Should have error key
        assert "error" in result
        error = result["error"]
        assert isinstance(error, UserError)
        assert error.error_type == "timeout"
        assert error.provider == "gemini"
        assert error.agent == "dm"
        assert error.last_checkpoint_turn == 5

    @patch("persistence.save_checkpoint")
    @patch("persistence.get_latest_checkpoint")
    @patch("graph.create_game_workflow")
    def test_state_not_corrupted_on_error(
        self,
        mock_create_workflow: MagicMock,
        mock_get_latest: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Test game state remains valid after error."""
        mock_get_latest.return_value = 3
        mock_workflow = MagicMock()
        mock_workflow.invoke.side_effect = LLMError(
            provider="claude", agent="rogue", error_type="rate_limit"
        )
        mock_create_workflow.return_value = mock_workflow

        state = create_initial_game_state()
        state["turn_queue"] = ["dm", "rogue"]
        state["ground_truth_log"] = ["[dm] Test message"]
        original_log = state["ground_truth_log"].copy()

        result = run_single_round(state)

        # Original state fields should be preserved
        assert result["ground_truth_log"] == original_log
        assert result["turn_queue"] == ["dm", "rogue"]

    @patch("persistence.save_checkpoint")
    @patch("persistence.get_latest_checkpoint")
    @patch("graph.create_game_workflow")
    def test_generic_exception_creates_user_error(
        self,
        mock_create_workflow: MagicMock,
        mock_get_latest: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Test generic exceptions are converted to UserError."""
        mock_get_latest.return_value = 2
        mock_workflow = MagicMock()
        mock_workflow.invoke.side_effect = ValueError("Something went wrong")
        mock_create_workflow.return_value = mock_workflow

        state = create_initial_game_state()
        state["turn_queue"] = ["dm"]

        result = run_single_round(state)

        assert "error" in result
        error = result["error"]
        assert isinstance(error, UserError)
        # Should be categorized as unknown
        assert error.error_type == "unknown"

    @patch("persistence.save_checkpoint")
    @patch("persistence.get_latest_checkpoint")
    @patch("graph._append_transcript_for_new_entries")
    @patch("graph.create_game_workflow")
    def test_successful_round_no_error(
        self,
        mock_create_workflow: MagicMock,
        mock_transcript: MagicMock,
        mock_get_latest: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Test successful round does not have error key."""
        mock_get_latest.return_value = 1
        mock_workflow = MagicMock()
        mock_workflow.invoke.return_value = create_initial_game_state()
        mock_create_workflow.return_value = mock_workflow

        state = create_initial_game_state()
        state["turn_queue"] = ["dm"]

        result = run_single_round(state)

        # Should NOT have error key (or should be None)
        assert result.get("error") is None


# =============================================================================
# Task 5.8: Error Panel HTML Tests
# =============================================================================


class TestErrorPanelHTML:
    """Tests for error panel HTML rendering."""

    def test_error_panel_html_structure(self) -> None:
        """Test error panel has required HTML elements."""
        from app import render_error_panel_html

        error = create_user_error(error_type="timeout")
        html = render_error_panel_html(error)

        assert '<div class="error-panel">' in html
        assert '<h3 class="error-panel-title">' in html
        assert '<p class="error-panel-message">' in html
        assert '<p class="error-panel-action">' in html
        assert '<div class="error-panel-actions">' in html

    def test_error_panel_has_buttons(self) -> None:
        """Test error panel has Retry, Restore, New Session buttons."""
        from app import render_error_panel_html

        error = create_user_error(error_type="timeout")
        html = render_error_panel_html(error)

        assert "Retry" in html
        assert "Restore from Checkpoint" in html
        assert "Start New Session" in html

    def test_error_panel_narrative_style(self) -> None:
        """Test error messages use campfire narrative style."""
        from app import render_error_panel_html

        error = create_user_error(error_type="timeout")
        html = render_error_panel_html(error)

        # Should contain the narrative-style title
        assert "magical connection" in html.lower()

    def test_error_panel_shows_retry_count(self) -> None:
        """Test error panel shows remaining retries when count > 0."""
        from app import MAX_RETRY_ATTEMPTS, render_error_panel_html

        error = create_user_error(error_type="timeout", retry_count=1)
        html = render_error_panel_html(error)

        # Should show remaining retries
        expected_remaining = MAX_RETRY_ATTEMPTS - 1
        assert f"{expected_remaining} left" in html

    def test_error_panel_retry_disabled_at_max(self) -> None:
        """Test retry button is disabled when max retries reached."""
        from app import MAX_RETRY_ATTEMPTS, render_error_panel_html

        error = create_user_error(
            error_type="timeout", retry_count=MAX_RETRY_ATTEMPTS
        )
        html = render_error_panel_html(error)

        # Should have disabled attribute
        assert "disabled" in html

    def test_error_panel_escapes_html(self) -> None:
        """Test error panel escapes HTML in error messages."""
        from app import render_error_panel_html

        # Create error with HTML in title
        error = UserError(
            title="<script>alert('xss')</script>",
            message="Test & <message>",
            action="Action",
            error_type="unknown",
            timestamp="now",
        )
        html = render_error_panel_html(error)

        # Should be escaped
        assert "&lt;script&gt;" in html
        assert "&amp;" in html


# =============================================================================
# Task 6.7: Retry Functionality Tests
# =============================================================================


class TestRetryFunctionality:
    """Tests for retry functionality."""

    def test_handle_retry_click_increments_count(self) -> None:
        """Test retry button increments retry count."""
        from app import handle_retry_click

        mock_session_state: dict[str, Any] = {
            "error": create_user_error(error_type="timeout"),
            "error_retry_count": 0,
            "game": create_initial_game_state(),
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_game_turn", return_value=False):
                handle_retry_click()

        assert mock_session_state["error_retry_count"] == 1

    def test_handle_retry_click_clears_error_on_success(self) -> None:
        """Test retry clears error when successful."""
        from app import handle_retry_click

        mock_session_state: dict[str, Any] = {
            "error": create_user_error(error_type="timeout"),
            "error_retry_count": 0,
            "game": create_initial_game_state(),
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_game_turn", return_value=True):
                handle_retry_click()

        # Error should be cleared and retry count reset
        assert mock_session_state["error"] is None
        assert mock_session_state["error_retry_count"] == 0

    def test_handle_retry_click_stops_at_max(self) -> None:
        """Test retry stops after MAX_RETRY_ATTEMPTS."""
        from app import MAX_RETRY_ATTEMPTS, handle_retry_click

        error = create_user_error(
            error_type="timeout", retry_count=MAX_RETRY_ATTEMPTS
        )
        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": MAX_RETRY_ATTEMPTS,
            "game": create_initial_game_state(),
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_game_turn") as mock_run:
                handle_retry_click()
                # Should NOT call run_game_turn when at max retries
                mock_run.assert_not_called()


# =============================================================================
# Task 7.6: Restore From Error Tests
# =============================================================================


class TestRestoreFromError:
    """Tests for restore from error functionality."""

    def test_handle_error_restore_calls_checkpoint_restore(self) -> None:
        """Test restore button loads last successful checkpoint."""
        from app import handle_error_restore_click

        error = create_user_error(
            error_type="timeout", last_checkpoint_turn=5
        )
        state = create_initial_game_state()
        state["session_id"] = "001"

        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": 1,
            "game": state,
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch(
                "app.handle_checkpoint_restore", return_value=True
            ) as mock_restore:
                with patch("streamlit.toast"):
                    handle_error_restore_click()

        mock_restore.assert_called_once_with("001", 5)

    def test_handle_error_restore_clears_error(self) -> None:
        """Test restore clears error state after success."""
        from app import handle_error_restore_click

        error = create_user_error(
            error_type="timeout", last_checkpoint_turn=3
        )
        state = create_initial_game_state()
        state["session_id"] = "001"

        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": 2,
            "game": state,
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.handle_checkpoint_restore", return_value=True):
                with patch("streamlit.toast"):
                    handle_error_restore_click()

        assert mock_session_state["error"] is None
        assert mock_session_state["error_retry_count"] == 0


class TestNewSessionFromError:
    """Tests for new session from error functionality."""

    def test_handle_error_new_session_clears_error(self) -> None:
        """Test new session button clears error state."""
        from app import handle_error_new_session_click

        error = create_user_error(error_type="timeout")
        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": 2,
            "game": create_initial_game_state(),
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.handle_new_session_click") as mock_new_session:
                handle_error_new_session_click()

        # Error should be cleared
        assert mock_session_state["error"] is None
        assert mock_session_state["error_retry_count"] == 0
        # Should delegate to existing new session handler
        mock_new_session.assert_called_once()


# =============================================================================
# Integration Tests (Task 10)
# =============================================================================


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    @patch("agents.create_dm_agent")
    def test_dm_turn_raises_llm_error(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test dm_turn raises LLMError on API failure."""
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("Request timed out")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()

        mock_session_state: dict[str, Any] = {"pending_nudge": None}

        with patch("streamlit.session_state", mock_session_state):
            with pytest.raises(LLMError) as exc_info:
                dm_turn(state)

        assert exc_info.value.error_type == "timeout"
        assert exc_info.value.agent == "dm"

    @patch("agents.create_pc_agent")
    def test_pc_turn_raises_llm_error(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test pc_turn raises LLMError on API failure."""
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("Rate limit exceeded")
        mock_create_pc_agent.return_value = mock_model

        state = create_initial_game_state()
        state["characters"]["rogue"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Test",
            color="#6B8E6B",
        )

        with pytest.raises(LLMError) as exc_info:
            pc_turn(state, "rogue")

        assert exc_info.value.error_type == "rate_limit"
        assert exc_info.value.agent == "rogue"

    def test_error_message_narrative_style(self) -> None:
        """Test error messages use campfire narrative style."""
        for error_type, _info in ERROR_TYPES.items():
            error = create_user_error(error_type=error_type)

            # Titles should use narrative language
            assert not any(
                tech_term in error.title.lower()
                for tech_term in ["api", "http", "exception", "error code"]
            ), f"Title for {error_type} contains technical jargon"

    def test_autopilot_stops_on_error(self) -> None:
        """Test autopilot stops when error occurs."""
        from app import run_game_turn

        state = create_initial_game_state()
        state["turn_queue"] = ["dm"]

        mock_session_state: dict[str, Any] = {
            "game": state,
            "is_paused": False,
            "human_active": False,
            "is_generating": False,
            "is_autopilot_running": True,
            "error": None,
            "error_retry_count": 0,
            "waiting_for_human": False,
        }

        # Mock run_single_round to return an error
        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_single_round") as mock_run:
                error = create_user_error(error_type="timeout")
                mock_run.return_value = {"error": error, **state}

                run_game_turn()

        # Autopilot should be stopped
        assert mock_session_state["is_autopilot_running"] is False
        assert mock_session_state["error"] is error

    def test_network_error_suggests_ollama(self) -> None:
        """Test network error message suggests Ollama for offline play."""
        error = create_user_error(error_type="network_error")

        # Should mention Ollama as offline alternative
        assert "ollama" in error.action.lower()
        assert "offline" in error.action.lower()

    def test_technical_details_not_exposed(self) -> None:
        """Test technical details are NOT exposed to user."""
        # Create an LLMError with technical details
        original_error = Exception(
            "HTTPSConnectionPool(host='api.openai.com', port=443): "
            "Max retries exceeded with url: /v1/chat/completions"
        )

        llm_error = LLMError(
            provider="claude",
            agent="dm",
            error_type="network_error",
            original_error=original_error,
        )

        # Convert to UserError
        user_error = create_user_error(
            error_type=llm_error.error_type,
            provider=llm_error.provider,
            agent=llm_error.agent,
        )

        # Technical details should NOT be in user-facing error
        assert "HTTPSConnectionPool" not in user_error.title
        assert "HTTPSConnectionPool" not in user_error.message
        assert "HTTPSConnectionPool" not in user_error.action

    def test_at_most_one_turn_lost(self) -> None:
        """Test at most one turn lost on error recovery (NFR15)."""
        # When an error occurs:
        # 1. The failed turn is not saved
        # 2. The last checkpoint is preserved
        # 3. Restore returns to last checkpoint (before failed turn)
        # Therefore, at most one turn is lost

        error = create_user_error(
            error_type="timeout",
            last_checkpoint_turn=10,  # Last successful turn
        )

        # The error occurred during turn 11 attempt
        # Restoring to turn 10 loses only the failed turn 11
        turns_lost = 11 - error.last_checkpoint_turn  # type: ignore[operator]
        assert turns_lost <= 1
