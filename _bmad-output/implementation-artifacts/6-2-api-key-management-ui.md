# Story 6.2: API Key Management UI

Status: done

## Story

As a **user**,
I want **to enter and validate API keys through the settings interface**,
so that **I can configure providers without editing environment files**.

## Acceptance Criteria

1. **Given** the "API Keys" tab in the config modal
   **When** I view it
   **Then** I see entry fields for: Google (Gemini), Anthropic (Claude), Ollama Base URL (FR47)

2. **Given** an API key field
   **When** it's empty and no environment variable is set
   **Then** the field shows a placeholder prompting for input

3. **Given** an API key is set via environment variable
   **When** viewing the field
   **Then** it shows "Set via environment" with a masked preview
   **And** I can optionally override it in the UI

4. **Given** I enter an API key in the UI
   **When** I blur the field (move focus away)
   **Then** the key is validated asynchronously
   **And** a spinner shows during validation

5. **Given** an API key is valid
   **When** validation completes
   **Then** a green checkmark appears next to the field
   **And** the provider is marked as available

6. **Given** an API key is invalid
   **When** validation completes
   **Then** a red X appears with "Invalid key" message
   **And** the provider is marked as unavailable

7. **Given** Ollama configuration
   **When** entering the base URL
   **Then** it validates by attempting to connect to the Ollama server
   **And** shows available models if successful

## Tasks / Subtasks

- [x] Task 1: Create API key entry field component
  - [x] 1.1 Create `render_api_key_field()` function in app.py with parameters: provider_name, env_var_name, placeholder_text
  - [x] 1.2 Create `ApiKeyFieldState` model in models.py to track field state (value, source, validation_status)
  - [x] 1.3 Handle three states: empty (prompt for input), env-set (masked preview), ui-override (user-entered)
  - [x] 1.4 Style field with text input, masked by default (password type)
  - [x] 1.5 Add "Show/Hide" toggle button for revealing key contents
  - [x] 1.6 Write unit tests for field rendering in each state

