"""Agent definitions and LLM factory.

This module provides the factory function for creating LLM clients
for different providers (Gemini, Claude, Ollama), as well as agent
node functions for the LangGraph state machine.
"""

import logging
from datetime import UTC, datetime
from typing import Literal

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
    AgentSecrets,
    CallbackLog,
    CharacterConfig,
    CharacterFacts,
    CharacterSheet,
    CombatState,
    DMConfig,
    GameState,
    ModuleDiscoveryResult,
    ModuleInfo,
    NarrativeElement,
    NarrativeElementStore,
    NpcProfile,
)
from tools import (
    apply_character_sheet_update,
    dm_end_combat,
    dm_reveal_secret,
    dm_roll_dice,
    dm_start_combat,
    dm_update_character_sheet,
    dm_whisper_to_agent,
    pc_roll_dice,
    roll_initiative,
)

# Logger for error tracking (technical details logged internally per FR40)
logger = logging.getLogger("autodungeon")

__all__ = [
    "CLASS_GUIDANCE",
    "DEFAULT_MODELS",
    "DM_COMBAT_BOOKEND_PROMPT_TEMPLATE",
    "DM_CONTEXT_PLAYER_ENTRIES_LIMIT",
    "DM_CONTEXT_RECENT_EVENTS_LIMIT",
    "DM_NPC_TURN_PROMPT_TEMPLATE",
    "DM_SYSTEM_PROMPT",
    "LLMConfigurationError",
    "LLMError",
    "MAX_CALLBACK_SUGGESTIONS",
    "MIN_CALLBACK_SCORE",
    "MODULE_DISCOVERY_MAX_RETRIES",
    "MODULE_DISCOVERY_PROMPT",
    "MODULE_DISCOVERY_RETRY_PROMPT",
    "PC_CONTEXT_RECENT_EVENTS_LIMIT",
    "PC_SHARED_CONTEXT_LIMIT",
    "PC_SYSTEM_PROMPT_TEMPLATE",
    "SUPPORTED_PROVIDERS",
    "_build_combat_bookend_prompt",
    "_build_combatant_summary",
    "_build_dm_context",
    "_build_npc_turn_prompt",
    "_build_pc_context",
    "_get_combat_turn_type",
    "_execute_end_combat",
    "_execute_reveal",
    "_execute_sheet_update",
    "_execute_start_combat",
    "_execute_whisper",
    "_parse_module_json",
    "build_pc_system_prompt",
    "categorize_error",
    "create_dm_agent",
    "create_pc_agent",
    "detect_network_error",
    "discover_modules",
    "dm_turn",
    "format_all_secrets_context",
    "format_all_sheets_context",
    "format_callback_suggestions",
    "format_character_facts",
    "format_character_sheet_context",
    "format_module_context",
    "format_pc_secrets_context",
    "get_default_model",
    "get_llm",
    "pc_turn",
    "score_callback_relevance",
]

# Context building limits for DM
DM_CONTEXT_RECENT_EVENTS_LIMIT = 10  # Max recent events from DM's buffer
DM_CONTEXT_PLAYER_ENTRIES_LIMIT = 3  # Max entries per PC agent's buffer

# Context building limits for PC agents
PC_CONTEXT_RECENT_EVENTS_LIMIT = 10  # Max recent events from PC's buffer
PC_SHARED_CONTEXT_LIMIT = 15  # Max recent ground_truth_log entries shown to PCs

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
- Check the "Callback Opportunities" section in your context for specific story threads to weave in
- These suggestions are optional inspiration - use them when they fit naturally, ignore when they don't

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

**PC dice fallback**: Some player characters (especially those using local LLMs) may include dice \
notation in their text (e.g., "1d20+5") instead of an actual rolled result. If you see unresolved dice \
notation in a PC's response rather than a concrete number, use your dm_roll_dice tool to roll for them \
and adjudicate the outcome in your narration.

## Private Whispers

Use the dm_whisper_to_agent tool to send private information to individual characters:

- **Perception checks**: When one character notices something others don't
- **Background knowledge**: When a character's history gives them unique insight
- **Secret communications**: When an NPC whispers to a specific character
- **Divine/magical senses**: When a character's abilities reveal hidden information

Examples:
- "You notice the barkeep slipping a note under the counter" (to the observant rogue)
- "Your training as a city guard recognizes these as counterfeit coins" (to the fighter)
- "Your divine sense detects a faint aura of undeath from the cellar" (to the paladin)

Whispers create dramatic irony and player engagement. The whispered character can choose
when and how to share (or hide) this information from the party.

## Player Whispers

When you receive a "Player Whisper", the human player is privately asking you something:

- Answer their question through your narration or by whispering back to their character
- If they ask about perception/insight, consider having them roll or just incorporate the answer
- You can use dm_whisper_to_agent to send private information back to their character
- Keep the private nature - don't explicitly reveal in public narration that they asked

Example responses:
- Player whispers: "Can my rogue notice if the merchant is lying?"
  - You could whisper back: "Your keen eyes catch the merchant's tell - his left eye twitches when he mentions the price"
  - Or narrate: "As you study the merchant, something feels off about his demeanor..."

## Secret Revelations

When characters have secret knowledge, consider:
- Build dramatic tension before a secret is revealed
- Let the character with the secret choose their moment to act
- When a secret is revealed, use dm_reveal_secret to mark it as revealed
- After revelation, other characters can react to the newly-exposed information
- Create satisfying "aha" moments by paying off setup with revelation

Use dm_reveal_secret when:
- A character openly acts on knowledge only they had
- The truth comes out through roleplay or confrontation
- An NPC's hidden motives are exposed
- A secret naturally becomes common knowledge

Example flow:
1. Earlier: dm_whisper_to_agent("Shadowmere", "The merchant's coin purse is fake")
2. Shadowmere acts on this: "I point at his purse. 'Nice forgery, but I know fake gold when I see it.'"
3. DM: dm_reveal_secret("Shadowmere", content_hint="fake gold")
4. DM narrates: The merchant's face goes pale. The rest of the party now sees what Shadowmere spotted all along...

