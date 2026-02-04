"""Agent definitions and LLM factory.

This module provides the factory function for creating LLM clients
for different providers (Gemini, Claude, Ollama), as well as agent
node functions for the LangGraph state machine.
"""

import logging
from datetime import UTC, datetime

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from config import get_config, load_user_settings
from models import (
    AgentMemory,
    CharacterConfig,
    CharacterFacts,
    CharacterSheet,
    DMConfig,
    GameState,
    ModuleDiscoveryResult,
    ModuleInfo,
)
from tools import apply_character_sheet_update, dm_roll_dice, dm_update_character_sheet, pc_roll_dice

# Logger for error tracking (technical details logged internally per FR40)
logger = logging.getLogger("autodungeon")

__all__ = [
    "CLASS_GUIDANCE",
    "DEFAULT_MODELS",
    "DM_CONTEXT_PLAYER_ENTRIES_LIMIT",
    "DM_CONTEXT_RECENT_EVENTS_LIMIT",
    "DM_SYSTEM_PROMPT",
    "LLMConfigurationError",
    "LLMError",
    "MODULE_DISCOVERY_MAX_RETRIES",
    "MODULE_DISCOVERY_PROMPT",
    "MODULE_DISCOVERY_RETRY_PROMPT",
    "PC_CONTEXT_RECENT_EVENTS_LIMIT",
    "PC_SYSTEM_PROMPT_TEMPLATE",
    "SUPPORTED_PROVIDERS",
    "_build_dm_context",
    "_build_pc_context",
    "_execute_sheet_update",
    "_parse_module_json",
    "build_pc_system_prompt",
    "categorize_error",
    "create_dm_agent",
    "create_pc_agent",
    "detect_network_error",
    "discover_modules",
    "dm_turn",
    "format_all_sheets_context",
    "format_character_facts",
    "format_character_sheet_context",
    "format_module_context",
    "get_default_model",
    "get_llm",
    "pc_turn",
]

# Context building limits for DM
DM_CONTEXT_RECENT_EVENTS_LIMIT = 10  # Max recent events from DM's buffer
DM_CONTEXT_PLAYER_ENTRIES_LIMIT = 3  # Max entries per PC agent's buffer

# Context building limits for PC agents
PC_CONTEXT_RECENT_EVENTS_LIMIT = 10  # Max recent events from PC's buffer

# DM System Prompt with improv principles and encounter mode awareness
DM_SYSTEM_PROMPT = """You are the Dungeon Master for a D&D adventure. Your role is to narrate scenes, \
describe environments, control NPCs, and manage encounters with engaging storytelling.

## Core Improv Principles

Follow these improv principles to keep the story collaborative and engaging:

- **"Yes, and..."** - Accept player actions and build upon them. Never deny player creativity outright.
- **Collaborative storytelling** - The players are co-authors of this adventure. Let their choices matter.
- **Add unexpected details** - Surprise players with interesting twists that enhance rather than undermine their actions.
- **Reward creativity** - When players attempt clever solutions, acknowledge and incorporate them.

## Encounter Mode Awareness

Adjust your narration style based on the current encounter type:

### COMBAT Mode
- Keep descriptions action-focused and vivid
- Track initiative order and describe attacks dramatically
- Use the dice rolling tool for attacks, damage, and saving throws
- Maintain tension and pacing

### ROLEPLAY Mode
- Focus on character-driven interactions and emotional beats
- Give each NPC a distinct voice and speech pattern
- Use descriptive tags (e.g., "the merchant says nervously...")
- Allow space for character development

### EXPLORATION Mode
- Emphasize environmental details and atmosphere
- Plant seeds for future discoveries and foreshadowing
- Reward player attention to detail
- Build mystery and intrigue

## NPC Voice Guidelines

When voicing NPCs:
- Each NPC should have a unique speech pattern and personality
- Maintain consistency across scenes (a gruff dwarf stays gruff)
- Use character-appropriate vocabulary and mannerisms
- Express NPC emotions through their words and described actions

## Narrative Continuity

Reference earlier events naturally to maintain immersion:
- Mention consequences of past player decisions
- Weave plot threads from earlier scenes into current narration
- Acknowledge character growth and relationships
- Reward callbacks to earlier details with meaningful payoffs

## Dice Rolling

Use the dm_roll_dice tool when:
- A player attempts something with uncertain outcome (skill checks)
- Combat attacks or damage need to be resolved
- Saving throws against effects are required
- Random outcomes enhance the story

**CRITICAL**: When you call the dice tool, you MUST include narrative text in your response.
Never return just a tool call with no story content.

Common dice notations:
- "1d20+5" - Skill check with modifier (e.g., Perception +5)
- "1d20+3" - Attack roll with modifier
- "2d6+3" - Damage (e.g., greatsword 2d6 + 3 STR)
- "1d20" - Simple check (default if unsure)

Example - Player wants to pick a lock:
1. Call dm_roll_dice("1d20+7") for their Thieves' Tools check
2. Get result: "1d20+7: [15] + 7 = 22"
3. Your response: "Shadowmere's nimble fingers work the tumblers with practiced ease.
   (Thieves' Tools: 22) With a satisfying *click*, the lock surrenders."

After receiving dice results, integrate them meaningfully into your narration. A natural 20 should feel \
heroic; a natural 1 should be dramatically unfortunate but not humiliating.

## Response Format

Keep your responses focused and engaging:
- Start with vivid scene description or action outcome
- Include NPC dialogue when relevant (use quotation marks)
- End with a hook or prompt for player action when appropriate
- Avoid walls of text - aim for punchy, dramatic moments"""

# PC System Prompt Template with placeholders for character-specific content
PC_SYSTEM_PROMPT_TEMPLATE = """You are {name}, a {character_class}.

## Your Personality
{personality}

## Roleplay Guidelines

You are playing this character in a D&D adventure. Follow these guidelines:

- **First person only** - Always speak and act as {name}, using "I" and "me"
- **Stay in character** - Your responses should reflect your personality traits
- **Be consistent** - Remember your character's motivations and relationships
- **Collaborate** - Build on what others say and do; don't contradict established facts
- **Reference the past** - When something reminds you of earlier events, mention it naturally

## Class Behavior

{class_guidance}

## Actions and Dialogue

When responding:
- Describe your character's actions in first person: "I draw my sword and..."
- Use direct dialogue with quotation marks: "Stay back!" I warn them.
- Express your character's emotions and internal thoughts
- React authentically to what's happening around you

## Dice Rolling

Use the pc_roll_dice tool when:
- You attempt something with uncertain outcome
- You want to make a skill check (Perception, Stealth, etc.)
- The DM hasn't already rolled for you

**CRITICAL**: When you call the dice tool, you MUST include your character's action and
dialogue in your response. Never return just a tool call with no narrative text.

Common dice notations:
- "1d20+5" - Skill check with your modifier
- "1d20+3" - Attack roll
- "2d6+2" - Damage roll
- "1d20" - Simple check (default if unsure about modifier)

Example - You want to sneak past guards:
1. Call pc_roll_dice("1d20+5") for Stealth
2. Get result: "1d20+5: [14] + 5 = 19"
3. Your response: "I hold my breath and slip into the shadows, timing my steps
   to the creak of the old floorboards. (Stealth: 19) 'Stay close,' I whisper
   to the others without looking back."

Keep responses focused - you're one character in a party, not the narrator."""

