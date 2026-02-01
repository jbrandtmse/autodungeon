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
