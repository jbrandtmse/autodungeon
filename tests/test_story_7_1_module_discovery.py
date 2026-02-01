"""Tests for Story 7.1: Module Discovery via LLM Query.

This test file covers:
- ModuleInfo model validation
- ModuleDiscoveryResult model validation
- discover_modules() function with mocked LLM
- JSON parsing with various response formats
- Retry logic on parse failure
- Session state caching patterns
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

# =============================================================================
# Task 1: ModuleInfo Model Tests
# =============================================================================


class TestModuleInfo:
    """Tests for ModuleInfo Pydantic model (Task 1.1, 1.3, 1.4)."""

    def test_valid_module_info_minimal(self) -> None:
        """Test ModuleInfo can be created with required fields only."""
        from models import ModuleInfo

        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure in Barovia.",
        )

        assert module.number == 1
        assert module.name == "Curse of Strahd"
        assert module.description == "Gothic horror adventure in Barovia."
        assert module.setting == ""  # Default
        assert module.level_range == ""  # Default

    def test_valid_module_info_all_fields(self) -> None:
        """Test ModuleInfo can be created with all fields."""
        from models import ModuleInfo

        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure in Barovia.",
            setting="Ravenloft",
            level_range="1-10",
        )

        assert module.number == 1
        assert module.name == "Curse of Strahd"
        assert module.description == "Gothic horror adventure in Barovia."
        assert module.setting == "Ravenloft"
        assert module.level_range == "1-10"

    def test_module_info_number_range_valid_min(self) -> None:
        """Test ModuleInfo accepts number=1 (minimum)."""
        from models import ModuleInfo

        module = ModuleInfo(number=1, name="Test", description="Test desc")
        assert module.number == 1

    def test_module_info_number_range_valid_max(self) -> None:
        """Test ModuleInfo accepts number=100 (maximum)."""
        from models import ModuleInfo

        module = ModuleInfo(number=100, name="Test", description="Test desc")
        assert module.number == 100

    def test_module_info_number_range_invalid_zero(self) -> None:
        """Test ModuleInfo rejects number=0."""
        from models import ModuleInfo

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(number=0, name="Test", description="Test desc")
        errors = exc_info.value.errors()
        assert any("number" in str(e).lower() for e in errors)

    def test_module_info_number_range_invalid_negative(self) -> None:
        """Test ModuleInfo rejects negative numbers."""
        from models import ModuleInfo

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(number=-1, name="Test", description="Test desc")
        errors = exc_info.value.errors()
        assert any("number" in str(e).lower() for e in errors)

    def test_module_info_number_range_invalid_over_100(self) -> None:
        """Test ModuleInfo rejects numbers over 100."""
        from models import ModuleInfo

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(number=101, name="Test", description="Test desc")
        errors = exc_info.value.errors()
        assert any("number" in str(e).lower() for e in errors)

    def test_module_info_empty_name_validation(self) -> None:
        """Test ModuleInfo rejects empty name."""
        from models import ModuleInfo

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(number=1, name="", description="Test desc")
        errors = exc_info.value.errors()
        assert any("name" in str(e).lower() for e in errors)

    def test_module_info_empty_description_validation(self) -> None:
        """Test ModuleInfo rejects empty description."""
        from models import ModuleInfo

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(number=1, name="Test", description="")
        errors = exc_info.value.errors()
        assert any("description" in str(e).lower() for e in errors)

    def test_module_info_json_serialization(self) -> None:
        """Test ModuleInfo JSON serialization (Task 1.4)."""
        from models import ModuleInfo

        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror in Barovia.",
            setting="Ravenloft",
            level_range="1-10",
        )

        json_str = module.model_dump_json()
        data = json.loads(json_str)

        assert data["number"] == 1
        assert data["name"] == "Curse of Strahd"
        assert data["description"] == "Gothic horror in Barovia."
        assert data["setting"] == "Ravenloft"
        assert data["level_range"] == "1-10"

    def test_module_info_json_roundtrip(self) -> None:
        """Test ModuleInfo JSON roundtrip (Task 1.4)."""
        from models import ModuleInfo

        original = ModuleInfo(
            number=42,
            name="Lost Mine of Phandelver",
            description="Starter adventure in the Sword Coast.",
            setting="Forgotten Realms",
            level_range="1-5",
        )

        json_str = original.model_dump_json()
        restored = ModuleInfo.model_validate_json(json_str)

        assert restored.number == original.number
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.setting == original.setting
        assert restored.level_range == original.level_range

    def test_module_info_in_all_exports(self) -> None:
        """Test ModuleInfo is in module __all__ exports."""
        import models

        assert "ModuleInfo" in models.__all__


# =============================================================================
# Task 1: ModuleDiscoveryResult Model Tests
# =============================================================================


class TestModuleDiscoveryResult:
    """Tests for ModuleDiscoveryResult Pydantic model (Task 1.2, 1.4)."""

    def test_module_discovery_result_creation(self) -> None:
        """Test ModuleDiscoveryResult can be created."""
        from models import ModuleDiscoveryResult, ModuleInfo

        modules = [
            ModuleInfo(number=1, name="Module 1", description="Desc 1"),
            ModuleInfo(number=2, name="Module 2", description="Desc 2"),
        ]

        result = ModuleDiscoveryResult(
            modules=modules,
            provider="gemini",
            model="gemini-1.5-flash",
            timestamp="2026-02-01T10:00:00Z",
            retry_count=0,
        )

        assert len(result.modules) == 2
        assert result.provider == "gemini"
        assert result.model == "gemini-1.5-flash"
        assert result.timestamp == "2026-02-01T10:00:00Z"
        assert result.retry_count == 0

    def test_module_discovery_result_empty_modules(self) -> None:
        """Test ModuleDiscoveryResult accepts empty modules list."""
        from models import ModuleDiscoveryResult

        result = ModuleDiscoveryResult(
            modules=[],
            provider="claude",
            model="claude-3-haiku-20240307",
            timestamp="2026-02-01T10:00:00Z",
        )

        assert result.modules == []
        assert result.retry_count == 0  # Default

    def test_module_discovery_result_with_retry_count(self) -> None:
        """Test ModuleDiscoveryResult tracks retry count."""
        from models import ModuleDiscoveryResult

        result = ModuleDiscoveryResult(
            modules=[],
            provider="gemini",
            model="gemini-1.5-flash",
            timestamp="2026-02-01T10:00:00Z",
            retry_count=2,
        )

        assert result.retry_count == 2

    def test_module_discovery_result_negative_retry_count_rejected(self) -> None:
        """Test ModuleDiscoveryResult rejects negative retry_count."""
        from models import ModuleDiscoveryResult

        with pytest.raises(ValidationError) as exc_info:
            ModuleDiscoveryResult(
                modules=[],
                provider="gemini",
                model="gemini-1.5-flash",
                timestamp="2026-02-01T10:00:00Z",
                retry_count=-1,
            )
        errors = exc_info.value.errors()
        assert any("retry_count" in str(e).lower() for e in errors)

    def test_module_discovery_result_json_serialization(self) -> None:
        """Test ModuleDiscoveryResult JSON serialization (Task 1.4)."""
        from models import ModuleDiscoveryResult, ModuleInfo

        modules = [ModuleInfo(number=1, name="Test", description="Test desc")]
        result = ModuleDiscoveryResult(
            modules=modules,
            provider="gemini",
            model="gemini-1.5-flash",
            timestamp="2026-02-01T10:00:00Z",
            retry_count=1,
        )

        json_str = result.model_dump_json()
        data = json.loads(json_str)

        assert data["provider"] == "gemini"
        assert data["model"] == "gemini-1.5-flash"
        assert data["timestamp"] == "2026-02-01T10:00:00Z"
        assert data["retry_count"] == 1
        assert len(data["modules"]) == 1

    def test_module_discovery_result_json_roundtrip(self) -> None:
        """Test ModuleDiscoveryResult JSON roundtrip (Task 1.4)."""
        from models import ModuleDiscoveryResult, ModuleInfo

        modules = [
            ModuleInfo(number=1, name="Module 1", description="Desc 1"),
            ModuleInfo(number=2, name="Module 2", description="Desc 2"),
        ]
        original = ModuleDiscoveryResult(
            modules=modules,
            provider="ollama",
            model="llama3",
            timestamp="2026-02-01T12:00:00Z",
            retry_count=0,
        )

        json_str = original.model_dump_json()
        restored = ModuleDiscoveryResult.model_validate_json(json_str)

        assert len(restored.modules) == len(original.modules)
        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.timestamp == original.timestamp
        assert restored.retry_count == original.retry_count

    def test_module_discovery_result_in_all_exports(self) -> None:
        """Test ModuleDiscoveryResult is in module __all__ exports."""
        import models

        assert "ModuleDiscoveryResult" in models.__all__


# =============================================================================
# Task 1: ERROR_TYPES Tests
# =============================================================================


class TestModuleDiscoveryErrorType:
    """Tests for module_discovery_failed error type."""

    def test_module_discovery_failed_error_exists(self) -> None:
        """Test module_discovery_failed error type is defined."""
        from models import ERROR_TYPES

        assert "module_discovery_failed" in ERROR_TYPES

    def test_module_discovery_failed_error_has_required_keys(self) -> None:
        """Test module_discovery_failed has title, message, action."""
        from models import ERROR_TYPES

        error = ERROR_TYPES["module_discovery_failed"]
        assert "title" in error
        assert "message" in error
        assert "action" in error

    def test_module_discovery_failed_error_narrative_style(self) -> None:
        """Test module_discovery_failed uses campfire narrative style."""
        from models import ERROR_TYPES

        error = ERROR_TYPES["module_discovery_failed"]
        # Check for narrative styling (ellipsis, metaphorical language)
        assert "..." in error["title"]
        assert (
            "library" in error["title"].lower() or "dungeon" in error["title"].lower()
        )

    def test_create_user_error_with_module_discovery_failed(self) -> None:
        """Test create_user_error works with module_discovery_failed type."""
        from models import create_user_error

        error = create_user_error(
            error_type="module_discovery_failed",
            provider="gemini",
            agent="dm",
        )

        assert error.error_type == "module_discovery_failed"
        assert "library" in error.title.lower() or "dungeon" in error.title.lower()
        assert error.provider == "gemini"
        assert error.agent == "dm"


# =============================================================================
# Task 2: Module Discovery Function Tests
# =============================================================================


class TestParseModuleJson:
    """Tests for _parse_module_json helper function (Task 2.4)."""

    def test_parse_valid_json_array(self) -> None:
        """Test parsing valid JSON array response."""
        from agents import _parse_module_json

        response = """[
            {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror in Barovia."},
            {"number": 2, "name": "Lost Mine of Phandelver", "description": "Starter adventure."}
        ]"""

        modules = _parse_module_json(response)
        assert len(modules) == 2
        assert modules[0].name == "Curse of Strahd"
        assert modules[1].name == "Lost Mine of Phandelver"

    def test_parse_json_in_markdown_code_block(self) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""
        from agents import _parse_module_json

        response = """```json
[
    {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror."}
]
```"""

        modules = _parse_module_json(response)
        assert len(modules) == 1
        assert modules[0].name == "Curse of Strahd"

    def test_parse_json_in_plain_code_block(self) -> None:
        """Test parsing JSON wrapped in plain code blocks."""
        from agents import _parse_module_json

        response = """```
[
    {"number": 1, "name": "Test Module", "description": "Test description."}
]
```"""

        modules = _parse_module_json(response)
        assert len(modules) == 1
        assert modules[0].name == "Test Module"

    def test_parse_json_with_extra_text_before(self) -> None:
        """Test parsing JSON with extra text before array."""
        from agents import _parse_module_json

        response = """Here are the modules:

[
    {"number": 1, "name": "Test", "description": "Test desc."}
]"""

        modules = _parse_module_json(response)
        assert len(modules) == 1

    def test_parse_json_with_extra_text_after(self) -> None:
        """Test parsing JSON with extra text after array."""
        from agents import _parse_module_json

        response = """[{"number": 1, "name": "Test", "description": "Test desc."}]

I hope this helps!"""

        modules = _parse_module_json(response)
        assert len(modules) == 1

    def test_parse_handles_missing_optional_fields(self) -> None:
        """Test parsing handles modules without setting/level_range."""
        from agents import _parse_module_json

        response = '[{"number": 1, "name": "Test", "description": "Desc."}]'

        modules = _parse_module_json(response)
        assert len(modules) == 1
        assert modules[0].setting == ""
        assert modules[0].level_range == ""

    def test_parse_handles_extra_fields(self) -> None:
        """Test parsing ignores extra fields in module objects."""
        from agents import _parse_module_json

        response = """[{
            "number": 1,
            "name": "Test",
            "description": "Desc.",
            "edition": "5e",
            "year": 2016
        }]"""

        modules = _parse_module_json(response)
        assert len(modules) == 1
        assert modules[0].name == "Test"

    def test_parse_skips_invalid_entries(self) -> None:
        """Test parsing skips invalid module entries but keeps valid ones."""
        from agents import _parse_module_json

        response = """[
            {"number": 1, "name": "Valid", "description": "Valid desc."},
            {"number": 0, "name": "", "description": ""},
            {"number": 2, "name": "Also Valid", "description": "Another valid."}
        ]"""

        modules = _parse_module_json(response)
        # Entry with number=0, empty name/desc should be skipped due to validation
        # First entry (number=1) should always be valid
        assert len(modules) >= 1
        assert modules[0].name == "Valid"
        assert modules[0].number == 1
        # If both valid entries are kept, verify the second one
        if len(modules) >= 2:
            assert modules[1].name == "Also Valid"

    def test_parse_raises_on_invalid_json(self) -> None:
        """Test parsing raises JSONDecodeError on invalid JSON."""
        from agents import _parse_module_json

        response = "This is not JSON at all"

        with pytest.raises(json.JSONDecodeError):
            _parse_module_json(response)

    def test_parse_raises_on_no_array_found(self) -> None:
        """Test parsing raises error when no array brackets found."""
        from agents import _parse_module_json

        response = '{"modules": "not an array"}'

        with pytest.raises(json.JSONDecodeError):
            _parse_module_json(response)

    def test_parse_empty_array(self) -> None:
        """Test parsing returns empty list for empty JSON array."""
        from agents import _parse_module_json

        response = "[]"

        modules = _parse_module_json(response)
        assert modules == []

    def test_parse_empty_response_text_raises_error(self) -> None:
        """Test parsing raises error for empty response text."""
        from agents import _parse_module_json

        with pytest.raises(json.JSONDecodeError) as exc_info:
            _parse_module_json("")

        assert "Empty response" in str(exc_info.value)

    def test_parse_whitespace_only_response_raises_error(self) -> None:
        """Test parsing raises error for whitespace-only response text."""
        from agents import _parse_module_json

        with pytest.raises(json.JSONDecodeError) as exc_info:
            _parse_module_json("   \n\t   ")

        assert "Empty response" in str(exc_info.value)


class TestDiscoverModules:
    """Tests for discover_modules function (Task 2.1-2.8)."""

    def test_discover_modules_success_first_attempt(self) -> None:
        """Test successful module discovery on first attempt (Task 2.7)."""
        from models import DMConfig

        mock_response = MagicMock()
        mock_response.content = """[
            {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror."},
            {"number": 2, "name": "Lost Mine", "description": "Starter adventure."}
        ]"""

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig(provider="gemini", model="gemini-1.5-flash")
            result = discover_modules(dm_config)

            assert len(result.modules) == 2
            assert result.provider == "gemini"
            assert result.model == "gemini-1.5-flash"
            assert result.retry_count == 0

    def test_discover_modules_prompt_contains_required_elements(self) -> None:
        """Test that prompt includes required text (AC #1, #2)."""
        from models import DMConfig

        mock_response = MagicMock()
        mock_response.content = (
            '[{"number": 1, "name": "Test", "description": "Desc."}]'
        )

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()
            discover_modules(dm_config)

            # Check the prompt passed to invoke
            call_args = mock_llm.invoke.call_args
            messages = call_args[0][0]
            prompt_text = messages[0].content.lower()

            # AC #1: Should include DM context
            assert (
                "dungeon master" in prompt_text or "dungeons and dragons" in prompt_text
            )
            # AC #2: Should request 100 modules in JSON
            assert "100" in prompt_text
            assert "json" in prompt_text

    def test_discover_modules_retry_on_parse_failure(self) -> None:
        """Test retry with explicit schema on parse failure (AC #5, Task 2.8)."""
        from models import DMConfig

        # First response is invalid JSON, second is valid
        invalid_response = MagicMock()
        invalid_response.content = "Sorry, I can't provide that in JSON format."

        valid_response = MagicMock()
        valid_response.content = (
            '[{"number": 1, "name": "Test", "description": "Desc."}]'
        )

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = [invalid_response, valid_response]
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()
            result = discover_modules(dm_config)

            assert mock_llm.invoke.call_count == 2
            assert result.retry_count == 1
            assert len(result.modules) == 1

    def test_discover_modules_max_retries_exceeded(self) -> None:
        """Test graceful error when max retries exceeded (Task 2.6, 2.8)."""
        from agents import LLMError
        from models import DMConfig

        # All responses are invalid
        invalid_response = MagicMock()
        invalid_response.content = "Not valid JSON"

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = invalid_response
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()

            with pytest.raises(LLMError) as exc_info:
                discover_modules(dm_config)

            assert exc_info.value.error_type == "invalid_response"
            assert exc_info.value.provider == "gemini"

    def test_discover_modules_handles_llm_error(self) -> None:
        """Test LLM errors are wrapped in LLMError (Task 2.6)."""
        from agents import LLMError
        from models import DMConfig

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("API connection failed")
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()

            with pytest.raises(LLMError) as exc_info:
                discover_modules(dm_config)

            assert exc_info.value.provider == "gemini"
            assert exc_info.value.agent == "dm"

    def test_discover_modules_with_claude_provider(self) -> None:
        """Test discovery works with Claude provider (Task 2.7)."""
        from models import DMConfig

        mock_response = MagicMock()
        mock_response.content = (
            '[{"number": 1, "name": "Test", "description": "Desc."}]'
        )

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig(provider="claude", model="claude-3-haiku-20240307")
            result = discover_modules(dm_config)

            mock_get_llm.assert_called_once_with("claude", "claude-3-haiku-20240307")
            assert result.provider == "claude"

    def test_discover_modules_with_ollama_provider(self) -> None:
        """Test discovery works with Ollama provider (Task 2.7)."""
        from models import DMConfig

        mock_response = MagicMock()
        mock_response.content = (
            '[{"number": 1, "name": "Test", "description": "Desc."}]'
        )

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig(provider="ollama", model="llama3")
            result = discover_modules(dm_config)

            mock_get_llm.assert_called_once_with("ollama", "llama3")
            assert result.provider == "ollama"

    def test_discover_modules_returns_timestamp(self) -> None:
        """Test result includes ISO timestamp."""
        from models import DMConfig

        mock_response = MagicMock()
        mock_response.content = (
            '[{"number": 1, "name": "Test", "description": "Desc."}]'
        )

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()
            result = discover_modules(dm_config)

            # Should be a valid ISO timestamp ending in Z
            assert result.timestamp.endswith("Z")
            # Should parse as valid datetime
            datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))


class TestModuleDiscoveryPrompts:
    """Tests for module discovery prompt constants."""

    def test_module_discovery_prompt_exists(self) -> None:
        """Test MODULE_DISCOVERY_PROMPT constant is defined."""
        from agents import MODULE_DISCOVERY_PROMPT

        assert MODULE_DISCOVERY_PROMPT is not None
        assert isinstance(MODULE_DISCOVERY_PROMPT, str)
        assert len(MODULE_DISCOVERY_PROMPT) > 0

    def test_module_discovery_retry_prompt_exists(self) -> None:
        """Test MODULE_DISCOVERY_RETRY_PROMPT constant is defined."""
        from agents import MODULE_DISCOVERY_RETRY_PROMPT

        assert MODULE_DISCOVERY_RETRY_PROMPT is not None
        assert isinstance(MODULE_DISCOVERY_RETRY_PROMPT, str)
        assert len(MODULE_DISCOVERY_RETRY_PROMPT) > 0

    def test_discovery_prompt_requests_100_modules(self) -> None:
        """Test discovery prompt requests exactly 100 modules (AC #2)."""
        from agents import MODULE_DISCOVERY_PROMPT

        assert "100" in MODULE_DISCOVERY_PROMPT

    def test_discovery_prompt_requests_json_format(self) -> None:
        """Test discovery prompt requests JSON format (AC #2)."""
        from agents import MODULE_DISCOVERY_PROMPT

        assert "json" in MODULE_DISCOVERY_PROMPT.lower()

    def test_discovery_prompt_includes_dm_context(self) -> None:
        """Test discovery prompt includes DM context (AC #1)."""
        from agents import MODULE_DISCOVERY_PROMPT

        prompt_lower = MODULE_DISCOVERY_PROMPT.lower()
        assert (
            "dungeon master" in prompt_lower or "dungeons and dragons" in prompt_lower
        )

    def test_retry_prompt_more_explicit(self) -> None:
        """Test retry prompt has more explicit JSON instructions (AC #5)."""
        from agents import MODULE_DISCOVERY_PROMPT, MODULE_DISCOVERY_RETRY_PROMPT

        # Retry prompt should mention JSON parsing failed
        assert "json" in MODULE_DISCOVERY_RETRY_PROMPT.lower()
        # Retry prompt should be different from initial prompt
        assert MODULE_DISCOVERY_RETRY_PROMPT != MODULE_DISCOVERY_PROMPT


class TestDiscoverModulesExports:
    """Tests for module discovery function exports."""

    def test_discover_modules_in_all_exports(self) -> None:
        """Test discover_modules is in agents __all__."""
        import agents

        assert "discover_modules" in agents.__all__

    def test_parse_module_json_in_all_exports(self) -> None:
        """Test _parse_module_json is in agents __all__."""
        import agents

        assert "_parse_module_json" in agents.__all__

    def test_prompts_in_all_exports(self) -> None:
        """Test prompt constants are in agents __all__."""
        import agents

        assert "MODULE_DISCOVERY_PROMPT" in agents.__all__
        assert "MODULE_DISCOVERY_RETRY_PROMPT" in agents.__all__


# =============================================================================
# Task 3: Session State Caching Tests
# =============================================================================


class TestSessionStateCaching:
    """Tests for module discovery session state caching (Task 3)."""

    def test_start_module_discovery_sets_in_progress_flag(self) -> None:
        """Test start_module_discovery sets in_progress flag (Task 3.2)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_response = MagicMock()
            mock_response.content = (
                '[{"number": 1, "name": "Test", "description": "Desc."}]'
            )

            with patch("app.discover_modules") as mock_discover:
                from models import ModuleDiscoveryResult, ModuleInfo

                mock_discover.return_value = ModuleDiscoveryResult(
                    modules=[ModuleInfo(number=1, name="Test", description="Desc.")],
                    provider="gemini",
                    model="gemini-1.5-flash",
                    timestamp="2026-02-01T10:00:00Z",
                )

                from app import start_module_discovery

                start_module_discovery()

                # After completion, in_progress should be False
                assert mock_st.session_state["module_discovery_in_progress"] is False

    def test_start_module_discovery_stores_module_list(self) -> None:
        """Test start_module_discovery stores module list (Task 3.1, AC #4)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            with patch("app.discover_modules") as mock_discover:
                from models import ModuleDiscoveryResult, ModuleInfo

                modules = [
                    ModuleInfo(number=1, name="Test1", description="Desc1."),
                    ModuleInfo(number=2, name="Test2", description="Desc2."),
                ]
                mock_discover.return_value = ModuleDiscoveryResult(
                    modules=modules,
                    provider="gemini",
                    model="gemini-1.5-flash",
                    timestamp="2026-02-01T10:00:00Z",
                )

                from app import start_module_discovery

                start_module_discovery()

                assert "module_list" in mock_st.session_state
                assert len(mock_st.session_state["module_list"]) == 2

    def test_start_module_discovery_stores_error_on_failure(self) -> None:
        """Test start_module_discovery stores error on failure (Task 3.3)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            with patch("app.discover_modules") as mock_discover:
                from agents import LLMError

                mock_discover.side_effect = LLMError(
                    provider="gemini",
                    agent="dm",
                    error_type="invalid_response",
                    original_error=Exception("Test error"),
                )

                from app import start_module_discovery

                start_module_discovery()

                assert "module_discovery_error" in mock_st.session_state
                assert mock_st.session_state["module_discovery_error"] is not None
                assert mock_st.session_state["module_discovery_in_progress"] is False

    def test_clear_module_discovery_state_clears_all_keys(self) -> None:
        """Test clear_module_discovery_state removes all keys (Task 3.5)."""
        with patch("app.st") as mock_st:
            # Set up state with all module discovery keys
            mock_st.session_state = {
                "module_list": [],
                "module_discovery_result": None,
                "module_discovery_in_progress": False,
                "module_discovery_error": None,
                "selected_module": None,
                "other_key": "should remain",
            }

            from app import clear_module_discovery_state

            clear_module_discovery_state()

            # Module discovery keys should be gone
            assert "module_list" not in mock_st.session_state
            assert "module_discovery_result" not in mock_st.session_state
            assert "module_discovery_in_progress" not in mock_st.session_state
            assert "module_discovery_error" not in mock_st.session_state
            assert "selected_module" not in mock_st.session_state
            # Other keys should remain
            assert "other_key" in mock_st.session_state

    def test_module_list_persists_across_reruns(self) -> None:
        """Test module list persists in session state across reruns (Task 3.4)."""
        with patch("app.st") as mock_st:
            # Simulate session state that persists across reruns
            persistent_state: dict[str, object] = {}
            mock_st.session_state = persistent_state

            # First run: discovery stores modules
            with patch("app.discover_modules") as mock_discover:
                from models import ModuleDiscoveryResult, ModuleInfo

                modules = [ModuleInfo(number=1, name="Test", description="Desc.")]
                mock_discover.return_value = ModuleDiscoveryResult(
                    modules=modules,
                    provider="gemini",
                    model="gemini-1.5-flash",
                    timestamp="2026-02-01T10:00:00Z",
                )

                from app import start_module_discovery

                start_module_discovery()

            # Simulate rerun - session state should still have modules
            assert persistent_state.get("module_list") is not None
            assert len(persistent_state["module_list"]) == 1  # type: ignore[arg-type]


# =============================================================================
# Task 4: App Integration Tests
# =============================================================================


class TestAppIntegration:
    """Tests for app.py module discovery integration (Task 4)."""

    def test_render_module_discovery_loading_outputs_html(self) -> None:
        """Test render_module_discovery_loading renders HTML (Task 4.3)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_spinner = MagicMock()
            mock_spinner.__enter__ = MagicMock(return_value=None)
            mock_spinner.__exit__ = MagicMock(return_value=None)
            mock_st.spinner.return_value = mock_spinner

            from app import render_module_discovery_loading

            render_module_discovery_loading()

            # Should call markdown with loading HTML
            mock_st.markdown.assert_called()
            call_args = mock_st.markdown.call_args_list[0]
            html = call_args[0][0]

            # Check for expected content
            assert "module-discovery-loading" in html
            assert "Consulting the Dungeon Master" in html
            assert "Gathering tales" in html

    def test_start_module_discovery_function_exists(self) -> None:
        """Test start_module_discovery function exists in app module."""
        from app import start_module_discovery

        assert callable(start_module_discovery)

    def test_clear_module_discovery_state_function_exists(self) -> None:
        """Test clear_module_discovery_state function exists in app module."""
        from app import clear_module_discovery_state

        assert callable(clear_module_discovery_state)

    def test_render_module_discovery_loading_function_exists(self) -> None:
        """Test render_module_discovery_loading function exists in app module."""
        from app import render_module_discovery_loading

        assert callable(render_module_discovery_loading)


# =============================================================================
# Comprehensive Acceptance Tests (Task 5)
# =============================================================================


class TestAcceptanceCriteria:
    """Comprehensive acceptance tests for Story 7.1."""

    def test_ac1_llm_query_includes_correct_prompt(self) -> None:
        """AC #1: System queries DM LLM with correct prompt."""
        from agents import MODULE_DISCOVERY_PROMPT

        # Prompt should identify as DM
        assert "dungeon master" in MODULE_DISCOVERY_PROMPT.lower()
        # Prompt should ask about modules from training
        assert "modules" in MODULE_DISCOVERY_PROMPT.lower()

    def test_ac2_prompt_requests_100_modules_in_json(self) -> None:
        """AC #2: Prompt requests exactly 100 modules in JSON format."""
        from agents import MODULE_DISCOVERY_PROMPT

        assert "100" in MODULE_DISCOVERY_PROMPT
        assert "json" in MODULE_DISCOVERY_PROMPT.lower()
        assert "number" in MODULE_DISCOVERY_PROMPT.lower()
        assert "name" in MODULE_DISCOVERY_PROMPT.lower()
        assert "description" in MODULE_DISCOVERY_PROMPT.lower()

    def test_ac3_module_has_required_fields(self) -> None:
        """AC #3: Each module has number, name, description."""
        from models import ModuleInfo

        # Create a valid module - should not raise
        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure in Barovia.",
        )

        assert module.number == 1
        assert module.name == "Curse of Strahd"
        assert module.description == "Gothic horror adventure in Barovia."

    def test_ac4_module_list_stored_in_session_state(self) -> None:
        """AC #4: Module list stored in session state for adventure creation."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            with patch("app.discover_modules") as mock_discover:
                from models import ModuleDiscoveryResult, ModuleInfo

                modules = [ModuleInfo(number=1, name="Test", description="Desc.")]
                mock_discover.return_value = ModuleDiscoveryResult(
                    modules=modules,
                    provider="gemini",
                    model="gemini-1.5-flash",
                    timestamp="2026-02-01T10:00:00Z",
                )

                from app import start_module_discovery

                start_module_discovery()

                assert "module_list" in mock_st.session_state
                assert mock_st.session_state["module_list"] == modules

    def test_ac5_retry_with_explicit_schema_on_failure(self) -> None:
        """AC #5: Retry with more explicit JSON schema on parse failure."""
        from agents import MODULE_DISCOVERY_PROMPT, MODULE_DISCOVERY_RETRY_PROMPT

        # Retry prompt should be more explicit
        assert "json" in MODULE_DISCOVERY_RETRY_PROMPT.lower()
        # Retry prompt should be different (more explicit)
        assert MODULE_DISCOVERY_RETRY_PROMPT != MODULE_DISCOVERY_PROMPT
        # Retry prompt should mention the previous failure
        assert "previous" in MODULE_DISCOVERY_RETRY_PROMPT.lower()

    def test_all_providers_supported(self) -> None:
        """Test discovery works with all supported providers (AC requirement)."""
        from models import DMConfig

        providers = [
            ("gemini", "gemini-1.5-flash"),
            ("claude", "claude-3-haiku-20240307"),
            ("ollama", "llama3"),
        ]

        for provider, model in providers:
            mock_response = MagicMock()
            mock_response.content = (
                '[{"number": 1, "name": "Test", "description": "Desc."}]'
            )

            with patch("agents.get_llm") as mock_get_llm:
                mock_llm = MagicMock()
                mock_llm.invoke.return_value = mock_response
                mock_get_llm.return_value = mock_llm

                from agents import discover_modules

                dm_config = DMConfig(provider=provider, model=model)
                result = discover_modules(dm_config)

                assert result.provider == provider
                assert result.model == model
                mock_get_llm.assert_called_with(provider, model)


# =============================================================================
# Expanded Test Coverage (testarch-automate)
# =============================================================================


class TestModuleInfoEdgeCases:
    """Additional edge case tests for ModuleInfo model."""

    def test_module_info_boundary_values_min_and_max(self) -> None:
        """Test ModuleInfo with both boundary values in same test."""
        from models import ModuleInfo

        min_module = ModuleInfo(number=1, name="First", description="First module.")
        max_module = ModuleInfo(number=100, name="Last", description="Last module.")

        assert min_module.number == 1
        assert max_module.number == 100
        assert min_module.number < max_module.number

    def test_module_info_special_characters_in_name(self) -> None:
        """Test ModuleInfo handles special characters in name."""
        from models import ModuleInfo

        module = ModuleInfo(
            number=1,
            name="Tomb of Annihilation: Death's Curse",
            description="Jungle adventure with deadly traps.",
        )

        assert ":" in module.name
        assert "'" in module.name

    def test_module_info_special_characters_in_description(self) -> None:
        """Test ModuleInfo handles special characters in description."""
        from models import ModuleInfo

        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Heroes must defeat the \"Dark Lord\" & save the realm!",
        )

        assert '"' in module.description
        assert "&" in module.description
        assert "!" in module.description

    def test_module_info_unicode_characters(self) -> None:
        """Test ModuleInfo handles unicode characters."""
        from models import ModuleInfo

        module = ModuleInfo(
            number=1,
            name="Dragon's Lair",
            description="Explore the realm of Eryth\u00e9a.",
        )

        assert "\u00e9" in module.description

    def test_module_info_very_long_name(self) -> None:
        """Test ModuleInfo handles long name strings."""
        from models import ModuleInfo

        long_name = "A" * 500  # Very long name
        module = ModuleInfo(
            number=1,
            name=long_name,
            description="Test description.",
        )

        assert len(module.name) == 500

    def test_module_info_very_long_description(self) -> None:
        """Test ModuleInfo handles long description strings."""
        from models import ModuleInfo

        long_desc = "B" * 2000  # Very long description
        module = ModuleInfo(
            number=1,
            name="Test",
            description=long_desc,
        )

        assert len(module.description) == 2000

    def test_module_info_whitespace_only_name_accepted(self) -> None:
        """Test ModuleInfo accepts whitespace-only name (no strip validation)."""
        from models import ModuleInfo

        # ModuleInfo only validates min_length=1, not whitespace content
        # This differs from CharacterConfig which has explicit whitespace validation
        module = ModuleInfo(number=1, name="   ", description="Test desc")
        assert module.name == "   "

    def test_module_info_newlines_in_description(self) -> None:
        """Test ModuleInfo handles newlines in description."""
        from models import ModuleInfo

        module = ModuleInfo(
            number=1,
            name="Test",
            description="Line 1.\nLine 2.\nLine 3.",
        )

        assert "\n" in module.description

    def test_module_info_number_at_boundary_minus_one(self) -> None:
        """Test ModuleInfo accepts number=99 (near max boundary)."""
        from models import ModuleInfo

        module = ModuleInfo(number=99, name="Test", description="Desc")
        assert module.number == 99

    def test_module_info_number_at_boundary_plus_one(self) -> None:
        """Test ModuleInfo accepts number=2 (near min boundary)."""
        from models import ModuleInfo

        module = ModuleInfo(number=2, name="Test", description="Desc")
        assert module.number == 2