## Response Format

Keep your responses focused and engaging:
- Start with vivid scene description or action outcome
- Include NPC dialogue when relevant (use quotation marks)
- End with a hook or prompt for player action when appropriate
- Avoid walls of text - aim for punchy, dramatic moments"""

# Combat bookend prompt template (Story 15.4)
DM_COMBAT_BOOKEND_PROMPT_TEMPLATE = """
## Combat Round {round_number}

You are narrating the start of combat round {round_number}. Your role is to set the scene for this round.

**Your task:**
- Summarize the battlefield state and any changes from the previous round
- Describe environmental details, ongoing effects, or dramatic tension
- Set the stage for the combatants who will act this round
- Do NOT act for any specific NPC or monster -- their turns will come individually

**Current Combatants:**
{combatant_summary}

Keep this narration concise (2-4 sentences). Focus on atmosphere and tactical awareness.
"""

# NPC turn prompt template (Story 15.4)
DM_NPC_TURN_PROMPT_TEMPLATE = """
## NPC Turn: {npc_name}

You are now acting as **{npc_name}** for their combat turn.

**{npc_name}'s Status:**
- HP: {hp_current}/{hp_max} | AC: {ac} | Initiative: {initiative_roll}
- Personality: {personality}
- Tactics: {tactics}
{conditions_line}

**Your task:**
- Narrate {npc_name}'s action this round (attack, movement, ability, etc.)
- Stay in character using {npc_name}'s personality and tactics
- Focus ONLY on {npc_name}'s action -- do not narrate other combatants' turns
- Describe the action dramatically and with tactical detail

Respond as the DM narrating {npc_name}'s action in third person.
"""

# PC System Prompt Template with placeholders for character-specific content
PC_SYSTEM_PROMPT_TEMPLATE = """You are {name}, a {character_class}.

## Your Personality
{personality}

## Roleplay Guidelines

You are playing this character in a D&D adventure. Follow these guidelines:

- **Read the scene** - Carefully read the "Current Scene" in your context. Your response MUST \
react to what the DM just described and what other characters just did. Never ignore the scene.
- **First person only** - Always speak and act as {name}, using "I" and "me"
- **Match the situation** - In social encounters, talk to NPCs. In exploration, investigate. \
In combat, fight. Do NOT attack when the scene is peaceful or NPCs are friendly.
- **Stay in character** - Your responses should reflect your personality traits
- **No unprovoked violence** - Never attack NPCs or creatures unless they are hostile, \
you are provoked, or there is a clear strategic reason. When in doubt, use dialogue first.
- **Collaborate** - Build on what others say and do; don't contradict established facts
- **Reference the past** - When something reminds you of earlier events, mention it naturally

## Class Behavior

{class_guidance}

## Actions and Dialogue

When responding:
- **Respond to the current scene** - If the DM described an NPC talking to you, answer them. \
If the party is exploring, describe what you investigate. If combat started, then fight.
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
        "LLM API call failed: provider=%s agent=%s type=%s error=%s",
        error.provider,
        error.agent,
        error.error_type,
        str(error.original_error) if error.original_error else "",
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


def get_llm(provider: str, model: str, timeout: int | None = None) -> BaseChatModel:
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
                timeout=timeout or 120,  # Default 2 min, callers can override
                max_retries=1,  # Disable SDK infinite retry on 429s
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
                timeout=timeout or 300,  # Default 5 min, callers can override
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
    return base_model.bind_tools(
        [
            dm_roll_dice,
            dm_update_character_sheet,
            dm_whisper_to_agent,
            dm_reveal_secret,
            dm_start_combat,
            dm_end_combat,
        ]
    )


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


def format_character_sheet_context(
    sheet: CharacterSheet, for_own_character: bool = True
) -> str:
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
        props_lower = (
            [p.lower() for p in weapon.properties] if weapon.properties else []
        )
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


def format_pc_secrets_context(secrets: AgentSecrets) -> str:
    """Format a PC's secret knowledge for their prompt context.

    Creates a formatted section containing the agent's active whispers
    (unrevealed secrets) for injection into their LLM prompt context.
    Revealed whispers are excluded.

    Story 10.3: Secret Knowledge Injection.
    FR72: Whispered information only appears in recipient's context.

    Args:
        secrets: The agent's AgentSecrets object.

    Returns:
        Formatted secret knowledge section, or empty string if no active secrets.
    """
    active_whispers = secrets.active_whispers()
    if not active_whispers:
        return ""

    lines = ["## Secret Knowledge (Only You Know This)"]
    for whisper in active_whispers:
        lines.append(f"- [Turn {whisper.turn_created}] {whisper.content}")

    return "\n".join(lines)


def format_all_secrets_context(agent_secrets: dict[str, AgentSecrets]) -> str:
    """Format all active secrets for DM context.

    Creates a formatted section containing all agents' active whispers
    for the DM's prompt context. The DM sees all secrets to enable
    dramatic irony and narrative coherence.

    Story 10.3: Secret Knowledge Injection.
    DM sees ALL whispers (knows all secrets).

    Args:
        agent_secrets: Dict of all agent secrets keyed by agent name.

    Returns:
        Formatted secrets section for DM, or empty string if no active secrets.
    """
    all_secrets: list[str] = []
    for agent_key, secrets in sorted(agent_secrets.items()):
        active_whispers = secrets.active_whispers()
        for whisper in active_whispers:
            all_secrets.append(
                f"- [{agent_key.title()}] [Turn {whisper.turn_created}] {whisper.content}"
            )

    if not all_secrets:
        return ""

    lines = ["## Active Secrets (You Know All)"]
    lines.extend(all_secrets)
    return "\n".join(lines)


# =============================================================================
# Callback Suggestions (Story 11.3)
# =============================================================================

