"""Tests for function tools (dice rolling, etc.)."""

import json
from unittest.mock import patch

import pytest


class TestDiceResult:
    """Tests for DiceResult model."""

    def test_dice_result_creation(self) -> None:
        """Test DiceResult can be created with required fields."""
        from tools import DiceResult

        result = DiceResult(
            notation="1d20",
            rolls={"1d20": [15]},
            modifier=0,
            total=15,
        )
        assert result.notation == "1d20"
        assert result.rolls == {"1d20": [15]}
        assert result.modifier == 0
        assert result.total == 15

    def test_dice_result_with_modifier(self) -> None:
        """Test DiceResult with positive modifier."""
        from tools import DiceResult

        result = DiceResult(
            notation="1d20+5",
            rolls={"1d20": [10]},
            modifier=5,
            total=15,
        )
        assert result.modifier == 5
        assert result.total == 15

    def test_dice_result_with_negative_modifier(self) -> None:
        """Test DiceResult with negative modifier."""
        from tools import DiceResult

        result = DiceResult(
            notation="1d20-2",
            rolls={"1d20": [10]},
            modifier=-2,
            total=8,
        )
        assert result.modifier == -2
        assert result.total == 8

    def test_dice_result_multi_dice(self) -> None:
        """Test DiceResult with multiple dice groups."""
        from tools import DiceResult

        result = DiceResult(
            notation="2d6+1d4+3",
            rolls={"2d6": [4, 5], "1d4": [2]},
            modifier=3,
            total=14,
        )
        assert result.rolls == {"2d6": [4, 5], "1d4": [2]}
        assert result.total == 14

    def test_dice_result_str_no_modifier(self) -> None:
        """Test DiceResult __str__ method without modifier."""
        from tools import DiceResult

        result = DiceResult(
            notation="3d6",
            rolls={"3d6": [4, 2, 5]},
            modifier=0,
            total=11,
        )
        str_repr = str(result)
        assert "3d6" in str_repr
        assert "11" in str_repr

    def test_dice_result_str_positive_modifier(self) -> None:
        """Test DiceResult __str__ method with positive modifier."""
        from tools import DiceResult

        result = DiceResult(
            notation="3d6+2",
            rolls={"3d6": [4, 2, 5]},
            modifier=2,
            total=13,
        )
        str_repr = str(result)
        assert "+ 2" in str_repr
        assert "13" in str_repr

    def test_dice_result_str_negative_modifier(self) -> None:
        """Test DiceResult __str__ method with negative modifier."""
        from tools import DiceResult

        result = DiceResult(
            notation="1d20-3",
            rolls={"1d20": [15]},
            modifier=-3,
            total=12,
        )
        str_repr = str(result)
        assert "- 3" in str_repr
        assert "12" in str_repr

    def test_dice_result_json_serialization(self) -> None:
        """Test DiceResult can serialize to JSON."""
        from tools import DiceResult

        result = DiceResult(
            notation="2d6+3",
            rolls={"2d6": [4, 5]},
            modifier=3,
            total=12,
        )

        json_str = result.model_dump_json()
        data = json.loads(json_str)

        assert data["notation"] == "2d6+3"
        assert data["rolls"] == {"2d6": [4, 5]}
        assert data["modifier"] == 3
        assert data["total"] == 12

    def test_dice_result_json_roundtrip(self) -> None:
        """Test DiceResult serialization roundtrip works correctly."""
        from tools import DiceResult

        original = DiceResult(
            notation="2d6+1d4+3",
            rolls={"2d6": [3, 6], "1d4": [2]},
            modifier=3,
            total=14,
        )

        json_str = original.model_dump_json()
        restored = DiceResult.model_validate_json(json_str)

        assert restored.notation == original.notation
        assert restored.rolls == original.rolls
        assert restored.modifier == original.modifier
        assert restored.total == original.total

    def test_dice_result_in_all_exports(self) -> None:
        """Test DiceResult is exported in __all__."""
        import tools

        assert "DiceResult" in tools.__all__