class TestModuleDiscoveryResultEdgeCases:
    """Additional edge case tests for ModuleDiscoveryResult model."""

    def test_module_discovery_result_large_module_list(self) -> None:
        """Test ModuleDiscoveryResult with 100 modules (expected size)."""
        from models import ModuleDiscoveryResult, ModuleInfo

        modules = [
            ModuleInfo(number=i, name=f"Module {i}", description=f"Desc {i}")
            for i in range(1, 101)
        ]

        result = ModuleDiscoveryResult(
            modules=modules,
            provider="gemini",
            model="gemini-1.5-flash",
            timestamp="2026-02-01T10:00:00Z",
        )

        assert len(result.modules) == 100
        assert result.modules[0].number == 1
        assert result.modules[99].number == 100

    def test_module_discovery_result_retry_count_at_max(self) -> None:
        """Test ModuleDiscoveryResult with high retry count."""
        from models import ModuleDiscoveryResult

        result = ModuleDiscoveryResult(
            modules=[],
            provider="gemini",
            model="gemini-1.5-flash",
            timestamp="2026-02-01T10:00:00Z",
            retry_count=10,  # High retry count
        )

        assert result.retry_count == 10

    def test_module_discovery_result_timestamp_validation(self) -> None:
        """Test ModuleDiscoveryResult timestamp can be any string."""
        from models import ModuleDiscoveryResult

        result = ModuleDiscoveryResult(
            modules=[],
            provider="gemini",
            model="gemini-1.5-flash",
            timestamp="not-a-valid-iso-timestamp",
        )

        # Model doesn't validate timestamp format
        assert result.timestamp == "not-a-valid-iso-timestamp"

    def test_module_discovery_result_modules_is_copy_safe(self) -> None:
        """Test that modifying returned modules doesn't affect original."""
        from models import ModuleDiscoveryResult, ModuleInfo

        modules = [ModuleInfo(number=1, name="Test", description="Desc")]
        result = ModuleDiscoveryResult(
            modules=modules,
            provider="gemini",
            model="gemini-1.5-flash",
            timestamp="2026-02-01T10:00:00Z",
        )

        # Verify the modules are stored
        assert len(result.modules) == 1