# Constants for callback suggestions
MAX_CALLBACK_SUGGESTIONS = 5  # Max suggestions to include in DM context
MIN_CALLBACK_SCORE = 0.0  # Minimum score threshold (0.0 = include all scored)


def score_callback_relevance(
    element: NarrativeElement,
    current_turn: int,
    active_characters: list[str],
) -> float:
    """Score a narrative element for callback suggestion relevance.

    Higher scores indicate better candidates for DM callback suggestions.
    The scoring considers:
    - How long since the element was last referenced (longer gap = more impactful)
    - Whether involved characters are currently active
    - How established the element is in the narrative
    - Whether AI-suggested callback uses exist
    - Whether the element is dormant (penalty)

    Story 11.3: DM Callback Suggestions.
    FR78: DM context includes callback suggestions.

    Args:
        element: The NarrativeElement to score.
        current_turn: Current turn number for recency calculation.
        active_characters: List of currently active character names (from turn_queue).

    Returns:
        Float score (higher = better callback candidate).
    """
    score = 0.0

    # Recency gap bonus: elements unreferenced longer are more impactful callbacks
    # Capped at 5.0 to prevent ancient dormant elements from dominating
    # Floor at 0 to handle edge cases where last_referenced_turn > current_turn
    turns_since_reference = max(0, current_turn - element.last_referenced_turn)
    score += min(turns_since_reference / 10.0, 5.0)

    # Character involvement: bonus if involved characters are in active party
    active_lower = [c.lower() for c in active_characters]
    if any(c.lower() in active_lower for c in element.characters_involved):
        score += 2.0

    # Importance: more-referenced elements are more established
    score += element.times_referenced * 0.5

    # Potential callbacks: bonus if AI already suggested uses
    if element.potential_callbacks:
        score += 1.0

    # Dormancy penalty: still available but deprioritized
    if element.dormant:
        score -= 3.0

    return score


def format_callback_suggestions(
    callback_database: NarrativeElementStore,
    current_turn: int,
    active_characters: list[str],
) -> str:
    """Format callback suggestions for DM context injection.

    Scores active narrative elements by callback relevance, selects
    the top candidates, and formats them into a markdown section
    matching the epic AC format.

    Story 11.3: DM Callback Suggestions.
    FR78: DM context includes callback suggestions.

    Args:
        callback_database: Campaign-level NarrativeElementStore.
        current_turn: Current turn number.
        active_characters: List of active character names from turn_queue.

    Returns:
        Formatted markdown section, or empty string if no suggestions.
    """
    # Get active (non-resolved) elements
    active_elements = callback_database.get_active()
    if not active_elements:
        return ""

    # Score and rank elements
    scored: list[tuple[float, NarrativeElement]] = []
    for element in active_elements:
        element_score = score_callback_relevance(
            element, current_turn, active_characters
        )
        if element_score >= MIN_CALLBACK_SCORE:
            scored.append((element_score, element))

    if not scored:
        return ""

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top N
    top_suggestions = scored[:MAX_CALLBACK_SUGGESTIONS]

    # Format output matching epic AC
    lines = [
        "## Callback Opportunities",
        "Consider weaving in these earlier story elements:",
        "",
    ]

    for idx, (_score, element) in enumerate(top_suggestions, 1):
        # Header: name, turn, session
        lines.append(
            f"{idx}. **{element.name}** (Turn {element.turn_introduced}, Session {element.session_introduced})"
        )
        # Description
        if element.description:
            lines.append(f"   {element.description}")
        # Potential use (first suggestion only, for brevity)
        if element.potential_callbacks:
            lines.append(f"   Potential use: {element.potential_callbacks[0]}")
        # Blank line between entries
        lines.append("")

    return "\n".join(lines).rstrip()


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

    # Add all active (unrevealed) secrets for DM (Story 10.3 - DM sees all secrets)
    agent_secrets = state.get("agent_secrets", {})
    if agent_secrets:
        secrets_context = format_all_secrets_context(agent_secrets)
        if secrets_context:
            context_parts.append(secrets_context)

    # Add callback suggestions from campaign database (Story 11.3 - FR78)
    callback_database = state.get("callback_database", NarrativeElementStore())
    if callback_database.elements:
        current_turn = len(state.get("ground_truth_log", []))
        # Active characters are all agents except DM
        active_characters = [name for name in state["turn_queue"] if name != "dm"]
        callback_context = format_callback_suggestions(
            callback_database, current_turn, active_characters
        )
        if callback_context:
            context_parts.append(callback_context)

    # Player nudge/suggestion (Story 3.4 - Nudge System)
    # Story 16.2: Read from state dict first, fall back to st.session_state
    pending_nudge = state.get("pending_nudge")
    if pending_nudge is None:
        try:
            import streamlit as st

            pending_nudge = st.session_state.get("pending_nudge")
        except (ImportError, AttributeError):
            pass
    if pending_nudge:
        # Sanitize nudge to prevent any injection issues
        sanitized_nudge = str(pending_nudge).strip()
        if sanitized_nudge:
            context_parts.append(
                f"## Player Suggestion\nThe player offers this thought: {sanitized_nudge}"
            )

    # Player whisper (Story 10.4 - Human Whisper to DM)
    # Story 16.2: Read from state dict first, fall back to st.session_state
    pending_whisper = state.get("pending_human_whisper")
    if pending_whisper is None:
        try:
            import streamlit as st

            pending_whisper = st.session_state.get("pending_human_whisper")
        except (ImportError, AttributeError):
            pass
    if pending_whisper:
        # Sanitize whisper to prevent any injection/format issues
        sanitized_whisper = str(pending_whisper).strip()
        # Escape quotes to prevent format breaking in LLM context
        sanitized_whisper = sanitized_whisper.replace('"', "'")
        if sanitized_whisper:
            context_parts.append(
                f'## Player Whisper\nThe human player privately asks: "{sanitized_whisper}"'
            )

    return "\n\n".join(context_parts)


