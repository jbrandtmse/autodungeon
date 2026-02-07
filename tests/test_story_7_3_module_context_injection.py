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


# =============================================================================
# Extended Coverage Tests (testarch-automate expansion)
# =============================================================================


class TestModuleInfoValidation:
    """Extended tests for ModuleInfo Pydantic validation."""

    def test_module_info_number_at_min_boundary(self) -> None:
        """Test ModuleInfo accepts number=1 (minimum boundary)."""
        module = ModuleInfo(
            number=1,
            name="First Module",
            description="A module at the minimum boundary.",
        )
        assert module.number == 1

    def test_module_info_number_at_max_boundary(self) -> None:
        """Test ModuleInfo accepts number=100 (maximum boundary)."""
        module = ModuleInfo(
            number=100,
            name="Last Module",
            description="A module at the maximum boundary.",
        )
        assert module.number == 100

    def test_module_info_number_below_min_raises_error(self) -> None:
        """Test ModuleInfo rejects number=0 (below minimum)."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(
                number=0,
                name="Invalid Module",
                description="Number is too low.",
            )
        assert "number" in str(exc_info.value)

    def test_module_info_number_above_max_raises_error(self) -> None:
        """Test ModuleInfo rejects number=101 (above maximum)."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(
                number=101,
                name="Invalid Module",
                description="Number is too high.",
            )
        assert "number" in str(exc_info.value)

    def test_module_info_empty_name_raises_error(self) -> None:
        """Test ModuleInfo rejects empty name string."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(
                number=1,
                name="",
                description="Valid description.",
            )
        assert "name" in str(exc_info.value)

    def test_module_info_empty_description_raises_error(self) -> None:
        """Test ModuleInfo rejects empty description string."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ModuleInfo(
                number=1,
                name="Valid Name",
                description="",
            )
        assert "description" in str(exc_info.value)

    def test_module_info_with_unicode_in_name(self) -> None:
        """Test ModuleInfo handles unicode characters in name."""
        module = ModuleInfo(
            number=1,
            name="Curse of the Drow Queen",
            description="An adventure with unicode.",
        )
        assert module.name == "Curse of the Drow Queen"

    def test_module_info_with_unicode_in_description(self) -> None:
        """Test ModuleInfo handles unicode characters in description."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Fight the dragon and claim the treasure.",
        )
        assert "dragon" in module.description

    def test_module_info_whitespace_only_name_is_allowed(self) -> None:
        """Test ModuleInfo allows whitespace-only name (min_length=1 check).

        Unlike CharacterConfig, ModuleInfo doesn't have a custom validator
        to strip and check whitespace. Whitespace-only names satisfy
        min_length=1 constraint.
        """
        # This is allowed because min_length=1 is satisfied by spaces
        module = ModuleInfo(
            number=1,
            name="   ",  # Only whitespace - counts as 3 chars
            description="Valid description.",
        )
        assert module.name == "   "


class TestSerializationEdgeCases:
    """Extended tests for serialization edge cases."""

    def test_serialize_module_with_all_fields(self) -> None:
        """Test serialization preserves all ModuleInfo fields."""
        state = create_initial_game_state()
        state["selected_module"] = ModuleInfo(
            number=42,
            name="Complete Module",
            description="Has all fields populated.",
            setting="Greyhawk",
            level_range="5-10",
        )

        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        assert data["selected_module"]["number"] == 42
        assert data["selected_module"]["name"] == "Complete Module"
        assert data["selected_module"]["description"] == "Has all fields populated."
        assert data["selected_module"]["setting"] == "Greyhawk"
        assert data["selected_module"]["level_range"] == "5-10"

    def test_deserialize_module_with_only_required_fields(self) -> None:
        """Test deserialization works with only required fields."""
        checkpoint_data = {
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
                "name": "Minimal Module",
                "description": "Only required fields.",
            },
        }

        json_str = json.dumps(checkpoint_data)
        restored = deserialize_game_state(json_str)

        assert restored["selected_module"] is not None
        assert restored["selected_module"].name == "Minimal Module"
        # Optional fields should have default values
        assert restored["selected_module"].setting == ""
        assert restored["selected_module"].level_range == ""

    def test_serialize_with_special_characters(self) -> None:
        """Test serialization handles special JSON characters."""
        state = create_initial_game_state()
        state["selected_module"] = ModuleInfo(
            number=1,
            name='Module with "quotes" and \\backslashes',
            description="Contains special chars: \n\t and unicode.",
        )

        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        # Verify special characters survived round-trip
        assert '"quotes"' in data["selected_module"]["name"]
        assert "\\backslashes" in data["selected_module"]["name"]

    def test_deserialize_handles_explicit_null_module(self) -> None:
        """Test deserialization handles explicit null for selected_module."""
        checkpoint_data = {
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
            "selected_module": None,  # Explicit null
        }

        json_str = json.dumps(checkpoint_data)
        restored = deserialize_game_state(json_str)

        assert restored["selected_module"] is None

    def test_deserialize_with_wrong_number_type_raises_error(self) -> None:
        """Test deserialization fails when number is wrong type."""
        import pytest
        from pydantic import ValidationError

        checkpoint_data = {
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
                "number": "not_a_number",  # Wrong type
                "name": "Test Module",
                "description": "Test description.",
            },
        }

        json_str = json.dumps(checkpoint_data)

        with pytest.raises(ValidationError):
            deserialize_game_state(json_str)

    def test_round_trip_with_newlines_in_description(self) -> None:
        """Test round-trip preserves multiline descriptions."""
        state = create_initial_game_state()
        multiline_desc = """This is a module description.