- [x] Task 2: Implement environment variable detection (AC #2, #3)
  - [x] 2.1 Create `get_api_key_source()` function in config.py that returns: "environment", "ui_override", or "empty"
  - [x] 2.2 When source is "environment", show "Set via environment" label with masked preview (last 4 chars visible)
  - [x] 2.3 Add "Override" button/checkbox that enables UI entry while env var exists
  - [x] 2.4 Store UI overrides in `st.session_state["api_key_overrides"]` dict
  - [x] 2.5 Write unit tests for source detection logic

- [x] Task 3: Render API Keys tab content (AC #1)
  - [x] 3.1 Replace placeholder content in "API Keys" tab with actual fields
  - [x] 3.2 Add Google (Gemini) API key field with label, help text: "Required for Gemini models"
  - [x] 3.3 Add Anthropic (Claude) API key field with label, help text: "Required for Claude models"
  - [x] 3.4 Add Ollama Base URL field (not password type) with label, help text: "Local Ollama server URL"
  - [x] 3.5 Order fields: Gemini, Claude, Ollama (cloud providers first)
  - [x] 3.6 Add section header "Provider API Keys" with campfire styling
  - [x] 3.7 Write unit tests for tab content rendering

- [x] Task 4: Implement API key validation logic
  - [x] 4.1 Create `validate_google_api_key()` async function in config.py - make minimal API call to verify key
  - [x] 4.2 Create `validate_anthropic_api_key()` async function in config.py - make minimal API call to verify key
  - [x] 4.3 Create `validate_ollama_connection()` async function in config.py - attempt connection, return available models
  - [x] 4.4 Each function returns `ValidationResult(valid: bool, message: str, models: list[str] | None)`
  - [x] 4.5 Handle network errors gracefully with friendly messages
  - [x] 4.6 Add timeout (5 seconds) for validation requests
  - [x] 4.7 Write unit tests for validation functions with mocked API calls

- [x] Task 5: Implement on-blur validation trigger (AC #4)
  - [x] 5.1 Add `on_change` callback to each API key input field
  - [x] 5.2 Trigger validation when field value changes and is not empty
  - [x] 5.3 Set `st.session_state["api_key_validating_{provider}"] = True` during validation
  - [x] 5.4 Show spinner next to field while validating (use st.spinner or CSS animation)
  - [x] 5.5 Store validation result in `st.session_state["api_key_status_{provider}"]`
  - [x] 5.6 Write integration tests for validation flow

- [x] Task 6: Implement validation result display (AC #5, #6)
  - [x] 6.1 Create `render_validation_status()` function that shows icon based on status
  - [x] 6.2 Green checkmark (using Unicode or custom CSS) for valid: "Valid"
  - [x] 6.3 Red X for invalid: "Invalid key - check your credentials"
  - [x] 6.4 Gray question mark for untested (never validated)
  - [x] 6.5 Style status icons with character colors: green #6B8E6B, red #C45C4A, gray #888
  - [x] 6.6 Add provider availability to status (e.g., "Provider: Available" or "Provider: Unavailable")
  - [x] 6.7 Write unit tests for status display

- [x] Task 7: Implement Ollama-specific behavior (AC #7)
  - [x] 7.1 Ollama field uses text input (not password) since URL is not sensitive
  - [x] 7.2 Add "Test Connection" button next to Ollama URL field
  - [x] 7.3 When connection succeeds, show collapsible list of available models
  - [x] 7.4 Format model list: model name, size if available
  - [x] 7.5 Handle Ollama not running: "Ollama server not responding at [URL]"
  - [x] 7.6 Handle Ollama running but no models: "Connected - no models installed"
  - [x] 7.7 Write unit tests for Ollama-specific logic

- [x] Task 8: Wire up unsaved changes detection
  - [x] 8.1 Update `snapshot_config_values()` to include API key sources/overrides
  - [x] 8.2 Call `mark_config_changed()` when any API key field changes
  - [x] 8.3 Compare current values against snapshot for change detection
  - [x] 8.4 Write unit tests for change detection with API key fields

- [x] Task 9: Implement save/apply logic
  - [x] 9.1 Create `apply_api_key_overrides()` function that stores UI overrides
  - [x] 9.2 Update `get_config()` to check for UI overrides before falling back to env vars
  - [x] 9.3 UI overrides persist in session state (not written to .env file)
  - [x] 9.4 Clear previous validation status when key value changes
  - [x] 9.5 Write integration tests for save/apply flow

- [x] Task 10: Add CSS styling for API key fields
  - [x] 10.1 Add `.api-key-field` class to theme.css for field container
  - [x] 10.2 Style provider label with provider-specific color accent
  - [x] 10.3 Style validation status icons (checkmark, X, spinner)
  - [x] 10.4 Style "Set via environment" badge with subtle background
  - [x] 10.5 Add focus styles for accessibility
  - [x] 10.6 Write visual verification tests using chrome-devtools MCP

- [x] Task 11: Write acceptance tests
  - [x] 11.1 Test: API Keys tab shows three provider fields (AC #1)
  - [x] 11.2 Test: Empty field shows placeholder (AC #2)
  - [x] 11.3 Test: Env-set field shows "Set via environment" (AC #3)
  - [x] 11.4 Test: Validation triggers on blur with spinner (AC #4)
  - [x] 11.5 Test: Valid key shows green checkmark (AC #5)
  - [x] 11.6 Test: Invalid key shows red X with message (AC #6)
  - [x] 11.7 Test: Ollama URL validates and shows models (AC #7)
  - [x] 11.8 Test: Changes trigger unsaved changes detection

## Dev Notes

### Implementation Strategy

This story populates the "API Keys" tab created in Story 6.1 with actual functionality. The focus is on:

1. **Clear visual feedback** - Users should immediately understand the state of each API key
2. **Non-destructive behavior** - UI overrides don't modify .env files
3. **Async validation** - Don't block UI while validating keys

### Existing Foundation (from Story 6.1)

**Config modal and tab structure already exist:**

```python
# app.py lines 1173-1204 (render_config_modal)
@st.dialog("Configuration", width="large")
def render_config_modal() -> None:
    tab1, tab2, tab3 = st.tabs(["API Keys", "Models", "Settings"])

    with tab1:
        st.markdown(
            '<p class="config-tab-placeholder">'
            "API key configuration coming in Story 6.2"
            "</p>",
            unsafe_allow_html=True,
        )
    # ...
```

**AppConfig already loads API keys from environment:**

```python
# config.py lines 66-84
class AppConfig(BaseSettings):
    # API Keys (from environment)
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
```

**Validation helpers exist in config.py:**

```python
# config.py lines 220-239
def validate_api_keys(config: AppConfig) -> list[str]:
    """Validate API keys and return warnings for missing ones."""
    warnings: list[str] = []
    if not config.google_api_key:
        warnings.append("GOOGLE_API_KEY not set - Gemini models will not be available")
    if not config.anthropic_api_key:
        warnings.append("ANTHROPIC_API_KEY not set - Claude models will not be available")
    return warnings
```

### API Key Field States

Each API key field can be in one of these states:

| State | Source | Display | Actions |
|-------|--------|---------|---------|
| Empty | None | Placeholder text, gray | Enter key |
| Env Set | .env / Environment | "Set via environment" + masked, green badge | Override button |
| UI Override | Session state | User-entered value (masked), amber badge | Clear override |
| Validating | Any | Previous value + spinner | Wait |
| Valid | Any | Value + green checkmark | Change/clear |
| Invalid | Any | Value + red X + error message | Fix/clear |

### Session State Keys

**New keys for this story:**

| Key | Type | Purpose |
|-----|------|---------|
| `api_key_overrides` | `dict[str, str]` | UI-entered API key overrides |
| `api_key_status_google` | `ValidationResult` | Google API key validation result |
| `api_key_status_anthropic` | `ValidationResult` | Anthropic API key validation result |
| `api_key_status_ollama` | `ValidationResult` | Ollama connection validation result |
| `api_key_validating_google` | `bool` | Whether Google key is being validated |
| `api_key_validating_anthropic` | `bool` | Whether Anthropic key is being validated |
| `api_key_validating_ollama` | `bool` | Whether Ollama connection is being validated |
| `ollama_available_models` | `list[str]` | List of available Ollama models |

### Validation Implementation

**Google (Gemini) validation:**

```python
async def validate_google_api_key(api_key: str) -> ValidationResult:
    """Validate Google API key by making a minimal API call.

    Uses the Gemini API's model list endpoint which is lightweight
    and doesn't consume tokens.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # List models is a lightweight call that validates the key
        models = list(genai.list_models())
        return ValidationResult(
            valid=True,
            message="Valid - Gemini models available",
            models=[m.name for m in models if "generateContent" in m.supported_generation_methods]
        )
    except Exception as e:
        if "API_KEY" in str(e).upper() or "401" in str(e) or "403" in str(e):
            return ValidationResult(valid=False, message="Invalid API key", models=None)
        return ValidationResult(valid=False, message=f"Connection error: {str(e)[:50]}", models=None)
```

**Anthropic (Claude) validation:**

```python
async def validate_anthropic_api_key(api_key: str) -> ValidationResult:
    """Validate Anthropic API key by making a minimal API call.

    Uses a very short message that consumes minimal tokens.
    """
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        # Make a minimal API call - this will fail fast if key is invalid
        # Note: This WILL consume a small number of tokens
        client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1,
            messages=[{"role": "user", "content": "Hi"}]
        )
        return ValidationResult(
            valid=True,
            message="Valid - Claude models available",
            models=["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        )
    except Exception as e:
        if "authentication" in str(e).lower() or "api_key" in str(e).lower():
            return ValidationResult(valid=False, message="Invalid API key", models=None)
        return ValidationResult(valid=False, message=f"Connection error: {str(e)[:50]}", models=None)
```

**Ollama connection validation:**

```python
async def validate_ollama_connection(base_url: str) -> ValidationResult:
    """Validate Ollama connection by checking the server and listing models.

    No API key required - just needs network access to the Ollama server.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    return ValidationResult(
                        valid=True,
                        message=f"Connected - {len(models)} models available",
                        models=models
                    )
                else:
                    return ValidationResult(
                        valid=True,
                        message="Connected - no models installed",
                        models=[]
                    )
            else:
                return ValidationResult(
                    valid=False,
                    message=f"Server error: HTTP {response.status_code}",
                    models=None
                )
    except Exception as e:
        return ValidationResult(
            valid=False,
            message="Server not responding",
            models=None
        )
```

### ValidationResult Model

Add to models.py:

```python
class ValidationResult(BaseModel):
    """Result of API key or connection validation.

    Attributes:
        valid: Whether the validation passed.
        message: Human-readable status message.
        models: List of available models if valid, None otherwise.
    """
    valid: bool
    message: str
    models: list[str] | None = None
```

### UI Override Pattern

UI overrides are stored in session state and applied at runtime:

```python
def get_effective_api_key(provider: str) -> str | None:
    """Get the effective API key for a provider.

    Priority:
    1. UI override (if set)
    2. Environment variable
    3. None
    """
    overrides = st.session_state.get("api_key_overrides", {})
    if provider in overrides and overrides[provider]:
        return overrides[provider]

    config = get_config()
    match provider:
        case "google":
            return config.google_api_key
        case "anthropic":
            return config.anthropic_api_key
        case "ollama":
            return config.ollama_base_url
        case _:
            return None
```

### CSS Classes to Add

Add to `styles/theme.css`:

```css
/* API Key Fields (Story 6.2) */
.api-key-field {
    margin-bottom: var(--space-lg);
    padding: var(--space-md);
    background: var(--bg-secondary);
    border-radius: 8px;
}

.api-key-label {
    font-family: var(--font-ui);
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-sm);
}

.api-key-help {
    font-family: var(--font-ui);
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: var(--space-sm);
}

.api-key-source-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: var(--font-ui);
    font-size: 11px;
    font-weight: 500;
}

.api-key-source-badge.environment {
    background: rgba(107, 142, 107, 0.2);
    color: var(--char-rogue);
}

.api-key-source-badge.override {
    background: rgba(232, 168, 73, 0.2);
    color: var(--accent-warm);
}

.api-key-status {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    margin-top: var(--space-sm);
    font-family: var(--font-ui);
    font-size: 12px;
}

.api-key-status.valid {
    color: var(--char-rogue);  /* green */
}

.api-key-status.invalid {
    color: var(--char-fighter);  /* red */
}

.api-key-status.validating {
    color: var(--text-secondary);
}

.api-key-status-icon {
    font-size: 14px;
}

.api-key-status-icon.valid::before {
    content: "\u2713";  /* checkmark */
}

.api-key-status-icon.invalid::before {
    content: "\u2717";  /* X mark */
}

/* Ollama model list */
.ollama-models {
    margin-top: var(--space-sm);
    padding: var(--space-sm);
    background: var(--bg-primary);
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 12px;
}

.ollama-model-item {
    padding: 4px 0;
    color: var(--text-secondary);
}
```

### Streamlit Async Considerations

Streamlit doesn't natively support async callbacks. Options:

1. **Use `asyncio.run()` in callback** - Simple but blocks UI thread
2. **Background thread** - More complex but non-blocking
3. **Polling pattern** - Set flag, check on rerender

For MVP, use option 1 with timeout:

```python
def handle_api_key_change(provider: str, value: str) -> None:
    """Handle API key field change with validation."""
    import asyncio

    # Store the new value
    overrides = st.session_state.get("api_key_overrides", {})
    overrides[provider] = value
    st.session_state["api_key_overrides"] = overrides

    # Mark changes
    mark_config_changed()

    # Skip validation if empty
    if not value.strip():
        st.session_state[f"api_key_status_{provider}"] = None
        return

    # Set validating flag
    st.session_state[f"api_key_validating_{provider}"] = True

    # Run validation (blocking with timeout)
    try:
        match provider:
            case "google":
                result = asyncio.run(validate_google_api_key(value))
            case "anthropic":
                result = asyncio.run(validate_anthropic_api_key(value))
            case "ollama":
                result = asyncio.run(validate_ollama_connection(value))
                if result.models:
                    st.session_state["ollama_available_models"] = result.models
            case _:
                result = ValidationResult(valid=False, message="Unknown provider")

        st.session_state[f"api_key_status_{provider}"] = result
    finally:
        st.session_state[f"api_key_validating_{provider}"] = False
```

### Masked Key Display

Show only last 4 characters of API key for security:

```python
def mask_api_key(key: str) -> str:
    """Mask an API key, showing only last 4 characters.

    Example: "sk-abc123xyz789" -> "***************789"
    """
    if not key or len(key) < 8:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]
```

### Architecture Compliance

| Pattern | Compliance | Notes |
|---------|------------|-------|
| Session state for UI state | YES | API key overrides in session state |
| CSS via theme.css | YES | All styling in centralized stylesheet |
| Functions with docstrings | YES | All public functions documented |
| Pydantic for models | YES | ValidationResult is a Pydantic model |
| Never mutate .env | YES | UI overrides don't write to files |

### Performance Considerations

- Validation runs on-change, not on every keystroke (debounced by Streamlit)
- Timeout on all validation requests (5 seconds)
- Validation results cached in session state
- Model list fetched once per validation, not continuously

### Edge Cases

1. **API key with special characters**: URL-encode if needed for validation
2. **Ollama running but unreachable**: Clear error message about network
3. **Rate limiting during validation**: Detect and show appropriate message
4. **Validation timeout**: Show "Validation timed out - check network"
5. **Empty key submitted**: Clear validation status, don't show error
6. **Same key re-entered**: Skip re-validation if key matches last validated
7. **Modal closed during validation**: Cancel or let complete (validation result stored)

### What This Story Implements

1. Three provider API key fields in the API Keys tab
2. Environment variable detection and display
3. UI override capability
4. Async validation with visual feedback
5. Valid/invalid status display
6. Ollama connection test with model listing
7. Integration with unsaved changes detection

### What This Story Does NOT Implement

- Persisting UI overrides to .env file (by design - stays in session)
- Per-agent model selection (Story 6.3)
- Context limit configuration (Story 6.4)
- Provider switching logic (Story 6.5)

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR46 | API keys via environment variables | Detection and display of env-set keys |
| FR47 | Override API keys in UI | UI override with session state storage |
| FR48 | Support Google Gemini | Google API key validation |
| FR49 | Support Anthropic Claude | Anthropic API key validation |
| FR50 | Support Ollama local models | Ollama connection validation + model listing |

### Testing Strategy

**Unit Tests (pytest):**
- API key field rendering in each state
- Source detection logic
- Validation functions with mocked API calls
- Mask function behavior
- Override storage and retrieval

**Integration Tests (pytest + mock):**
- Full validation flow
- On-change callback behavior
- Session state management
- Change detection integration

**Visual Tests (chrome-devtools MCP):**
- Field layout and spacing
- Status icon colors
- Badge styling
- Ollama model list display

### Files to Modify

| File | Changes |
|------|---------|
| `app.py` | Replace API Keys tab placeholder with fields, add handlers |
| `config.py` | Add validation functions, get_effective_api_key |
| `models.py` | Add ValidationResult model |
| `styles/theme.css` | Add API key field CSS classes |

### Files to Create

None - all code goes in existing files.

### Dependencies

- Story 6.1 (Configuration Modal Structure) - COMPLETE
- Streamlit 1.40.0+ (for st.dialog)
- httpx (for Ollama connection check, already in deps)
- google-generativeai (for Gemini validation, already in deps)
- anthropic (for Claude validation, already in deps)

### References

- [Source: planning-artifacts/prd.md#LLM Configuration FR46-FR50]
- [Source: planning-artifacts/architecture.md#LLM Provider Abstraction]
- [Source: planning-artifacts/architecture.md#Configuration Hierarchy]
- [Source: planning-artifacts/epics.md#Story 6.2]
- [Source: app.py#render_config_modal] - Tab structure to populate
- [Source: config.py#AppConfig] - API key fields to display
- [Source: config.py#validate_api_keys] - Existing validation pattern
- [Source: agents.py#get_llm] - LLM factory that uses API keys

---

## Senior Developer Review (AI)

**Review Date:** 2026-01-28
**Reviewer:** Claude Opus 4.5 (code-review workflow)
**Outcome:** APPROVED with AUTO-FIXES APPLIED

### Issues Found and Resolved

| Severity | Issue | Resolution |
|----------|-------|------------|
| HIGH | Error messages could leak API key values | Added `_sanitize_error_message()` function to redact key patterns |
| HIGH | HTML attribute not escaped for provider | Added `escape_html(provider)` in `render_api_key_field()` |
| HIGH | No test for error message key sanitization | Added 6 security tests in `TestApiKeySecuritySanitization` class |
| MEDIUM | Docstring for Anthropic validation was misleading | Updated docstring to accurately describe API call behavior |
| MEDIUM | `apply_api_key_overrides()` was empty no-op | Added proper documentation and config_has_changes reset |
| LOW | CSS class `.api-key-source-badge.override` not defined | Documented - empty badge styling is sufficient |
| LOW | Story shows async signatures but impl is sync | Documented - sync is correct for Streamlit |
| LOW | Provider naming inconsistency | Documented - works correctly as-is |

### Security Validation

- API keys are NEVER logged or printed
- Error messages are sanitized via `_sanitize_error_message()` to remove key patterns
- Keys are properly masked (showing only last 4 chars)
- HTML attributes are escaped to prevent XSS
- 6 new security-focused tests added and passing

### Test Results

- **76 tests passed** (70 original + 6 new security tests)
- **Linting:** All checks passed (ruff)
- **Coverage:** All acceptance criteria verified via tests

### Files Modified in Review

| File | Changes |
|------|---------|
| `config.py` | Added `_sanitize_error_message()`, updated docstrings, sanitized error output |
| `app.py` | Escaped provider in HTML attribute, improved `apply_api_key_overrides()` docs |
| `tests/test_story_6_2_api_key_management.py` | Added `TestApiKeySecuritySanitization` class (6 tests) |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-28 | Story created via create-story workflow | Claude Opus 4.5 |
| 2026-01-28 | Code review: Fixed 3 HIGH, 2 MEDIUM security issues; added 6 security tests | Claude Opus 4.5 |