class TestRollDice:
    """Tests for roll_dice function."""

    def test_roll_dice_1d20(self) -> None:
        """Test basic 1d20 roll."""
        from tools import roll_dice

        result = roll_dice("1d20")
        assert result.notation == "1d20"
        assert "1d20" in result.rolls
        assert len(result.rolls["1d20"]) == 1
        assert 1 <= result.rolls["1d20"][0] <= 20
        assert result.total == result.rolls["1d20"][0]

    def test_roll_dice_1d20_deterministic(self) -> None:
        """Test 1d20 with mocked random for deterministic result."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=15):
            result = roll_dice("1d20")
            assert result.total == 15
            assert result.rolls == {"1d20": [15]}

    def test_roll_dice_with_positive_modifier(self) -> None:
        """Test dice roll with positive modifier."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=10):
            result = roll_dice("1d20+5")
            assert result.notation == "1d20+5"
            assert result.modifier == 5
            assert result.total == 15

    def test_roll_dice_with_negative_modifier(self) -> None:
        """Test dice roll with negative modifier."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=10):
            result = roll_dice("1d20-2")
            assert result.notation == "1d20-2"
            assert result.modifier == -2
            assert result.total == 8

    def test_roll_dice_3d6(self) -> None:
        """Test multi-dice roll 3d6."""
        from tools import roll_dice

        with patch("tools.random.randint", side_effect=[4, 5, 6]):
            result = roll_dice("3d6")
            assert result.notation == "3d6"
            assert result.rolls == {"3d6": [4, 5, 6]}
            assert result.total == 15

    def test_roll_dice_complex_notation(self) -> None:
        """Test complex notation 2d6+1d4+3."""
        from tools import roll_dice

        # 2d6: [3, 4] = 7, 1d4: [2] = 2, modifier: 3, total: 12
        with patch("tools.random.randint", side_effect=[3, 4, 2]):
            result = roll_dice("2d6+1d4+3")
            assert result.notation == "2d6+1d4+3"
            assert result.rolls == {"2d6": [3, 4], "1d4": [2]}
            assert result.modifier == 3
            assert result.total == 12

    def test_roll_dice_multiple_dice_groups(self) -> None:
        """Test notation with multiple dice groups 1d20+1d4."""
        from tools import roll_dice

        with patch("tools.random.randint", side_effect=[15, 3]):
            result = roll_dice("1d20+1d4")
            assert result.rolls == {"1d20": [15], "1d4": [3]}
            assert result.modifier == 0
            assert result.total == 18

    def test_roll_dice_implicit_count(self) -> None:
        """Test d20 notation (implicit count of 1)."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=17):
            result = roll_dice("d20")
            assert result.rolls == {"1d20": [17]}
            assert result.total == 17

    def test_roll_dice_case_insensitive(self) -> None:
        """Test dice notation is case insensitive."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=10):
            result = roll_dice("1D20")
            assert result.notation == "1D20"
            assert result.total == 10

    def test_roll_dice_bounds_1d20(self) -> None:
        """Test that 1d20 rolls are within valid bounds."""
        from tools import roll_dice

        for _ in range(100):
            result = roll_dice("1d20")
            assert 1 <= result.total <= 20

    def test_roll_dice_bounds_3d6(self) -> None:
        """Test that 3d6 rolls are within valid bounds."""
        from tools import roll_dice

        for _ in range(100):
            result = roll_dice("3d6")
            assert 3 <= result.total <= 18

    def test_roll_dice_zero_modifier(self) -> None:
        """Test dice roll with explicit +0 modifier."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=10):
            result = roll_dice("1d20+0")
            assert result.modifier == 0
            assert result.total == 10

    def test_roll_dice_in_all_exports(self) -> None:
        """Test roll_dice is exported in __all__."""
        import tools

        assert "roll_dice" in tools.__all__