It has multiple paragraphs.

And continues for a while with various content."""

        state["selected_module"] = ModuleInfo(
            number=1,
            name="Multiline Module",
            description=multiline_desc,
        )

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        assert restored["selected_module"] is not None
        assert restored["selected_module"].description == multiline_desc
        assert "\n\n" in restored["selected_module"].description


class TestFormatModuleContextEdgeCases:
    """Extended tests for format_module_context edge cases."""

    def test_format_module_context_with_markdown_in_name(self) -> None:
        """Test format_module_context handles markdown characters in name."""
        module = ModuleInfo(
            number=1,
            name="Module **with** _markdown_ `chars`",
            description="Test description.",
        )
        result = format_module_context(module)

        # Should not escape the markdown - passed through as-is
        assert "Module **with** _markdown_ `chars`" in result

    def test_format_module_context_with_html_in_name(self) -> None:
        """Test format_module_context handles HTML-like characters in name."""
        module = ModuleInfo(
            number=1,
            name="Module <with> & HTML",
            description="Test description.",
        )
        result = format_module_context(module)

        # Should pass through without HTML escaping (for LLM context)
        assert "<with>" in result

    def test_format_module_context_preserves_line_breaks(self) -> None:
        """Test format_module_context preserves line breaks in description."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Line 1.\nLine 2.\nLine 3.",
        )
        result = format_module_context(module)

        assert "Line 1.\nLine 2.\nLine 3." in result

    def test_format_module_context_with_very_long_name(self) -> None:
        """Test format_module_context handles very long module names."""
        long_name = "A" * 500  # 500 character name
        module = ModuleInfo(
            number=1,
            name=long_name,
            description="Test description.",
        )
        result = format_module_context(module)

        # Should include the full name (no truncation)
        assert long_name in result
        assert f"## Campaign Module: {long_name}" in result

    def test_format_module_context_structure(self) -> None:
        """Test format_module_context produces expected structure."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="A test description.",
        )
        result = format_module_context(module)

        # Verify structure: header, then description, then guidance
        lines = result.split("\n")

        # First line should be the header
        assert lines[0] == "## Campaign Module: Test Module"

        # Second line should be the description
        assert lines[1] == "A test description."

        # Should contain the "You are running" guidance paragraph
        assert "You are running this official D&D module" in result


class TestDMTurnModuleIntegration:
    """Extended integration tests for DM turn with module context."""

    @patch("agents.create_dm_agent")
    @patch("agents.get_llm")
    def test_dm_turn_module_appears_after_base_prompt(
        self, mock_get_llm: MagicMock, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test module context appears after base DM prompt."""
        import sys
        from unittest.mock import MagicMock as MM

        mock_streamlit = MM()
        mock_streamlit.session_state = {}
        sys.modules["streamlit"] = mock_streamlit

        from agents import dm_turn

        mock_response = MM()
        mock_response.content = "The adventure continues..."
        mock_response.tool_calls = None
        mock_agent = MM()
        mock_agent.invoke.return_value = mock_response
        mock_create_dm_agent.return_value = mock_agent

        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description.",
        )
        state = create_initial_game_state()
        state["selected_module"] = module
        state["turn_queue"] = ["dm"]
        state["dm_config"] = DMConfig()
        state["agent_memories"]["dm"] = AgentMemory()

        dm_turn(state)

        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]
        system_content = messages[0].content

        # Module should appear AFTER the base DM prompt content
        dm_prompt_pos = system_content.find("Dungeon Master")
        module_pos = system_content.find("Campaign Module")

        assert dm_prompt_pos < module_pos, "Module should appear after base DM prompt"

    @patch("agents.create_dm_agent")
    @patch("agents.get_llm")
    def test_dm_turn_with_tool_calls_preserves_module(
        self, mock_get_llm: MagicMock, mock_create_dm_agent: MagicMock
    ) -> None:
        """Test dm_turn preserves module through tool call loop."""
        import sys
        from unittest.mock import MagicMock as MM

        mock_streamlit = MM()
        mock_streamlit.session_state = {}
        sys.modules["streamlit"] = mock_streamlit

        from agents import dm_turn

        # First response has tool call, second has content
        mock_tool_response = MM()
        mock_tool_response.content = ""
        mock_tool_response.tool_calls = [
            {"name": "dm_roll_dice", "args": {"notation": "1d20"}, "id": "call_1"}
        ]

        mock_final_response = MM()
        mock_final_response.content = "You rolled a 15!"
        mock_final_response.tool_calls = None

        mock_agent = MM()
        mock_agent.invoke.side_effect = [mock_tool_response, mock_final_response]
        mock_create_dm_agent.return_value = mock_agent

        module = ModuleInfo(
            number=1,
            name="Combat Module",
            description="Battle-focused adventure.",
        )
        state = create_initial_game_state()
        state["selected_module"] = module
        state["turn_queue"] = ["dm"]
        state["dm_config"] = DMConfig()
        state["agent_memories"]["dm"] = AgentMemory()

        result = dm_turn(state)

        # Module should still be preserved after tool calls
        assert result["selected_module"] is not None
        assert result["selected_module"].name == "Combat Module"


