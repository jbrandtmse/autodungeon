"""Function tools for dice rolling, scene generation, etc."""

import random
import re

from langchain_core.tools import tool
from pydantic import BaseModel, Field

__all__ = [
    "DiceResult",
    "dm_roll_dice",
    "pc_roll_dice",
    "roll_dice",
    "MAX_DICE_COUNT",
    "MAX_DICE_SIDES",
    "MAX_TOTAL_DICE",
]

# Safety limits to prevent abuse
MAX_DICE_COUNT = 100  # Maximum dice in a single group
MAX_DICE_SIDES = 1000  # Maximum sides on a die
MAX_TOTAL_DICE = 100  # Maximum total dice across all groups

# Regex pattern to match dice groups (e.g., "2d6", "d20", "1d4")
DICE_PATTERN = re.compile(r"(\d*)d(\d+)", re.IGNORECASE)

# Pattern to validate the entire notation
NOTATION_PATTERN = re.compile(r"^(\d*d\d+)([+-](\d*d\d+|\d+))*$", re.IGNORECASE)


class DiceResult(BaseModel):
    """Result of a dice roll with full breakdown.

    Attributes:
        notation: The original dice notation (e.g., "2d6+3")
        rolls: Dict of individual die results grouped by dice type
               e.g., {"2d6": [4, 2], "1d4": [3]} for "2d6+1d4"
        modifier: The total modifier (can be negative)
        total: The final computed total
    """

    notation: str
    rolls: dict[str, list[int]] = Field(default_factory=dict)
    modifier: int = 0
    total: int

    def __str__(self) -> str:
        """Human-readable format for narrative display."""
        parts: list[str] = []
        for dice, values in self.rolls.items():
            parts.append(f"{dice}: {values}")
        roll_str = ", ".join(parts)
        if self.modifier > 0:
            return f"{self.notation}: [{roll_str}] + {self.modifier} = {self.total}"
        elif self.modifier < 0:
            return (
                f"{self.notation}: [{roll_str}] - {abs(self.modifier)} = {self.total}"
            )
        else:
            return f"{self.notation}: [{roll_str}] = {self.total}"


def _roll_single_die(sides: int) -> int:
    """Roll a single die with the given number of sides."""
    return random.randint(1, sides)


def _roll_dice_group(count: int, sides: int) -> list[int]:
    """Roll multiple dice and return individual results."""
    return [_roll_single_die(sides) for _ in range(count)]


def roll_dice(notation: str | None) -> DiceResult:
    """Roll dice using standard D&D notation.

    Supports notation like:
    - 1d20, d20, 3d6, 1d4
    - 1d20+5, 1d20-2 (modifiers)
    - 2d6+1d4+3 (complex notation with multiple dice groups)

    Args:
        notation: Dice notation string (e.g., "2d6+3", "1d20+5")

    Returns:
        DiceResult with rolls breakdown and total

    Raises:
        ValueError: If notation is invalid
        TypeError: If notation is None
    """
    if notation is None:
        raise TypeError("Dice notation cannot be None")

    if not notation or not notation.strip():
        raise ValueError("Dice notation cannot be empty")

    original_notation = notation
    # Strip whitespace and remove internal spaces around operators
    notation = notation.strip().replace(" ", "")

    # Validate notation format
    if not NOTATION_PATTERN.match(notation):
        raise ValueError(f"Invalid dice notation: {original_notation}")

    # Parse the notation into components
    rolls: dict[str, list[int]] = {}
    total = 0
    modifier = 0
    total_dice_count = 0

    # Split by + and - while keeping the operator
    # Handle the notation by processing each component
    components: list[tuple[str, str]] = []  # (sign, component)

    # First, normalize the notation for parsing
    # Replace - with +- to split easier
    normalized = notation.replace("-", "+-")
    parts = [p.strip() for p in normalized.split("+") if p.strip()]

    for part in parts:
        if part.startswith("-"):
            components.append(("-", part[1:]))
        else:
            components.append(("+", part))

    for sign, component in components:
        multiplier = 1 if sign == "+" else -1

        # Check if this is a dice group (contains 'd')
        dice_match = DICE_PATTERN.match(component.lower())
        if dice_match:
            count_str = dice_match.group(1)
            sides_str = dice_match.group(2)

            count = int(count_str) if count_str else 1
            sides = int(sides_str)

            if count <= 0:
                raise ValueError(f"Invalid dice count: {count}")
            if sides <= 0:
                raise ValueError(f"Invalid die sides: {sides}")

            # Check safety limits
            if count > MAX_DICE_COUNT:
                raise ValueError(
                    f"Dice count {count} exceeds maximum of {MAX_DICE_COUNT}"
                )
            if sides > MAX_DICE_SIDES:
                raise ValueError(
                    f"Die sides {sides} exceeds maximum of {MAX_DICE_SIDES}"
                )

            total_dice_count += count
            if total_dice_count > MAX_TOTAL_DICE:
                raise ValueError(
                    f"Total dice count {total_dice_count} exceeds maximum of {MAX_TOTAL_DICE}"
                )

            # Roll the dice
            dice_rolls = _roll_dice_group(count, sides)

            # Store with normalized key (always include count)
            # Handle duplicate dice types by appending to existing list
            dice_key = f"{count}d{sides}"
            if dice_key in rolls:
                rolls[dice_key].extend(dice_rolls)
            else:
                rolls[dice_key] = dice_rolls

            # Add to total (with sign)
            total += multiplier * sum(dice_rolls)
        else:
            # It's a numeric modifier
            try:
                mod_value = int(component)
                modifier += multiplier * mod_value
            except ValueError as err:
                raise ValueError(f"Invalid dice notation: {original_notation}") from err

    total += modifier

    return DiceResult(
        notation=original_notation,
        rolls=rolls,
        modifier=modifier,
        total=total,
    )


@tool
def dm_roll_dice(notation: str) -> str:
    """Roll dice for skill checks, attacks, saving throws, or damage.

    Use this tool when:
    - A player attempts something with uncertain outcome (skill checks)
    - Combat attacks or damage need to be resolved
    - Saving throws against effects are required
    - Random determination enhances the story

    Args:
        notation: D&D dice notation (e.g., "1d20+5", "2d6+3", "d20")

    Returns:
        Formatted roll result for narrative integration, including
        the breakdown of individual dice and the total.
    """
    result = roll_dice(notation)
    return str(result)


@tool
def pc_roll_dice(notation: str) -> str:
    """Roll dice for a skill check or action.

    Use this when:
    - You attempt something risky (climbing, sneaking, persuading)
    - You want to check your perception or investigation
    - You make an attack or use an ability
    - The outcome of your action is uncertain

    Args:
        notation: D&D dice notation (e.g., "1d20+5", "1d20+3", "2d6")

    Returns:
        Formatted roll result showing the breakdown and total.
    """
    result = roll_dice(notation)
    return str(result)