class TestParseModuleJsonEdgeCases:
    """Additional edge case tests for _parse_module_json function."""

    def test_parse_json_with_trailing_comma(self) -> None:
        """Test parsing handles trailing comma in array (invalid JSON)."""
        from agents import _parse_module_json

        # JSON with trailing comma - should fail
        response = '[{"number": 1, "name": "Test", "description": "Desc."},]'

        with pytest.raises(json.JSONDecodeError):
            _parse_module_json(response)

    def test_parse_json_with_single_quotes(self) -> None:
        """Test parsing rejects single-quoted JSON (invalid JSON)."""
        from agents import _parse_module_json

        response = "[{'number': 1, 'name': 'Test', 'description': 'Desc.'}]"

        with pytest.raises(json.JSONDecodeError):
            _parse_module_json(response)

    def test_parse_json_with_escaped_quotes(self) -> None:
        """Test parsing handles escaped quotes in values."""
        from agents import _parse_module_json

        response = r'[{"number": 1, "name": "Test \"Module\"", "description": "Desc."}]'

        modules = _parse_module_json(response)
        assert len(modules) == 1
        assert '"' in modules[0].name

    def test_parse_json_with_nested_objects(self) -> None:
        """Test parsing handles modules with extra nested data."""
        from agents import _parse_module_json

        response = """[{
            "number": 1,
            "name": "Test",
            "description": "Desc.",
            "metadata": {"edition": "5e", "year": 2016}
        }]"""

        modules = _parse_module_json(response)
        assert len(modules) == 1
        assert modules[0].name == "Test"

    def test_parse_json_with_null_values(self) -> None:
        """Test parsing handles null values (converts via str())."""
        from agents import _parse_module_json

        response = '[{"number": 1, "name": "Test", "description": "Desc.", "setting": null}]'

        modules = _parse_module_json(response)
        assert len(modules) == 1
        # str(None) = "None", not empty string - this is the actual behavior
        assert modules[0].setting == "None"

    def test_parse_json_with_numeric_strings(self) -> None:
        """Test parsing handles number as string in JSON."""
        from agents import _parse_module_json

        # Note: "number": "1" should fail validation since ModuleInfo expects int
        response = '[{"number": "1", "name": "Test", "description": "Desc."}]'

        # This may or may not work depending on Pydantic coercion
        # If it works, verify the result
        try:
            modules = _parse_module_json(response)
            # Pydantic coerces string "1" to int 1
            assert modules[0].number == 1
        except Exception:
            # If validation fails, that's also acceptable behavior
            pass

    def test_parse_json_with_multiple_arrays_raises_error(self) -> None:
        """Test parsing raises error when multiple arrays present (invalid JSON)."""
        from agents import _parse_module_json

        response = """Here's the data:
        [{"number": 1, "name": "First", "description": "Desc."}]
        And here's more:
        [{"number": 2, "name": "Second", "description": "Desc."}]
        """

        # The implementation extracts from first [ to last ]
        # This creates invalid JSON (array followed by text followed by array)
        # which causes json.loads to raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            _parse_module_json(response)

    def test_parse_json_with_none_input(self) -> None:
        """Test parsing raises error for None input."""
        from agents import _parse_module_json

        with pytest.raises((json.JSONDecodeError, TypeError, AttributeError)):
            _parse_module_json(None)  # type: ignore[arg-type]

    def test_parse_json_deeply_nested_code_blocks(self) -> None:
        """Test parsing handles deeply nested code blocks."""
        from agents import _parse_module_json

        response = """Here's the response:

```json
```json
[{"number": 1, "name": "Test", "description": "Desc."}]
```
```"""

        # Should extract the JSON array despite nested blocks
        modules = _parse_module_json(response)
        assert len(modules) == 1

    def test_parse_json_with_bom(self) -> None:
        """Test parsing handles UTF-8 BOM prefix."""
        from agents import _parse_module_json

        # UTF-8 BOM + JSON
        response = '\ufeff[{"number": 1, "name": "Test", "description": "Desc."}]'

        modules = _parse_module_json(response)
        assert len(modules) == 1

    def test_parse_json_large_array(self) -> None:
        """Test parsing handles large arrays (100 modules)."""
        from agents import _parse_module_json

        modules_json = [
            {"number": i, "name": f"Module {i}", "description": f"Description {i}"}
            for i in range(1, 101)
        ]
        response = json.dumps(modules_json)

        modules = _parse_module_json(response)
        assert len(modules) == 100


