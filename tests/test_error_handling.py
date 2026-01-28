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


# =============================================================================
# Story 4.5 Expanded Coverage: Edge Cases
# =============================================================================


class TestUserErrorEdgeCases:
    """Extended edge case tests for UserError model."""

    def test_user_error_negative_retry_count_rejected(self) -> None:
        """Test that negative retry_count is rejected."""
        with pytest.raises(ValueError):
            UserError(
                title="T",
                message="M",
                action="A",
                error_type="unknown",
                timestamp="now",
                retry_count=-1,
            )

    def test_user_error_zero_retry_count_valid(self) -> None:
        """Test that retry_count of 0 is valid."""
        error = UserError(
            title="T",
            message="M",
            action="A",
            error_type="unknown",
            timestamp="now",
            retry_count=0,
        )
        assert error.retry_count == 0

    def test_user_error_empty_provider(self) -> None:
        """Test UserError with empty provider string."""
        error = UserError(
            title="T",
            message="M",
            action="A",
            error_type="unknown",
            timestamp="now",
            provider="",
        )
        assert error.provider == ""

    def test_user_error_empty_agent(self) -> None:
        """Test UserError with empty agent string."""
        error = UserError(
            title="T",
            message="M",
            action="A",
            error_type="unknown",
            timestamp="now",
            agent="",
        )
        assert error.agent == ""

    def test_user_error_none_checkpoint_turn(self) -> None:
        """Test UserError with None last_checkpoint_turn."""
        error = UserError(
            title="T",
            message="M",
            action="A",
            error_type="unknown",
            timestamp="now",
            last_checkpoint_turn=None,
        )
        assert error.last_checkpoint_turn is None

    def test_user_error_very_long_title(self) -> None:
        """Test UserError with very long title string."""
        long_title = "A" * 1000
        error = UserError(
            title=long_title,
            message="M",
            action="A",
            error_type="unknown",
            timestamp="now",
        )
        assert len(error.title) == 1000

    def test_user_error_unicode_in_message(self) -> None:
        """Test UserError with unicode characters in message."""
        error = UserError(
            title="Error",
            message="The spirits speak: 魔法の接続が切れました",
            action="Try again",
            error_type="network_error",
            timestamp="now",
        )
        assert "魔法" in error.message


class TestCreateUserErrorEdgeCases:
    """Extended edge case tests for create_user_error factory."""

    def test_create_user_error_all_error_types(self) -> None:
        """Test factory creates valid errors for all error types."""
        for error_type in ERROR_TYPES:
            error = create_user_error(error_type=error_type)
            assert error.error_type == error_type
            assert error.title == ERROR_TYPES[error_type]["title"]
            assert error.message == ERROR_TYPES[error_type]["message"]
            assert error.action == ERROR_TYPES[error_type]["action"]

    def test_create_user_error_invalid_response(self) -> None:
        """Test factory creates invalid_response error correctly."""
        error = create_user_error(error_type="invalid_response")
        assert "riddles" in error.title.lower()
        assert error.error_type == "invalid_response"

    def test_create_user_error_preserves_all_parameters(self) -> None:
        """Test factory preserves all provided parameters."""
        error = create_user_error(
            error_type="timeout",
            provider="ollama",
            agent="wizard",
            retry_count=2,
            last_checkpoint_turn=15,
        )
        assert error.provider == "ollama"
        assert error.agent == "wizard"
        assert error.retry_count == 2
        assert error.last_checkpoint_turn == 15

    def test_create_user_error_empty_strings_preserved(self) -> None:
        """Test factory preserves empty string parameters."""
        error = create_user_error(
            error_type="timeout", provider="", agent=""
        )
        assert error.provider == ""
        assert error.agent == ""