class TestRollDiceValidation:
    """Tests for roll_dice validation and error handling."""

    def test_roll_dice_empty_string_defaults_to_1d20(self) -> None:
        """Test empty string defaults to 1d20."""
        from tools import roll_dice

        result = roll_dice("")
        assert result.notation == "1d20"
        assert 1 <= result.total <= 20

    def test_roll_dice_none_defaults_to_1d20(self) -> None:
        """Test None input defaults to 1d20."""
        from tools import roll_dice

        result = roll_dice(None)  # type: ignore[arg-type]
        assert result.notation == "1d20"
        assert 1 <= result.total <= 20

    def test_roll_dice_whitespace_only_defaults_to_1d20(self) -> None:
        """Test whitespace-only string defaults to 1d20."""
        from tools import roll_dice

        result = roll_dice("   ")
        assert result.notation == "1d20"
        assert 1 <= result.total <= 20

    @pytest.mark.parametrize(
        "invalid_notation",
        [
            "abc",
            "xyz123",
            "roll",
            "1d",
            "d",
            "1",
            "++",
            "1d20++5",
        ],
    )
    def test_roll_dice_invalid_notation_raises_value_error(
        self, invalid_notation: str
    ) -> None:
        """Test invalid notations raise ValueError."""
        from tools import roll_dice

        with pytest.raises(ValueError):
            roll_dice(invalid_notation)

    def test_roll_dice_zero_sides_raises_value_error(self) -> None:
        """Test d0 raises ValueError."""
        from tools import roll_dice

        with pytest.raises(ValueError, match="sides"):
            roll_dice("1d0")

    def test_roll_dice_zero_count_raises_value_error(self) -> None:
        """Test 0d6 raises ValueError."""
        from tools import roll_dice

        with pytest.raises(ValueError, match="count"):
            roll_dice("0d6")

    def test_roll_dice_negative_sides_raises_value_error(self) -> None:
        """Test negative sides raises ValueError."""
        from tools import roll_dice

        with pytest.raises(ValueError):
            roll_dice("1d-6")

    def test_roll_dice_exceeds_max_dice_count(self) -> None:
        """Test exceeding max dice count raises ValueError."""
        from tools import MAX_DICE_COUNT, roll_dice

        with pytest.raises(ValueError, match="count"):
            roll_dice(f"{MAX_DICE_COUNT + 1}d6")

    def test_roll_dice_exceeds_max_sides(self) -> None:
        """Test exceeding max die sides raises ValueError."""
        from tools import MAX_DICE_SIDES, roll_dice

        with pytest.raises(ValueError, match="sides"):
            roll_dice(f"1d{MAX_DICE_SIDES + 1}")

    def test_roll_dice_exceeds_max_total_dice(self) -> None:
        """Test exceeding max total dice across groups raises ValueError."""
        from tools import roll_dice

        # 60d6 + 60d4 = 120 dice, exceeds MAX_TOTAL_DICE of 100
        with pytest.raises(ValueError, match="(?i)total"):
            roll_dice("60d6+60d4")

    def test_roll_dice_at_max_limits_succeeds(self) -> None:
        """Test rolling at exactly the max limits succeeds."""
        from tools import MAX_DICE_COUNT, MAX_DICE_SIDES, roll_dice

        # These should work without raising
        result = roll_dice(f"{MAX_DICE_COUNT}d6")
        assert len(result.rolls[f"{MAX_DICE_COUNT}d6"]) == MAX_DICE_COUNT

        result = roll_dice(f"1d{MAX_DICE_SIDES}")
        assert f"1d{MAX_DICE_SIDES}" in result.rolls

    def test_roll_dice_helpful_error_message(self) -> None:
        """Test error messages include the invalid input."""
        from tools import roll_dice

        with pytest.raises(ValueError) as exc_info:
            roll_dice("invalid_dice")
        assert (
            "invalid_dice" in str(exc_info.value).lower()
            or "invalid" in str(exc_info.value).lower()
        )