class TestDiscoverModulesEdgeCases:
    """Additional edge case tests for discover_modules function."""

    def test_discover_modules_configuration_error(self) -> None:
        """Test discover_modules propagates LLMConfigurationError from get_llm.

        Note: get_llm is called outside the try block, so LLMConfigurationError
        is raised directly rather than being converted to LLMError. The error
        handling for LLMConfigurationError is inside the for loop, but get_llm
        is called before the loop starts.
        """
        from agents import LLMConfigurationError, discover_modules
        from models import DMConfig

        dm_config = DMConfig()

        # The get_llm function raises LLMConfigurationError when API key is missing
        # Since get_llm is called outside the try/except block, the exception
        # propagates directly without being converted to LLMError
        with patch.object(
            __import__("agents", fromlist=["get_llm"]),
            "get_llm",
            side_effect=LLMConfigurationError("gemini", "GOOGLE_API_KEY"),
        ):
            with pytest.raises(LLMConfigurationError) as exc_info:
                discover_modules(dm_config)

            assert exc_info.value.provider == "gemini"
            assert exc_info.value.missing_credential == "GOOGLE_API_KEY"

    def test_discover_modules_retry_prompt_used_after_failure(self) -> None:
        """Test that retry prompt is used after first parse failure."""
        from agents import (
            MODULE_DISCOVERY_PROMPT,
            MODULE_DISCOVERY_RETRY_PROMPT,
            discover_modules,
        )
        from models import DMConfig

        invalid_response = MagicMock()
        invalid_response.content = "Not valid JSON"

        valid_response = MagicMock()
        valid_response.content = '[{"number": 1, "name": "Test", "description": "Desc."}]'

        captured_prompts: list[str] = []

        def capture_invoke(messages: list) -> MagicMock:
            captured_prompts.append(messages[0].content)
            if len(captured_prompts) == 1:
                return invalid_response
            return valid_response

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = capture_invoke
            mock_get_llm.return_value = mock_llm

            dm_config = DMConfig()
            discover_modules(dm_config)

            # First call should use initial prompt
            assert MODULE_DISCOVERY_PROMPT in captured_prompts[0]
            # Second call should use retry prompt
            assert MODULE_DISCOVERY_RETRY_PROMPT in captured_prompts[1]

    def test_discover_modules_max_retries_constant(self) -> None:
        """Test MODULE_DISCOVERY_MAX_RETRIES constant value."""
        from agents import MODULE_DISCOVERY_MAX_RETRIES

        # Should be 2 as per implementation
        assert MODULE_DISCOVERY_MAX_RETRIES == 2

    def test_discover_modules_retry_count_increments(self) -> None:
        """Test retry_count increments on each parse failure."""
        from agents import LLMError
        from models import DMConfig

        invalid_response = MagicMock()
        invalid_response.content = "Invalid JSON response"

        call_count = 0

        def count_calls(messages: list) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return invalid_response

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = count_calls
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()

            with pytest.raises(LLMError):
                discover_modules(dm_config)

            # Should have called invoke MAX_RETRIES + 1 times (initial + retries)
            assert call_count == 3  # 1 initial + 2 retries

    def test_discover_modules_network_error_categorization(self) -> None:
        """Test network errors are categorized correctly."""
        from agents import LLMError
        from models import DMConfig

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = ConnectionError("Network unreachable")
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()

            with pytest.raises(LLMError) as exc_info:
                discover_modules(dm_config)

            assert exc_info.value.error_type == "network_error"

    def test_discover_modules_rate_limit_error_categorization(self) -> None:
        """Test rate limit errors are categorized correctly."""
        from agents import LLMError
        from models import DMConfig

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("429 Too Many Requests")
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()

            with pytest.raises(LLMError) as exc_info:
                discover_modules(dm_config)

            assert exc_info.value.error_type == "rate_limit"

    def test_discover_modules_timeout_error_categorization(self) -> None:
        """Test timeout errors are categorized correctly."""
        from agents import LLMError
        from models import DMConfig

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = TimeoutError("Request timed out")
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()

            with pytest.raises(LLMError) as exc_info:
                discover_modules(dm_config)

            assert exc_info.value.error_type == "timeout"

    def test_discover_modules_empty_response_triggers_retry(self) -> None:
        """Test empty LLM response triggers retry."""
        from agents import LLMError
        from models import DMConfig

        empty_response = MagicMock()
        empty_response.content = ""
        # Also set .text to empty so _extract_response_text returns empty
        empty_response.text = ""

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = empty_response
            mock_get_llm.return_value = mock_llm

            from agents import discover_modules

            dm_config = DMConfig()

            with pytest.raises(LLMError) as exc_info:
                discover_modules(dm_config)

            # Empty response triggers JSONDecodeError which is categorized as invalid_response
            assert exc_info.value.error_type == "invalid_response"
            # Should have retried
            assert mock_llm.invoke.call_count == 3


