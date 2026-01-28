# Story 4.5: Error Handling & Recovery

Status: review

## Story

As a **user**,
I want **clear error messages and easy recovery when things go wrong**,
so that **I don't lose progress and can continue my adventure**.

## Acceptance Criteria

1. **Given** an LLM API call fails (timeout, rate limit, invalid response)
   **When** the error occurs
   **Then** a user-friendly error message displays (FR40, NFR7)
   **And** the message uses campfire-narrative style (e.g., "The magical connection was interrupted...")

2. **Given** an error panel appears
   **When** I view it
   **Then** I see:
   - Friendly title explaining what happened
   - Suggested actions (Retry, Restore from checkpoint, Start new session)
   - No technical jargon exposed to the user

3. **Given** an error occurs mid-turn
   **When** I choose to recover
   **Then** I can restore to the last successful checkpoint
   **And** I lose at most one turn of progress (FR41, NFR15)

4. **Given** I click "Retry" on an error
   **When** the retry executes
   **Then** the failed action is attempted again
   **And** if successful, the game continues normally

5. **Given** the error logging
   **When** an error occurs
   **Then** technical details are logged internally for debugging
   **And** the log includes: provider, agent, error type, timestamp

6. **Given** network connectivity is lost
   **When** using cloud LLM providers
   **Then** a clear message indicates the connection issue
   **And** suggests checking internet or switching to Ollama for offline play

## Tasks / Subtasks