def _build_pc_context(state: GameState, agent_name: str) -> str:
    """Build the context string for a PC agent.

    PC agents have memory isolation for private state (character facts,
    long-term summary, secrets) but see shared game events via the
    ground_truth_log - just like a player at the table hears the DM
    and sees other players' actions.

    Args:
        state: Current game state.
        agent_name: The name of the PC agent (lowercase).

    Returns:
        Formatted context string with shared scene + private memory.
    """
    context_parts: list[str] = []

    # Shared context: recent game events from ground_truth_log.
    # This is what everyone at the table sees - DM narration and PC actions.
    # Without this, PCs would be blind to the current scene.
    ground_truth_log = state.get("ground_truth_log", [])
    if ground_truth_log:
        recent_shared = ground_truth_log[-PC_SHARED_CONTEXT_LIMIT:]
        shared_events = "\n".join(recent_shared)
        context_parts.append(f"## Current Scene\n{shared_events}")

    # Private memory: PC agents only access their own AgentMemory
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

    # Add PC's own character sheet (Story 8.3 - FR62: PC sees only own sheet)
    # Find this PC's character sheet by matching character name
    character_sheets = state.get("character_sheets", {})
    character_config = state["characters"].get(agent_name)
    if character_config:
        # Look up sheet by character name (e.g., "Thorin" not "fighter")
        sheet = character_sheets.get(character_config.name)
        if sheet:
            context_parts.append(
                format_character_sheet_context(sheet, for_own_character=True)
            )

    # Add secret knowledge section (Story 10.3 - FR72: PC sees only own secrets)
    agent_secrets = state.get("agent_secrets", {})
    my_secrets = agent_secrets.get(agent_name)
    if my_secrets:
        secrets_context = format_pc_secrets_context(my_secrets)
        if secrets_context:
            context_parts.append(secrets_context)

    return "\n\n".join(context_parts)


# Maximum characters to include from the last DM narration in the turn prompt
_DM_EXCERPT_MAX_CHARS = 300


def _build_pc_turn_prompt(state: GameState, character_name: str) -> str:
    """Build a scene-aware turn prompt for a PC agent.

    Extracts the last DM narration from ground_truth_log and includes
    it in the prompt so the model has a direct reminder of what to
    respond to. This significantly helps smaller/local models stay
    on-topic instead of defaulting to combat actions.

    Args:
        state: Current game state.
        character_name: Display name of the PC (e.g. "Thorin").

    Returns:
        A turn prompt string that references the current scene.
    """
    ground_truth_log = state.get("ground_truth_log", [])

    # Find the last DM entry
    last_dm_line = ""
    for entry in reversed(ground_truth_log):
        if entry.startswith("[DM]:"):
            last_dm_line = entry[len("[DM]:") :].strip()
            break

    if not last_dm_line:
        return "It's your turn. What do you do?"

    # Truncate to a reasonable excerpt
    excerpt = last_dm_line
    if len(excerpt) > _DM_EXCERPT_MAX_CHARS:
        # Cut at last sentence boundary within limit
        truncated = excerpt[:_DM_EXCERPT_MAX_CHARS]
        last_period = truncated.rfind(".")
        last_question = truncated.rfind("?")
        last_quote = truncated.rfind('"')
        cut = max(last_period, last_question, last_quote)
        if cut > _DM_EXCERPT_MAX_CHARS // 2:
            excerpt = truncated[: cut + 1]
        else:
            excerpt = truncated + "..."

    # Collect what other PCs said this round (after the last DM entry)
    other_pc_actions: list[str] = []
    found_dm = False
    for entry in ground_truth_log:
        if (
            entry.startswith("[DM]:")
            and entry[len("[DM]:") :].strip() == last_dm_line[: len(entry) - 5]
        ):
            found_dm = True
            other_pc_actions.clear()
            continue
        if found_dm and not entry.startswith("[DM]:"):
            # Extract character name from "[Name]: action"
            bracket_end = entry.find("]:")
            if bracket_end > 1:
                name = entry[1:bracket_end]
                if name != character_name and name not in ("DM", "SHEET"):
                    other_pc_actions.append(name)

    parts = [f'The DM said: "{excerpt}"']
    if other_pc_actions:
        parts.append(f"{', '.join(other_pc_actions)} already responded.")
    parts.append(
        f"It's your turn, {character_name}. Respond to the scene above "
        "- what do you say or do?"
    )
    return "\n\n".join(parts)


# =============================================================================
# Combat Turn Helpers (Story 15.4)
# =============================================================================


def _get_combat_turn_type(
    state: GameState,
) -> Literal["non_combat", "bookend", "npc_turn"]:
    """Determine the type of DM turn based on combat state.

    Args:
        state: Current game state.

    Returns:
        "non_combat" if no active combat,
        "bookend" if DM round-start narration turn,
        "npc_turn" if DM is acting for a specific NPC.
    """
    combat = state.get("combat_state")
    if not combat or not isinstance(combat, CombatState) or not combat.active:
        return "non_combat"

    current = state.get("current_turn", "dm")
    if isinstance(current, str) and current.startswith("dm:"):
        return "npc_turn"
    return "bookend"


def _build_combatant_summary(state: GameState) -> str:
    """Build a brief combatant status summary for the DM bookend prompt.

    Lists all combatants from initiative_order with HP and conditions,
    skipping the bookend "dm" entry itself.

    Args:
        state: Current game state.

    Returns:
        Formatted string with one combatant per line.
    """
    combat = state.get("combat_state")
    if not combat:
        return ""

    lines: list[str] = []
    character_sheets = state.get("character_sheets", {})

    for entry in combat.initiative_order:
        if entry == "dm":
            continue  # Skip bookend entry itself
        if entry.startswith("dm:"):
            npc_key = entry.split(":", 1)[1]
            npc = combat.npc_profiles.get(npc_key)
            if npc:
                roll = combat.initiative_rolls.get(entry, "?")
                status = f"HP {npc.hp_current}/{npc.hp_max}"
                if npc.conditions:
                    status += f" [{', '.join(npc.conditions)}]"
                lines.append(f"- {npc.name} (Init {roll}): {status}")
            else:
                lines.append(f"- {npc_key} (Init ?): Unknown NPC")
        else:
            # PC entry
            sheet = character_sheets.get(entry)
            roll = combat.initiative_rolls.get(entry, "?")
            if sheet:
                status = f"HP {sheet.hit_points_current}/{sheet.hit_points_max}"
                if hasattr(sheet, "conditions") and sheet.conditions:
                    status += f" [{', '.join(sheet.conditions)}]"
                lines.append(f"- {sheet.name} (Init {roll}): {status}")
            else:
                lines.append(f"- {entry} (Init {roll})")

    return "\n".join(lines) if lines else "No combatants listed."