class TestCheckpointModulePersistence:
    """Tests for module persistence through checkpoint save/load cycle."""

    def test_save_and_load_checkpoint_with_module(self, tmp_path: Path) -> None:
        """Test module survives full checkpoint save/load cycle."""
        import shutil

        from persistence import (
            ensure_session_dir,
            load_checkpoint,
            save_checkpoint,
        )

        test_session_id = "test_save_load"
        session_dir = ensure_session_dir(test_session_id)

        try:
            module = ModuleInfo(
                number=42,
                name="Persisted Module",
                description="Should survive checkpoint.",
                setting="Test Setting",
                level_range="1-20",
            )

            state = create_initial_game_state()
            state["selected_module"] = module
            state["session_id"] = test_session_id

            # Save checkpoint
            save_checkpoint(state, test_session_id, 1, update_metadata=False)

            # Load checkpoint
            restored = load_checkpoint(test_session_id, 1)

            assert restored is not None
            assert restored["selected_module"] is not None
            assert restored["selected_module"].name == "Persisted Module"
            assert restored["selected_module"].number == 42
            assert restored["selected_module"].setting == "Test Setting"
            assert restored["selected_module"].level_range == "1-20"

        finally:
            if session_dir.exists():
                shutil.rmtree(session_dir)

    def test_save_and_load_checkpoint_without_module(self, tmp_path: Path) -> None:
        """Test checkpoint save/load with None module."""
        import shutil

        from persistence import (
            ensure_session_dir,
            load_checkpoint,
            save_checkpoint,
        )

        test_session_id = "test_no_module"
        session_dir = ensure_session_dir(test_session_id)

        try:
            state = create_initial_game_state()
            state["selected_module"] = None
            state["session_id"] = test_session_id

            save_checkpoint(state, test_session_id, 1, update_metadata=False)
            restored = load_checkpoint(test_session_id, 1)

            assert restored is not None
            assert restored["selected_module"] is None

        finally:
            if session_dir.exists():
                shutil.rmtree(session_dir)