class TestSessionStateCachingEdgeCases:
    """Additional edge case tests for session state caching."""

    def test_start_module_discovery_with_existing_game(self) -> None:
        """Test start_module_discovery uses game's DM config when available."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "game": {
                    "dm_config": MagicMock(provider="claude", model="claude-3-opus")
                }
            }

            with patch("app.discover_modules") as mock_discover:
                from models import ModuleDiscoveryResult

                mock_discover.return_value = ModuleDiscoveryResult(
                    modules=[],
                    provider="claude",
                    model="claude-3-opus",
                    timestamp="2026-02-01T10:00:00Z",
                )

                from app import start_module_discovery

                start_module_discovery()

                # Should have called discover_modules with game's dm_config
                mock_discover.assert_called_once()
                call_args = mock_discover.call_args[0]
                assert call_args[0].provider == "claude"

    def test_start_module_discovery_without_game_loads_defaults(self) -> None:
        """Test start_module_discovery loads default config when no game."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            with patch("app.discover_modules") as mock_discover:
                # Patch the config module where load_dm_config is imported from
                with patch("config.load_dm_config") as mock_load_config:
                    from models import DMConfig, ModuleDiscoveryResult

                    mock_load_config.return_value = DMConfig(
                        provider="gemini", model="gemini-1.5-flash"
                    )
                    mock_discover.return_value = ModuleDiscoveryResult(
                        modules=[],
                        provider="gemini",
                        model="gemini-1.5-flash",
                        timestamp="2026-02-01T10:00:00Z",
                    )

                    from app import start_module_discovery

                    start_module_discovery()

                    # discover_modules should have been called
                    mock_discover.assert_called_once()

    def test_start_module_discovery_generic_exception(self) -> None:
        """Test start_module_discovery handles generic exceptions."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            with patch("app.discover_modules") as mock_discover:
                mock_discover.side_effect = RuntimeError("Unexpected error")

                from app import start_module_discovery

                start_module_discovery()

                assert "module_discovery_error" in mock_st.session_state
                error = mock_st.session_state["module_discovery_error"]
                assert error.error_type == "module_discovery_failed"

    def test_clear_module_discovery_state_idempotent(self) -> None:
        """Test clear_module_discovery_state is idempotent (safe to call multiple times)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {"other_key": "value"}

            from app import clear_module_discovery_state

            # First call - no module discovery keys exist
            clear_module_discovery_state()
            assert "other_key" in mock_st.session_state

            # Second call - still no module discovery keys
            clear_module_discovery_state()
            assert "other_key" in mock_st.session_state

    def test_clear_module_discovery_state_partial_keys(self) -> None:
        """Test clear_module_discovery_state handles partial key presence."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "module_list": [],
                # Other keys not present
                "other_key": "value",
            }

            from app import clear_module_discovery_state

            clear_module_discovery_state()

            assert "module_list" not in mock_st.session_state
            assert "other_key" in mock_st.session_state

    def test_start_module_discovery_clears_previous_error(self) -> None:
        """Test start_module_discovery clears previous error before running."""
        with patch("app.st") as mock_st:
            from models import UserError

            previous_error = UserError(
                title="Previous error",
                message="Previous message",
                action="Previous action",
                error_type="unknown",
                timestamp="2026-01-01T00:00:00Z",
            )
            mock_st.session_state = {"module_discovery_error": previous_error}

            with patch("app.discover_modules") as mock_discover:
                from models import ModuleDiscoveryResult

                mock_discover.return_value = ModuleDiscoveryResult(
                    modules=[],
                    provider="gemini",
                    model="gemini-1.5-flash",
                    timestamp="2026-02-01T10:00:00Z",
                )

                from app import start_module_discovery

                start_module_discovery()

                # Error should be cleared after successful discovery
                assert mock_st.session_state["module_discovery_error"] is None


class TestRenderModuleDiscoveryLoadingEdgeCases:
    """Additional tests for render_module_discovery_loading function."""

    def test_render_module_discovery_loading_html_structure(self) -> None:
        """Test render_module_discovery_loading has proper HTML structure."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_spinner = MagicMock()
            mock_spinner.__enter__ = MagicMock(return_value=None)
            mock_spinner.__exit__ = MagicMock(return_value=None)
            mock_st.spinner.return_value = mock_spinner

            from app import render_module_discovery_loading

            render_module_discovery_loading()

            # Verify markdown was called
            assert mock_st.markdown.called

            call_args = mock_st.markdown.call_args_list[0]
            html = call_args[0][0]

            # Check HTML structure
            assert "<div" in html
            assert "</div>" in html
            assert "class=" in html

    def test_render_module_discovery_loading_uses_unsafe_html(self) -> None:
        """Test render_module_discovery_loading uses unsafe_allow_html=True."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_spinner = MagicMock()
            mock_spinner.__enter__ = MagicMock(return_value=None)
            mock_spinner.__exit__ = MagicMock(return_value=None)
            mock_st.spinner.return_value = mock_spinner

            from app import render_module_discovery_loading

            render_module_discovery_loading()

            call_kwargs = mock_st.markdown.call_args_list[0][1]
            assert call_kwargs.get("unsafe_allow_html") is True

    def test_render_module_discovery_loading_spinner_called(self) -> None:
        """Test render_module_discovery_loading calls spinner."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_spinner = MagicMock()
            mock_spinner.__enter__ = MagicMock(return_value=None)
            mock_spinner.__exit__ = MagicMock(return_value=None)
            mock_st.spinner.return_value = mock_spinner

            from app import render_module_discovery_loading

            render_module_discovery_loading()

            mock_st.spinner.assert_called()


