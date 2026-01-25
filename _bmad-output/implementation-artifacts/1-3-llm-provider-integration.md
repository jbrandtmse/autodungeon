# Story 1.3: LLM Provider Integration

Status: done

## Story

As a **developer**,
I want **a factory function that creates LLM clients for different providers**,
so that **agents can use Gemini, Claude, or Ollama interchangeably**.

## Acceptance Criteria

1. **Given** the agents.py module with `get_llm(provider: str, model: str)` function
   **When** I call `get_llm("gemini", "gemini-1.5-flash")`
   **Then** it returns a ChatGoogleGenerativeAI instance configured with that model

2. **Given** valid Anthropic API credentials in environment
   **When** I call `get_llm("claude", "claude-3-haiku-20240307")`
   **Then** it returns a ChatAnthropic instance configured with that model

3. **Given** Ollama running locally
   **When** I call `get_llm("ollama", "llama3")`
   **Then** it returns a ChatOllama instance pointing to the local server

4. **Given** an unknown provider string
   **When** I call `get_llm("unknown", "model")`
   **Then** it raises a ValueError with message "Unknown provider: unknown"

5. **Given** missing API credentials for a cloud provider
   **When** I attempt to use that provider
   **Then** a clear error message indicates which credentials are missing

## Tasks / Subtasks

