"""Tests for Story 7.3: Module Context Injection.

This test file covers:
- GameState with and without selected_module
- Serialization/deserialization roundtrip with module
- format_module_context() output validation
- DM prompt includes module context when present
- DM prompt omits module section when None
- Backward compatibility with checkpoints without selected_module
- Error handling for malformed module data
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    pass

from agents import DM_SYSTEM_PROMPT, format_module_context
from models import (
    AgentMemory,
    CharacterConfig,
    DMConfig,
    ModuleInfo,
    create_initial_game_state,
    populate_game_state,
)
from persistence import deserialize_game_state, serialize_game_state

# =============================================================================
# Task 1: GameState with selected_module Tests
# =============================================================================


class TestGameStateWithModule:
    """Tests for GameState with selected_module field (Task 1)."""

    def test_create_initial_game_state_has_selected_module_none(self) -> None:
        """Test create_initial_game_state includes selected_module=None."""
        state = create_initial_game_state()
        assert "selected_module" in state
        assert state["selected_module"] is None

    def test_populate_game_state_without_module(self) -> None:
        """Test populate_game_state with no module defaults to None."""
        state = populate_game_state(include_sample_messages=False)
        assert "selected_module" in state
        assert state["selected_module"] is None

    def test_populate_game_state_with_module(self) -> None:
        """Test populate_game_state accepts selected_module parameter."""
        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure in Barovia.",
            setting="Ravenloft",
            level_range="1-10",
        )
        state = populate_game_state(
            include_sample_messages=False, selected_module=module
        )

        assert state["selected_module"] is not None
        assert state["selected_module"].name == "Curse of Strahd"
        assert state["selected_module"].setting == "Ravenloft"

    def test_game_state_module_is_optional(self) -> None:
        """Test that selected_module can be None for freeform adventures."""
        state = create_initial_game_state()
        state["selected_module"] = None

        # Should work fine without module
        assert state["selected_module"] is None


# =============================================================================
# Task 2: Serialization Tests
# =============================================================================


class TestGameStateSerialization:
    """Tests for GameState serialization with selected_module (Task 2)."""

    def test_serialize_with_module(self) -> None:
        """Test serialize_game_state includes selected_module in output."""
        state = create_initial_game_state()
        state["selected_module"] = ModuleInfo(
            number=42,
            name="Lost Mine of Phandelver",
            description="Classic starter adventure in the Sword Coast.",
            setting="Forgotten Realms",
            level_range="1-5",
        )

        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        assert "selected_module" in data
        assert data["selected_module"] is not None
        assert data["selected_module"]["name"] == "Lost Mine of Phandelver"
        assert data["selected_module"]["number"] == 42
        assert data["selected_module"]["setting"] == "Forgotten Realms"

    def test_serialize_without_module(self) -> None:
        """Test serialize_game_state handles None module."""
        state = create_initial_game_state()
        state["selected_module"] = None

        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        assert "selected_module" in data
        assert data["selected_module"] is None

    def test_deserialize_with_module(self) -> None:
        """Test deserialize_game_state reconstructs ModuleInfo."""
        state = create_initial_game_state()
        state["selected_module"] = ModuleInfo(
            number=1,
            name="Tomb of Annihilation",
            description="Jungle death curse adventure.",
            setting="Forgotten Realms",
            level_range="1-11",
        )

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        assert restored["selected_module"] is not None
        assert isinstance(restored["selected_module"], ModuleInfo)
        assert restored["selected_module"].name == "Tomb of Annihilation"
        assert restored["selected_module"].number == 1

    def test_deserialize_without_module(self) -> None:
        """Test deserialize_game_state handles None module."""
        state = create_initial_game_state()
        state["selected_module"] = None

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        assert restored["selected_module"] is None

    def test_round_trip_preserves_module(self) -> None:
        """Test serialize->deserialize round trip preserves all module fields."""
        state = create_initial_game_state()
        state["selected_module"] = ModuleInfo(
            number=50,
            name="Storm King's Thunder",
            description="Giant-themed adventure across the Sword Coast.",
            setting="Forgotten Realms",
            level_range="1-11",
        )

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        original = state["selected_module"]
        assert original is not None
        restored_module = restored["selected_module"]
        assert restored_module is not None

        assert restored_module.number == original.number
        assert restored_module.name == original.name
        assert restored_module.description == original.description
        assert restored_module.setting == original.setting
        assert restored_module.level_range == original.level_range

    def test_backward_compatibility_without_selected_module_field(self) -> None:
        """Test deserialize handles old checkpoints without selected_module.

        This tests backward compatibility for checkpoints created before
        Story 7.3 was implemented.
        """
        # Simulate old checkpoint JSON without selected_module field
        old_checkpoint_data = {
            "ground_truth_log": [],
            "turn_queue": ["dm"],
            "current_turn": "dm",
            "agent_memories": {},
            "game_config": {},
            "dm_config": {},
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            # Note: no "selected_module" field
        }

        json_str = json.dumps(old_checkpoint_data)
        restored = deserialize_game_state(json_str)

        # Should default to None for missing field
        assert restored["selected_module"] is None

    def test_deserialize_with_malformed_module_raises_validation_error(self) -> None:
        """Test deserialize raises ValidationError for malformed module data.

        Story 7.3: Error handling for corrupted checkpoint data.
        """
        import pytest
        from pydantic import ValidationError

        # Simulate checkpoint with malformed selected_module (missing required fields)
        malformed_checkpoint = {
            "ground_truth_log": [],
            "turn_queue": ["dm"],
            "current_turn": "dm",
            "agent_memories": {},
            "game_config": {},
            "dm_config": {},
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "selected_module": {
                "number": 1,
                # Missing required fields: "name" and "description"
            },
        }

        json_str = json.dumps(malformed_checkpoint)

        # Should raise ValidationError due to missing required fields
        with pytest.raises(ValidationError):
            deserialize_game_state(json_str)

    def test_deserialize_with_invalid_module_number_raises_validation_error(
        self,
    ) -> None:
        """Test deserialize raises ValidationError for out-of-range module number.

        Story 7.3: ModuleInfo validation is enforced on deserialization.
        """
        import pytest
        from pydantic import ValidationError

        # Simulate checkpoint with invalid module number (> 100)
        invalid_checkpoint = {
            "ground_truth_log": [],
            "turn_queue": ["dm"],
            "current_turn": "dm",
            "agent_memories": {},
            "game_config": {},
            "dm_config": {},
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "selected_module": {
                "number": 999,  # Invalid: must be 1-100
                "name": "Test Module",
                "description": "Test description.",
            },
        }

        json_str = json.dumps(invalid_checkpoint)

        # Should raise ValidationError due to number constraint
        with pytest.raises(ValidationError):
            deserialize_game_state(json_str)


# =============================================================================
# Task 3: format_module_context Tests
# =============================================================================


class TestFormatModuleContext:
    """Tests for format_module_context function (Task 3)."""

    def test_includes_module_name(self) -> None:
        """Test formatted output includes module name in header."""
        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure.",
        )
        result = format_module_context(module)
        assert "## Campaign Module: Curse of Strahd" in result

    def test_includes_module_description(self) -> None:
        """Test formatted output includes module description."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="A thrilling adventure through dangerous lands.",
        )
        result = format_module_context(module)
        assert "A thrilling adventure through dangerous lands." in result

    def test_includes_guidance_bullets(self) -> None:
        """Test formatted output includes all guidance bullet points."""
        module = ModuleInfo(number=1, name="Test", description="Test description.")
        result = format_module_context(module)

        assert "- The setting, locations, and atmosphere" in result
        assert "- Key NPCs, their motivations, and personalities" in result
        assert "- The main plot hooks and story beats" in result
        assert (
            "- Encounters, monsters, and challenges appropriate to this module"
            in result
        )

    def test_includes_official_module_reference(self) -> None:
        """Test formatted output mentions official D&D module."""
        module = ModuleInfo(number=1, name="Test", description="Test description.")
        result = format_module_context(module)
        assert "You are running this official D&D module" in result

    def test_handles_special_characters_in_name(self) -> None:
        """Test module names with special characters work correctly."""
        module = ModuleInfo(
            number=1,
            name="Hoard of the Dragon Queen",
            description="First part of the Tyranny of Dragons storyline.",
        )
        result = format_module_context(module)
        assert "## Campaign Module: Hoard of the Dragon Queen" in result

    def test_handles_apostrophes_in_name(self) -> None:
        """Test module names with apostrophes work correctly."""
        module = ModuleInfo(
            number=1,
            name="Storm King's Thunder",
            description="Giant-themed adventure.",
        )
        result = format_module_context(module)
        assert "## Campaign Module: Storm King's Thunder" in result

    def test_output_format_matches_specification(self) -> None:
        """Test output exactly matches AC#2 specification format."""
        module = ModuleInfo(
            number=1,
            name="TestModule",
            description="Test description here.",
        )
        result = format_module_context(module)

        # Check the exact format specified in AC#2
        expected_header = "## Campaign Module: TestModule"
        expected_desc = "Test description here."

        assert result.startswith(expected_header)
        assert expected_desc in result
        # Check it's properly formatted markdown
        assert result.count("##") == 1  # Only one header

    def test_empty_setting_and_level_range_ok(self) -> None:
        """Test module with empty optional fields still formats correctly."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Description only.",
            setting="",  # Empty
            level_range="",  # Empty
        )
        result = format_module_context(module)

        # Should still produce valid output
        assert "## Campaign Module: Test Module" in result
        assert "Description only." in result


# =============================================================================
# Task 4: DM Prompt Integration Tests
# =============================================================================


class TestDMPromptWithModule:
    """Tests for DM prompt module context injection (Task 4)."""

    @patch("agents.create_dm_agent")
    @patch("agents.get_llm")
    def test_dm_turn_includes_module_in_prompt(
        self, mock_get_llm: MagicMock, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test dm_turn builds system prompt with module context when present."""
        import sys
        from unittest.mock import MagicMock as MM

        # Create streamlit mock before importing dm_turn
        mock_streamlit = MM()
        mock_streamlit.session_state = {}
        sys.modules["streamlit"] = mock_streamlit

        from agents import dm_turn

        # Setup mock LLM response
        mock_response = MM()
        mock_response.content = "The adventure continues..."
        mock_response.tool_calls = None
        mock_agent = MM()
        mock_agent.invoke.return_value = mock_response
        mock_create_dm_agent.return_value = mock_agent

        # Create state with module
        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror in Barovia.",
        )
        state = create_initial_game_state()
        state["selected_module"] = module
        state["turn_queue"] = ["dm"]
        state["dm_config"] = DMConfig()
        state["agent_memories"]["dm"] = AgentMemory()

        dm_turn(state)

        # Verify the agent was invoked
        assert mock_agent.invoke.called
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]

        # Check that SystemMessage contains module context
        system_message = messages[0]
        assert "Campaign Module: Curse of Strahd" in system_message.content
        assert "Gothic horror in Barovia." in system_message.content

    @patch("agents.create_dm_agent")
    @patch("agents.get_llm")
    def test_dm_turn_omits_module_when_none(
        self, mock_get_llm: MagicMock, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test dm_turn omits module section when selected_module is None."""
        import sys
        from unittest.mock import MagicMock as MM

        # Create streamlit mock
        mock_streamlit = MM()
        mock_streamlit.session_state = {}
        sys.modules["streamlit"] = mock_streamlit

        from agents import dm_turn

        # Setup mock LLM response
        mock_response = MM()
        mock_response.content = "The adventure continues..."
        mock_response.tool_calls = None
        mock_agent = MM()
        mock_agent.invoke.return_value = mock_response
        mock_create_dm_agent.return_value = mock_agent

        # Create state without module
        state = create_initial_game_state()
        state["selected_module"] = None
        state["turn_queue"] = ["dm"]
        state["dm_config"] = DMConfig()
        state["agent_memories"]["dm"] = AgentMemory()

        dm_turn(state)

        # Verify the agent was invoked
        assert mock_agent.invoke.called
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]

        # Check that SystemMessage does NOT contain module context
        system_message = messages[0]
        assert "Campaign Module" not in system_message.content

    @patch("agents.create_dm_agent")
    @patch("agents.get_llm")
    def test_dm_turn_preserves_selected_module_in_returned_state(
        self, mock_get_llm: MagicMock, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test dm_turn preserves selected_module in returned GameState."""
        import sys
        from unittest.mock import MagicMock as MM

        # Create streamlit mock
        mock_streamlit = MM()
        mock_streamlit.session_state = {}
        sys.modules["streamlit"] = mock_streamlit

        from agents import dm_turn

        # Setup mock LLM response
        mock_response = MM()
        mock_response.content = "The adventure continues..."
        mock_response.tool_calls = None
        mock_agent = MM()
        mock_agent.invoke.return_value = mock_response
        mock_create_dm_agent.return_value = mock_agent

        # Create state with module
        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror in Barovia.",
        )
        state = create_initial_game_state()
        state["selected_module"] = module
        state["turn_queue"] = ["dm"]
        state["dm_config"] = DMConfig()
        state["agent_memories"]["dm"] = AgentMemory()

        result = dm_turn(state)

        # Verify module is preserved in returned state
        assert result["selected_module"] is not None
        assert result["selected_module"].name == "Curse of Strahd"

    def test_base_dm_prompt_not_modified(self) -> None:
        """Test that DM_SYSTEM_PROMPT constant is not modified by module injection."""
        # Verify the base prompt doesn't contain module markers
        assert "Campaign Module" not in DM_SYSTEM_PROMPT
        # And that it still contains expected content
        assert "Dungeon Master" in DM_SYSTEM_PROMPT