def _build_combat_bookend_prompt(state: GameState) -> str:
    """Build the combat bookend system prompt addendum.

    Creates a round-opening narration prompt with combatant summary
    for the DM to narrate the start of a combat round.

    Story 15.4: DM Bookend & NPC Turns (AC #1, #5, #8, #12).

    Args:
        state: Current game state.

    Returns:
        Formatted bookend prompt string.
    """
    combat = state.get("combat_state", CombatState())
    round_number = combat.round_number
    combatant_summary = _build_combatant_summary(state)

    return DM_COMBAT_BOOKEND_PROMPT_TEMPLATE.format(
        round_number=round_number,
        combatant_summary=combatant_summary,
    )


def _build_npc_turn_prompt(state: GameState, npc_key: str) -> str:
    """Build the NPC turn system prompt addendum.

    Creates an NPC-specific action prompt with profile data for the DM
    to narrate a specific NPC's combat turn.

    Story 15.4: DM Bookend & NPC Turns (AC #2, #3, #7).

    Args:
        state: Current game state.
        npc_key: The NPC's key in npc_profiles (e.g., "goblin_1").

    Returns:
        Formatted NPC turn prompt string.
    """
    combat = state.get("combat_state", CombatState())
    npc = combat.npc_profiles.get(npc_key)

    if npc is None:
        logger.warning(
            "NPC '%s' not found in npc_profiles. Available: %s",
            npc_key,
            ", ".join(sorted(combat.npc_profiles.keys())) if combat.npc_profiles else "none",
        )
        return f"It is now {npc_key}'s turn. Narrate their action."

    initiative_roll = combat.initiative_rolls.get(f"dm:{npc_key}", "?")

    conditions_line = ""
    if npc.conditions:
        conditions_line = f"- Conditions: {', '.join(npc.conditions)}"

    return DM_NPC_TURN_PROMPT_TEMPLATE.format(
        npc_name=npc.name,
        hp_current=npc.hp_current,
        hp_max=npc.hp_max,
        ac=npc.ac,
        initiative_roll=initiative_roll,
        personality=npc.personality or "None specified",
        tactics=npc.tactics or "None specified",
        conditions_line=conditions_line,
    )


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
    import sys
    import time as _time

    _t0 = _time.time()
    print(f"[{_time.strftime('%H:%M:%S')}] dm_turn: START", file=sys.stderr, flush=True)
    # Get DM config and create agent
    dm_config = state["dm_config"]

    # Clear nudge after reading (single-use) - Story 3.4
    # Story 16.2: Clear from state dict AND st.session_state
    state["pending_nudge"] = None  # type: ignore[literal-required]
    try:
        import streamlit as st

        st.session_state["pending_nudge"] = None
    except (ImportError, AttributeError, KeyError):
        pass

    # Clear human whisper after reading (single-use) - Story 10.4
    # Story 16.2: Clear from state dict AND st.session_state
    state["pending_human_whisper"] = None  # type: ignore[literal-required]
    try:
        import streamlit as st

        st.session_state["pending_human_whisper"] = None
    except (ImportError, AttributeError, KeyError):
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

        # Add combat-specific prompt addendum (Story 15.4)
        combat_turn_type = _get_combat_turn_type(state)
        if combat_turn_type == "bookend":
            system_prompt_parts.append(_build_combat_bookend_prompt(state))
        elif combat_turn_type == "npc_turn":
            npc_key = state["current_turn"].split(":", 1)[1]
            system_prompt_parts.append(_build_npc_turn_prompt(state, npc_key))

        full_system_prompt = "\n\n".join(system_prompt_parts)

        # Build messages for the model
        messages: list[BaseMessage] = [SystemMessage(content=full_system_prompt)]
        if context:
            messages.append(HumanMessage(content=f"Current game context:\n\n{context}"))

        # Story 15.4: Use turn-type-specific human message
        if combat_turn_type == "npc_turn":
            npc_key = state["current_turn"].split(":", 1)[1]
            combat_st = state.get("combat_state", CombatState())
            npc = combat_st.npc_profiles.get(npc_key)
            npc_name = npc.name if npc else npc_key
            messages.append(
                HumanMessage(
                    content=f"It is now {npc_name}'s turn in combat. Narrate their action."
                )
            )
        elif combat_turn_type == "bookend":
            combat_st = state.get("combat_state", CombatState())
            messages.append(
                HumanMessage(
                    content=f"Begin round {combat_st.round_number} of combat. Set the scene."
                )
            )
        else:
            messages.append(HumanMessage(content="Continue the adventure."))

        # Track any dice results for fallback response
        dice_results: list[str] = []

        # Track sheet update notifications for narrative display (Story 8.5)
        sheet_notifications: list[str] = []

        # Track character sheet updates from tool calls (Story 8.4)
        updated_sheets: dict[str, CharacterSheet] = dict(
            state.get("character_sheets", {})
        )

        # Track agent secrets updates from whisper tool calls (Story 10.2)
        updated_secrets: dict[str, AgentSecrets] = dict(state.get("agent_secrets", {}))

        # Track combat state updates from combat tool calls (Story 15.2)
        updated_combat_state: CombatState | None = None
        # Track restored turn queue from end combat (Story 15.6)
        restored_turn_queue: list[str] | None = None

        # Invoke the model with tool call handling loop
        max_tool_iterations = 5  # Increased for sheet updates alongside dice rolls
        import time as _time

        _context_chars = sum(len(m.content) for m in messages if hasattr(m, "content"))
        logger.info(
            "DM turn — invoking LLM (%s/%s), context ~%d chars",
            dm_config.provider,
            dm_config.model,
            _context_chars,
        )
        for _iter in range(max_tool_iterations):
            _call_start = _time.time()
            response = dm_agent.invoke(messages)
            logger.info(
                "DM LLM call returned in %.1fs (iteration %d)",
                _time.time() - _call_start,
                _iter + 1,
            )

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
                    tool_result = _execute_sheet_update(tool_args, updated_sheets)
                    logger.info(
                        "DM updated character sheet: %s -> %s",
                        tool_args,
                        tool_result,
                    )
                    # Collect successful update notifications (Story 8.5)
                    if not tool_result.startswith("Error"):
                        sheet_notifications.append(tool_result)

                # Execute the whisper tool (Story 10.2)
                elif tool_name == "dm_whisper_to_agent":
                    turn_number = len(state.get("ground_truth_log", []))
                    # Build set of valid agent keys for validation
                    valid_agents = set(state["turn_queue"])
                    tool_result = _execute_whisper(
                        tool_args, updated_secrets, turn_number, valid_agents
                    )
                    logger.info(
                        "DM whispered to agent: %s",
                        tool_args.get("character_name"),
                    )

                # Execute the reveal secret tool (Story 10.5)
                elif tool_name == "dm_reveal_secret":
                    turn_number = len(state.get("ground_truth_log", []))
                    tool_result, revealed_content = _execute_reveal(
                        tool_args, updated_secrets, turn_number
                    )
                    if revealed_content:
                        logger.info(
                            "DM revealed secret for: %s",
                            tool_args.get("character_name"),
                        )
                        # Store pending reveal for UI notification (Story 10.5)
                        try:
                            import streamlit as st

                            st.session_state["pending_secret_reveal"] = {
                                "character_name": str(
                                    tool_args.get("character_name", "")
                                ),
                                "content": revealed_content,
                                "turn": turn_number,
                            }
                        except Exception:
                            pass  # Not in Streamlit context (e.g., testing)

                # Execute the start combat tool (Story 15.2)
                elif tool_name == "dm_start_combat":
                    tool_result, new_combat_state = _execute_start_combat(
                        tool_args, state
                    )
                    if new_combat_state is not None:
                        updated_combat_state = new_combat_state
                    logger.info("DM started combat: %s", tool_result)

                # Execute the end combat tool (Story 15.2, 15.6)
                elif tool_name == "dm_end_combat":
                    tool_result, reset_combat_state, restored_queue = (
                        _execute_end_combat(state)
                    )
                    updated_combat_state = reset_combat_state
                    if restored_queue is not None:
                        restored_turn_queue = restored_queue
                    logger.info("DM ended combat: %s", tool_result)

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
    # Append sheet change notifications before DM narrative (Story 8.5)
    for notification in sheet_notifications:
        new_log.append(f"[SHEET]: {notification}")
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

    # Extract narrative elements from DM response (Story 11.1, 11.2, 11.4)
    turn_number = len(new_log)
    try:
        from memory import extract_narrative_elements

        extraction_result = extract_narrative_elements(
            state, response_content, turn_number
        )
        updated_narrative = extraction_result["narrative_elements"]
        updated_callback_db = extraction_result["callback_database"]
        updated_callback_log = extraction_result["callback_log"]
    except Exception as e:
        logger.warning("Narrative element extraction failed: %s", e)
        updated_narrative = state.get("narrative_elements", {})
        updated_callback_db = state.get("callback_database", NarrativeElementStore())
        updated_callback_log = state.get("callback_log", CallbackLog())

    # Story 15.4: Set current_turn dynamically for combat routing
    # Determine the final combat state (after any tool calls that started/ended combat)
    combat_state_for_return = (
        updated_combat_state
        if updated_combat_state is not None
        else state.get("combat_state", CombatState())
    )
    if combat_state_for_return.active:
        # Preserve "dm" for bookend or "dm:npc_name" for NPC turns
        return_current_turn = state["current_turn"]
    else:
        return_current_turn = "dm"

    # Story 15.6: Restore turn queue when combat ends
    turn_queue_for_return = (
        restored_turn_queue if restored_turn_queue is not None
        else state["turn_queue"]
    )

    # Return new state with current_turn set appropriately
    # This is critical for route_to_next_agent to know who just acted
    print(
        f"[{_time.strftime('%H:%M:%S')}] dm_turn: DONE ({_time.time() - _t0:.1f}s)",
        file=sys.stderr,
        flush=True,
    )
    return GameState(
        ground_truth_log=new_log,
        turn_queue=turn_queue_for_return,
        current_turn=return_current_turn,
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
        agent_secrets=updated_secrets,
        narrative_elements=updated_narrative,
        callback_database=updated_callback_db,
        callback_log=updated_callback_log,
        active_fork_id=state.get("active_fork_id"),
        combat_state=combat_state_for_return,
    )