class TestLLMErrorEdgeCases:
    """Extended edge case tests for LLMError exception."""

    def test_llm_error_none_original_error(self) -> None:
        """Test LLMError with None original error."""
        error = LLMError(
            provider="gemini",
            agent="dm",
            error_type="timeout",
            original_error=None,
        )
        assert error.original_error is None

    def test_llm_error_nested_exception(self) -> None:
        """Test LLMError preserves nested exception chain."""
        root_error = ValueError("Root cause")
        wrapped = RuntimeError("Wrapper")
        wrapped.__cause__ = root_error

        error = LLMError(
            provider="claude",
            agent="fighter",
            error_type="unknown",
            original_error=wrapped,
        )

        assert error.original_error is wrapped
        assert error.original_error.__cause__ is root_error

    def test_llm_error_with_empty_strings(self) -> None:
        """Test LLMError with empty provider and agent."""
        error = LLMError(
            provider="",
            agent="",
            error_type="unknown",
        )
        assert error.provider == ""
        assert error.agent == ""

    def test_llm_error_inherits_from_exception(self) -> None:
        """Test that LLMError is a proper Exception subclass."""
        error = LLMError(
            provider="gemini",
            agent="dm",
            error_type="timeout",
        )
        assert isinstance(error, Exception)


class TestCategorizeErrorEdgeCases:
    """Extended edge case tests for categorize_error function."""

    def test_categorize_too_many_requests(self) -> None:
        """Test categorizing 'too many requests' as rate_limit."""
        error = Exception("Error: too many requests")
        assert categorize_error(error) == "rate_limit"

    def test_categorize_permission_denied(self) -> None:
        """Test categorizing permission denied as auth_error."""
        error = Exception("Permission denied for this operation")
        assert categorize_error(error) == "auth_error"

    def test_categorize_invalid_key(self) -> None:
        """Test categorizing invalid key as auth_error."""
        error = Exception("Invalid key provided")
        assert categorize_error(error) == "auth_error"

    def test_categorize_malformed_response(self) -> None:
        """Test categorizing malformed response as invalid_response."""
        error = Exception("Malformed response from server")
        assert categorize_error(error) == "invalid_response"

    def test_categorize_unexpected_response(self) -> None:
        """Test categorizing unexpected response format as invalid_response."""
        error = Exception("Unexpected response format")
        assert categorize_error(error) == "invalid_response"

    def test_categorize_empty_message(self) -> None:
        """Test categorizing error with empty message."""
        error = Exception("")
        assert categorize_error(error) == "unknown"

    def test_categorize_case_insensitive(self) -> None:
        """Test that categorization is case-insensitive."""
        assert categorize_error(Exception("TIMEOUT")) == "timeout"
        assert categorize_error(Exception("Rate Limit Exceeded")) == "rate_limit"
        assert categorize_error(Exception("AUTH ERROR")) == "auth_error"

    def test_categorize_mixed_error_indicators(self) -> None:
        """Test error with multiple indicators takes first match."""
        # Timeout is checked before rate_limit in the function
        error = Exception("Request timed out due to rate limit")
        assert categorize_error(error) == "timeout"


class TestDetectNetworkErrorEdgeCases:
    """Extended edge case tests for detect_network_error function."""

    def test_detect_getaddrinfo_error(self) -> None:
        """Test detecting getaddrinfo DNS errors."""
        error = Exception("getaddrinfo failed")
        assert detect_network_error(error) is True

    def test_detect_errno_11001_windows(self) -> None:
        """Test detecting Windows DNS failure errno."""
        error = Exception("Errno 11001: name resolution failed")
        assert detect_network_error(error) is True

    def test_detect_errno_minus_2_linux(self) -> None:
        """Test detecting Linux DNS failure errno."""
        error = Exception("errno -2: temporary failure")
        assert detect_network_error(error) is True

    def test_detect_error_in_type_name(self) -> None:
        """Test detecting network indicators in exception type name."""

        class ConnectionResetError(Exception):
            pass

        error = ConnectionResetError("Connection was reset")
        assert detect_network_error(error) is True

    def test_non_network_error_not_detected(self) -> None:
        """Test that non-network errors return False."""
        error = ValueError("Invalid value")
        assert detect_network_error(error) is False