# =============================================================================
# Task 5: PC Turn Module Preservation Tests
# =============================================================================


class TestPCTurnModulePreservation:
    """Tests for PC turn preserving selected_module (Task 4 extension)."""

    @patch("agents.create_pc_agent")
    @patch("agents.get_llm")
    def test_pc_turn_preserves_selected_module(
        self, mock_get_llm: MagicMock, mock_create_pc_agent: MagicMock
    ) -> None:
        """Test pc_turn preserves selected_module in returned GameState."""
        from agents import pc_turn

        # Setup mock LLM response
        mock_response = MagicMock()
        mock_response.content = "I draw my sword..."
        mock_response.tool_calls = None
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = mock_response
        mock_create_pc_agent.return_value = mock_agent

        # Create state with module
        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror in Barovia.",
        )
        state = create_initial_game_state()
        state["selected_module"] = module
        state["turn_queue"] = ["dm", "fighter"]
        state["dm_config"] = DMConfig()
        state["characters"]["fighter"] = CharacterConfig(
            name="Fighter",
            character_class="Fighter",
            personality="Brave and bold",
            color="#FF0000",
        )
        state["agent_memories"]["fighter"] = AgentMemory()

        result = pc_turn(state, "fighter")

        # Verify module is preserved in returned state
        assert result["selected_module"] is not None
        assert result["selected_module"].name == "Curse of Strahd"


