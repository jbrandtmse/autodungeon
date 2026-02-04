"""Function tools for dice rolling, character sheet updates, etc."""

from __future__ import annotations

import logging
import random
import re
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from models import CharacterSheet, EquipmentItem, SpellSlots

logger = logging.getLogger("autodungeon")

__all__ = [
    "DiceResult",
    "apply_character_sheet_update",
    "dm_roll_dice",
    "dm_update_character_sheet",
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


def roll_dice(notation: str | None = None) -> DiceResult:
    """Roll dice using standard D&D notation.

    Supports notation like:
    - 1d20, d20, 3d6, 1d4
    - 1d20+5, 1d20-2 (modifiers)
    - 2d6+1d4+3 (complex notation with multiple dice groups)

    Args:
        notation: Dice notation string (e.g., "2d6+3", "1d20+5").
                  Defaults to "1d20" if None or empty.

    Returns:
        DiceResult with rolls breakdown and total

    Raises:
        ValueError: If notation is invalid
    """
    # Default to 1d20 (standard D&D check) if no notation provided
    if notation is None or not notation.strip():
        notation = "1d20"

    original_notation = notation
    # Strip whitespace and remove internal spaces around operators
    notation = notation.strip().replace(" ", "")

    # Handle semicolon-separated multiple rolls (e.g., "d20+1;d20+2;d20+3")
    # Roll only the first one and ignore the rest - LLM should call tool multiple times
    if ";" in notation:
        notation = notation.split(";")[0]

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
def dm_roll_dice(notation: str = "1d20") -> str:
    """Roll dice for skill checks, attacks, saving throws, or damage.

    IMPORTANT: After calling this tool, you MUST include the result in your narrative
    response. Never call this tool without providing accompanying story text.

    Use this tool when:
    - A player attempts something with uncertain outcome (skill checks)
    - Combat attacks or damage need to be resolved
    - Saving throws against effects are required
    - Random determination enhances the story

    Args:
        notation: D&D dice notation. Defaults to "1d20" for standard checks.

    Common notation examples:
        - "1d20" or "d20" - Standard ability/skill check
        - "1d20+5" - Skill check with +5 modifier
        - "1d20+3" - Attack roll with +3 to hit
        - "2d6+3" - Damage roll (e.g., greatsword + STR)
        - "1d8+2" - Damage roll (e.g., longsword + STR)
        - "8d6" - Spell damage (e.g., fireball)
        - "1d20-1" - Check with negative modifier

    Returns:
        Formatted roll result like "1d20+5: [14] + 5 = 19"

    Example usage in narrative:
        Tool call: dm_roll_dice("1d20+5")
        Result: "1d20+5: [14] + 5 = 19"
        Your response: "Thorin swings his axe at the goblin. (Attack: 19) The blade
        connects solidly, biting deep into the creature's shoulder!"
    """
    result = roll_dice(notation)
    return str(result)


@tool
def pc_roll_dice(notation: str = "1d20") -> str:
    """Roll dice for your character's skill checks, attacks, or actions.

    IMPORTANT: After calling this tool, you MUST describe your action and include
    the result in your response. Never call this tool without providing your
    character's narrative action.

    Use this when:
    - You attempt something risky (climbing, sneaking, persuading)
    - You want to check your perception or investigation
    - You make an attack or use an ability
    - The outcome of your action is uncertain

    Args:
        notation: D&D dice notation. Defaults to "1d20" for standard checks.

    Common notation examples:
        - "1d20" or "d20" - Standard ability/skill check
        - "1d20+5" - Skill check with modifier (e.g., Stealth +5)
        - "1d20+3" - Attack roll with modifier
        - "2d6+3" - Damage roll
        - "1d20-1" - Check with negative modifier

    Returns:
        Formatted roll result like "1d20+5: [14] + 5 = 19"

    Example - Correct usage:
        You want to sneak past guards. Call pc_roll_dice("1d20+5").
        Result: "1d20+5: [17] + 5 = 22"
        Your response: "I press myself against the cold stone wall, timing my
        movements to the guards' patrol pattern. (Stealth: 22) My soft boots
        make no sound as I slip past them into the shadows."

    Example - WRONG (don't do this):
        Calling the tool without any accompanying narrative text.
    """
    result = roll_dice(notation)
    return str(result)


# =============================================================================
# Character Sheet Update Tool (Story 8-4)
# =============================================================================


def _apply_list_updates(current: list[str], updates: list[str]) -> list[str]:
    """Apply add/remove updates to a list of strings.

    Items prefixed with "+" are added, items prefixed with "-" are removed.
    Items without a prefix are added (same as "+").

    Args:
        current: The current list.
        updates: List of strings with optional +/- prefix.

    Returns:
        Updated list.
    """
    result = current.copy()
    for item in updates:
        item = item.strip()
        if not item:
            continue
        if item.startswith("-"):
            name = item[1:].strip()
            for i, existing in enumerate(result):
                if existing.lower() == name.lower():
                    result.pop(i)
                    break
        elif item.startswith("+"):
            name = item[1:].strip()
            if not any(existing.lower() == name.lower() for existing in result):
                result.append(name)
        else:
            if not any(existing.lower() == item.lower() for existing in result):
                result.append(item)
    return result


def _apply_equipment_updates(
    current: list[EquipmentItem], updates: list[str]
) -> list[EquipmentItem]:
    """Apply add/remove updates to equipment list.

    Items prefixed with "+" are added, items prefixed with "-" are removed.
    Items without a prefix are added (same as "+").

    Args:
        current: Current equipment items.
        updates: List of item names with optional +/- prefix.

    Returns:
        Updated equipment list.
    """
    result = current.copy()
    for item in updates:
        item = item.strip()
        if not item:
            continue
        if item.startswith("-"):
            name = item[1:].strip()
            for i, existing in enumerate(result):
                if existing.name.lower() == name.lower():
                    result.pop(i)
                    break
        elif item.startswith("+"):
            name = item[1:].strip()
            if not any(existing.name.lower() == name.lower() for existing in result):
                result.append(EquipmentItem(name=name))
        else:
            if not any(existing.name.lower() == item.lower() for existing in result):
                result.append(EquipmentItem(name=item))
    return result


def apply_character_sheet_update(
    sheet: CharacterSheet, updates: dict[str, Any]
) -> tuple[CharacterSheet, str]:
    """Apply updates to a character sheet with validation.

    Supports updating:
    - hit_points_current: Set current HP (clamped to 0..max+temp)
    - hit_points_temp: Set temporary HP
    - conditions: List with +/- prefix for add/remove
    - equipment: List with +/- prefix for add/remove
    - gold, silver, copper: Set currency values (clamped to >= 0)
    - spell_slots: Dict of {level: {"current": N}} to update slot usage
    - experience_points: Set XP value

    Story 8.4: DM Tool Calls for Sheet Updates.
    FR63: DM can update character sheets via tool calls.

    Args:
        sheet: The character sheet to update.
        updates: Dictionary of field names to new values.

    Returns:
        Tuple of (updated CharacterSheet, confirmation message string).

    Raises:
        ValueError: If updates contain invalid fields or values.
    """
    changes: list[str] = []
    update_dict: dict[str, Any] = {}

    for key, value in updates.items():
        if key == "hit_points_current":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"hit_points_current must be an integer, got {type(value).__name__}")
            max_hp = sheet.hit_points_max + sheet.hit_points_temp
            clamped = max(0, min(value, max_hp))
            update_dict["hit_points_current"] = clamped
            diff = clamped - sheet.hit_points_current
            if diff < 0:
                changes.append(f"HP: {sheet.hit_points_current} -> {clamped} ({diff})")
            elif diff > 0:
                changes.append(f"HP: {sheet.hit_points_current} -> {clamped} (+{diff})")
            else:
                changes.append(f"HP: unchanged at {clamped}")

        elif key == "hit_points_temp":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"hit_points_temp must be an integer, got {type(value).__name__}")
            clamped = max(0, value)
            update_dict["hit_points_temp"] = clamped
            changes.append(f"Temp HP: {sheet.hit_points_temp} -> {clamped}")

        elif key == "conditions":
            if not isinstance(value, list):
                raise ValueError(f"conditions must be a list, got {type(value).__name__}")
            new_conditions = _apply_list_updates(sheet.conditions, value)
            update_dict["conditions"] = new_conditions
            added = [v.lstrip("+").strip() for v in value if not v.strip().startswith("-")]
            removed = [v[1:].strip() for v in value if v.strip().startswith("-")]
            parts: list[str] = []
            if added:
                parts.append(f"added {', '.join(added)}")
            if removed:
                parts.append(f"removed {', '.join(removed)}")
            changes.append(f"Conditions: {'; '.join(parts) if parts else 'unchanged'}")

        elif key == "equipment":
            if not isinstance(value, list):
                raise ValueError(f"equipment must be a list, got {type(value).__name__}")
            new_equipment = _apply_equipment_updates(sheet.equipment, value)
            update_dict["equipment"] = new_equipment
            added = [v.lstrip("+").strip() for v in value if not v.strip().startswith("-")]
            removed = [v[1:].strip() for v in value if v.strip().startswith("-")]
            parts_eq: list[str] = []
            if added:
                parts_eq.append(f"gained {', '.join(added)}")
            if removed:
                parts_eq.append(f"lost {', '.join(removed)}")
            changes.append(f"Equipment: {'; '.join(parts_eq) if parts_eq else 'unchanged'}")

        elif key in ("gold", "silver", "copper"):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{key} must be an integer, got {type(value).__name__}")
            clamped = max(0, value)
            update_dict[key] = clamped
            old_val = getattr(sheet, key)
            diff = clamped - old_val
            if diff > 0:
                changes.append(f"{key.capitalize()}: {old_val} -> {clamped} (+{diff})")
            elif diff < 0:
                changes.append(f"{key.capitalize()}: {old_val} -> {clamped} ({diff})")
            else:
                changes.append(f"{key.capitalize()}: unchanged at {clamped}")

        elif key == "spell_slots":
            if not isinstance(value, dict):
                raise ValueError(f"spell_slots must be a dict, got {type(value).__name__}")
            new_slots = {k: v for k, v in sheet.spell_slots.items()}
            slot_changes: list[str] = []
            for level_key, slot_update in value.items():
                level = int(level_key)
                if level not in new_slots:
                    raise ValueError(f"No spell slot at level {level}")
                if not isinstance(slot_update, dict) or "current" not in slot_update:
                    raise ValueError(f"spell_slots[{level}] must have 'current' key")
                new_current = slot_update["current"]
                if not isinstance(new_current, int) or isinstance(new_current, bool):
                    raise ValueError(f"spell_slots[{level}].current must be int")
                old_slot = new_slots[level]
                clamped_current = max(0, min(new_current, old_slot.max))
                new_slots[level] = SpellSlots(current=clamped_current, max=old_slot.max)
                slot_changes.append(f"L{level}: {old_slot.current}/{old_slot.max} -> {clamped_current}/{old_slot.max}")
            update_dict["spell_slots"] = new_slots
            changes.append(f"Spell Slots: {', '.join(slot_changes)}")

        elif key == "experience_points":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"experience_points must be an integer, got {type(value).__name__}")
            clamped = max(0, value)
            update_dict["experience_points"] = clamped
            changes.append(f"XP: {sheet.experience_points} -> {clamped}")

        else:
            raise ValueError(f"Unsupported update field: {key}")

    if not update_dict:
        return sheet, "No changes applied."

    updated_sheet = sheet.model_copy(update=update_dict)
    confirmation = f"Updated {sheet.name}: " + "; ".join(changes)
    return updated_sheet, confirmation