# Class-specific behavior guidance for PC agents
CLASS_GUIDANCE: dict[str, str] = {
    "Fighter": """As a Fighter, you:
- Prefer direct action and combat solutions
- Protect your allies and hold the front line
- Value honor, courage, and martial prowess
- Speak plainly and act decisively""",
    "Rogue": """As a Rogue, you:
- Look for clever solutions and hidden angles
- Prefer stealth, deception, and precision over brute force
- Keep an eye on valuables and escape routes
- Are naturally suspicious and observant""",
    "Wizard": """As a Wizard, you:
- Approach problems with knowledge and arcane insight
- Value learning, research, and magical solutions
- Think before acting, considering magical implications
- Reference your spellbook and arcane studies""",
    "Cleric": """As a Cleric, you:
- Support and protect your allies
- Channel divine power through faith
- Consider the moral and spiritual aspects of situations
- Offer guidance, healing, and wisdom""",
}

# Default guidance for classes not in CLASS_GUIDANCE
_DEFAULT_CLASS_GUIDANCE = """As a {character_class}, you:
- Act according to your class abilities and training
- Make decisions consistent with your background
- Support your party with your unique skills"""

# Supported LLM providers (immutable)
SUPPORTED_PROVIDERS: frozenset[str] = frozenset(["gemini", "claude", "ollama"])

# Default models for each provider
DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-1.5-flash",
    "claude": "claude-3-haiku-20240307",
    "ollama": "llama3",
}


class LLMConfigurationError(Exception):
    """Raised when LLM provider is misconfigured."""

    def __init__(self, provider: str, missing_credential: str) -> None:
        """Initialize the error with provider and missing credential info.

        Args:
            provider: The LLM provider name (e.g., "gemini", "claude").
            missing_credential: The name of the missing credential.
        """
        self.provider = provider
        self.missing_credential = missing_credential
        super().__init__(
            f"Cannot use {provider}: {missing_credential} not set. "
            f"Add it to your .env file or environment."
        )


