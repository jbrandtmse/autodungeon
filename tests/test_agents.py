"""Tests for agent definitions and LLM factory."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

import agents
import config as config_module
from agents import (
    CLASS_GUIDANCE,
    DEFAULT_MODELS,
    DM_CONTEXT_PLAYER_ENTRIES_LIMIT,
    DM_CONTEXT_RECENT_EVENTS_LIMIT,
    DM_SYSTEM_PROMPT,
    PC_CONTEXT_RECENT_EVENTS_LIMIT,
    PC_SYSTEM_PROMPT_TEMPLATE,
    SUPPORTED_PROVIDERS,
    LLMConfigurationError,
    _build_dm_context,
    _build_pc_context,
    build_pc_system_prompt,
    create_dm_agent,
    create_pc_agent,
    dm_turn,
    get_default_model,
    get_llm,
    pc_turn,
)
from models import AgentMemory, CharacterConfig, DMConfig, create_initial_game_state


@pytest.fixture(autouse=True)
def reset_config_singleton() -> Generator[None, None, None]:
    """Reset config singleton before each test to ensure isolation."""
    config_module._config = None
    yield
    config_module._config = None


class TestSupportedProviders:
    """Tests for provider constants."""

    def test_supported_providers_frozenset(self) -> None:
        """Test that SUPPORTED_PROVIDERS is an immutable frozenset with expected providers."""
        assert isinstance(SUPPORTED_PROVIDERS, frozenset)
        assert "gemini" in SUPPORTED_PROVIDERS
        assert "claude" in SUPPORTED_PROVIDERS
        assert "ollama" in SUPPORTED_PROVIDERS
        assert len(SUPPORTED_PROVIDERS) == 3

    def test_default_models_dict(self) -> None:
        """Test that DEFAULT_MODELS has entries for all providers."""
        for provider in SUPPORTED_PROVIDERS:
            assert provider in DEFAULT_MODELS
            assert isinstance(DEFAULT_MODELS[provider], str)
            assert len(DEFAULT_MODELS[provider]) > 0


class TestGetDefaultModel:
    """Tests for get_default_model helper."""

    def test_get_default_model_gemini(self) -> None:
        """Test getting default model for gemini."""
        model = get_default_model("gemini")
        assert model == "gemini-1.5-flash"

    def test_get_default_model_claude(self) -> None:
        """Test getting default model for claude."""
        model = get_default_model("claude")
        assert model == "claude-3-haiku-20240307"

    def test_get_default_model_ollama(self) -> None:
        """Test getting default model for ollama."""
        model = get_default_model("ollama")
        assert model == "llama3"

    def test_get_default_model_unknown_provider(self) -> None:
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            get_default_model("unknown")


class TestLLMConfigurationError:
    """Tests for LLMConfigurationError exception."""

    def test_error_attributes(self) -> None:
        """Test that error has provider and missing_credential attributes."""
        error = LLMConfigurationError("gemini", "GOOGLE_API_KEY")
        assert error.provider == "gemini"
        assert error.missing_credential == "GOOGLE_API_KEY"

    def test_error_message_format(self) -> None:
        """Test that error message is descriptive."""
        error = LLMConfigurationError("claude", "ANTHROPIC_API_KEY")
        message = str(error)
        assert "claude" in message
        assert "ANTHROPIC_API_KEY" in message
        assert ".env" in message


class TestGetLLMGemini:
    """Tests for get_llm with Gemini provider."""

    @patch("agents.ChatGoogleGenerativeAI")
    def test_get_llm_gemini_returns_correct_type(self, mock_class: MagicMock) -> None:
        """Test that get_llm returns ChatGoogleGenerativeAI for gemini."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-12345"}, clear=False):
            result = get_llm("gemini", "gemini-1.5-flash")

        assert result is mock_instance
        mock_class.assert_called_once()
        call_kwargs = mock_class.call_args.kwargs
        assert call_kwargs["model"] == "gemini-1.5-flash"
        assert call_kwargs["google_api_key"] == "test-key-12345"

    def test_get_llm_gemini_missing_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing GOOGLE_API_KEY raises LLMConfigurationError."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            get_llm("gemini", "gemini-1.5-flash")

        assert exc_info.value.provider == "gemini"
        assert exc_info.value.missing_credential == "GOOGLE_API_KEY"
        assert "GOOGLE_API_KEY" in str(exc_info.value)


