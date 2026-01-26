"""Tests for agent definitions and LLM factory."""

import os
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

import agents
import config as config_module
from agents import (
    DEFAULT_MODELS,
    DM_CONTEXT_PLAYER_ENTRIES_LIMIT,
    DM_CONTEXT_RECENT_EVENTS_LIMIT,
    DM_SYSTEM_PROMPT,
    SUPPORTED_PROVIDERS,
    LLMConfigurationError,
    _build_dm_context,
    create_dm_agent,
    dm_turn,
    get_default_model,
    get_llm,
)
from models import AgentMemory, DMConfig, create_initial_game_state


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
            "SUPPORTED_PROVIDERS",
            "DEFAULT_MODELS",
            "DM_SYSTEM_PROMPT",
            "DM_CONTEXT_RECENT_EVENTS_LIMIT",
            "DM_CONTEXT_PLAYER_ENTRIES_LIMIT",
            "_build_dm_context",
            "create_dm_agent",
            "dm_turn",
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
        from agents import _build_dm_context

        state = create_initial_game_state()
        context = _build_dm_context(state)

        assert context == ""

    def test_build_dm_context_with_dm_long_term_summary(self) -> None:
        """Test context includes DM's long-term summary."""
        from agents import _build_dm_context

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="The party defeated the dragon"
        )

        context = _build_dm_context(state)

        assert "Story So Far" in context
        assert "The party defeated the dragon" in context

    def test_build_dm_context_with_dm_short_term_buffer(self) -> None:
        """Test context includes DM's recent events."""
        from agents import _build_dm_context

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
        from agents import _build_dm_context

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
        from agents import _build_dm_context

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
        from agents import DM_CONTEXT_RECENT_EVENTS_LIMIT, _build_dm_context

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
        from agents import DM_CONTEXT_PLAYER_ENTRIES_LIMIT, _build_dm_context

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
        from agents import _build_dm_context

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
        assert "  " not in DM_SYSTEM_PROMPT or "  -" in DM_SYSTEM_PROMPT  # Allow list indents