class LLMError(Exception):
    """Exception raised when LLM API calls fail.

    This exception wraps the original error and provides categorization
    for user-friendly error handling. Technical details are preserved
    for logging while the error_type enables friendly messaging.

    Attributes:
        provider: LLM provider name (gemini, claude, ollama).
        agent: Agent that was executing (dm, rogue, fighter, etc.).
        error_type: Categorized error type (timeout, rate_limit, auth_error, network_error, invalid_response, unknown).
        original_error: The original exception that was caught.
    """

    def __init__(
        self,
        provider: str,
        agent: str,
        error_type: str,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize the LLM error.

        Args:
            provider: LLM provider name.
            agent: Agent that was executing.
            error_type: Categorized error type.
            original_error: The original exception that was caught.
        """
        self.provider = provider
        self.agent = agent
        self.error_type = error_type
        self.original_error = original_error
        super().__init__(f"LLM error ({error_type}) for {agent} using {provider}")


def detect_network_error(exception: Exception) -> bool:
    """Check if exception indicates network connectivity issues.

    Args:
        exception: The caught exception.

    Returns:
        True if this is a network error, False otherwise.
    """
    error_str = str(exception).lower()
    error_type = type(exception).__name__.lower()

    network_indicators = [
        "connection",
        "network",
        "dns",
        "resolve",
        "socket",
        "refused",
        "unreachable",
        "no route",
        "getaddrinfo",
        "errno 11001",  # Windows DNS failure
        "errno -2",  # Linux DNS failure
    ]

    return any(
        indicator in error_str or indicator in error_type
        for indicator in network_indicators
    )


def categorize_error(exception: Exception) -> str:
    """Categorize exception into user-friendly error type.

    Maps various exception types and error messages to one of the
    supported error categories for user-friendly display.

    Args:
        exception: The caught exception.

    Returns:
        Error type string (timeout, rate_limit, auth_error, network_error, invalid_response, unknown).
    """
    error_str = str(exception).lower()

    # Timeout errors
    if "timeout" in error_str or "timed out" in error_str:
        return "timeout"
    if "deadline" in error_str and "exceed" in error_str:
        return "timeout"

    # Rate limit errors
    if "rate" in error_str and "limit" in error_str:
        return "rate_limit"
    if "429" in error_str:
        return "rate_limit"
    if "too many requests" in error_str:
        return "rate_limit"
    if "quota" in error_str and ("exceed" in error_str or "limit" in error_str):
        return "rate_limit"

    # Auth errors
    if "auth" in error_str or "api key" in error_str or "credential" in error_str:
        return "auth_error"
    if "401" in error_str or "403" in error_str:
        return "auth_error"
    if "permission" in error_str and "denied" in error_str:
        return "auth_error"
    if "invalid" in error_str and "key" in error_str:
        return "auth_error"

    # Network errors
    if detect_network_error(exception):
        return "network_error"

    # Invalid response (parsing errors, unexpected format)
    if "parse" in error_str or "json" in error_str or "decode" in error_str:
        return "invalid_response"
    if "unexpected" in error_str and ("response" in error_str or "format" in error_str):
        return "invalid_response"
    if "malformed" in error_str:
        return "invalid_response"

    return "unknown"


def _log_llm_error(error: LLMError) -> None:
    """Log LLM error with structured data for debugging.

    Logs technical details internally per FR40 and NFR7.
    Never exposes these details to users.

    Args:
        error: The LLMError to log.
    """
    logger.error(
        "LLM API call failed",
        extra={
            "provider": error.provider,
            "agent": error.agent,
            "error_type": error.error_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "original_error": str(error.original_error) if error.original_error else "",
        },
    )


def get_default_model(provider: str) -> str:
    """Get the default model for a provider.

    Args:
        provider: The LLM provider name.

    Returns:
        The default model name for the provider.

    Raises:
        ValueError: If the provider is not supported.
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    return DEFAULT_MODELS[provider]


def _get_effective_api_key(provider: str) -> str | None:
    """Get API key for provider, checking user settings first, then env.

    Priority:
    1. User settings (user-settings.yaml from UI configuration)
    2. Environment variable (.env file or system environment)

    Args:
        provider: Provider name ("google", "anthropic", or "ollama").

    Returns:
        The effective API key/URL, or None if not available.
    """
    # Check user settings first (UI overrides)
    user_settings = load_user_settings()
    api_keys = user_settings.get("api_keys", {})

    if provider == "google" and api_keys.get("google"):
        return api_keys["google"]
    if provider == "anthropic" and api_keys.get("anthropic"):
        return api_keys["anthropic"]
    if provider == "ollama" and api_keys.get("ollama"):
        return api_keys["ollama"]

    # Fall back to environment config
    config = get_config()
    if provider == "google":
        return config.google_api_key
    if provider == "anthropic":
        return config.anthropic_api_key
    if provider == "ollama":
        return config.ollama_base_url

    return None


def _extract_text_from_content(content: str | list | None) -> str:
    """Extract text from content value (helper for _extract_response_text).

    Args:
        content: Content value (string, list of strings, or list of content blocks).

    Returns:
        Extracted text string.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if hasattr(content, "__iter__"):
        text_parts: list[str] = []
        for part in content:  # type: ignore[union-attr]
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                # Gemini 3 content block: {"type": "text", "text": "..."}
                text_parts.append(str(part["text"]))
        return "".join(text_parts)
    return str(content) if content else ""


def _extract_response_text(response: object) -> str:
    """Extract text from LLM response object.

    Handles various response formats from different LLM providers:
    - Direct strings (Claude, older Gemini models)
    - List of strings
    - List of content block dicts with 'text' key (Gemini 3 series)
    - content_blocks attribute (Gemini 3 Pro with thinking tokens)
    - .text convenience property (Gemini)

    Args:
        response: The full response object from an LLM invocation.

    Returns:
        Extracted text string, empty string if no text found.
    """
    # Try response.content first (most common)
    content = getattr(response, "content", None)
    text = _extract_text_from_content(content)
    if text:
        return text

    # Try content_blocks (Gemini 3 Pro with thinking tokens)
    content_blocks = getattr(response, "content_blocks", None)
    if content_blocks:
        text = _extract_text_from_content(content_blocks)
        if text:
            logger.info("Extracted text from content_blocks")
            return text

    # Try .text property (Gemini convenience method)
    if hasattr(response, "text"):
        text = response.text  # type: ignore[union-attr]
        if text:
            logger.info("Extracted text from .text property")
            return text

    # Nothing found
    logger.warning("No text extracted from response: content=%r", content)
    return ""


def get_llm(provider: str, model: str) -> BaseChatModel:
    """Create an LLM client for the specified provider and model.

    Factory function that returns the appropriate LangChain chat model
    based on the provider string. Provider names are case-insensitive.

    API keys are resolved in order:
    1. User settings (user-settings.yaml from UI configuration)
    2. Environment variable (.env file or system environment)

    Args:
        provider: The LLM provider ("gemini", "claude", or "ollama").
        model: The model name to use.

    Returns:
        A BaseChatModel instance configured for the specified provider.

    Raises:
        ValueError: If the provider is not supported.
        LLMConfigurationError: If required credentials are missing.
    """
    config = get_config()
    provider = provider.lower()

    match provider:
        case "gemini":
            api_key = _get_effective_api_key("google")
            if not api_key:
                raise LLMConfigurationError("gemini", "GOOGLE_API_KEY")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                timeout=120,  # 2 minutes for Gemini 3 models
            )
        case "claude":
            api_key = _get_effective_api_key("anthropic")
            if not api_key:
                raise LLMConfigurationError("claude", "ANTHROPIC_API_KEY")
            # type: ignore needed - langchain-anthropic type stubs are incomplete
            return ChatAnthropic(  # type: ignore[call-arg]
                model_name=model,
                api_key=api_key,
            )
        case "ollama":
            base_url = _get_effective_api_key("ollama") or config.ollama_base_url
            return ChatOllama(
                model=model,
                base_url=base_url,
            )
        case _:
            raise ValueError(f"Unknown provider: {provider}")


def create_dm_agent(config: DMConfig) -> Runnable:  # type: ignore[type-arg]
    """Create a DM agent with tool bindings.

    Factory function that creates a DM chat model configured with
    the dice rolling tool for combat and skill checks.

    Args:
        config: DM configuration with provider and model settings.

    Returns:
        Configured chat model with dice rolling tool bound.
    """
    base_model = get_llm(config.provider, config.model)
    return base_model.bind_tools([dm_roll_dice, dm_update_character_sheet])


def build_pc_system_prompt(config: CharacterConfig) -> str:
    """Build a personalized system prompt for a PC agent.

    Creates a complete system prompt by injecting the character's
    name, class, personality, and class-specific guidance into
    the PC_SYSTEM_PROMPT_TEMPLATE.

    Args:
        config: Character configuration with name, class, and personality.

    Returns:
        Complete system prompt string personalized for the character.
    """
    class_guidance = CLASS_GUIDANCE.get(
        config.character_class,
        _DEFAULT_CLASS_GUIDANCE.format(character_class=config.character_class),
    )
    return PC_SYSTEM_PROMPT_TEMPLATE.format(
        name=config.name,
        character_class=config.character_class,
        personality=config.personality,
        class_guidance=class_guidance,
    )


def create_pc_agent(config: CharacterConfig) -> Runnable:  # type: ignore[type-arg]
    """Create a PC agent with tool bindings.

    Factory function that creates a PC chat model configured with
    the dice rolling tool for skill checks and actions.

    Args:
        config: Character configuration with provider and model settings.

    Returns:
        Configured chat model with dice rolling tool bound.
    """
    base_model = get_llm(config.provider, config.model)
    return base_model.bind_tools([pc_roll_dice])


def format_character_facts(facts: CharacterFacts) -> str:
    """Format CharacterFacts into a context string for inclusion in agent prompts.

    Story 5.4: Cross-Session Memory & Character Facts.

    Args:
        facts: The CharacterFacts to format.

    Returns:
        Formatted string with character identity information.
    """
    lines = [f"**{facts.name}** ({facts.character_class})"]

    if facts.key_traits:
        traits = ", ".join(facts.key_traits)
        lines.append(f"  Traits: {traits}")

    if facts.relationships:
        rel_parts = [f"{name}: {desc}" for name, desc in facts.relationships.items()]
        lines.append(f"  Relationships: {'; '.join(rel_parts)}")

    if facts.notable_events:
        lines.append(f"  Notable: {'; '.join(facts.notable_events)}")

    return "\n".join(lines)


def format_module_context(module: ModuleInfo | None) -> str:
    """Format module info for DM system prompt injection.

    Creates a formatted markdown section containing the module name and
    description, along with guidance for how the DM should use the module
    knowledge. This is injected into the DM's system prompt when a module
    is selected.

    Story 7.3: Module Context Injection.
    Story 7.4: Returns empty string for freeform adventures (None module).

    Args:
        module: The selected ModuleInfo object, or None for freeform adventures.

    Returns:
        Formatted markdown section for DM prompt, or empty string if no module.
    """
    if module is None:
        return ""

    return f"""## Campaign Module: {module.name}
{module.description}

You are running this official D&D module. Draw upon your knowledge of:
- The setting, locations, and atmosphere
- Key NPCs, their motivations, and personalities
- The main plot hooks and story beats
- Encounters, monsters, and challenges appropriate to this module
"""


# D&D 5e skill-to-ability mapping for modifier calculation
_SKILL_ABILITY_MAP: dict[str, str] = {
    "Acrobatics": "dexterity",
    "Animal Handling": "wisdom",
    "Arcana": "intelligence",
    "Athletics": "strength",
    "Deception": "charisma",
    "History": "intelligence",
    "Insight": "wisdom",
    "Intimidation": "charisma",
    "Investigation": "intelligence",
    "Medicine": "wisdom",
    "Nature": "intelligence",
    "Perception": "wisdom",
    "Performance": "charisma",
    "Persuasion": "charisma",
    "Religion": "intelligence",
    "Sleight of Hand": "dexterity",
    "Stealth": "dexterity",
    "Survival": "wisdom",
}


def _format_modifier(value: int) -> str:
    """Format a modifier with explicit sign.

    Args:
        value: The modifier value.

    Returns:
        Formatted string with + or - prefix.
    """
    return f"+{value}" if value >= 0 else str(value)


def format_character_sheet_context(sheet: CharacterSheet, for_own_character: bool = True) -> str:
    """Format a CharacterSheet into a context string for agent prompts.

    Creates a concise but complete text representation of a character sheet
    suitable for injection into LLM prompts. The format is optimized for
    token efficiency while maintaining readability.

    Story 8.3: Character Sheet Context Injection.
    FR62: Character sheet data is included in agent context.

    Args:
        sheet: The CharacterSheet to format.
        for_own_character: If True, uses "Your Character Sheet" header.
            If False, uses "Character Sheet: {name}" for DM context.

    Returns:
        Formatted character sheet string.
    """
    lines: list[str] = []

    # Header
    if for_own_character:
        lines.append(
            f"## Your Character Sheet: {sheet.name}, {sheet.race} {sheet.character_class} (Level {sheet.level})"
        )
    else:
        lines.append(
            f"### {sheet.name}, {sheet.race} {sheet.character_class} (Level {sheet.level})"
        )

    # HP line with temp HP if present
    hp_parts = [f"HP: {sheet.hit_points_current}/{sheet.hit_points_max}"]
    if sheet.hit_points_temp > 0:
        hp_parts.append(f"(+{sheet.hit_points_temp} temp)")
    hp_line = " ".join(hp_parts)
    lines.append(f"{hp_line} | AC: {sheet.armor_class} | Speed: {sheet.speed}ft")

    # Conditions (always shown per AC3)
    if sheet.conditions:
        lines.append(f"Conditions: {', '.join(sheet.conditions)}")
    else:
        lines.append("Conditions: None")

    # Empty line before abilities
    lines.append("")

    # Ability scores - all on one line for compactness
    abilities = [
        f"STR: {sheet.strength} ({_format_modifier(sheet.strength_modifier)})",
        f"DEX: {sheet.dexterity} ({_format_modifier(sheet.dexterity_modifier)})",
        f"CON: {sheet.constitution} ({_format_modifier(sheet.constitution_modifier)})",
    ]
    lines.append(" | ".join(abilities))

    abilities2 = [
        f"INT: {sheet.intelligence} ({_format_modifier(sheet.intelligence_modifier)})",
        f"WIS: {sheet.wisdom} ({_format_modifier(sheet.wisdom_modifier)})",
        f"CHA: {sheet.charisma} ({_format_modifier(sheet.charisma_modifier)})",
    ]
    lines.append(" | ".join(abilities2))

    # Empty line
    lines.append("")

    # Proficiencies (consolidated)
    prof_parts: list[str] = []
    if sheet.armor_proficiencies:
        prof_parts.append(f"Armor: {', '.join(sheet.armor_proficiencies)}")
    if sheet.weapon_proficiencies:
        prof_parts.append(f"Weapons: {', '.join(sheet.weapon_proficiencies)}")
    if sheet.tool_proficiencies:
        prof_parts.append(f"Tools: {', '.join(sheet.tool_proficiencies)}")
    if prof_parts:
        lines.append(f"Proficiencies: {'; '.join(prof_parts)}")

    # Skills (with calculated modifiers per AC3)
    if sheet.skill_proficiencies or sheet.skill_expertise:
        skill_parts: list[str] = []
        all_skills = list(sheet.skill_proficiencies)
        for skill in sheet.skill_expertise:
            if skill not in all_skills:
                all_skills.append(skill)
        for skill in all_skills:
            # Calculate skill modifier: ability mod + proficiency (or double for expertise)
            ability = _SKILL_ABILITY_MAP.get(skill)
            ability_mod = sheet.get_ability_modifier(ability) if ability else 0
            if skill in sheet.skill_expertise:
                total_mod = ability_mod + (sheet.proficiency_bonus * 2)
            else:
                total_mod = ability_mod + sheet.proficiency_bonus
            skill_parts.append(f"{skill} ({_format_modifier(total_mod)})")
        if skill_parts:
            lines.append(f"Skills: {', '.join(skill_parts)}")

    # Empty line
    lines.append("")

    # Equipment section
    equipment_parts: list[str] = []

    # Weapons with attack bonus and damage
    for weapon in sheet.weapons:
        # Calculate attack bonus based on weapon properties
        attack_bonus = sheet.proficiency_bonus + weapon.attack_bonus
        props_lower = [p.lower() for p in weapon.properties] if weapon.properties else []
        if "finesse" in props_lower:
            # Finesse weapons use higher of STR/DEX
            attack_bonus += max(sheet.strength_modifier, sheet.dexterity_modifier)
        elif "ranged" in props_lower or "ammunition" in props_lower:
            attack_bonus += sheet.dexterity_modifier
        else:
            attack_bonus += sheet.strength_modifier
        equipment_parts.append(
            f"{weapon.name} ({_format_modifier(attack_bonus)}, {weapon.damage_dice} {weapon.damage_type})"
        )

    # Armor
    if sheet.armor:
        equipment_parts.append(sheet.armor.name)

    if equipment_parts:
        lines.append(f"Equipment: {', '.join(equipment_parts)}")

    # Inventory (other items + currency per AC3)
    inv_parts: list[str] = []
    if sheet.equipment:
        inv_parts.extend(
            f"{item.name} ({item.quantity})" if item.quantity > 1 else item.name
            for item in sheet.equipment
        )
    # Currency appended to inventory line per AC3 format
    if sheet.gold > 0:
        inv_parts.append(f"{sheet.gold} gold")
    if sheet.silver > 0:
        inv_parts.append(f"{sheet.silver} silver")
    if sheet.copper > 0:
        inv_parts.append(f"{sheet.copper} copper")
    if inv_parts:
        lines.append(f"Inventory: {', '.join(inv_parts)}")

    # Empty line
    lines.append("")

    # Features
    features: list[str] = []
    features.extend(sheet.class_features)
    features.extend(sheet.racial_traits)
    features.extend(sheet.feats)
    if features:
        lines.append(f"Features: {', '.join(features)}")

    # Spellcasting section (if applicable)
    if sheet.spellcasting_ability:
        lines.append("")
        lines.append(
            f"Spellcasting: {sheet.spellcasting_ability.capitalize()} | "
            f"DC: {sheet.spell_save_dc} | Attack: {_format_modifier(sheet.spell_attack_bonus or 0)}"
        )

        # Cantrips
        if sheet.cantrips:
            lines.append(f"Cantrips: {', '.join(sheet.cantrips)}")

        # Spell slots
        slot_parts: list[str] = []
        for level in sorted(sheet.spell_slots.keys()):
            slots = sheet.spell_slots[level]
            slot_parts.append(f"L{level}: {slots.current}/{slots.max}")
        if slot_parts:
            lines.append(f"Spell Slots: {' | '.join(slot_parts)}")

        # Prepared/known spells
        if sheet.spells_known:
            spell_names = [spell.name for spell in sheet.spells_known]
            lines.append(f"Prepared Spells: {', '.join(spell_names)}")

    return "\n".join(lines)


def format_all_sheets_context(sheets: dict[str, CharacterSheet]) -> str:
    """Format all character sheets for DM context injection.

    Creates a consolidated view of all party character sheets for the DM.
    The DM sees all character sheets to enable informed narrative decisions.

    Story 8.3: Character Sheet Context Injection.
    FR62: DM sees all character sheets.

    Args:
        sheets: Dictionary of character sheets keyed by character name.

    Returns:
        Formatted string with all character sheets, or empty string if none.
    """
    if not sheets:
        return ""

    parts: list[str] = ["## Party Character Sheets"]

    for _name, sheet in sorted(sheets.items()):
        parts.append("")
        parts.append(format_character_sheet_context(sheet, for_own_character=False))

    return "\n".join(parts)


def _build_dm_context(state: GameState) -> str:
    """Build the context string for the DM from all agent memories.

    The DM has asymmetric memory access - it can read ALL agent memories
    to enable dramatic irony and maintain narrative coherence.

    Args:
        state: Current game state.

    Returns:
        Formatted context string containing all relevant memory info.
    """
    context_parts: list[str] = []

    # Add DM's own long-term summary if available
    dm_memory = state["agent_memories"].get("dm")
    if dm_memory and dm_memory.long_term_summary:
        context_parts.append(f"## Story So Far\n{dm_memory.long_term_summary}")

    # Add recent events from DM's short-term buffer
    if dm_memory and dm_memory.short_term_buffer:
        recent_events = "\n".join(
            dm_memory.short_term_buffer[-DM_CONTEXT_RECENT_EVENTS_LIMIT:]
        )
        context_parts.append(f"## Recent Events\n{recent_events}")

    # Add CharacterFacts for all PC agents (Story 5.4)
    character_facts_parts: list[str] = []
    for agent_name, memory in state["agent_memories"].items():
        if agent_name == "dm":
            continue  # DM doesn't have character facts
        if memory.character_facts:
            character_facts_parts.append(format_character_facts(memory.character_facts))

    if character_facts_parts:
        context_parts.append("## Party Members\n" + "\n\n".join(character_facts_parts))

    # Add ALL character sheets for DM (Story 8.3 - FR62: DM sees all)
    character_sheets = state.get("character_sheets", {})
    if character_sheets:
        sheets_context = format_all_sheets_context(character_sheets)
        if sheets_context:
            context_parts.append(sheets_context)

    # DM reads ALL agent memories (asymmetric access per architecture)
    agent_knowledge: list[str] = []
    for agent_name, memory in state["agent_memories"].items():
        if agent_name == "dm":
            continue  # Already handled above
        if memory.short_term_buffer:
            recent = memory.short_term_buffer[-DM_CONTEXT_PLAYER_ENTRIES_LIMIT:]
            agent_knowledge.append(f"[{agent_name} knows]: {'; '.join(recent)}")

    if agent_knowledge:
        context_parts.append("## Player Knowledge\n" + "\n".join(agent_knowledge))

    # Player nudge/suggestion (Story 3.4 - Nudge System)
    # Note: We access Streamlit session_state here because the nudge is UI-specific
    # state that doesn't belong in GameState (per architecture decisions).
    try:
        import streamlit as st

        pending_nudge = st.session_state.get("pending_nudge")
        if pending_nudge:
            # Sanitize nudge to prevent any injection issues
            sanitized_nudge = str(pending_nudge).strip()
            if sanitized_nudge:
                context_parts.append(
                    f"## Player Suggestion\nThe player offers this thought: {sanitized_nudge}"
                )
    except (ImportError, AttributeError):
        # Streamlit not available or session_state not initialized
        # (e.g., in tests without mocking)
        pass

    return "\n\n".join(context_parts)


def _build_pc_context(state: GameState, agent_name: str) -> str:
    """Build the context string for a PC agent from their own memory only.

    PC agents have strict memory isolation - they can ONLY see their own
    AgentMemory. This is the opposite of the DM's asymmetric access.

    Args:
        state: Current game state.
        agent_name: The name of the PC agent (lowercase).

    Returns:
        Formatted context string containing only this PC's memory.
    """
    context_parts: list[str] = []

    # PC agents ONLY access their own memory - strict isolation
    pc_memory = state["agent_memories"].get(agent_name)
    if pc_memory:
        # Add CharacterFacts first - who am I? (Story 5.4)
        if pc_memory.character_facts:
            context_parts.append(
                f"## Character Identity\n{format_character_facts(pc_memory.character_facts)}"
            )

        # Add long-term summary if available
        if pc_memory.long_term_summary:
            context_parts.append(f"## What You Remember\n{pc_memory.long_term_summary}")

        # Add recent events from short-term buffer
        if pc_memory.short_term_buffer:
            recent = "\n".join(
                pc_memory.short_term_buffer[-PC_CONTEXT_RECENT_EVENTS_LIMIT:]
            )
            context_parts.append(f"## Recent Events\n{recent}")

    # Add PC's own character sheet (Story 8.3 - FR62: PC sees only own sheet)
    # Find this PC's character sheet by matching character name
    character_sheets = state.get("character_sheets", {})
    character_config = state["characters"].get(agent_name)
    if character_config:
        # Look up sheet by character name (e.g., "Thorin" not "fighter")
        sheet = character_sheets.get(character_config.name)
        if sheet:
            context_parts.append(format_character_sheet_context(sheet, for_own_character=True))

    return "\n\n".join(context_parts)


def dm_turn(state: GameState) -> GameState:
    """Execute the DM's turn in the game loop.

    LangGraph node function that handles the DM's narrative generation.
    The DM reads all agent memories (asymmetric access), generates a
    narrative response, and updates the game state.

    Args:
        state: Current game state (never mutated).

    Returns:
        New GameState with DM's response appended to logs.

    Raises:
        LLMError: If the LLM API call fails. The error is categorized
            and logged internally before being re-raised for handling
            in the game loop (Story 4.5).
    """
    # Get DM config and create agent
    dm_config = state["dm_config"]

    # Clear nudge after reading (single-use) - Story 3.4
    # Note: We access Streamlit session_state here because the nudge is UI-specific
    # state that doesn't belong in GameState (per architecture decisions).
    try:
        import streamlit as st

        st.session_state["pending_nudge"] = None
    except (ImportError, AttributeError, KeyError):
        # Streamlit not available, session_state not initialized,
        # or pending_nudge key doesn't exist (e.g., in tests without mocking)
        pass

    # Wrap agent creation and invocation in try/except for error handling (Story 4.5)
    try:
        dm_agent = create_dm_agent(dm_config)

        # Build context from all agent memories
        context = _build_dm_context(state)

        # Build system prompt with optional module context (Story 7.3)
        # Module context is appended after base DM instructions
        system_prompt_parts: list[str] = [DM_SYSTEM_PROMPT]
        selected_module = state.get("selected_module")
        if selected_module is not None:
            system_prompt_parts.append(format_module_context(selected_module))
        full_system_prompt = "\n\n".join(system_prompt_parts)

        # Build messages for the model
        messages: list[BaseMessage] = [SystemMessage(content=full_system_prompt)]
        if context:
            messages.append(HumanMessage(content=f"Current game context:\n\n{context}"))
        messages.append(HumanMessage(content="Continue the adventure."))

        # Track any dice results for fallback response
        dice_results: list[str] = []

        # Track character sheet updates from tool calls (Story 8.4)
        updated_sheets: dict[str, "CharacterSheet"] = {
            k: v for k, v in state.get("character_sheets", {}).items()
        }

        # Invoke the model with tool call handling loop
        max_tool_iterations = 5  # Increased for sheet updates alongside dice rolls
        for _ in range(max_tool_iterations):
            response = dm_agent.invoke(messages)

            # Check if model wants to call tools
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                break  # No tool calls, we have the final response

            # Execute tool calls and collect results
            messages.append(response)  # Add AI message with tool calls
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                # Execute the dice roll tool
                if tool_name == "dm_roll_dice":
                    from tools import roll_dice

                    result = roll_dice(tool_args.get("notation"))
                    tool_result = str(result)
                    dice_results.append(tool_result)
                    logger.info("DM rolled dice: %s -> %s", tool_args, tool_result)

                # Execute the character sheet update tool (Story 8.4)
                elif tool_name == "dm_update_character_sheet":
                    tool_result = _execute_sheet_update(
                        tool_args, updated_sheets
                    )
                    logger.info(
                        "DM updated character sheet: %s -> %s",
                        tool_args,
                        tool_result,
                    )

                else:
                    tool_result = f"Unknown tool: {tool_name}"

                # Add tool result message
                messages.append(ToolMessage(content=tool_result, tool_call_id=tool_id))

            # Continue loop to get model's response after tool execution

        # Extract text from response (handles Gemini 3 content blocks)
        response_content = _extract_response_text(response)

        # Retry logic for empty responses
        max_retries = 2
        retry_count = 0
        while not response_content and retry_count < max_retries:
            retry_count += 1
            logger.warning(
                "DM response empty (attempt %d/%d), retrying with nudge...",
                retry_count,
                max_retries,
            )

            # Add a nudge message asking for narrative
            nudge = (
                "Your response was empty. Please provide narrative text describing "
                "what happens next in the adventure. "
            )
            if dice_results:
                nudge += (
                    f"Include the dice result ({dice_results[-1]}) in your narrative."
                )
            messages.append(HumanMessage(content=nudge))

            # Retry the invocation
            response = dm_agent.invoke(messages)
            response_content = _extract_response_text(response)

        # If still empty after retries, generate a fallback response
        if not response_content:
            if dice_results:
                response_content = (
                    f"*The tension in the air is palpable as fate intervenes.* "
                    f"(Roll: {dice_results[-1]}) The outcome hangs in the balance..."
                )
            else:
                response_content = (
                    "*A moment of stillness falls over the scene. The adventurers "
                    "sense that something significant is about to unfold...*"
                )
            logger.warning(
                "DM using fallback response after %d retries: %s",
                max_retries,
                response_content,
            )

    except LLMConfigurationError as e:
        # Re-raise config errors as LLMError for consistent handling
        llm_error = LLMError(
            provider=dm_config.provider,
            agent="dm",
            error_type="auth_error",
            original_error=e,
        )
        _log_llm_error(llm_error)
        raise llm_error from None
    except Exception as e:
        # Categorize and log the error
        error_type = categorize_error(e)
        llm_error = LLMError(
            provider=dm_config.provider,
            agent="dm",
            error_type=error_type,
            original_error=e,
        )
        _log_llm_error(llm_error)
        raise llm_error from e

    # Create new state (never mutate input)
    new_log = state["ground_truth_log"].copy()
    new_log.append(f"[DM]: {response_content}")

    # Update DM's memory
    new_memories = {k: v.model_copy() for k, v in state["agent_memories"].items()}
    dm_memory = new_memories.get("dm")
    if dm_memory is None:
        dm_memory = AgentMemory(token_limit=dm_config.token_limit)
        new_memories["dm"] = dm_memory

    # Append to short-term buffer
    new_buffer = dm_memory.short_term_buffer.copy()
    new_buffer.append(f"[DM]: {response_content}")
    new_memories["dm"] = dm_memory.model_copy(update={"short_term_buffer": new_buffer})

    # Return new state with current_turn updated to "dm"
    # This is critical for route_to_next_agent to know who just acted
    return GameState(
        ground_truth_log=new_log,
        turn_queue=state["turn_queue"],
        current_turn="dm",
        agent_memories=new_memories,
        game_config=state["game_config"],
        dm_config=state["dm_config"],
        characters=state["characters"],
        whisper_queue=state["whisper_queue"],
        human_active=state["human_active"],
        controlled_character=state["controlled_character"],
        session_number=state["session_number"],
        session_id=state["session_id"],
        summarization_in_progress=state.get("summarization_in_progress", False),
        selected_module=state.get("selected_module"),
        character_sheets=updated_sheets,
    )


def _execute_sheet_update(
    tool_args: dict[str, object],
    sheets: dict[str, "CharacterSheet"],
) -> str:
    """Execute a character sheet update from DM tool call.

    Parses the tool arguments, finds the character sheet, applies updates,
    and returns a confirmation message.

    Story 8.4: DM Tool Calls for Sheet Updates.

    Args:
        tool_args: Tool call arguments with "character_name" and "updates".
        sheets: Mutable dict of character sheets (updated in place).

    Returns:
        Confirmation or error message string.
    """
    import json

    character_name = tool_args.get("character_name", "")
    updates_raw = tool_args.get("updates", "{}")

    if not character_name:
        return "Error: character_name is required."

    # Parse updates JSON string
    if isinstance(updates_raw, str):
        try:
            updates = json.loads(updates_raw)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON in updates: {e}"
    elif isinstance(updates_raw, dict):
        updates = updates_raw
    else:
        return f"Error: updates must be a JSON string or dict, got {type(updates_raw).__name__}"

    if not isinstance(updates, dict):
        return f"Error: updates must be a JSON object, got {type(updates).__name__}"

    # Find the character sheet
    sheet = sheets.get(str(character_name))
    if sheet is None:
        available = ", ".join(sheets.keys()) if sheets else "none"
        return f"Error: No character sheet found for '{character_name}'. Available: {available}"

    # Apply updates
    try:
        updated_sheet, confirmation = apply_character_sheet_update(sheet, updates)
        sheets[str(character_name)] = updated_sheet
        return confirmation
    except (ValueError, TypeError) as e:
        return f"Error updating {character_name}: {e}"


def pc_turn(state: GameState, agent_name: str) -> GameState:
    """Execute a PC agent's turn in the game loop.

    LangGraph node function that handles a PC's action/dialogue generation.
    PC agents have strict memory isolation - they only see their own memory.

    Note: This function takes an extra agent_name parameter to identify
    which PC is acting. When added to LangGraph (Story 1.7), this will be
    wrapped in lambdas or partial functions.

    Args:
        state: Current game state (never mutated).
        agent_name: The name of the PC agent (lowercase, e.g., "shadowmere").

    Returns:
        New GameState with PC's response appended to logs.

    Raises:
        KeyError: If the agent_name is not found in characters dict.
        LLMError: If the LLM API call fails. The error is categorized
            and logged internally before being re-raised for handling
            in the game loop (Story 4.5).
    """
    # Get character config from state
    character_config = state["characters"][agent_name]

    # Wrap agent creation and invocation in try/except for error handling (Story 4.5)
    try:
        # Create agent with tools bound
        pc_agent = create_pc_agent(character_config)

        # Build system prompt personalized for this character
        system_prompt = build_pc_system_prompt(character_config)

        # Build context from PC's own memory only (strict isolation)
        context = _build_pc_context(state, agent_name)

        # Build messages for the model
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        if context:
            messages.append(
                HumanMessage(content=f"Your current knowledge:\n\n{context}")
            )
        messages.append(HumanMessage(content="It's your turn. What do you do?"))

        # Track any dice results for fallback response
        dice_results: list[str] = []

        # Invoke the model with tool call handling loop
        max_tool_iterations = 3  # Prevent infinite loops
        for _ in range(max_tool_iterations):
            response = pc_agent.invoke(messages)

            # Check if model wants to call tools
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                break  # No tool calls, we have the final response

            # Execute tool calls and collect results
            messages.append(response)  # Add AI message with tool calls
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                # Execute the dice roll tool
                if tool_name == "pc_roll_dice":
                    from tools import roll_dice

                    result = roll_dice(tool_args.get("notation"))
                    tool_result = str(result)
                    dice_results.append(tool_result)
                    logger.info(
                        "%s rolled dice: %s -> %s", agent_name, tool_args, tool_result
                    )
                else:
                    tool_result = f"Unknown tool: {tool_name}"

                # Add tool result message
                messages.append(ToolMessage(content=tool_result, tool_call_id=tool_id))

            # Continue loop to get model's response after tool execution

        # Extract text from response (handles Gemini 3 content blocks)
        response_content = _extract_response_text(response)

        # Retry logic for empty responses
        max_retries = 2
        retry_count = 0
        while not response_content and retry_count < max_retries:
            retry_count += 1
            logger.warning(
                "%s response empty (attempt %d/%d), retrying with nudge...",
                agent_name,
                retry_count,
                max_retries,
            )

            # Add a nudge message asking for narrative
            nudge = (
                "Your response was empty. Please describe your character's action "
                "in first person, including any dialogue. "
            )
            if dice_results:
                nudge += (
                    f"Include your dice result ({dice_results[-1]}) in your narrative."
                )
            messages.append(HumanMessage(content=nudge))

            # Retry the invocation
            response = pc_agent.invoke(messages)
            response_content = _extract_response_text(response)

        # If still empty after retries, generate a fallback response
        if not response_content:
            if dice_results:
                response_content = (
                    f"*{character_config.name} takes action cautiously, watching the "
                    f"situation unfold.* (Roll: {dice_results[-1]})"
                )
            else:
                response_content = (
                    f"*{character_config.name} observes the situation carefully, "
                    "ready to act when the moment is right.*"
                )
            logger.warning(
                "%s using fallback response after %d retries: %s",
                agent_name,
                max_retries,
                response_content,
            )

    except LLMConfigurationError as e:
        # Re-raise config errors as LLMError for consistent handling
        llm_error = LLMError(
            provider=character_config.provider,
            agent=agent_name,
            error_type="auth_error",
            original_error=e,
        )
        _log_llm_error(llm_error)
        raise llm_error from None
    except Exception as e:
        # Categorize and log the error
        error_type = categorize_error(e)
        llm_error = LLMError(
            provider=character_config.provider,
            agent=agent_name,
            error_type=error_type,
            original_error=e,
        )
        _log_llm_error(llm_error)
        raise llm_error from e

    # Create new state (never mutate input)
    new_log = state["ground_truth_log"].copy()
    new_log.append(f"[{character_config.name}]: {response_content}")

    # Update PC's memory
    new_memories = {k: v.model_copy() for k, v in state["agent_memories"].items()}
    pc_memory = new_memories.get(agent_name)
    if pc_memory is None:
        pc_memory = AgentMemory(token_limit=character_config.token_limit)
        new_memories[agent_name] = pc_memory

    # Append to short-term buffer
    new_buffer = pc_memory.short_term_buffer.copy()
    new_buffer.append(f"[{character_config.name}]: {response_content}")
    new_memories[agent_name] = pc_memory.model_copy(
        update={"short_term_buffer": new_buffer}
    )

    # Return new state with current_turn updated to this agent's name
    # This is critical for route_to_next_agent to know who just acted
    return GameState(
        ground_truth_log=new_log,
        turn_queue=state["turn_queue"],
        current_turn=agent_name,
        agent_memories=new_memories,
        game_config=state["game_config"],
        dm_config=state["dm_config"],
        characters=state["characters"],
        whisper_queue=state["whisper_queue"],
        human_active=state["human_active"],
        controlled_character=state["controlled_character"],
        session_number=state["session_number"],
        session_id=state["session_id"],
        summarization_in_progress=state.get("summarization_in_progress", False),
        selected_module=state.get("selected_module"),
        character_sheets=state.get("character_sheets", {}),
    )


# =============================================================================
# Module Discovery (Story 7.1)
# =============================================================================

# Maximum retry attempts for module discovery
MODULE_DISCOVERY_MAX_RETRIES = 2

# Initial module discovery prompt
MODULE_DISCOVERY_PROMPT = """You are the dungeon master in a dungeons and dragons game.

What dungeons and dragons modules do you know from your training?

Return exactly 100 modules in JSON format. Each module must have:
- number: Integer from 1 to 100
- name: The official module name
- description: A 1-2 sentence description of the adventure

Example format:
```json
[
  {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror adventure in the haunted realm of Barovia, where players must defeat the vampire lord Strahd von Zarovich."},
  {"number": 2, "name": "Lost Mine of Phandelver", "description": "Starter adventure set in the Sword Coast where heroes discover a lost dwarven mine and its magical forge."}
]
```

Include modules from different editions (AD&D, 2e, 3e, 4e, 5e) and various campaign settings (Forgotten Realms, Greyhawk, Dragonlance, Ravenloft, Eberron, etc.).

Return ONLY the JSON array, no additional text."""

# Retry prompt with more explicit JSON instructions
MODULE_DISCOVERY_RETRY_PROMPT = """Your previous response could not be parsed as valid JSON.

Please return exactly 100 D&D modules as a valid JSON array. Each object must have these exact keys:
- "number": integer (1-100)
- "name": string (module name)
- "description": string (brief description)

The response must:
1. Start with [ and end with ]
2. Use double quotes for strings
3. Separate objects with commas
4. Have no trailing commas
5. Contain no text before or after the JSON array

Example of valid format:
[
  {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror in Barovia."},
  {"number": 2, "name": "Lost Mine of Phandelver", "description": "Starter adventure in the Sword Coast."}
]

Return ONLY the JSON array now:"""


def _parse_module_json(response_text: str) -> list["ModuleInfo"]:
    """Parse JSON array of modules from LLM response text.

    Handles common LLM response quirks:
    - JSON wrapped in markdown code blocks
    - Leading/trailing whitespace
    - Extra text before/after JSON

    Args:
        response_text: Raw text from LLM response.

    Returns:
        List of validated ModuleInfo objects.

    Raises:
        json.JSONDecodeError: If JSON parsing fails.
        ValueError: If parsed data doesn't match expected structure.
    """
    import json

    # Validate input - empty response should fail fast
    if not response_text or not response_text.strip():
        raise json.JSONDecodeError("Empty response text", response_text or "", 0)

    # Strip whitespace
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Try to find JSON array in response
    # Look for first [ and last ]
    start_idx = text.find("[")
    end_idx = text.rfind("]")

    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        raise json.JSONDecodeError("No JSON array found in response", text, 0)

    json_text = text[start_idx : end_idx + 1]

    # Parse JSON
    data = json.loads(json_text)

    if not isinstance(data, list):
        raise ValueError("Expected JSON array, got: " + type(data).__name__)

    # Validate and convert to ModuleInfo objects
    modules: list[ModuleInfo] = []
    for item in data:
        if not isinstance(item, dict):
            continue  # Skip invalid items

        try:
            module = ModuleInfo(
                number=item.get("number", len(modules) + 1),
                name=str(item.get("name", "")).strip(),
                description=str(item.get("description", "")).strip(),
                setting=str(item.get("setting", "")).strip(),
                level_range=str(item.get("level_range", "")).strip(),
            )
            modules.append(module)
        except Exception as e:
            logger.warning("Skipping invalid module entry: %s", e)
            continue

    return modules


def discover_modules(dm_config: DMConfig) -> "ModuleDiscoveryResult":
    """Query the DM LLM for known D&D modules.

    Uses the configured DM provider and model to ask what D&D modules
    the LLM knows from training. Returns a structured list of modules.

    Story 7.1: Module Discovery via LLM Query.

    Args:
        dm_config: DM configuration with provider and model settings.

    Returns:
        ModuleDiscoveryResult containing list of ModuleInfo objects.

    Raises:
        LLMError: If the LLM API call fails after retries.
    """
    import json

    llm = get_llm(dm_config.provider, dm_config.model)
    retry_count = 0

    for attempt in range(MODULE_DISCOVERY_MAX_RETRIES + 1):
        try:
            # Use standard prompt on first attempt, retry prompt on subsequent
            prompt = (
                MODULE_DISCOVERY_PROMPT
                if attempt == 0
                else MODULE_DISCOVERY_RETRY_PROMPT
            )

            # Invoke LLM
            messages = [HumanMessage(content=prompt)]
            response = llm.invoke(messages)

            # Extract response text
            response_text = _extract_response_text(response)

            # Parse JSON from response
            modules = _parse_module_json(response_text)

            return ModuleDiscoveryResult(
                modules=modules,
                provider=dm_config.provider,
                model=dm_config.model,
                timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                retry_count=retry_count,
            )

        except json.JSONDecodeError as e:
            retry_count += 1
            if attempt == MODULE_DISCOVERY_MAX_RETRIES:
                # Log error and raise LLMError (truncate error message for safety)
                error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
                logger.error(
                    "Module discovery JSON parse failed after %d retries: %s",
                    retry_count,
                    error_msg,
                )
                raise LLMError(
                    provider=dm_config.provider,
                    agent="dm",
                    error_type="invalid_response",
                    original_error=e,
                ) from e
            logger.warning(
                "Module discovery JSON parse failed (attempt %d), retrying...",
                attempt + 1,
            )

        except LLMConfigurationError as e:
            # Re-raise config errors as LLMError for consistent handling
            raise LLMError(
                provider=dm_config.provider,
                agent="dm",
                error_type="auth_error",
                original_error=e,
            ) from e

        except Exception as e:
            # Categorize and wrap the error
            error_type = categorize_error(e)
            raise LLMError(
                provider=dm_config.provider,
                agent="dm",
                error_type=error_type,
                original_error=e,
            ) from e

    # Should not reach here, but safety return
    return ModuleDiscoveryResult(
        modules=[],
        provider=dm_config.provider,
        model=dm_config.model,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        retry_count=retry_count,
    )