- [x] Task 1: Implement `get_llm` factory function (AC: #1, #2, #3, #4)
  - [x] 1.1 Create `get_llm(provider: str, model: str) -> BaseChatModel` in agents.py
  - [x] 1.2 Implement Gemini provider with ChatGoogleGenerativeAI
  - [x] 1.3 Implement Claude provider with ChatAnthropic
  - [x] 1.4 Implement Ollama provider with ChatOllama
  - [x] 1.5 Raise ValueError for unknown providers with clear message
  - [x] 1.6 Add type hints and docstring

- [x] Task 2: Implement credential validation (AC: #5)
  - [x] 2.1 Check for GOOGLE_API_KEY when provider is "gemini"
  - [x] 2.2 Check for ANTHROPIC_API_KEY when provider is "claude"
  - [x] 2.3 Check for OLLAMA_BASE_URL when provider is "ollama" (with default)
  - [x] 2.4 Raise ConfigurationError with specific missing credential message
  - [x] 2.5 Integrate with existing `get_config()` from config.py

- [x] Task 3: Create custom exception class
  - [x] 3.1 Create `LLMConfigurationError` exception in agents.py
  - [x] 3.2 Include provider name and missing credential in error message
  - [x] 3.3 Export in `__all__`

- [x] Task 4: Add provider constants and model defaults
  - [x] 4.1 Define SUPPORTED_PROVIDERS = ["gemini", "claude", "ollama"]
  - [x] 4.2 Define DEFAULT_MODELS dict for each provider
  - [x] 4.3 Add `get_default_model(provider: str) -> str` helper function

- [x] Task 5: Write comprehensive tests
  - [x] 5.1 Test `get_llm` returns correct type for each provider
  - [x] 5.2 Test ValueError raised for unknown provider
  - [x] 5.3 Test missing API key raises LLMConfigurationError
  - [x] 5.4 Test Ollama uses correct base URL from config
  - [x] 5.5 Test `get_default_model` returns expected values
  - [x] 5.6 Mock LLM classes to avoid actual API calls in tests

## Dev Notes

### Architecture Compliance (MANDATORY)

**LLM Factory Pattern (CRITICAL)**

Per architecture.md, this EXACT pattern must be implemented:

```python
# agents.py
def get_llm(provider: str, model: str) -> BaseChatModel:
    match provider:
        case "gemini": return ChatGoogleGenerativeAI(model=model)
        case "claude": return ChatAnthropic(model=model)
        case "ollama": return ChatOllama(model=model)
        case _: raise ValueError(f"Unknown provider: {provider}")
```

[Source: architecture.md#LLM Provider Abstraction]

**Configuration Hierarchy:**

1. Default config file (`config/defaults.yaml`) sets initial model assignments
2. Campaign config can override defaults
3. UI (Streamlit sidebar) can override at runtime
4. Runtime changes persist to session state

[Source: architecture.md#LLM Provider Abstraction]

### Import Requirements

The following imports are REQUIRED from LangChain packages:

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
```

These packages are already in pyproject.toml dependencies (Story 1.1).

### Integration with Existing Code

**From config.py (Story 1.1):**
- `get_config()` - Returns AppConfig singleton
- `AppConfig.google_api_key` - Google API key from env
- `AppConfig.anthropic_api_key` - Anthropic API key from env
- `AppConfig.ollama_base_url` - Ollama server URL (default: http://localhost:11434)

**Usage pattern:**
```python
from config import get_config

config = get_config()
if not config.google_api_key:
    raise LLMConfigurationError("gemini", "GOOGLE_API_KEY")
```

### Provider-Specific Configuration

**Gemini:**
```python
ChatGoogleGenerativeAI(
    model=model,
    google_api_key=config.google_api_key,
)
```

**Claude:**
```python
ChatAnthropic(
    model=model,
    anthropic_api_key=config.anthropic_api_key,
)
```

**Ollama:**
```python
ChatOllama(
    model=model,
    base_url=config.ollama_base_url,
)
```

### Default Models Reference

| Provider | Default Model | Notes |
|----------|--------------|-------|
| gemini | gemini-1.5-flash | Fast, good for PCs |
| claude | claude-3-haiku-20240307 | Fast, cost-effective |
| ollama | llama3 | Local, no API key needed |

### Error Handling Pattern

Per architecture.md, user-facing errors should use friendly narrative:

```python
class LLMConfigurationError(Exception):
    """Raised when LLM provider is misconfigured."""

    def __init__(self, provider: str, missing_credential: str):
        self.provider = provider
        self.missing_credential = missing_credential
        super().__init__(
            f"Cannot use {provider}: {missing_credential} not set. "
            f"Add it to your .env file or environment."
        )
```

### Testing Strategy

**Mock the LLM classes to avoid API calls:**

```python
from unittest.mock import patch, MagicMock

@patch("agents.ChatGoogleGenerativeAI")
def test_get_llm_gemini(mock_class):
    mock_class.return_value = MagicMock()
    result = get_llm("gemini", "gemini-1.5-flash")
    mock_class.assert_called_once_with(
        model="gemini-1.5-flash",
        google_api_key=ANY,  # from config
    )
```

**Test credential validation with monkeypatch:**

```python
def test_get_llm_missing_google_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError) as exc_info:
        get_llm("gemini", "gemini-1.5-flash")
    assert "GOOGLE_API_KEY" in str(exc_info.value)
```

### Previous Story Intelligence

**From Story 1.2:**
- models.py now has `AgentMemory`, `CharacterConfig`, `GameConfig`, `GameState`
- CharacterConfig includes `provider` and `model` fields
- All code uses Python 3.10+ type hints (`str | None`, not `Optional`)
- `__all__` exports in all modules
- Docstrings on all public classes/functions

**From Story 1.1:**
- config.py has `get_config()` returning AppConfig with API keys
- .env file support via python-dotenv
- Testing patterns established in tests/test_config.py

### Git Intelligence

Recent commits show consistent patterns:
- b4434b4: Story 1.2 - Pydantic models with validators
- 341b9df: Story 1.1 - Config with Pydantic Settings

Files to modify:
- `agents.py` - Currently just a docstring placeholder
- `tests/test_agents.py` - New file for agent tests

### Project Structure Notes

- agents.py is in flat project root (per architecture)
- Import as: `from agents import get_llm, LLMConfigurationError`
- Export via `__all__` for explicit public API

### References

- [architecture.md#LLM Provider Abstraction]
- [architecture.md#Configuration Hierarchy]
- [epics.md#Story 1.3 - LLM Provider Integration]
- [config.py] - AppConfig with API key fields

### What NOT To Do

- Do NOT make actual API calls in tests (mock the LLM classes)
- Do NOT hardcode API keys (always read from config)
- Do NOT create new config loading logic (use existing get_config())
- Do NOT add UI concerns to agents.py (that's for later stories)
- Do NOT add agent creation logic yet (just the LLM factory)
- Do NOT use `Optional[str]` syntax (use `str | None`)

### Dependency Verification

Run this to verify LangChain packages are installed:

```bash
uv run python -c "from langchain_google_genai import ChatGoogleGenerativeAI; print('OK')"
uv run python -c "from langchain_anthropic import ChatAnthropic; print('OK')"
uv run python -c "from langchain_ollama import ChatOllama; print('OK')"
```

### Return Type Note

The return type `BaseChatModel` is the abstract base class from LangChain that all chat models inherit from. This allows the factory to return any provider while maintaining type safety.

```python
from langchain_core.language_models.chat_models import BaseChatModel
```

## Dev Agent Record

### Implementation Plan
- Implemented `get_llm` factory function with match/case pattern per architecture.md
- Created `LLMConfigurationError` custom exception with provider and missing_credential attributes
- Added `SUPPORTED_PROVIDERS` list and `DEFAULT_MODELS` dict
- Added `get_default_model(provider)` helper function
- Integrated with existing `get_config()` for credential validation

### Debug Log
- ChatAnthropic uses `model_name` and `api_key` parameters (not `model` and `anthropic_api_key`) due to Pydantic alias configuration
- Added `type: ignore[call-arg]` for ChatAnthropic due to incomplete type stubs in langchain-anthropic

### Completion Notes
- All 5 acceptance criteria satisfied
- 17 new tests in test_agents.py covering all functionality
- All 53 project tests pass (no regressions)
- Lint, format, and type checks pass
- Used Python 3.10+ match/case syntax per architecture pattern

## File List

### New Files
- `tests/test_agents.py` - 17 comprehensive tests for LLM factory

### Modified Files
- `agents.py` - LLM factory implementation (was placeholder docstring)

## Change Log

- 2026-01-25: Implemented Story 1.3 - LLM Provider Integration
  - Added `get_llm()` factory function for Gemini, Claude, Ollama
  - Added `LLMConfigurationError` exception for missing credentials
  - Added `SUPPORTED_PROVIDERS`, `DEFAULT_MODELS`, `get_default_model()`
  - Created comprehensive test suite (17 tests)

- 2026-01-25: Code Review Fixes (Amelia - Dev Agent)
  - Fixed M1/M2: Added `@pytest.fixture(autouse=True)` for config singleton reset
  - Fixed M3: Added `TestModuleExports` class with `__all__` consistency test
  - Fixed M4: Added `.lower()` normalization for provider strings (case-insensitive)
  - Fixed L1: Changed `SUPPORTED_PROVIDERS` from list to `frozenset[str]` (immutable)
  - Added 3 new tests (20 total): provider normalization + exports
  - All 56 project tests pass, lint clean, type check clean