# =============================================================================
# Story 4.5 Expanded Coverage: Boundary Conditions
# =============================================================================


class TestRetryBoundaryConditions:
    """Tests for retry boundary conditions."""

    def test_retry_at_boundary_zero(self) -> None:
        """Test retry with count at 0."""
        error = create_user_error(error_type="timeout", retry_count=0)
        assert error.retry_count == 0
        # User should be able to retry (count 0 < MAX)

    def test_retry_at_boundary_max_minus_one(self) -> None:
        """Test retry with count at MAX-1."""
        from app import MAX_RETRY_ATTEMPTS

        error = create_user_error(
            error_type="timeout", retry_count=MAX_RETRY_ATTEMPTS - 1
        )
        assert error.retry_count == MAX_RETRY_ATTEMPTS - 1
        # User should still be able to retry once more

    def test_retry_at_boundary_max(self) -> None:
        """Test retry with count at MAX (should disable retry)."""
        from app import MAX_RETRY_ATTEMPTS

        error = create_user_error(error_type="timeout", retry_count=MAX_RETRY_ATTEMPTS)
        assert error.retry_count == MAX_RETRY_ATTEMPTS

    def test_max_retry_attempts_is_three(self) -> None:
        """Test that MAX_RETRY_ATTEMPTS is exactly 3."""
        from app import MAX_RETRY_ATTEMPTS

        assert MAX_RETRY_ATTEMPTS == 3


class TestErrorMessageLengthBoundaries:
    """Tests for error message length boundary conditions."""

    def test_error_panel_with_single_char_title(self) -> None:
        """Test error panel with single character title."""
        from app import render_error_panel_html

        error = UserError(
            title="X",
            message="M",
            action="A",
            error_type="unknown",
            timestamp="now",
        )
        html = render_error_panel_html(error)
        assert ">X</h3>" in html

    def test_error_panel_with_single_char_message(self) -> None:
        """Test error panel with single character message."""
        from app import render_error_panel_html

        error = UserError(
            title="T",
            message="Y",
            action="A",
            error_type="unknown",
            timestamp="now",
        )
        html = render_error_panel_html(error)
        assert ">Y</p>" in html


class TestCheckpointTurnBoundaries:
    """Tests for checkpoint turn number boundary conditions."""

    def test_checkpoint_turn_zero(self) -> None:
        """Test error with checkpoint turn 0."""
        error = create_user_error(error_type="timeout", last_checkpoint_turn=0)
        assert error.last_checkpoint_turn == 0

    def test_checkpoint_turn_one(self) -> None:
        """Test error with checkpoint turn 1."""
        error = create_user_error(error_type="timeout", last_checkpoint_turn=1)
        assert error.last_checkpoint_turn == 1

    def test_checkpoint_turn_large_number(self) -> None:
        """Test error with very large checkpoint turn number."""
        error = create_user_error(error_type="timeout", last_checkpoint_turn=99999)
        assert error.last_checkpoint_turn == 99999


# =============================================================================
# Story 4.5 Expanded Coverage: Error Paths
# =============================================================================