class TestModuleContextInDMPrompt:
    """Tests verifying module context structure in DM prompts."""

    def test_module_context_contains_all_guidance_points(self) -> None:
        """Test format_module_context includes all required guidance."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description.",
        )
        result = format_module_context(module)

        # All four guidance points from Story 7.3 spec
        guidance_points = [
            "setting, locations, and atmosphere",
            "Key NPCs, their motivations",
            "main plot hooks and story beats",
            "Encounters, monsters, and challenges",
        ]

        for point in guidance_points:
            assert point in result, f"Missing guidance: {point}"

    def test_module_context_is_valid_markdown(self) -> None:
        """Test format_module_context produces valid markdown."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description here.",
        )
        result = format_module_context(module)

        # Check markdown header format
        assert result.startswith("## ")

        # Check bullet points are present
        assert result.count("- ") >= 4  # At least 4 bullet points

    def test_module_name_and_description_not_escaped(self) -> None:
        """Test module name and description are not HTML-escaped."""
        module = ModuleInfo(
            number=1,
            name='<Module> & "Test"',
            description="Description with <html> & 'quotes'",
        )
        result = format_module_context(module)

        # Should NOT be escaped (this is for LLM context, not HTML)
        assert "<Module>" in result
        assert "&" in result
        assert '"Test"' in result


class TestPopulateGameStateWithModule:
    """Tests for populate_game_state with module parameter."""

    def test_populate_game_state_includes_module_in_turn_queue(self) -> None:
        """Test populated state has correct turn queue regardless of module."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description.",
        )
        state = populate_game_state(
            include_sample_messages=False, selected_module=module
        )

        # Turn queue should start with dm
        assert state["turn_queue"][0] == "dm"
        # Module shouldn't affect turn queue
        assert "module" not in state["turn_queue"]

    def test_populate_game_state_module_is_same_object(self) -> None:
        """Test module passed in is the same object (not copied)."""
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description.",
        )
        state = populate_game_state(
            include_sample_messages=False, selected_module=module
        )

        # Should be same object reference
        assert state["selected_module"] is module


class TestDeserializationEdgeCases:
    """Additional deserialization edge cases."""

    def test_deserialize_with_extra_module_fields_ignored(self) -> None:
        """Test deserialization ignores unknown fields in module."""
        checkpoint_data = {
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
                "name": "Test Module",
                "description": "Test description.",
                "unknown_field": "should be ignored",
                "another_unknown": 12345,
            },
        }

        json_str = json.dumps(checkpoint_data)
        restored = deserialize_game_state(json_str)

        # Should successfully deserialize despite extra fields
        assert restored["selected_module"] is not None
        assert restored["selected_module"].name == "Test Module"
        # Extra fields should not be present
        assert not hasattr(restored["selected_module"], "unknown_field")

    def test_deserialize_with_negative_module_number_raises_error(self) -> None:
        """Test deserialization fails with negative module number."""
        import pytest
        from pydantic import ValidationError

        checkpoint_data = {
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
                "number": -5,  # Negative number
                "name": "Test Module",
                "description": "Test description.",
            },
        }

        json_str = json.dumps(checkpoint_data)

        with pytest.raises(ValidationError):
            deserialize_game_state(json_str)