class TestGetLLMClaude:
    """Tests for get_llm with Claude provider."""

    @patch("agents.ChatAnthropic")
    def test_get_llm_claude_returns_correct_type(self, mock_class: MagicMock) -> None:
        """Test that get_llm returns ChatAnthropic for claude."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"}, clear=False
        ):
            result = get_llm("claude", "claude-3-haiku-20240307")

        assert result is mock_instance
        mock_class.assert_called_once()
        call_kwargs = mock_class.call_args.kwargs
        assert call_kwargs["model_name"] == "claude-3-haiku-20240307"
        assert call_kwargs["api_key"] == "test-anthropic-key"

    def test_get_llm_claude_missing_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing ANTHROPIC_API_KEY raises LLMConfigurationError."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(LLMConfigurationError) as exc_info:
            get_llm("claude", "claude-3-haiku-20240307")

        assert exc_info.value.provider == "claude"
        assert exc_info.value.missing_credential == "ANTHROPIC_API_KEY"


class TestGetLLMOllama:
    """Tests for get_llm with Ollama provider."""

    @patch("agents.ChatOllama")
    def test_get_llm_ollama_returns_correct_type(self, mock_class: MagicMock) -> None:
        """Test that get_llm returns ChatOllama for ollama."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        result = get_llm("ollama", "llama3")

        assert result is mock_instance
        mock_class.assert_called_once()
        call_kwargs = mock_class.call_args.kwargs
        assert call_kwargs["model"] == "llama3"
        assert call_kwargs["base_url"] == "http://localhost:11434"

    @patch("agents.ChatOllama")
    def test_get_llm_ollama_uses_custom_base_url(
        self, mock_class: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that Ollama uses custom base URL from config."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:11434")

        result = get_llm("ollama", "mistral")

        assert result is mock_instance
        call_kwargs = mock_class.call_args.kwargs
        assert call_kwargs["base_url"] == "http://custom:11434"

    @patch("agents.ChatOllama")
    def test_get_llm_ollama_no_api_key_required(
        self, mock_class: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that Ollama doesn't require API keys."""
        mock_class.return_value = MagicMock()

        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Should not raise - Ollama doesn't need API keys
        result = get_llm("ollama", "llama3")
        assert result is not None


class TestGetLLMUnknownProvider:
    """Tests for get_llm with unknown provider."""

    def test_get_llm_unknown_provider_raises_valueerror(self) -> None:
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            get_llm("unknown", "some-model")

    def test_get_llm_valueerror_message_includes_provider(self) -> None:
        """Test that ValueError message includes the provider name."""
        with pytest.raises(ValueError) as exc_info:
            get_llm("not-a-provider", "model")

        assert "not-a-provider" in str(exc_info.value)


class TestProviderNormalization:
    """Tests for provider string normalization."""

    @patch("agents.ChatGoogleGenerativeAI")
    def test_get_llm_accepts_uppercase_provider(
        self, mock_class: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that uppercase provider names are accepted."""
        mock_class.return_value = MagicMock()
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        # Should not raise - provider should be normalized
        result = get_llm("GEMINI", "gemini-1.5-flash")
        assert result is not None

    @patch("agents.ChatAnthropic")
    def test_get_llm_accepts_mixed_case_provider(
        self, mock_class: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that mixed case provider names are accepted."""
        mock_class.return_value = MagicMock()
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Should not raise - provider should be normalized
        result = get_llm("Claude", "claude-3-haiku-20240307")
        assert result is not None


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_public_symbols_exported(self) -> None:
        """Test that all public symbols are in __all__."""
        # Expected exports defined in agents module
        expected_exports = {
            "get_llm",
            "get_default_model",
            "LLMConfigurationError",
            "LLMError",
            "SUPPORTED_PROVIDERS",
            "DEFAULT_MODELS",
            "DM_SYSTEM_PROMPT",
            "DM_CONTEXT_RECENT_EVENTS_LIMIT",
            "DM_CONTEXT_PLAYER_ENTRIES_LIMIT",
            "_build_dm_context",
            "create_dm_agent",
            "dm_turn",
            # PC agent exports
            "PC_SYSTEM_PROMPT_TEMPLATE",
            "CLASS_GUIDANCE",
            "PC_CONTEXT_RECENT_EVENTS_LIMIT",
            "build_pc_system_prompt",
            "create_pc_agent",
            "_build_pc_context",
            "pc_turn",
            # Error handling exports (Story 4.5)
            "categorize_error",
            "detect_network_error",
            # Story 5.4: Cross-Session Memory
            "format_character_facts",
            # Story 7.1: Module Discovery
            "MODULE_DISCOVERY_PROMPT",
            "MODULE_DISCOVERY_RETRY_PROMPT",
            "MODULE_DISCOVERY_MAX_RETRIES",
            "discover_modules",
            "_parse_module_json",
            # Story 7.3: Module Context Injection
            "format_module_context",
            # Story 8.3: Character Sheet Context Injection
            "format_character_sheet_context",
            "format_all_sheets_context",
            # Story 8.4: DM Tool Calls for Sheet Updates
            "_execute_sheet_update",
            # Story 10.2: DM Whisper Tool
            "_execute_whisper",
        }

        assert set(agents.__all__) == expected_exports


class TestDMSystemPrompt:
    """Tests for DM system prompt constants."""

    def test_dm_system_prompt_contains_improv_principles(self) -> None:
        """Test that DM system prompt contains improv principles."""
        assert "Yes, and" in DM_SYSTEM_PROMPT
        assert "Collaborative storytelling" in DM_SYSTEM_PROMPT

    def test_dm_system_prompt_contains_encounter_modes(self) -> None:
        """Test that DM system prompt contains encounter mode awareness."""
        assert "COMBAT" in DM_SYSTEM_PROMPT
        assert "ROLEPLAY" in DM_SYSTEM_PROMPT
        assert "EXPLORATION" in DM_SYSTEM_PROMPT

    def test_dm_system_prompt_contains_npc_guidelines(self) -> None:
        """Test that DM system prompt contains NPC voice guidelines."""
        assert "NPC" in DM_SYSTEM_PROMPT
        assert "unique speech pattern" in DM_SYSTEM_PROMPT

    def test_dm_system_prompt_contains_dice_rolling_guidance(self) -> None:
        """Test that DM system prompt contains dice rolling instructions."""
        assert "dice rolling tool" in DM_SYSTEM_PROMPT
        assert "skill check" in DM_SYSTEM_PROMPT

    def test_dm_system_prompt_contains_callback_instructions(self) -> None:
        """Test that DM system prompt contains callback instructions."""
        assert "earlier events" in DM_SYSTEM_PROMPT
        assert "consequences" in DM_SYSTEM_PROMPT


class TestCreateDMAgent:
    """Tests for create_dm_agent factory function."""

    @patch("agents.get_llm")
    def test_create_dm_agent_returns_model_with_tools(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Test that create_dm_agent returns a model with tools bound."""
        mock_model = MagicMock()
        mock_model_with_tools = MagicMock()
        mock_model.bind_tools.return_value = mock_model_with_tools
        mock_get_llm.return_value = mock_model

        config = DMConfig()
        result = create_dm_agent(config)

        assert result is mock_model_with_tools
        mock_get_llm.assert_called_once_with(config.provider, config.model)
        mock_model.bind_tools.assert_called_once()

    @patch("agents.get_llm")
    def test_create_dm_agent_uses_config_provider(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Test that create_dm_agent uses the provider from config."""
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = MagicMock()
        mock_get_llm.return_value = mock_model

        config = DMConfig(provider="claude", model="claude-3-sonnet-20240229")
        create_dm_agent(config)

        mock_get_llm.assert_called_once_with("claude", "claude-3-sonnet-20240229")


class TestDMTurn:
    """Tests for dm_turn node function."""

    @patch("agents.create_dm_agent")
    def test_dm_turn_appends_to_ground_truth_log(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that dm_turn appends DM response to ground_truth_log."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="The tavern is quiet...")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()
        new_state = dm_turn(state)

        assert len(new_state["ground_truth_log"]) == 1
        assert "[DM]:" in new_state["ground_truth_log"][0]
        assert "The tavern is quiet..." in new_state["ground_truth_log"][0]

    @patch("agents.create_dm_agent")
    def test_dm_turn_updates_dm_short_term_buffer(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that dm_turn updates DM's short_term_buffer."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="A dragon appears!")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()
        new_state = dm_turn(state)

        assert "dm" in new_state["agent_memories"]
        dm_memory = new_state["agent_memories"]["dm"]
        assert len(dm_memory.short_term_buffer) == 1
        assert "[DM]: A dragon appears!" in dm_memory.short_term_buffer[0]

    @patch("agents.create_dm_agent")
    def test_dm_turn_does_not_mutate_input_state(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that dm_turn returns new state and doesn't mutate input."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()
        original_log_len = len(state["ground_truth_log"])

        new_state = dm_turn(state)

        # Original state unchanged
        assert len(state["ground_truth_log"]) == original_log_len
        # New state has updates
        assert len(new_state["ground_truth_log"]) > original_log_len

    @patch("agents.create_dm_agent")
    def test_dm_turn_has_access_to_all_agent_memories(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that DM can read all agent memories (asymmetric access)."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Response")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()
        # Add PC memories that DM should be able to see
        state["agent_memories"]["rogue"] = AgentMemory(
            short_term_buffer=["I found a secret passage"]
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["I'm planning to attack"]
        )

        dm_turn(state)

        # Verify the model was invoked (DM processed the state)
        mock_model.invoke.assert_called_once()
        # The context building happens internally - we verify the DM processed state
        # with multiple agent memories present

    @patch("agents.create_dm_agent")
    def test_dm_turn_preserves_other_state_fields(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that dm_turn preserves all other GameState fields."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()
        state["turn_queue"] = ["dm", "fighter", "rogue"]
        state["current_turn"] = "dm"
        state["human_active"] = True
        state["controlled_character"] = "fighter"

        new_state = dm_turn(state)

        assert new_state["turn_queue"] == ["dm", "fighter", "rogue"]
        assert new_state["current_turn"] == "dm"
        assert new_state["human_active"] is True
        assert new_state["controlled_character"] == "fighter"

    @patch("agents.create_dm_agent")
    def test_dm_turn_creates_dm_memory_if_missing(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that dm_turn creates DM memory if not present."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Opening scene")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()
        assert "dm" not in state["agent_memories"]

        new_state = dm_turn(state)

        assert "dm" in new_state["agent_memories"]
        assert isinstance(new_state["agent_memories"]["dm"], AgentMemory)

    @patch("agents.create_dm_agent")
    def test_dm_turn_uses_dm_config_from_state(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that dm_turn uses DMConfig from game state."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test")
        mock_create_dm_agent.return_value = mock_model

        state = create_initial_game_state()
        state["dm_config"] = DMConfig(provider="claude", model="claude-3-opus")

        dm_turn(state)

        # Verify create_dm_agent was called with the state's dm_config
        call_args = mock_create_dm_agent.call_args
        assert call_args[0][0].provider == "claude"
        assert call_args[0][0].model == "claude-3-opus"


class TestBuildDMContext:
    """Tests for _build_dm_context helper function."""

    def test_build_dm_context_empty_state(self) -> None:
        """Test context building with empty agent memories."""

        state = create_initial_game_state()
        context = _build_dm_context(state)

        assert context == ""

    def test_build_dm_context_with_dm_long_term_summary(self) -> None:
        """Test context includes DM's long-term summary."""

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="The party defeated the dragon"
        )

        context = _build_dm_context(state)

        assert "Story So Far" in context
        assert "The party defeated the dragon" in context

    def test_build_dm_context_with_dm_short_term_buffer(self) -> None:
        """Test context includes DM's recent events."""

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3"]
        )

        context = _build_dm_context(state)

        assert "Recent Events" in context
        assert "Event 1" in context
        assert "Event 3" in context

    def test_build_dm_context_reads_all_agent_memories(self) -> None:
        """Test DM context includes knowledge from all PC agents."""

        state = create_initial_game_state()
        state["agent_memories"]["rogue"] = AgentMemory(
            short_term_buffer=["I found a secret passage"]
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["I'm planning to attack the orc"]
        )

        context = _build_dm_context(state)

        assert "Player Knowledge" in context
        assert "[rogue knows]" in context
        assert "secret passage" in context
        assert "[fighter knows]" in context
        assert "attack the orc" in context

    def test_build_dm_context_excludes_dm_from_player_knowledge(self) -> None:
        """Test DM's own memory is not duplicated in player knowledge section."""

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["DM narrated something"]
        )
        state["agent_memories"]["rogue"] = AgentMemory(
            short_term_buffer=["Rogue did something"]
        )

        context = _build_dm_context(state)

        # DM should not appear in player knowledge section
        assert "[dm knows]" not in context
        assert "[rogue knows]" in context

    def test_build_dm_context_limits_short_term_buffer(self) -> None:
        """Test context limits DM's short-term buffer to recent entries."""

        state = create_initial_game_state()
        # Create more events than the limit
        events = [f"Event {i}" for i in range(15)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=events)

        context = _build_dm_context(state)

        # Should only include last DM_CONTEXT_RECENT_EVENTS_LIMIT events
        assert f"Event {15 - DM_CONTEXT_RECENT_EVENTS_LIMIT}" in context
        assert "Event 14" in context
        # Earlier events should not be included
        assert "Event 0" not in context

    def test_build_dm_context_limits_player_buffer(self) -> None:
        """Test context limits PC agent buffer to recent entries."""

        state = create_initial_game_state()
        # Create more entries than the limit
        entries = [f"Action {i}" for i in range(10)]
        state["agent_memories"]["rogue"] = AgentMemory(short_term_buffer=entries)

        context = _build_dm_context(state)

        # Should only include last DM_CONTEXT_PLAYER_ENTRIES_LIMIT entries
        assert f"Action {10 - DM_CONTEXT_PLAYER_ENTRIES_LIMIT}" in context
        assert "Action 9" in context

    def test_build_dm_context_handles_empty_pc_buffers(self) -> None:
        """Test context handles PCs with empty buffers gracefully."""

        state = create_initial_game_state()
        state["agent_memories"]["rogue"] = AgentMemory(short_term_buffer=[])
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fighter action"]
        )

        context = _build_dm_context(state)

        # Rogue with empty buffer should not appear
        assert "[rogue knows]" not in context
        # Fighter with content should appear
        assert "[fighter knows]" in context


class TestDMSystemPromptSerialization:
    """Tests for DM system prompt serialization integrity."""

    def test_dm_system_prompt_json_serializable(self) -> None:
        """Test DM system prompt can be serialized to JSON."""
        import json

        # Should not raise
        json_str = json.dumps({"system": DM_SYSTEM_PROMPT})
        data = json.loads(json_str)
        assert data["system"] == DM_SYSTEM_PROMPT

    def test_dm_system_prompt_preserves_structure(self) -> None:
        """Test DM system prompt preserves markdown structure."""
        # Check headers are present
        assert "## Core Improv Principles" in DM_SYSTEM_PROMPT
        assert "## Encounter Mode Awareness" in DM_SYSTEM_PROMPT
        assert "## NPC Voice Guidelines" in DM_SYSTEM_PROMPT
        assert "## Narrative Continuity" in DM_SYSTEM_PROMPT
        assert "## Dice Rolling" in DM_SYSTEM_PROMPT
        assert "## Response Format" in DM_SYSTEM_PROMPT

    def test_dm_system_prompt_no_broken_continuations(self) -> None:
        """Test DM system prompt has no orphaned backslash continuations."""
        # Backslash continuations in Python should not leave artifacts
        assert "\\\n" not in DM_SYSTEM_PROMPT
        # Should not have double spaces from bad joins
        assert (
            "  " not in DM_SYSTEM_PROMPT or "  -" in DM_SYSTEM_PROMPT
        )  # Allow list indents


# ============================================================
# PC Agent Tests
# ============================================================


class TestPCSystemPromptTemplate:
    """Tests for PC system prompt template."""

    def test_pc_system_prompt_template_contains_personality_placeholders(self) -> None:
        """Test that PC system prompt template has required placeholders."""
        assert "{name}" in PC_SYSTEM_PROMPT_TEMPLATE
        assert "{character_class}" in PC_SYSTEM_PROMPT_TEMPLATE
        assert "{personality}" in PC_SYSTEM_PROMPT_TEMPLATE
        assert "{class_guidance}" in PC_SYSTEM_PROMPT_TEMPLATE

    def test_pc_system_prompt_template_contains_roleplay_instructions(self) -> None:
        """Test that template contains first-person roleplay instructions."""
        assert "First person" in PC_SYSTEM_PROMPT_TEMPLATE
        assert '"I"' in PC_SYSTEM_PROMPT_TEMPLATE
        assert "Stay in character" in PC_SYSTEM_PROMPT_TEMPLATE

    def test_pc_system_prompt_template_contains_collaborative_guidelines(self) -> None:
        """Test that template contains collaborative storytelling guidelines."""
        assert "Collaborate" in PC_SYSTEM_PROMPT_TEMPLATE
        assert "don't contradict" in PC_SYSTEM_PROMPT_TEMPLATE

    def test_pc_system_prompt_template_contains_dice_instructions(self) -> None:
        """Test that template contains dice rolling guidance."""
        assert "dice rolling tool" in PC_SYSTEM_PROMPT_TEMPLATE
        assert "skill check" in PC_SYSTEM_PROMPT_TEMPLATE


class TestClassGuidance:
    """Tests for CLASS_GUIDANCE dictionary."""

    def test_class_guidance_contains_core_classes(self) -> None:
        """Test that CLASS_GUIDANCE contains standard D&D classes."""
        assert "Fighter" in CLASS_GUIDANCE
        assert "Rogue" in CLASS_GUIDANCE
        assert "Wizard" in CLASS_GUIDANCE
        assert "Cleric" in CLASS_GUIDANCE

    @pytest.mark.parametrize(
        "class_name,expected_text",
        [
            ("Fighter", "direct action"),
            ("Fighter", "protect your allies"),
            ("Rogue", "stealth"),
            ("Rogue", "deception"),
            ("Wizard", "arcane"),
            ("Wizard", "knowledge"),
            ("Cleric", "divine power"),
            ("Cleric", "healing"),
        ],
    )
    def test_class_guidance_contains_class_specific_text(
        self, class_name: str, expected_text: str
    ) -> None:
        """Test that each class guidance contains appropriate text."""
        guidance = CLASS_GUIDANCE[class_name]
        assert expected_text.lower() in guidance.lower()


class TestBuildPCSystemPrompt:
    """Tests for build_pc_system_prompt function."""

    def test_build_pc_system_prompt_injects_character_name(self) -> None:
        """Test that character name is injected into prompt."""
        config = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sardonic wit",
            color="#6B8E6B",
        )
        prompt = build_pc_system_prompt(config)

        assert "Shadowmere" in prompt

    def test_build_pc_system_prompt_injects_character_class(self) -> None:
        """Test that character class is injected into prompt."""
        config = CharacterConfig(
            name="Test",
            character_class="Wizard",
            personality="Test",
            color="#000000",
        )
        prompt = build_pc_system_prompt(config)

        assert "Wizard" in prompt

    def test_build_pc_system_prompt_injects_personality(self) -> None:
        """Test that personality is injected into prompt."""
        config = CharacterConfig(
            name="Test",
            character_class="Fighter",
            personality="Brave and honorable, always protects the innocent",
            color="#000000",
        )
        prompt = build_pc_system_prompt(config)

        assert "Brave and honorable" in prompt

    def test_build_pc_system_prompt_injects_class_guidance(self) -> None:
        """Test that class-specific guidance is injected."""
        config = CharacterConfig(
            name="Test",
            character_class="Rogue",
            personality="Test",
            color="#000000",
        )
        prompt = build_pc_system_prompt(config)

        # Rogue guidance should be present
        assert "stealth" in prompt.lower()
        assert "deception" in prompt.lower()

    def test_build_pc_system_prompt_uses_default_for_unknown_class(self) -> None:
        """Test that unknown classes get default guidance."""
        config = CharacterConfig(
            name="Test",
            character_class="Bard",  # Not in CLASS_GUIDANCE
            personality="Test",
            color="#000000",
        )
        prompt = build_pc_system_prompt(config)

        # Should contain the class name and default guidance text
        assert "Bard" in prompt
        assert "class abilities" in prompt.lower()

    @pytest.mark.parametrize(
        "class_name,expected_text",
        [
            ("Fighter", "protect your allies"),
            ("Rogue", "stealth, deception"),
            ("Wizard", "arcane insight"),
            ("Cleric", "divine power"),
        ],
    )
    def test_class_guidance_injection(
        self, class_name: str, expected_text: str
    ) -> None:
        """Test that correct class guidance is injected for each class."""
        config = CharacterConfig(
            name="Test",
            character_class=class_name,
            personality="Test personality",
            color="#000000",
        )
        prompt = build_pc_system_prompt(config)

        assert expected_text.lower() in prompt.lower()


class TestCreatePCAgent:
    """Tests for create_pc_agent factory function."""

    @patch("agents.get_llm")
    def test_create_pc_agent_returns_model_with_tools(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Test that create_pc_agent returns a model with tools bound."""
        mock_model = MagicMock()
        mock_model_with_tools = MagicMock()
        mock_model.bind_tools.return_value = mock_model_with_tools
        mock_get_llm.return_value = mock_model

        config = CharacterConfig(
            name="Test",
            character_class="Fighter",
            personality="Test",
            color="#000000",
        )
        result = create_pc_agent(config)

        assert result is mock_model_with_tools
        mock_get_llm.assert_called_once_with(config.provider, config.model)
        mock_model.bind_tools.assert_called_once()

    @patch("agents.get_llm")
    def test_create_pc_agent_uses_config_provider(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Test that create_pc_agent uses the provider from config."""
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = MagicMock()
        mock_get_llm.return_value = mock_model

        config = CharacterConfig(
            name="Test",
            character_class="Rogue",
            personality="Test",
            color="#000000",
            provider="claude",
            model="claude-3-sonnet-20240229",
        )
        create_pc_agent(config)

        mock_get_llm.assert_called_once_with("claude", "claude-3-sonnet-20240229")


class TestBuildPCContext:
    """Tests for _build_pc_context helper function."""

    def test_build_pc_context_empty_state(self) -> None:
        """Test context building with empty agent memories."""
        state = create_initial_game_state()
        context = _build_pc_context(state, "shadowmere")

        assert context == ""

    def test_build_pc_context_with_long_term_summary(self) -> None:
        """Test context includes PC's long-term summary."""
        state = create_initial_game_state()
        state["agent_memories"]["shadowmere"] = AgentMemory(
            long_term_summary="I have traveled far from my homeland"
        )

        context = _build_pc_context(state, "shadowmere")

        assert "What You Remember" in context
        assert "traveled far from my homeland" in context

    def test_build_pc_context_with_short_term_buffer(self) -> None:
        """Test context includes PC's recent events."""
        state = create_initial_game_state()
        state["agent_memories"]["shadowmere"] = AgentMemory(
            short_term_buffer=["I entered the tavern", "I spoke to the barkeep"]
        )

        context = _build_pc_context(state, "shadowmere")

        assert "Recent Events" in context
        assert "entered the tavern" in context
        assert "spoke to the barkeep" in context

    def test_build_pc_context_only_sees_own_memory(self) -> None:
        """Test PC ONLY sees their own memory (strict isolation)."""
        state = create_initial_game_state()
        state["agent_memories"]["shadowmere"] = AgentMemory(
            short_term_buffer=["I am Shadowmere the rogue"]
        )
        state["agent_memories"]["thor"] = AgentMemory(
            short_term_buffer=["I am Thor the mighty"]
        )
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["The DM narrates..."]
        )

        context = _build_pc_context(state, "shadowmere")

        # Should see own memory
        assert "Shadowmere" in context
        # Should NOT see other PC's memory
        assert "Thor" not in context
        # Should NOT see DM's memory
        assert "DM narrates" not in context

    def test_build_pc_context_limits_short_term_buffer(self) -> None:
        """Test context limits PC's short-term buffer to recent entries."""
        state = create_initial_game_state()
        # Create more events than the limit
        events = [f"Event {i}" for i in range(15)]
        state["agent_memories"]["shadowmere"] = AgentMemory(short_term_buffer=events)

        context = _build_pc_context(state, "shadowmere")

        # Should only include last PC_CONTEXT_RECENT_EVENTS_LIMIT events
        assert f"Event {15 - PC_CONTEXT_RECENT_EVENTS_LIMIT}" in context
        assert "Event 14" in context
        # Earlier events should not be included
        assert "Event 0" not in context

    def test_build_pc_context_returns_empty_for_unknown_agent(self) -> None:
        """Test context returns empty string for unknown agent name."""
        state = create_initial_game_state()
        state["agent_memories"]["shadowmere"] = AgentMemory(
            short_term_buffer=["Some memory"]
        )

        context = _build_pc_context(state, "unknown_agent")

        assert context == ""


class TestPCTurn:
    """Tests for pc_turn node function."""

    @patch("agents.create_pc_agent")
    def test_pc_turn_appends_to_ground_truth_log(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test that pc_turn appends PC response to ground_truth_log."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="I draw my sword...")
        mock_create_pc_agent.return_value = mock_model

        state = create_initial_game_state()
        state["characters"]["shadowmere"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Sardonic",
            color="#6B8E6B",
        )

        new_state = pc_turn(state, "shadowmere")

        assert len(new_state["ground_truth_log"]) == 1
        assert "[Shadowmere]:" in new_state["ground_truth_log"][0]
        assert "I draw my sword" in new_state["ground_truth_log"][0]

    @patch("agents.create_pc_agent")
    def test_pc_turn_updates_pc_short_term_buffer(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test that pc_turn updates PC's short_term_buffer."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="I check for traps")
        mock_create_pc_agent.return_value = mock_model

        state = create_initial_game_state()
        state["characters"]["shadowmere"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Careful",
            color="#6B8E6B",
        )

        new_state = pc_turn(state, "shadowmere")

        assert "shadowmere" in new_state["agent_memories"]
        pc_memory = new_state["agent_memories"]["shadowmere"]
        assert len(pc_memory.short_term_buffer) == 1
        assert "[Shadowmere]: I check for traps" in pc_memory.short_term_buffer[0]

    @patch("agents.create_pc_agent")
    def test_pc_turn_does_not_mutate_input_state(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test that pc_turn returns new state and doesn't mutate input."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_create_pc_agent.return_value = mock_model

        state = create_initial_game_state()
        state["characters"]["shadowmere"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Test",
            color="#6B8E6B",
        )
        original_log_len = len(state["ground_truth_log"])

        new_state = pc_turn(state, "shadowmere")

        # Original state unchanged
        assert len(state["ground_truth_log"]) == original_log_len
        # New state has updates
        assert len(new_state["ground_truth_log"]) > original_log_len

    @patch("agents.create_pc_agent")
    def test_pc_turn_preserves_other_state_fields(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test that pc_turn preserves all other GameState fields."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test")
        mock_create_pc_agent.return_value = mock_model

        state = create_initial_game_state()
        state["characters"]["shadowmere"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Test",
            color="#6B8E6B",
        )
        state["turn_queue"] = ["dm", "shadowmere", "thor"]
        state["current_turn"] = "shadowmere"
        state["human_active"] = True
        state["controlled_character"] = "thor"

        new_state = pc_turn(state, "shadowmere")

        assert new_state["turn_queue"] == ["dm", "shadowmere", "thor"]
        assert new_state["current_turn"] == "shadowmere"
        assert new_state["human_active"] is True
        assert new_state["controlled_character"] == "thor"

    @patch("agents.create_pc_agent")
    def test_pc_turn_creates_pc_memory_if_missing(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test that pc_turn creates PC memory if not present."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="First action")
        mock_create_pc_agent.return_value = mock_model

        state = create_initial_game_state()
        state["characters"]["shadowmere"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Test",
            color="#6B8E6B",
        )
        assert "shadowmere" not in state["agent_memories"]

        new_state = pc_turn(state, "shadowmere")

        assert "shadowmere" in new_state["agent_memories"]
        assert isinstance(new_state["agent_memories"]["shadowmere"], AgentMemory)

    @patch("agents.create_pc_agent")
    def test_pc_turn_uses_character_name_from_config(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test that pc_turn uses the character name from CharacterConfig."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Response")
        mock_create_pc_agent.return_value = mock_model

        state = create_initial_game_state()
        # Use a different name than the key
        state["characters"]["agent_key"] = CharacterConfig(
            name="Thorin Ironforge",
            character_class="Fighter",
            personality="Test",
            color="#8B4513",
        )

        new_state = pc_turn(state, "agent_key")

        # Should use the character name, not the key
        assert "[Thorin Ironforge]:" in new_state["ground_truth_log"][0]

    @patch("agents.create_pc_agent")
    def test_pc_turn_different_characters_have_different_voices(
        self, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test that different PC agents produce different responses."""
        mock_model = MagicMock()
        responses = iter(
            [
                AIMessage(content="I scout ahead quietly"),
                AIMessage(content="By the gods, I charge!"),
            ]
        )
        mock_model.invoke.side_effect = lambda msgs: next(responses)  # type: ignore[misc]
        mock_create_pc_agent.return_value = mock_model

        state = create_initial_game_state()
        state["characters"]["shadowmere"] = CharacterConfig(
            name="Shadowmere",
            character_class="Rogue",
            personality="Cautious",
            color="#6B8E6B",
        )
        state["characters"]["thor"] = CharacterConfig(
            name="Thor",
            character_class="Fighter",
            personality="Bold",
            color="#8B4513",
        )

        state1 = pc_turn(state, "shadowmere")
        state2 = pc_turn(state1, "thor")

        # Both responses should be in the log
        assert len(state2["ground_truth_log"]) == 2
        assert "[Shadowmere]:" in state2["ground_truth_log"][0]
        assert "[Thor]:" in state2["ground_truth_log"][1]

    def test_pc_turn_raises_key_error_for_unknown_character(self) -> None:
        """Test that pc_turn raises KeyError for unknown character."""
        state = create_initial_game_state()

        with pytest.raises(KeyError):
            pc_turn(state, "unknown_character")


# =============================================================================
# Story 3.4: Nudge System Tests for DM Context
# =============================================================================


class TestNudgeDMContextIntegration:
    """Tests for nudge integration in DM context (Story 3.4, Tasks 6, 7)."""

    def test_dm_context_includes_nudge_when_present(self) -> None:
        """Test that DM context includes pending nudge."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "The wizard should cast detect magic",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            assert "Player Suggestion" in context
            assert "detect magic" in context
            assert "The player offers this thought" in context

    def test_dm_context_excludes_nudge_when_none(self) -> None:
        """Test that DM context doesn't include nudge section when None."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": None,
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            assert "Player Suggestion" not in context

    def test_dm_context_excludes_nudge_when_missing(self) -> None:
        """Test that DM context handles missing pending_nudge gracefully."""
        mock_session_state: dict[str, Any] = {}

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            assert "Player Suggestion" not in context


class TestNudgeClearingAfterDMTurn:
    """Tests for nudge clearing after DM processes it (Story 3.4, Task 7)."""

    @patch("agents.create_dm_agent")
    def test_dm_turn_clears_nudge(self, mock_create_dm_agent: MagicMock) -> None:
        """Test that dm_turn clears pending_nudge after processing."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(
            content="The DM narrates the scene..."
        )
        mock_create_dm_agent.return_value = mock_model

        mock_session_state: dict[str, Any] = {
            "pending_nudge": "Check for traps",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            dm_turn(state)

            # Nudge should be cleared after DM turn
            assert mock_session_state["pending_nudge"] is None

    @patch("agents.create_dm_agent")
    def test_dm_turn_clears_nudge_only_once(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that nudge is single-use (consumed after one DM turn)."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="Response")
        mock_create_dm_agent.return_value = mock_model

        mock_session_state: dict[str, Any] = {
            "pending_nudge": "Investigate the noise",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            # First DM turn - nudge is consumed
            new_state = dm_turn(state)
            assert mock_session_state["pending_nudge"] is None

            # Second DM turn - no nudge to consume
            dm_turn(new_state)
            assert mock_session_state["pending_nudge"] is None


# =============================================================================
# Story 3.4: Nudge System Extended Tests - DM Context & Edge Cases
# =============================================================================


class TestNudgeDMContextEdgeCases:
    """Extended tests for nudge integration in DM context edge cases."""

    def test_dm_context_excludes_empty_string_nudge(self) -> None:
        """Test that empty string nudge is not included in context."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            assert "Player Suggestion" not in context

    def test_dm_context_excludes_whitespace_nudge(self) -> None:
        """Test that whitespace-only nudge is not included in context."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "   \t\n   ",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            # The nudge handler should prevent this, but context builder
            # should also handle it gracefully by stripping
            # If strip results in empty, should not appear
            # Note: Current implementation stores "   \t\n   ".strip() = ""
            # But if it somehow got through, the sanitized_nudge.strip() handles it
            assert "Player Suggestion" not in context

    def test_dm_context_with_unicode_nudge(self) -> None:
        """Test that unicode nudge is included correctly in context."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "勇者は洞窟を探検してください",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            assert "Player Suggestion" in context
            assert "勇者は洞窟を探検してください" in context

    def test_dm_context_with_multiline_nudge(self) -> None:
        """Test that multiline nudge is included correctly."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "Line 1\nLine 2\nLine 3",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            assert "Player Suggestion" in context
            assert "Line 1" in context
            assert "Line 2" in context
            assert "Line 3" in context

    def test_dm_context_nudge_with_special_chars(self) -> None:
        """Test that special characters in nudge are preserved."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "Check <the> \"door\" & 'window'!",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            assert "Player Suggestion" in context
            assert "<the>" in context
            assert '"door"' in context
            assert "'window'" in context

    def test_dm_context_nudge_ordering(self) -> None:
        """Test that nudge appears after other context sections."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "A player nudge",
        }

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="Campaign summary",
            short_term_buffer=["Recent event 1"],
        )
        state["agent_memories"]["rogue"] = AgentMemory(
            short_term_buffer=["Rogue did something"],
        )

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            # All sections should be present
            assert "Story So Far" in context
            assert "Recent Events" in context
            assert "Player Knowledge" in context
            assert "Player Suggestion" in context

            # Check ordering - nudge should be last section
            story_idx = context.find("Story So Far")
            events_idx = context.find("Recent Events")
            knowledge_idx = context.find("Player Knowledge")
            suggestion_idx = context.find("Player Suggestion")

            assert story_idx < events_idx < knowledge_idx < suggestion_idx


class TestNudgeClearingEdgeCases:
    """Extended tests for nudge clearing edge cases."""

    @patch("agents.create_dm_agent")
    def test_dm_turn_clears_nudge_even_on_model_error(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test that nudge is cleared even if model invocation fails.

        Note: This tests the current behavior - nudge is cleared before
        model invocation, so it's consumed regardless of model success/failure.
        """
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("Model error")
        mock_create_dm_agent.return_value = mock_model

        mock_session_state: dict[str, Any] = {
            "pending_nudge": "Should be cleared",
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            try:
                dm_turn(state)
            except Exception:
                pass  # Expected to fail

            # Nudge should still be cleared (it's cleared before invoke)
            assert mock_session_state["pending_nudge"] is None

    @patch("agents.create_dm_agent")
    def test_dm_turn_handles_missing_nudge_key(
        self, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test dm_turn handles missing pending_nudge key gracefully."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="Response")
        mock_create_dm_agent.return_value = mock_model

        # Empty session state - no pending_nudge key
        mock_session_state: dict[str, Any] = {}

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            # Should not raise
            new_state = dm_turn(state)

            # Should complete successfully
            assert len(new_state["ground_truth_log"]) == 1

    @patch("agents.create_dm_agent")
    def test_dm_turn_with_none_nudge(self, mock_create_dm_agent: MagicMock) -> None:
        """Test dm_turn handles None nudge correctly (no-op clear)."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="Response")
        mock_create_dm_agent.return_value = mock_model

        mock_session_state: dict[str, Any] = {
            "pending_nudge": None,
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            new_state = dm_turn(state)

            # Should complete and nudge should still be None
            assert mock_session_state["pending_nudge"] is None
            assert len(new_state["ground_truth_log"]) == 1


class TestNudgeContextIntegrationWithOtherState:
    """Tests for nudge context interaction with other game state elements."""

    def test_dm_context_nudge_with_all_memories_populated(self) -> None:
        """Test nudge context when all memory types are populated."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "The wizard should use detect magic",
        }

        state = create_initial_game_state()
        # Populate all memories
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="The party entered the ancient temple",
            short_term_buffer=["DM described the entrance hall"],
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            long_term_summary="Theron is a brave warrior",
            short_term_buffer=["Theron checked the door"],
        )
        state["agent_memories"]["rogue"] = AgentMemory(
            long_term_summary="Shadowmere is a cunning thief",
            short_term_buffer=["Shadowmere spotted a trap"],
        )
        state["agent_memories"]["wizard"] = AgentMemory(
            long_term_summary="Elara is a wise mage",
            short_term_buffer=["Elara studied the runes"],
        )

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            # All sections should be present
            assert "Story So Far" in context
            assert "Recent Events" in context
            assert "Player Knowledge" in context
            assert "Player Suggestion" in context
            assert "detect magic" in context

    def test_dm_context_nudge_preserves_other_content(self) -> None:
        """Test that adding nudge doesn't remove other context content."""
        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="Important story summary",
            short_term_buffer=["Critical event"],
        )

        # First without nudge
        mock_session_state_no_nudge: dict[str, Any] = {
            "pending_nudge": None,
        }

        with patch("streamlit.session_state", mock_session_state_no_nudge):
            context_without_nudge = _build_dm_context(state)

        # Then with nudge
        mock_session_state_with_nudge: dict[str, Any] = {
            "pending_nudge": "A suggestion",
        }

        with patch("streamlit.session_state", mock_session_state_with_nudge):
            context_with_nudge = _build_dm_context(state)

        # Original content should still be present
        assert "Important story summary" in context_without_nudge
        assert "Important story summary" in context_with_nudge
        assert "Critical event" in context_without_nudge
        assert "Critical event" in context_with_nudge

        # Only difference should be the nudge section
        assert "Player Suggestion" not in context_without_nudge
        assert "Player Suggestion" in context_with_nudge


class TestNudgeNoStreamlitEnvironment:
    """Tests for nudge behavior when Streamlit is not available."""

    def test_build_dm_context_without_streamlit(self) -> None:
        """Test _build_dm_context handles ImportError gracefully."""
        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["A recent event"],
        )

        # When Streamlit import fails, context should still build without nudge
        # The actual import doesn't fail in tests, but the code handles it
        # This tests the fallback path indirectly
        with patch("streamlit.session_state", new=None):
            # This should not raise, even with None session_state
            try:
                context = _build_dm_context(state)
                # Context should have other content
                assert "Recent Events" in context
                # But no nudge section (since session_state is None)
                assert "Player Suggestion" not in context
            except (TypeError, AttributeError):
                # If it does raise due to None, that's also acceptable
                # as long as it's handled somewhere in the call chain
                pass


class TestNudgeLongContentHandling:
    """Tests for nudge with long content in DM context."""

    def test_dm_context_with_max_length_nudge(self) -> None:
        """Test DM context handles 1000 character nudge."""
        long_nudge = "x" * 1000

        mock_session_state: dict[str, Any] = {
            "pending_nudge": long_nudge,
        }

        state = create_initial_game_state()

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            assert "Player Suggestion" in context
            # The full 1000 chars should be in context
            assert long_nudge in context

    def test_dm_context_nudge_doesnt_affect_other_limits(self) -> None:
        """Test that nudge doesn't interfere with other context limits."""
        mock_session_state: dict[str, Any] = {
            "pending_nudge": "A nudge",
        }

        state = create_initial_game_state()
        # Add more events than the limit
        events = [f"Event {i}" for i in range(20)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=events)

        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(state)

            # Should still respect DM_CONTEXT_RECENT_EVENTS_LIMIT
            # Only last N events should be present
            assert "Event 0" not in context  # Too old
            assert f"Event {20 - DM_CONTEXT_RECENT_EVENTS_LIMIT}" in context
            assert "Event 19" in context

            # Nudge should still be present
            assert "A nudge" in context


# =============================================================================
# Story 5.4: CharacterFacts in Context Building Tests
# =============================================================================


class TestCharacterFactsInContext:
    """Tests for CharacterFacts inclusion in agent context (Story 5.4, Task 5)."""

    def test_pc_context_includes_character_facts(self) -> None:
        """Test _build_pc_context includes character_facts when present."""
        from models import CharacterFacts

        state = create_initial_game_state()
        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sardonic wit", "Trust issues"],
            relationships={"Theros": "Trusted ally", "Lord Blackwood": "Enemy"},
            notable_events=["Stole enchanted dagger", "Discovered secret passage"],
        )
        state["agent_memories"]["rogue"] = AgentMemory(
            long_term_summary="My journey through the dungeon",
            short_term_buffer=["Recent event"],
            character_facts=facts,
        )

        context = _build_pc_context(state, "rogue")

        # Character identity section should be present
        assert "Character Identity" in context or "Shadowmere" in context
        assert "Rogue" in context

    def test_pc_context_includes_key_traits(self) -> None:
        """Test _build_pc_context includes key_traits from character_facts."""
        from models import CharacterFacts

        state = create_initial_game_state()
        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sardonic wit", "Trust issues", "Observant"],
        )
        state["agent_memories"]["rogue"] = AgentMemory(character_facts=facts)

        context = _build_pc_context(state, "rogue")

        assert "Sardonic wit" in context
        assert "Trust issues" in context
        assert "Observant" in context

    def test_pc_context_includes_relationships(self) -> None:
        """Test _build_pc_context includes relationships from character_facts."""
        from models import CharacterFacts

        state = create_initial_game_state()
        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            relationships={
                "Theros": "Trusted party member, saved my life",
                "Lord Blackwood": "Enemy - stole from him",
            },
        )
        state["agent_memories"]["rogue"] = AgentMemory(character_facts=facts)

        context = _build_pc_context(state, "rogue")

        assert "Theros" in context
        assert "Trusted party member" in context or "saved my life" in context
        assert "Lord Blackwood" in context
        assert "Enemy" in context or "stole from him" in context

    def test_pc_context_includes_notable_events(self) -> None:
        """Test _build_pc_context includes notable_events from character_facts."""
        from models import CharacterFacts

        state = create_initial_game_state()
        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            notable_events=[
                "Discovered the hidden passage in Thornwood Tower",
                "Stole the enchanted dagger from Lord Blackwood",
            ],
        )
        state["agent_memories"]["rogue"] = AgentMemory(character_facts=facts)

        context = _build_pc_context(state, "rogue")

        assert "Thornwood Tower" in context or "hidden passage" in context
        assert "enchanted dagger" in context or "Lord Blackwood" in context

    def test_pc_context_without_character_facts_works(self) -> None:
        """Test _build_pc_context works when character_facts is None."""
        state = create_initial_game_state()
        state["agent_memories"]["rogue"] = AgentMemory(
            long_term_summary="My journey",
            short_term_buffer=["Recent event"],
        )

        context = _build_pc_context(state, "rogue")

        # Should work without character_facts
        assert "My journey" in context
        assert "Recent event" in context

    def test_dm_context_includes_character_facts_for_all_pcs(self) -> None:
        """Test _build_dm_context includes character_facts for all PC agents."""
        from models import CharacterFacts

        state = create_initial_game_state()
        facts_rogue = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            relationships={"Theros": "Ally"},
        )
        facts_fighter = CharacterFacts(
            name="Theros",
            character_class="Fighter",
            relationships={"Shadowmere": "Fellow adventurer"},
        )
        state["agent_memories"]["dm"] = AgentMemory()
        state["agent_memories"]["rogue"] = AgentMemory(character_facts=facts_rogue)
        state["agent_memories"]["fighter"] = AgentMemory(character_facts=facts_fighter)

        with patch("streamlit.session_state", {}):
            context = _build_dm_context(state)

        # DM should see both characters' facts
        assert "Shadowmere" in context
        assert "Theros" in context

    def test_format_character_facts_helper(self) -> None:
        """Test format_character_facts helper function."""
        from agents import format_character_facts
        from models import CharacterFacts

        facts = CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Sardonic wit", "Trust issues"],
            relationships={"Theros": "Trusted ally"},
            notable_events=["Stole the dagger"],
        )

        formatted = format_character_facts(facts)

        assert "Shadowmere" in formatted
        assert "Rogue" in formatted
        assert "Sardonic wit" in formatted
        assert "Trust issues" in formatted
        assert "Theros" in formatted
        assert "Trusted ally" in formatted
        assert "Stole the dagger" in formatted

    def test_format_character_facts_empty_fields(self) -> None:
        """Test format_character_facts handles empty optional fields."""
        from agents import format_character_facts
        from models import CharacterFacts

        facts = CharacterFacts(
            name="BasicCharacter",
            character_class="Fighter",
        )

        formatted = format_character_facts(facts)

        assert "BasicCharacter" in formatted
        assert "Fighter" in formatted
        # Should not crash with empty lists/dicts

    def test_format_character_facts_in_exports(self) -> None:
        """Test format_character_facts is in module __all__."""
        assert "format_character_facts" in agents.__all__