@tool
def dm_update_character_sheet(character_name: str, updates: dict[str, Any]) -> str:
    """Update a character's sheet with game mechanic changes.

    Use this tool when game events change a character's stats, such as:
    - Taking damage or healing
    - Gaining or losing equipment/items
    - Adding or removing conditions
    - Using spell slots
    - Gaining gold or treasure

    IMPORTANT: You must include narrative text in your response alongside this tool call.
    The tool updates the mechanical data; you provide the story.

    Args:
        character_name: The character's name (e.g., "Thorin", "Elara").
        updates: Dictionary describing the changes. Supported fields:
            - "hit_points_current": integer (new HP value)
            - "hit_points_temp": integer (new temp HP value)
            - "conditions": list of strings with +/- prefix
              (e.g., ["+poisoned"] to add, ["-poisoned"] to remove)
            - "equipment": list of strings with +/- prefix
              (e.g., ["+Potion of Healing"] to add, ["-Rope"] to remove)
            - "gold": integer (new gold amount)
            - "silver": integer (new silver amount)
            - "copper": integer (new copper amount)
            - "spell_slots": dict of level to {"current": N}
              (e.g., {"1": {"current": 2}} to set level 1 slots to 2)
            - "experience_points": integer (new XP value)

    Returns:
        Confirmation of changes or error message.

    Examples:
        - Damage: character_name="Thorin", updates={"hit_points_current": 35}
        - Loot: character_name="Thorin", updates={"gold": 100, "equipment": ["+Potion of Healing"]}
        - Condition: character_name="Elara", updates={"conditions": ["+poisoned"]}
        - Spell usage: character_name="Elara", updates={"spell_slots": {"1": {"current": 2}}}
        - Healing: character_name="Thorin", updates={"hit_points_current": 52}
    """
    # This tool's execution is intercepted in dm_turn() which has access to game state.
    # The @tool decorator is for LangChain schema binding only.
    # Actual execution happens in agents.py _execute_sheet_update().
    return f"Sheet update for {character_name}: {updates}"