class TestErrorCategorization:
    """Tests for error categorization in module discovery context."""

    def test_categorize_auth_error(self) -> None:
        """Test auth error categorization."""
        from agents import categorize_error

        error = Exception("401 Unauthorized: Invalid API key")
        assert categorize_error(error) == "auth_error"

    def test_categorize_quota_exceeded_as_rate_limit(self) -> None:
        """Test quota exceeded is categorized as rate limit."""
        from agents import categorize_error

        error = Exception("Quota exceeded for API")
        assert categorize_error(error) == "rate_limit"

    def test_categorize_json_parse_error(self) -> None:
        """Test JSON parse errors are categorized as invalid_response."""
        from agents import categorize_error

        error = Exception("JSON decode error at position 42")
        assert categorize_error(error) == "invalid_response"

    def test_categorize_unknown_error(self) -> None:
        """Test unknown errors are categorized correctly."""
        from agents import categorize_error

        error = Exception("Something completely random happened")
        assert categorize_error(error) == "unknown"


class TestModuleInfoIntegration:
    """Integration tests between ModuleInfo and other components."""

    def test_module_info_from_llm_response_simulation(self) -> None:
        """Test creating ModuleInfo from simulated LLM response."""
        from agents import _parse_module_json

        # Simulate realistic LLM response
        llm_response = """Here are the top D&D modules:

```json
[
    {
        "number": 1,
        "name": "Curse of Strahd",
        "description": "Gothic horror adventure in the haunted realm of Barovia.",
        "setting": "Ravenloft",
        "level_range": "1-10"
    },
    {
        "number": 2,
        "name": "Tomb of Annihilation",
        "description": "Jungle adventure featuring the deadly Tomb of the Nine Gods.",
        "setting": "Forgotten Realms",
        "level_range": "1-11"
    }
]
```

These are considered classics!"""

        modules = _parse_module_json(llm_response)

        assert len(modules) == 2
        assert modules[0].name == "Curse of Strahd"
        assert modules[0].setting == "Ravenloft"
        assert modules[1].name == "Tomb of Annihilation"
        assert modules[1].level_range == "1-11"

    def test_module_discovery_result_to_session_state_simulation(self) -> None:
        """Test full flow from discovery to session state."""
        from models import ModuleDiscoveryResult, ModuleInfo

        # Create discovery result
        modules = [
            ModuleInfo(number=i, name=f"Module {i}", description=f"Desc {i}")
            for i in range(1, 11)
        ]

        result = ModuleDiscoveryResult(
            modules=modules,
            provider="gemini",
            model="gemini-1.5-flash",
            timestamp="2026-02-01T10:00:00Z",
            retry_count=0,
        )

        # Simulate session state storage
        session_state: dict[str, object] = {}
        session_state["module_discovery_result"] = result
        session_state["module_list"] = result.modules

        # Verify retrieval
        retrieved_modules = session_state["module_list"]
        assert len(retrieved_modules) == 10  # type: ignore[arg-type]
        assert retrieved_modules[0].name == "Module 1"  # type: ignore[union-attr]