def _execute_whisper(
    tool_args: dict[str, object],
    agent_secrets: dict[str, "AgentSecrets"],
    turn_number: int,
    valid_agents: set[str] | None = None,
) -> str:
    """Execute a whisper from DM to agent.

    Creates a new Whisper object and adds it to the target agent's secrets.

    Story 10.2: DM Whisper Tool.
    FR71: DM can send private information to individual agents.
    FR75: Whisper history is tracked per agent.

    Args:
        tool_args: Tool call arguments with character_name, secret_info, context.
        agent_secrets: Mutable dict of agent secrets (updated in place).
        turn_number: Current turn number for turn_created.
        valid_agents: Optional set of valid agent keys for validation.
            If provided, whispers to unknown agents will log a warning
            but still proceed (LLM may know character names we don't).

    Returns:
        Confirmation or error message string.
    """
    from models import AgentSecrets, create_whisper

    character_name = tool_args.get("character_name", "")
    secret_info = tool_args.get("secret_info", "")
    # context is optional and not stored in the whisper (informational for DM only)

    # Validate inputs
    if not character_name or not isinstance(character_name, str):
        return "Error: character_name is required and must be a string."
    if not secret_info or not isinstance(secret_info, str):
        return "Error: secret_info is required and must be a string."

    # Normalize character name to lowercase for agent key lookup
    agent_key = character_name.lower()

    # Warn if agent is not known (but still proceed - LLM may use character names)
    if valid_agents is not None and agent_key not in valid_agents:
        logger.warning(
            "Whisper sent to unknown agent '%s'. Known agents: %s",
            agent_key,
            ", ".join(sorted(valid_agents)),
        )

    # Create the whisper
    whisper = create_whisper(
        from_agent="dm",
        to_agent=agent_key,
        content=secret_info,
        turn_created=turn_number,
    )

    # Add to agent's secrets
    if agent_key not in agent_secrets:
        agent_secrets[agent_key] = AgentSecrets()

    # Create new whispers list with this whisper added
    current_secrets = agent_secrets[agent_key]
    new_whispers = current_secrets.whispers.copy()
    new_whispers.append(whisper)
    agent_secrets[agent_key] = current_secrets.model_copy(
        update={"whispers": new_whispers}
    )

    # Return confirmation with normalized agent key for consistency
    return f"Secret shared with {agent_key}"