class TestRollDiceComprehensive:
    """Comprehensive tests for all dice types and edge cases."""

    @pytest.mark.parametrize(
        "notation,sides",
        [
            ("1d4", 4),
            ("1d6", 6),
            ("1d8", 8),
            ("1d10", 10),
            ("1d12", 12),
            ("1d20", 20),
            ("1d100", 100),
        ],
    )
    def test_roll_dice_standard_dice_types(self, notation: str, sides: int) -> None:
        """Test all standard D&D dice types produce valid results."""
        from tools import roll_dice

        for _ in range(10):
            result = roll_dice(notation)
            assert result.notation == notation
            assert len(result.rolls[notation]) == 1
            assert 1 <= result.rolls[notation][0] <= sides
            assert result.total == result.rolls[notation][0]

    @pytest.mark.parametrize(
        "notation,count",
        [
            ("3d6", 3),
            ("4d6", 4),
            ("8d6", 8),
            ("2d8", 2),
            ("5d4", 5),
        ],
    )
    def test_roll_dice_multi_dice_counts(self, notation: str, count: int) -> None:
        """Test multi-dice rolls produce correct number of results."""
        from tools import roll_dice

        result = roll_dice(notation)
        assert len(result.rolls[notation]) == count
        # Total should be sum of all individual rolls
        assert result.total == sum(result.rolls[notation])

    @pytest.mark.parametrize(
        "notation,expected_modifier",
        [
            ("1d20+5", 5),
            ("1d20-2", -2),
            ("2d6+3", 3),
            ("1d8+10", 10),
            ("3d6-5", -5),
        ],
    )
    def test_roll_dice_modifier_extraction(
        self, notation: str, expected_modifier: int
    ) -> None:
        """Test modifiers are correctly extracted and applied."""
        from tools import roll_dice

        result = roll_dice(notation)
        assert result.modifier == expected_modifier

    def test_roll_dice_4d6_deterministic(self) -> None:
        """Test 4d6 with mocked random for deterministic result."""
        from tools import roll_dice

        with patch("tools.random.randint", side_effect=[4, 3, 5, 2]):
            result = roll_dice("4d6")
            assert result.rolls == {"4d6": [4, 3, 5, 2]}
            assert result.total == 14

    def test_roll_dice_8d6_deterministic(self) -> None:
        """Test 8d6 with mocked random for deterministic result."""
        from tools import roll_dice

        with patch("tools.random.randint", side_effect=[1, 2, 3, 4, 5, 6, 1, 2]):
            result = roll_dice("8d6")
            assert result.rolls == {"8d6": [1, 2, 3, 4, 5, 6, 1, 2]}
            assert result.total == 24

    def test_roll_dice_bounds_4d6(self) -> None:
        """Test that 4d6 rolls are within valid bounds."""
        from tools import roll_dice

        for _ in range(50):
            result = roll_dice("4d6")
            assert 4 <= result.total <= 24

    def test_roll_dice_1d100_percentile(self) -> None:
        """Test d100 (percentile) rolls are within bounds."""
        from tools import roll_dice

        for _ in range(50):
            result = roll_dice("1d100")
            assert 1 <= result.total <= 100

    def test_roll_dice_complex_with_subtraction(self) -> None:
        """Test complex notation with subtraction."""
        from tools import roll_dice

        with patch("tools.random.randint", side_effect=[10, 5, 3]):
            result = roll_dice("1d20+1d6-3")
            # 10 + 5 - 3 = 12
            assert result.total == 12
            assert result.modifier == -3

    def test_roll_dice_large_modifier(self) -> None:
        """Test dice roll with large modifier."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=10):
            result = roll_dice("1d20+100")
            assert result.total == 110
            assert result.modifier == 100

    def test_roll_dice_transcript_format_compatibility(self) -> None:
        """Test DiceResult works with expected transcript format."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=18):
            result = roll_dice("1d20+7")

            # Simulate how it would be used in transcript
            tool_call = {
                "name": "roll_dice",
                "args": {"notation": "1d20+7"},
                "result": result.total,
            }
            assert tool_call["result"] == 25

            # Also check JSON serialization
            import json

            json_str = result.model_dump_json()
            data = json.loads(json_str)
            assert data["total"] == 25
            assert data["notation"] == "1d20+7"

    def test_roll_dice_duplicate_dice_type(self) -> None:
        """Test notation with same dice type appearing twice (1d6+1d6)."""
        from tools import roll_dice

        with patch("tools.random.randint", side_effect=[6, 1]):
            result = roll_dice("1d6+1d6")
            # Both rolls should be captured, not overwritten
            assert result.rolls == {"1d6": [6, 1]}
            assert result.total == 7

    def test_roll_dice_duplicate_multi_dice_type(self) -> None:
        """Test notation with same multi-dice type appearing twice (2d6+2d6)."""
        from tools import roll_dice

        with patch("tools.random.randint", side_effect=[3, 4, 5, 6]):
            result = roll_dice("2d6+2d6+5")
            # All four d6 rolls should be in the list
            assert result.rolls == {"2d6": [3, 4, 5, 6]}
            assert result.total == 23  # 3+4+5+6+5

    def test_roll_dice_whitespace_in_notation(self) -> None:
        """Test dice notation with whitespace around operators."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=10):
            result = roll_dice("1d20 + 5")
            assert result.total == 15
            assert result.modifier == 5

        with patch("tools.random.randint", return_value=10):
            result = roll_dice("  1d20  -  2  ")
            assert result.total == 8
            assert result.modifier == -2

    def test_roll_dice_negative_total(self) -> None:
        """Test dice roll that results in negative total."""
        from tools import roll_dice

        with patch("tools.random.randint", return_value=1):
            result = roll_dice("1d4-10")
            assert result.total == -9
            assert result.modifier == -10
            assert result.rolls == {"1d4": [1]}


class TestDMRollDice:
    """Tests for dm_roll_dice LangChain tool."""

    def test_dm_roll_dice_returns_string(self) -> None:
        """Test that dm_roll_dice returns a string."""
        from tools import dm_roll_dice

        with patch("tools.random.randint", return_value=15):
            result = dm_roll_dice.invoke("1d20")
            assert isinstance(result, str)

    def test_dm_roll_dice_formatted_output(self) -> None:
        """Test dm_roll_dice returns formatted result."""
        from tools import dm_roll_dice

        with patch("tools.random.randint", return_value=18):
            result = dm_roll_dice.invoke("1d20+5")
            assert "1d20+5" in result
            assert "23" in result  # 18 + 5

    def test_dm_roll_dice_is_langchain_tool(self) -> None:
        """Test dm_roll_dice is a LangChain tool with proper metadata."""
        from tools import dm_roll_dice

        # Tool should have name and description
        assert dm_roll_dice.name == "dm_roll_dice"
        assert "dice" in dm_roll_dice.description.lower()

    def test_dm_roll_dice_in_all_exports(self) -> None:
        """Test dm_roll_dice is exported in __all__."""
        import tools

        assert "dm_roll_dice" in tools.__all__

    def test_dm_roll_dice_includes_breakdown(self) -> None:
        """Test dm_roll_dice result includes roll breakdown."""
        from tools import dm_roll_dice

        with patch("tools.random.randint", side_effect=[4, 5, 6]):
            result = dm_roll_dice.invoke("3d6")
            # Should contain the rolls
            assert "3d6" in result
            assert "15" in result  # 4 + 5 + 6


class TestPCRollDice:
    """Tests for pc_roll_dice LangChain tool."""

    def test_pc_roll_dice_returns_string(self) -> None:
        """Test that pc_roll_dice returns a string."""
        from tools import pc_roll_dice

        with patch("tools.random.randint", return_value=15):
            result = pc_roll_dice.invoke("1d20")
            assert isinstance(result, str)

    def test_pc_roll_dice_formatted_output(self) -> None:
        """Test pc_roll_dice returns formatted result."""
        from tools import pc_roll_dice

        with patch("tools.random.randint", return_value=18):
            result = pc_roll_dice.invoke("1d20+5")
            assert "1d20+5" in result
            assert "23" in result  # 18 + 5

    def test_pc_roll_dice_is_langchain_tool(self) -> None:
        """Test pc_roll_dice is a LangChain tool with proper metadata."""
        from tools import pc_roll_dice

        # Tool should have name and description
        assert pc_roll_dice.name == "pc_roll_dice"
        assert "dice" in pc_roll_dice.description.lower()

    def test_pc_roll_dice_in_all_exports(self) -> None:
        """Test pc_roll_dice is exported in __all__."""
        import tools

        assert "pc_roll_dice" in tools.__all__

    def test_pc_roll_dice_includes_breakdown(self) -> None:
        """Test pc_roll_dice result includes roll breakdown."""
        from tools import pc_roll_dice

        with patch("tools.random.randint", side_effect=[4, 5, 6]):
            result = pc_roll_dice.invoke("3d6")
            # Should contain the rolls
            assert "3d6" in result
            assert "15" in result  # 4 + 5 + 6

    def test_pc_roll_dice_description_mentions_skill_check(self) -> None:
        """Test pc_roll_dice description contains guidance for PCs."""
        from tools import pc_roll_dice

        # PC tool should have guidance about when to roll
        description = pc_roll_dice.description.lower()
        assert "skill check" in description or "risky" in description