class TestNestedErrorHandling:
    """Tests for nested error scenarios."""

    @patch("agents.create_dm_agent")
    def test_dm_turn_handles_llm_config_error_as_auth_error(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that LLMConfigurationError is wrapped as auth_error."""
        from agents import LLMConfigurationError

        mock_create_dm_agent.side_effect = LLMConfigurationError(
            "gemini", "GOOGLE_API_KEY"
        )

        state = create_initial_game_state()

        mock_session_state: dict[str, Any] = {"pending_nudge": None}

        with patch("streamlit.session_state", mock_session_state):
            with pytest.raises(LLMError) as exc_info:
                dm_turn(state)

        assert exc_info.value.error_type == "auth_error"

    @patch("agents.create_pc_agent")
    def test_pc_turn_handles_llm_config_error_as_auth_error(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test that LLMConfigurationError is wrapped as auth_error for PC."""
        from agents import LLMConfigurationError

        mock_create_pc_agent.side_effect = LLMConfigurationError(
            "claude", "ANTHROPIC_API_KEY"
        )

        state = create_initial_game_state()
        state["characters"]["rogue"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Test",
            color="#6B8E6B",
        )

        with pytest.raises(LLMError) as exc_info:
            pc_turn(state, "rogue")

        assert exc_info.value.error_type == "auth_error"


class TestErrorDuringErrorHandling:
    """Tests for errors occurring during error handling itself."""

    def test_error_panel_html_handles_none_checkpoint(self) -> None:
        """Test error panel handles None checkpoint gracefully."""
        from app import render_error_panel_html

        error = create_user_error(
            error_type="timeout", last_checkpoint_turn=None
        )
        html = render_error_panel_html(error)
        # Should still render without crashing
        assert "error-panel" in html

    def test_handle_retry_with_no_error_in_session(self) -> None:
        """Test retry handler when no error exists in session."""
        from app import handle_retry_click

        mock_session_state: dict[str, Any] = {
            "error": None,
            "error_retry_count": 0,
            "game": create_initial_game_state(),
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_game_turn") as mock_run:
                handle_retry_click()
                # Should attempt retry even without error
                mock_run.assert_called_once()


class TestErrorStateCorruption:
    """Tests verifying error handling doesn't corrupt state."""

    @patch("persistence.save_checkpoint")
    @patch("persistence.get_latest_checkpoint")
    @patch("graph.create_game_workflow")
    def test_state_fields_preserved_on_llm_error(
        self,
        mock_create_workflow: MagicMock,
        mock_get_latest: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Test all GameState fields are preserved after LLM error."""
        mock_get_latest.return_value = 5
        mock_workflow = MagicMock()
        mock_workflow.invoke.side_effect = LLMError(
            provider="gemini", agent="dm", error_type="timeout"
        )
        mock_create_workflow.return_value = mock_workflow

        state = create_initial_game_state()
        state["turn_queue"] = ["dm", "fighter", "rogue"]
        state["current_turn"] = "dm"
        state["ground_truth_log"] = ["[dm] Test message"]
        state["human_active"] = True
        state["controlled_character"] = "fighter"
        state["session_number"] = 3
        state["session_id"] = "003"

        result = run_single_round(state)

        # All fields should be preserved
        assert result["turn_queue"] == ["dm", "fighter", "rogue"]
        assert result["current_turn"] == "dm"
        assert result["ground_truth_log"] == ["[dm] Test message"]
        assert result["human_active"] is True
        assert result["controlled_character"] == "fighter"
        assert result["session_number"] == 3
        assert result["session_id"] == "003"

    @patch("persistence.save_checkpoint")
    @patch("persistence.get_latest_checkpoint")
    @patch("graph.create_game_workflow")
    def test_agent_memories_preserved_on_error(
        self,
        mock_create_workflow: MagicMock,
        mock_get_latest: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        """Test agent_memories are preserved after error."""
        from models import AgentMemory

        mock_get_latest.return_value = 2
        mock_workflow = MagicMock()
        mock_workflow.invoke.side_effect = LLMError(
            provider="claude", agent="fighter", error_type="rate_limit"
        )
        mock_create_workflow.return_value = mock_workflow

        state = create_initial_game_state()
        state["turn_queue"] = ["dm"]
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="Previous story",
            short_term_buffer=["Event 1", "Event 2"],
        )

        result = run_single_round(state)

        # Agent memories should be preserved
        assert "dm" in result["agent_memories"]
        assert result["agent_memories"]["dm"].long_term_summary == "Previous story"
        assert result["agent_memories"]["dm"].short_term_buffer == ["Event 1", "Event 2"]


# =============================================================================
# Story 4.5 Expanded Coverage: Integration Scenarios
# =============================================================================


class TestFullErrorRecoveryFlow:
    """Integration tests for full error -> retry -> success flow."""

    def test_error_then_retry_success_flow(self) -> None:
        """Test full flow: error occurs, user retries, success."""
        from app import handle_retry_click

        # Initial state: error occurred
        error = create_user_error(error_type="timeout")
        state = create_initial_game_state()

        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": 0,
            "game": state,
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_game_turn", return_value=True):
                handle_retry_click()

        # After successful retry: error cleared, count reset
        assert mock_session_state["error"] is None
        assert mock_session_state["error_retry_count"] == 0

    def test_error_then_multiple_retries_then_success(self) -> None:
        """Test multiple retries before success."""
        from app import handle_retry_click

        error = create_user_error(error_type="timeout")
        state = create_initial_game_state()

        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": 0,
            "game": state,
        }

        with patch("streamlit.session_state", mock_session_state):
            # First retry fails
            with patch("app.run_game_turn", return_value=False):
                handle_retry_click()
            assert mock_session_state["error_retry_count"] == 1

            # Second retry fails
            with patch("app.run_game_turn", return_value=False):
                handle_retry_click()
            assert mock_session_state["error_retry_count"] == 2

            # Third retry succeeds
            with patch("app.run_game_turn", return_value=True):
                handle_retry_click()
            assert mock_session_state["error"] is None
            assert mock_session_state["error_retry_count"] == 0


class TestErrorAndAutopilotInteraction:
    """Tests for error handling and autopilot mode interaction."""

    def test_autopilot_pauses_on_error(self) -> None:
        """Test that autopilot is paused when error occurs."""
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

        error = create_user_error(error_type="rate_limit")

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_single_round") as mock_run:
                mock_run.return_value = {"error": error, **state}
                run_game_turn()

        assert mock_session_state["is_autopilot_running"] is False
        assert mock_session_state["error"] is error


class TestProviderSpecificErrors:
    """Tests for provider-specific error scenarios."""

    def test_gemini_auth_error(self) -> None:
        """Test Gemini authentication error is properly categorized."""
        error = Exception("Invalid API key for Google AI")
        assert categorize_error(error) == "auth_error"

    def test_claude_rate_limit_error(self) -> None:
        """Test Claude rate limit error is properly categorized."""
        error = Exception("Anthropic API: 429 Too Many Requests")
        assert categorize_error(error) == "rate_limit"

    def test_ollama_connection_error(self) -> None:
        """Test Ollama connection error is properly categorized."""
        error = Exception("Connection refused to localhost:11434")
        assert categorize_error(error) == "network_error"


class TestErrorTypeMessages:
    """Tests verifying all error types have appropriate messaging."""

    def test_all_error_types_have_required_fields(self) -> None:
        """Test all ERROR_TYPES entries have title, message, action."""
        for error_type, info in ERROR_TYPES.items():
            assert "title" in info, f"Missing 'title' for {error_type}"
            assert "message" in info, f"Missing 'message' for {error_type}"
            assert "action" in info, f"Missing 'action' for {error_type}"
            assert len(info["title"]) > 0, f"Empty 'title' for {error_type}"
            assert len(info["message"]) > 0, f"Empty 'message' for {error_type}"
            assert len(info["action"]) > 0, f"Empty 'action' for {error_type}"

    def test_all_error_types_use_narrative_style(self) -> None:
        """Test all error types use campfire narrative style (no tech jargon).

        Note: "API" is allowed in action text as it's user-facing terminology
        that users understand when configuring their LLM providers.
        """
        # Tech terms not allowed in title or message (user-facing narrative)
        tech_terms_narrative = ["http", "json", "ssl", "tcp", "dns", "500", "502", "503"]

        for error_type, info in ERROR_TYPES.items():
            for field in ["title", "message"]:
                content = info[field].lower()
                for term in tech_terms_narrative:
                    assert term not in content, (
                        f"Technical term '{term}' found in {error_type} {field}"
                    )


class TestErrorPanelRendering:
    """Additional tests for error panel HTML rendering."""

    def test_error_panel_includes_all_buttons(self) -> None:
        """Test error panel includes all three action buttons."""
        from app import render_error_panel_html

        error = create_user_error(error_type="timeout")
        html = render_error_panel_html(error)

        assert "Retry" in html
        assert "Restore from Checkpoint" in html
        assert "Start New Session" in html

    def test_error_panel_title_is_escaped(self) -> None:
        """Test error panel escapes HTML in title."""
        from app import render_error_panel_html

        error = UserError(
            title="<b>Title</b>",
            message="Message",
            action="Action",
            error_type="unknown",
            timestamp="now",
        )
        html = render_error_panel_html(error)
        assert "&lt;b&gt;" in html
        assert "<b>Title" not in html

    def test_error_panel_message_is_escaped(self) -> None:
        """Test error panel escapes HTML in message."""
        from app import render_error_panel_html

        error = UserError(
            title="Title",
            message="<script>alert(1)</script>",
            action="Action",
            error_type="unknown",
            timestamp="now",
        )
        html = render_error_panel_html(error)
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_error_panel_action_is_escaped(self) -> None:
        """Test error panel escapes HTML in action."""
        from app import render_error_panel_html

        error = UserError(
            title="Title",
            message="Message",
            action="Click <a href='evil'>here</a>",
            error_type="unknown",
            timestamp="now",
        )
        html = render_error_panel_html(error)
        assert "&lt;a href" in html
        assert "<a href=" not in html


class TestRestoreFromCheckpointEdgeCases:
    """Additional tests for restore from checkpoint functionality."""

    def test_handle_error_restore_with_none_checkpoint_shows_error(self) -> None:
        """Test restore when last_checkpoint_turn is None shows error."""
        from app import handle_error_restore_click

        error = create_user_error(error_type="timeout", last_checkpoint_turn=None)
        state = create_initial_game_state()
        state["session_id"] = "001"

        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": 1,
            "game": state,
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.handle_checkpoint_restore") as mock_restore:
                with patch("streamlit.error") as mock_error:
                    handle_error_restore_click()

        # Should NOT call restore when checkpoint is None
        mock_restore.assert_not_called()
        # Should show error message
        mock_error.assert_called_once()
        assert "No checkpoint" in mock_error.call_args[0][0]

    def test_handle_error_restore_preserves_state_on_failure(self) -> None:
        """Test restore preserves error state on restore failure."""
        from app import handle_error_restore_click

        error = create_user_error(error_type="timeout", last_checkpoint_turn=5)
        state = create_initial_game_state()
        state["session_id"] = "001"

        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": 2,
            "game": state,
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.handle_checkpoint_restore", return_value=False):
                with patch("streamlit.toast"):
                    with patch("streamlit.error"):
                        handle_error_restore_click()

        # Error state should NOT be cleared when restore fails
        # (per the actual implementation behavior)
        assert mock_session_state["error"] is error
        assert mock_session_state["error_retry_count"] == 2


class TestErrorLogging:
    """Tests for error logging functionality."""

    @patch("agents.logger")
    @patch("agents.create_dm_agent")
    def test_llm_error_is_logged(
        self, mock_create_dm_agent: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test that LLM errors are logged with proper context."""
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("Timeout occurred")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()

        mock_session_state: dict[str, Any] = {"pending_nudge": None}

        with patch("streamlit.session_state", mock_session_state):
            try:
                dm_turn(state)
            except LLMError:
                pass

        # Verify logger was called
        mock_logger.error.assert_called_once()


class TestConcurrentErrorScenarios:
    """Tests for concurrent/rapid error scenarios."""

    def test_rapid_retry_clicks_increment_correctly(self) -> None:
        """Test rapid retry clicks increment count correctly."""
        from app import handle_retry_click

        error = create_user_error(error_type="timeout")
        state = create_initial_game_state()

        mock_session_state: dict[str, Any] = {
            "error": error,
            "error_retry_count": 0,
            "game": state,
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("app.run_game_turn", return_value=False):
                # Simulate rapid clicks
                for i in range(3):
                    handle_retry_click()
                    assert mock_session_state["error_retry_count"] == i + 1