def _execute_reveal(
    tool_args: dict[str, object],
    agent_secrets: dict[str, "AgentSecrets"],
    turn_number: int,
) -> tuple[str, str | None]:
    """Mark a whisper as revealed and return updated state.

    Finds a matching unrevealed whisper by ID or content hint and marks
    it as revealed. Updates the agent_secrets dict in place.

    Story 10.5: Secret Revelation System.
    FR74: Secrets can be revealed dramatically in narrative.

    Args:
        tool_args: Tool call arguments with character_name, whisper_id, content_hint.
        agent_secrets: Mutable dict of agent secrets (updated in place).
        turn_number: Current turn number for turn_revealed.

    Returns:
        Tuple of (result_message, revealed_content) where revealed_content is
        the whisper content if reveal succeeded (for UI notification), or None.
    """
    from models import AgentSecrets

    character_name = tool_args.get("character_name", "")
    whisper_id = tool_args.get("whisper_id", "")
    content_hint = tool_args.get("content_hint", "")

    # Validate inputs
    if not character_name or not isinstance(character_name, str):
        return "Error: character_name is required and must be a string.", None

    # Strip whitespace from identifiers
    if isinstance(whisper_id, str):
        whisper_id = whisper_id.strip()
    if isinstance(content_hint, str):
        content_hint = content_hint.strip()

    # Need at least one identifier (after stripping whitespace)
    if not whisper_id and not content_hint:
        return (
            "Error: Either whisper_id or content_hint is required to identify the secret.",
            None,
        )

    # Normalize character name to lowercase for agent key lookup
    agent_key = character_name.lower()

    # Check if agent has secrets
    if agent_key not in agent_secrets:
        return f"Error: No character named '{character_name}' has secrets.", None

    secrets = agent_secrets[agent_key]
    if not secrets.whispers:
        return f"Error: {character_name} has no whispers to reveal.", None

    # Find the matching whisper
    found_idx: int | None = None
    found_whisper = None

    for idx, whisper in enumerate(secrets.whispers):
        # Match by ID first if provided
        if whisper_id and isinstance(whisper_id, str) and whisper.id == whisper_id:
            found_idx = idx
            found_whisper = whisper
            break
        # Match by content hint (case-insensitive substring)
        if content_hint and isinstance(content_hint, str):
            if content_hint.lower() in whisper.content.lower():
                found_idx = idx
                found_whisper = whisper
                break

    if found_whisper is None:
        return f"Error: No matching secret found for {character_name}.", None

    # Check if already revealed
    if found_whisper.revealed:
        return (
            f"Error: That secret was already revealed on turn {found_whisper.turn_revealed}.",
            None,
        )

    # Create updated whisper with revealed=True
    updated_whisper = found_whisper.model_copy(
        update={
            "revealed": True,
            "turn_revealed": turn_number,
        }
    )

    # Build new whispers list with the updated whisper
    updated_whispers = secrets.whispers.copy()
    updated_whispers[found_idx] = updated_whisper  # type: ignore[index]

    # Update agent_secrets in place
    agent_secrets[agent_key] = AgentSecrets(whispers=updated_whispers)

    # Generate confirmation with content preview
    content_preview = found_whisper.content[:50]
    if len(found_whisper.content) > 50:
        content_preview += "..."

    return (
        f"SECRET REVEALED: {character_name.title()}'s secret about '{content_preview}' is now known to all.",
        found_whisper.content,
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

    if not character_name or not isinstance(character_name, str):
        return "Error: character_name is required and must be a string."

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


def _execute_start_combat(
    tool_args: dict[str, object],
    state: GameState,
) -> tuple[str, CombatState | None]:
    """Process dm_start_combat tool call.

    Parses NPC participant data, rolls initiative for all PCs and NPCs,
    builds a CombatState with initiative order and NPC profiles. When
    combat_mode is Narrative, returns a no-op placeholder.

    Story 15.2: Initiative Rolling & Turn Reordering.

    Args:
        tool_args: Tool call arguments with "participants" list of NPC dicts.
        state: Current game state for reading config, turn queue, and sheets.

    Returns:
        Tuple of (tool_result_string, new_combat_state_or_None).
        Returns None for combat_state when combat_mode is Narrative (no-op).
    """
    from tools import _sanitize_npc_name

    # Check combat mode gate
    game_config = state["game_config"]
    if game_config.combat_mode == "Narrative":
        return (
            f"Combat started with {len(tool_args.get('participants', []))} NPC(s). "
            "(Narrative mode -- initiative not rolled.)",
            None,
        )

    # Parse NPC participants
    participants = tool_args.get("participants", [])
    if not isinstance(participants, list):
        participants = []

    npc_profiles: dict[str, NpcProfile] = {}
    for p in participants:
        if not isinstance(p, dict):
            continue
        name = p.get("name", "Unknown")
        key = _sanitize_npc_name(str(name))
        hp = p.get("hp", 1)
        if not isinstance(hp, int) or hp < 1:
            hp = 1
        npc_profiles[key] = NpcProfile(
            name=str(name),
            initiative_modifier=int(p.get("initiative_modifier", 0)),
            hp_max=hp,
            hp_current=hp,
            ac=int(p.get("ac", 10)),
            personality=str(p.get("personality", "")),
            tactics=str(p.get("tactics", "")),
            secret=str(p.get("secret", "")),
        )

    # Get PC names from turn queue (all entries except "dm")
    pc_names = [name for name in state["turn_queue"] if name != "dm"]

    # Get character sheets for initiative modifiers
    character_sheets = dict(state.get("character_sheets", {}))

    # Roll initiative
    initiative_rolls, initiative_order = roll_initiative(
        pc_names, character_sheets, npc_profiles
    )

    # Save current turn queue and build combat state
    combat_state = CombatState(
        active=True,
        round_number=1,
        initiative_order=initiative_order,
        initiative_rolls=initiative_rolls,
        original_turn_queue=list(state["turn_queue"]),
        npc_profiles=npc_profiles,
    )

    # Format initiative order summary for DM feedback
    # Skip the "dm" bookend at index 0 for the summary
    order_parts: list[str] = []
    for entry in initiative_order[1:]:
        roll = initiative_rolls.get(entry, 0)
        # Use display name: for NPCs strip "dm:" prefix and title-case
        if entry.startswith("dm:"):
            display_name = entry[3:].replace("_", " ").title()
        else:
            display_name = entry.replace("_", " ").title()
        order_parts.append(f"{display_name} ({roll})")

    result_str = (
        f"Combat started! Initiative order: {', '.join(order_parts)}. Round 1 begins."
    )
    return result_str, combat_state


def _execute_end_combat(
    state: GameState,
) -> tuple[str, CombatState, list[str] | None]:
    """Process dm_end_combat tool call.

    Resets combat state to defaults and restores the original turn queue.

    Story 15.6: Combat End Conditions.

    Args:
        state: Current game state for reading combat_state.

    Returns:
        Tuple of (tool_result_string, reset_combat_state, restored_turn_queue).
        restored_turn_queue is None when combat was not active or
        original_turn_queue was empty.
    """
    combat_state = state.get("combat_state")
    if combat_state is None or not combat_state.active:
        return "No combat is currently active.", CombatState(), None

    # Restore turn queue from backup
    restored_queue: list[str] | None = None
    if combat_state.original_turn_queue:
        restored_queue = list(combat_state.original_turn_queue)
    else:
        logger.warning(
            "Combat ending but original_turn_queue is empty -- "
            "turn_queue will not be modified"
        )

    return (
        "Combat ended. Restoring exploration turn order.",
        CombatState(),
        restored_queue,
    )


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
    import sys
    import time as _time

    _t0 = _time.time()
    print(
        f"[{_time.strftime('%H:%M:%S')}] pc_turn: START [{agent_name}]",
        file=sys.stderr,
        flush=True,
    )
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

        # Build a scene-aware turn prompt that helps the model respond to
        # the current situation rather than defaulting to combat.
        turn_prompt = _build_pc_turn_prompt(state, character_config.name)
        messages.append(HumanMessage(content=turn_prompt))

        # Track any dice results for fallback response
        dice_results: list[str] = []

        # Invoke the model with tool call handling loop
        max_tool_iterations = 3  # Prevent infinite loops
        import time as _time

        _context_chars = sum(len(m.content) for m in messages if hasattr(m, "content"))
        logger.info(
            "PC turn [%s] — invoking LLM (%s/%s), context ~%d chars",
            agent_name,
            character_config.provider,
            character_config.model,
            _context_chars,
        )
        for _iter in range(max_tool_iterations):
            _call_start = _time.time()
            response = pc_agent.invoke(messages)
            logger.info(
                "PC [%s] LLM call returned in %.1fs (iteration %d)",
                agent_name,
                _time.time() - _call_start,
                _iter + 1,
            )

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

        # Auto-resolve any inline dice notation that the LLM wrote as text
        # instead of calling the pc_roll_dice tool (common with local LLMs).
        from tools import resolve_inline_dice_notation

        response_content = resolve_inline_dice_notation(response_content)

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

    # Extract narrative elements from PC response (Story 11.1, 11.2, 11.4)
    turn_number = len(new_log)
    try:
        from memory import extract_narrative_elements

        extraction_result = extract_narrative_elements(
            state, response_content, turn_number
        )
        updated_narrative = extraction_result["narrative_elements"]
        updated_callback_db = extraction_result["callback_database"]
        updated_callback_log = extraction_result["callback_log"]
    except Exception as e:
        logger.warning("Narrative element extraction failed: %s", e)
        updated_narrative = state.get("narrative_elements", {})
        updated_callback_db = state.get("callback_database", NarrativeElementStore())
        updated_callback_log = state.get("callback_log", CallbackLog())

    # Return new state with current_turn updated to this agent's name
    # This is critical for route_to_next_agent to know who just acted
    print(
        f"[{_time.strftime('%H:%M:%S')}] pc_turn: DONE [{agent_name}] ({_time.time() - _t0:.1f}s)",
        file=sys.stderr,
        flush=True,
    )
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
        agent_secrets=state.get("agent_secrets", {}),
        narrative_elements=updated_narrative,
        callback_database=updated_callback_db,
        callback_log=updated_callback_log,
        active_fork_id=state.get("active_fork_id"),
        combat_state=state.get("combat_state", CombatState()),
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