# =============================================================================
# Integration Tests
# =============================================================================


class TestModuleContextIntegration:
    """Integration tests for module context flow (Task 6)."""

    def test_module_flow_through_serialization(self) -> None:
        """Test module flows correctly through serialize/deserialize cycle."""
        # Create state with module
        module = ModuleInfo(
            number=1,
            name="Dragon of Icespire Peak",
            description="Starter adventure with dragon threat.",
            setting="Forgotten Realms",
            level_range="1-7",
        )
        state = populate_game_state(
            include_sample_messages=False, selected_module=module
        )

        # Serialize
        json_str = serialize_game_state(state)

        # Deserialize
        restored = deserialize_game_state(json_str)

        # Verify module survived
        assert restored["selected_module"] is not None
        assert restored["selected_module"].name == "Dragon of Icespire Peak"
        assert restored["selected_module"].setting == "Forgotten Realms"
        assert restored["selected_module"].level_range == "1-7"

    def test_format_module_context_returns_string(self) -> None:
        """Test format_module_context returns a non-empty string."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="A test adventure.",
        )
        result = format_module_context(module)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_module_in_exports(self) -> None:
        """Test format_module_context is in agents module exports."""
        import agents

        assert "format_module_context" in agents.__all__


# =============================================================================
# Error Handling Tests (Code Review - Added for Story 7.3)
# =============================================================================


class TestModuleErrorHandling:
    """Tests for graceful error handling with malformed module data."""

    def test_load_checkpoint_handles_malformed_module_gracefully(
        self, tmp_path: Path
    ) -> None:
        """Test load_checkpoint returns None for checkpoint with malformed module.

        Story 7.3: Graceful degradation when checkpoint has invalid module data.
        This tests the safety net in load_checkpoint that catches ValidationError.
        """

        from persistence import (
            ensure_session_dir,
            get_checkpoint_path,
            load_checkpoint,
        )

        # Create a test session directory
        test_session_id = "test_malformed"
        session_dir = ensure_session_dir(test_session_id)

        try:
            # Write a checkpoint with malformed module data directly
            malformed_checkpoint = {
                "ground_truth_log": [],
                "turn_queue": ["dm"],
                "current_turn": "dm",
                "agent_memories": {},
                "game_config": {},
                "dm_config": {},
                "characters": {},
                "whisper_queue": [],
                "human_active": False,
                "controlled_character": None,
                "session_number": 1,
                "session_id": test_session_id,
                "selected_module": {
                    "number": 1,
                    # Missing required "name" and "description" fields
                },
            }

            checkpoint_path = get_checkpoint_path(test_session_id, 1)
            checkpoint_path.write_text(
                json.dumps(malformed_checkpoint), encoding="utf-8"
            )

            # load_checkpoint should return None (graceful failure)
            result = load_checkpoint(test_session_id, 1)
            assert result is None

        finally:
            # Cleanup
            import shutil

            if session_dir.exists():
                shutil.rmtree(session_dir)

    def test_format_module_context_with_long_description(self) -> None:
        """Test format_module_context handles very long descriptions.

        Story 7.3: Edge case test for long module descriptions.
        """
        # Create module with very long description
        long_desc = "A" * 10000  # 10k character description
        module = ModuleInfo(
            number=1,
            name="Long Description Module",
            description=long_desc,
        )

        result = format_module_context(module)

        # Should include the full description (per story spec - no truncation)
        assert long_desc in result
        assert "## Campaign Module: Long Description Module" in result