- [x] Task 1: Create UserError model for user-facing errors (AC: #1, #2)
  - [x] 1.1 Create `UserError` Pydantic model in models.py with fields: title (str), message (str), action (str), error_type (str), timestamp (str)
  - [x] 1.2 Add `friendly_titles` dict mapping error types to narrative-style titles (e.g., "timeout" -> "The magical connection was interrupted...")
  - [x] 1.3 Add `friendly_messages` dict mapping error types to user-friendly explanations
  - [x] 1.4 Create `create_user_error(error_type, provider, agent)` factory function
  - [x] 1.5 Add `UserError` to `__all__` exports in models.py
  - [x] 1.6 Write tests for UserError model validation and factory function

- [x] Task 2: Implement error capture in LLM calls (AC: #1, #5, #6)
  - [x] 2.1 Create `LLMError` exception class in agents.py with provider, agent, original_error fields
  - [x] 2.2 Wrap `get_llm()` calls in dm_turn() with try/except to catch API errors
  - [x] 2.3 Wrap `get_llm()` calls in pc_turn() with try/except to catch API errors
  - [x] 2.4 Categorize errors: timeout, rate_limit, auth_error, network_error, invalid_response
  - [x] 2.5 Log technical details with structured logging (provider, agent, error_type, timestamp)
  - [x] 2.6 Re-raise as `LLMError` with categorized error_type
  - [x] 2.7 Write tests for error categorization and logging

- [x] Task 3: Implement error handling in game loop (AC: #3)
  - [x] 3.1 Modify `run_single_round()` in graph.py to catch `LLMError`
  - [x] 3.2 On error, create `UserError` via factory and store in state
  - [x] 3.3 Return state with `error` field populated (not ground_truth_log)
  - [x] 3.4 Ensure game state is not corrupted by partial turn
  - [x] 3.5 Preserve last successful checkpoint reference in error
  - [x] 3.6 Write tests for error handling in game loop

- [x] Task 4: Implement error handling in app.py (AC: #1, #2, #4)
  - [x] 4.1 Modify `run_game_turn()` to check for errors in returned state
  - [x] 4.2 Store error in `st.session_state["error"]` when detected
  - [x] 4.3 Stop autopilot when error occurs
  - [x] 4.4 Create `render_error_panel()` function
  - [x] 4.5 Integrate error panel display into main render flow
  - [x] 4.6 Write tests for error state handling in app

- [x] Task 5: Create error panel UI component (AC: #2)
  - [x] 5.1 Create `render_error_panel_html(error: UserError) -> str` function
  - [x] 5.2 Display friendly title with campfire styling
  - [x] 5.3 Display friendly message explaining what happened
  - [x] 5.4 Add "Retry" button
  - [x] 5.5 Add "Restore from Checkpoint" button
  - [x] 5.6 Add "Start New Session" button
  - [x] 5.7 Style with existing theme colors (error: amber, buttons: secondary style)
  - [x] 5.8 Write tests for error panel HTML rendering

- [x] Task 6: Implement retry functionality (AC: #4)
  - [x] 6.1 Create `handle_retry_click()` function in app.py
  - [x] 6.2 Clear error from session state
  - [x] 6.3 Re-execute `run_game_turn()` for the failed turn
  - [x] 6.4 If retry succeeds, game continues normally
  - [x] 6.5 If retry fails again, show error panel with updated attempt count
  - [x] 6.6 Add retry counter to prevent infinite retry loops (max 3)
  - [x] 6.7 Write tests for retry functionality

- [x] Task 7: Implement restore from error functionality (AC: #3)
  - [x] 7.1 Create `handle_error_restore_click()` function in app.py
  - [x] 7.2 Get latest successful checkpoint before error
  - [x] 7.3 Reuse existing `handle_checkpoint_restore()` logic
  - [x] 7.4 Clear error state after successful restore
  - [x] 7.5 Show toast confirmation "Restored to Turn N"
  - [x] 7.6 Write tests for restore from error

- [x] Task 8: Add CSS styling for error panel (AC: #2)
  - [x] 8.1 Add `.error-panel` container styles to theme.css
  - [x] 8.2 Add `.error-panel-title` styles (amber color, narrative font)
  - [x] 8.3 Add `.error-panel-message` styles
  - [x] 8.4 Add `.error-panel-actions` button container styles
  - [x] 8.5 Add button hover states
  - [x] 8.6 Verify styling in browser (manual verification)

- [x] Task 9: Implement network error detection (AC: #6)
  - [x] 9.1 Create `detect_network_error(exception)` helper function
  - [x] 9.2 Check for connection errors, timeouts, DNS failures
  - [x] 9.3 Create special message for network errors with Ollama suggestion
  - [x] 9.4 Write tests for network error detection

- [x] Task 10: Integration and acceptance tests
  - [x] 10.1 Test error panel displays when LLM call fails
  - [x] 10.2 Test retry button re-executes turn
  - [x] 10.3 Test restore button loads last checkpoint
  - [x] 10.4 Test error message uses narrative style
  - [x] 10.5 Test technical details logged (not shown to user)
  - [x] 10.6 Test network error shows Ollama suggestion
  - [x] 10.7 Test autopilot stops on error
  - [x] 10.8 Test at most one turn lost on error recovery (NFR15)

## Dev Agent Record

### Implementation Summary

Implemented comprehensive error handling and recovery system for the autodungeon game engine. The implementation follows the campfire aesthetic with narrative-style error messages that maintain immersion while providing clear recovery options.

### Files Modified

| File | Changes |
|------|---------|
| `models.py` | Added `UserError` Pydantic model, `ERROR_TYPES` dict with campfire-narrative messages, `create_user_error()` factory function |
| `agents.py` | Added `LLMError` exception class, `categorize_error()` and `detect_network_error()` helpers, wrapped `dm_turn()` and `pc_turn()` with error handling |
| `graph.py` | Modified `run_single_round()` to catch errors and return `GameStateWithError`, preserves last checkpoint for recovery |
| `app.py` | Added error handling in `run_game_turn()`, `render_error_panel()`, `render_error_panel_html()`, `handle_retry_click()`, `handle_error_restore_click()`, `handle_error_new_session_click()` functions |
| `styles/theme.css` | Added `.error-panel`, `.error-panel-title`, `.error-panel-message`, `.error-panel-action`, `.error-panel-actions` styles with campfire aesthetic |
| `tests/test_error_handling.py` | Created comprehensive test suite with 55 tests covering all functionality |
| `tests/test_agents.py` | Updated export test to include new error handling exports |
| `tests/test_graph.py` | Updated return type annotation test for `GameStateWithError` |

### Key Design Decisions

1. **Error Type System**: Created 6 categorized error types (timeout, rate_limit, auth_error, network_error, invalid_response, unknown) with narrative-style messages
2. **Immutable Error Pattern**: Errors do not corrupt game state - original state is preserved and returned with error attached
3. **Retry Limiting**: MAX_RETRY_ATTEMPTS = 3 to prevent infinite retry loops
4. **Checkpoint Integration**: Last successful checkpoint turn is stored in error for seamless recovery
5. **Autopilot Integration**: Autopilot automatically stops when errors occur

### Test Results

- 55 new tests in `test_error_handling.py`
- 1421 total tests passing
- 1 skipped
- All lint checks pass (ruff)

### Architecture Compliance

| Decision | Status |
|----------|--------|
| User-facing errors: Friendly narrative style | Compliant |
| Internal errors: Structured logging | Compliant |
| Error recovery: Checkpoint restore | Compliant |
| Session state keys: underscore separated | Compliant |

### FR/NFR Coverage

| Requirement | Implementation |
|-------------|----------------|
| FR40 | UserError model with narrative messages, render_error_panel() |
| FR41 | handle_error_restore_click() restores last checkpoint |
| NFR7 | Error panel with Retry/Restore/New Session buttons |
| NFR15 | Auto-checkpoint ensures max 1 turn loss |

## Dev Notes

### Existing Infrastructure Analysis

**models.py (Current State):**

The models module already has a placeholder comment in the architecture for UserError:

```python
# From architecture.md:
class UserError(BaseModel):
    title: str    # "The magical connection was interrupted"
    message: str  # "The spirits are not responding..."
    action: str   # "Try again or restore from checkpoint"
```

**agents.py (Current State):**

The `get_llm()` factory and turn functions already exist:

```python
def get_llm(provider: str, model: str) -> BaseChatModel:
    """Factory function for creating LLM instances."""
    ...

def dm_turn(state: GameState) -> GameState:
    """Execute DM's turn in the game loop."""
    ...

def pc_turn(state: GameState, agent_name: str) -> GameState:
    """Execute a PC agent's turn in the game loop."""
    ...
```

These need to be wrapped with error handling.

**app.py (Current State):**

Session state already has patterns for error handling:

```python
st.session_state["error"] = None  # Ready for UserError
```

The `run_game_turn()` function is the integration point.

**graph.py (Current State):**

The `run_single_round()` function calls the workflow:

```python
def run_single_round(state: GameState) -> GameState:
    workflow = create_game_workflow(state["turn_queue"])
    result: GameState = workflow.invoke(state, config={...})
    return result
```

This needs try/except to catch LLM errors.

### Architecture Compliance

Per architecture.md:

| Decision | Compliance |
|----------|------------|
| User-facing errors: Friendly narrative style | Following - campfire aesthetic |
| Internal errors: Structured logging | Following - provider, agent, error_type |
| Error recovery: Checkpoint restore | Following - reuse existing restore logic |
| Session state keys: underscore separated | Following - `st.session_state["error"]` |

**Error Handling Pattern (from Architecture):**

```python
# User-Facing (Friendly):
class UserError(BaseModel):
    title: str    # "The magical connection was interrupted"
    message: str  # "The spirits are not responding..."
    action: str   # "Try again or restore from checkpoint"

# Internal (Structured Logging):
logger.error("LLM API failed", extra={"provider": "gemini", "agent": "dm"})
```

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR40 | Clear error messages when LLM API calls fail | UserError model, render_error_panel() |
| FR41 | Recover from errors without losing significant progress | handle_error_restore_click(), checkpoint restore |
| NFR7 | Display clear error message and offer checkpoint restore | Error panel with Retry/Restore buttons |
| NFR15 | User can recover without losing more than current turn | Auto-checkpoint ensures max 1 turn loss |

[Source: epics.md#Story 4.5, prd.md#Persistence & Recovery FR40-41]

### What This Story Does NOT Do

- Does NOT implement automatic retry with backoff (manual retry only)
- Does NOT implement provider failover (switch providers on error)
- Does NOT implement error analytics/aggregation
- Does NOT implement error email notifications
- Does NOT implement memory system integration (Epic 5)
- Does NOT implement LLM config UI integration (Epic 6)

### Error Type Categorization

```python
ERROR_TYPES = {
    "timeout": {
        "title": "The magical connection was interrupted...",
        "message": "The spirits took too long to respond. The astral plane may be congested.",
        "action": "Try again or restore to your last checkpoint."
    },
    "rate_limit": {
        "title": "The spirits need rest...",
        "message": "Too many requests have been made. Wait a moment before continuing.",
        "action": "Wait a few seconds, then try again."
    },
    "auth_error": {
        "title": "The magical seal is broken...",
        "message": "Your credentials could not be verified. Check your API keys.",
        "action": "Check your API configuration in LLM Status."
    },
    "network_error": {
        "title": "The connection to the realm has been severed...",
        "message": "Unable to reach the spirit realm. Check your internet connection.",
        "action": "Check your connection, or try Ollama for offline play."
    },
    "invalid_response": {
        "title": "The spirits speak in riddles...",
        "message": "The response could not be understood. This may be temporary.",
        "action": "Try again or restore to your last checkpoint."
    },
    "unknown": {
        "title": "Something unexpected happened...",
        "message": "An unknown error occurred in the magical realm.",
        "action": "Try again or restore to your last checkpoint."
    }
}
```

### Error Panel Design

The error panel follows the campfire aesthetic:

```html
<div class="error-panel">
  <h3 class="error-panel-title">The magical connection was interrupted...</h3>
  <p class="error-panel-message">The spirits took too long to respond. The astral plane may be congested.</p>
  <p class="error-panel-action">Try again or restore to your last checkpoint.</p>
  <div class="error-panel-actions">
    <button class="error-retry-btn">Retry</button>
    <button class="error-restore-btn">Restore from Checkpoint</button>
    <button class="error-new-session-btn">Start New Session</button>
  </div>
</div>
```

CSS styling uses existing theme colors:
- Panel background: #2D2520 (warm gray-brown)
- Title: #E8A849 (amber accent)
- Message: #F5E6D3 (warm off-white)
- Buttons: Secondary style with amber highlight

### LLMError Exception Design

```python
class LLMError(Exception):
    """Exception raised when LLM API calls fail.

    Attributes:
        provider: LLM provider name (gemini, claude, ollama)
        agent: Agent that was executing (dm, rogue, fighter, etc.)
        error_type: Categorized error type (timeout, rate_limit, etc.)
        original_error: The original exception that was caught
    """
    def __init__(
        self,
        provider: str,
        agent: str,
        error_type: str,
        original_error: Exception | None = None
    ):
        self.provider = provider
        self.agent = agent
        self.error_type = error_type
        self.original_error = original_error
        super().__init__(f"LLM error ({error_type}) for {agent} using {provider}")
```

### Error Categorization Logic

```python
def categorize_error(exception: Exception) -> str:
    """Categorize exception into user-friendly error type.

    Args:
        exception: The caught exception.

    Returns:
        Error type string (timeout, rate_limit, auth_error, network_error, invalid_response, unknown)
    """
    error_str = str(exception).lower()
    error_type = type(exception).__name__.lower()

    # Timeout errors
    if "timeout" in error_str or "timed out" in error_str:
        return "timeout"

    # Rate limit errors
    if "rate" in error_str and "limit" in error_str:
        return "rate_limit"
    if "429" in error_str:
        return "rate_limit"

    # Auth errors
    if "auth" in error_str or "api key" in error_str or "credential" in error_str:
        return "auth_error"
    if "401" in error_str or "403" in error_str:
        return "auth_error"

    # Network errors
    if detect_network_error(exception):
        return "network_error"

    # Invalid response (parsing errors, unexpected format)
    if "parse" in error_str or "json" in error_str or "decode" in error_str:
        return "invalid_response"

    return "unknown"


def detect_network_error(exception: Exception) -> bool:
    """Check if exception indicates network connectivity issues.

    Args:
        exception: The caught exception.

    Returns:
        True if this is a network error, False otherwise.
    """
    error_str = str(exception).lower()
    error_type = type(exception).__name__.lower()

    network_indicators = [
        "connection",
        "network",
        "dns",
        "resolve",
        "socket",
        "refused",
        "unreachable",
        "no route",
    ]

    return any(indicator in error_str or indicator in error_type for indicator in network_indicators)
```

### Retry Logic Design

```python
MAX_RETRY_ATTEMPTS = 3

def handle_retry_click() -> None:
    """Handle retry button click on error panel."""
    # Get current retry count
    retry_count = st.session_state.get("error_retry_count", 0)

    if retry_count >= MAX_RETRY_ATTEMPTS:
        # Too many retries - show message
        st.session_state["error"].message += " (Maximum retry attempts reached)"
        return

    # Increment retry count
    st.session_state["error_retry_count"] = retry_count + 1

    # Clear error
    st.session_state["error"] = None

    # Re-execute turn
    if run_game_turn():
        # Success - clear retry count
        st.session_state["error_retry_count"] = 0
        st.rerun()

    # If failed again, error will be set by run_game_turn
```

### Integration with Existing Autopilot

When an error occurs during autopilot:

```python
def run_autopilot_step() -> None:
    """Execute one step of autopilot."""
    # ... existing checks ...

    # Execute one turn
    if run_game_turn():
        # ... continue autopilot ...
    else:
        # Check for error
        if st.session_state.get("error"):
            # Stop autopilot on error
            st.session_state["is_autopilot_running"] = False
            # Don't rerun - let error panel display
            return
```

### Testing Strategy

```python
# tests/test_error_handling.py

class TestUserError:
    """Tests for UserError model."""

    def test_user_error_creation(self):
        """Test creating a UserError with all fields."""

    def test_create_user_error_factory(self):
        """Test factory function creates correct errors."""


class TestLLMError:
    """Tests for LLMError exception."""

    def test_llm_error_attributes(self):
        """Test LLMError stores provider, agent, error_type."""


class TestErrorCategorization:
    """Tests for error categorization logic."""

    def test_timeout_categorization(self):
        """Test timeout errors are categorized correctly."""

    def test_rate_limit_categorization(self):
        """Test rate limit errors are categorized correctly."""

    def test_network_error_detection(self):
        """Test network errors are detected correctly."""


class TestErrorPanel:
    """Tests for error panel HTML rendering."""

    def test_error_panel_html_structure(self):
        """Test error panel has required elements."""

    def test_error_panel_narrative_style(self):
        """Test error messages use campfire narrative style."""


class TestErrorRecovery:
    """Tests for error recovery functionality."""

    def test_retry_clears_error_and_retries(self):
        """Test retry button clears error and re-executes."""

    def test_restore_loads_checkpoint(self):
        """Test restore loads last successful checkpoint."""

    def test_max_retry_attempts_enforced(self):
        """Test retry stops after MAX_RETRY_ATTEMPTS."""


class TestErrorInGameLoop:
    """Tests for error handling in game loop."""

    def test_llm_error_creates_user_error(self):
        """Test LLMError is converted to UserError in game loop."""

    def test_state_not_corrupted_on_error(self):
        """Test game state remains valid after error."""

    def test_autopilot_stops_on_error(self):
        """Test autopilot stops when error occurs."""
```

### Logging Configuration

Technical errors are logged with structured data:

```python
import logging

logger = logging.getLogger("autodungeon")

# On error:
logger.error(
    "LLM API call failed",
    extra={
        "provider": error.provider,
        "agent": error.agent,
        "error_type": error.error_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "original_error": str(error.original_error),
    }
)
```

### Security Considerations

- **Error messages:** Never expose raw exception text to users (could contain API keys, internal paths)
- **Logging:** Sanitize sensitive data before logging
- **Retry limits:** Prevent DoS via unlimited retries
- **Error state:** Clear error state on successful retry to prevent stale displays

### References

- [Source: planning-artifacts/prd.md#Persistence & Recovery FR40-41]
- [Source: planning-artifacts/prd.md#Non-Functional Requirements NFR7, NFR15]
- [Source: planning-artifacts/architecture.md#Error Handling]
- [Source: planning-artifacts/epics.md#Story 4.5]
- [Source: planning-artifacts/prd.md#Journey 2: Marcus - Session Recovery]
- [Source: app.py] - Existing UI patterns
- [Source: graph.py] - Game loop integration point
- [Source: agents.py] - LLM factory and turn functions
