"""Agent definitions and LLM factory.

This module provides the factory function for creating LLM clients
for different providers (Gemini, Claude, Ollama), as well as agent
node functions for the LangGraph state machine.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from config import get_config
from models import AgentMemory, CharacterConfig, DMConfig, GameState
from tools import dm_roll_dice, pc_roll_dice

__all__ = [
    "CLASS_GUIDANCE",
    "DEFAULT_MODELS",
    "DM_CONTEXT_PLAYER_ENTRIES_LIMIT",
    "DM_CONTEXT_RECENT_EVENTS_LIMIT",
    "DM_SYSTEM_PROMPT",
    "LLMConfigurationError",
    "PC_CONTEXT_RECENT_EVENTS_LIMIT",
    "PC_SYSTEM_PROMPT_TEMPLATE",
    "SUPPORTED_PROVIDERS",
    "_build_dm_context",
    "_build_pc_context",
    "build_pc_system_prompt",
    "create_dm_agent",
    "create_pc_agent",
    "dm_turn",
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

Use the dice rolling tool when:
- A player attempts something with uncertain outcome (skill checks)
- Combat attacks or damage need to be resolved
- Saving throws against effects are required
- Random outcomes enhance the story

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

## Class Behavior

{class_guidance}

## Actions and Dialogue

When responding:
- Describe your character's actions in first person: "I draw my sword and..."
- Use direct dialogue with quotation marks: "Stay back!" I warn them.
- Express your character's emotions and internal thoughts
- React authentically to what's happening around you

## Dice Rolling

Use the dice rolling tool when:
- You attempt something with uncertain outcome
- You want to make a skill check (Perception, Stealth, etc.)
- The DM hasn't already rolled for you

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


def get_llm(provider: str, model: str) -> BaseChatModel:
    """Create an LLM client for the specified provider and model.

    Factory function that returns the appropriate LangChain chat model
    based on the provider string. Provider names are case-insensitive.

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
            if not config.google_api_key:
                raise LLMConfigurationError("gemini", "GOOGLE_API_KEY")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=config.google_api_key,
            )
        case "claude":
            if not config.anthropic_api_key:
                raise LLMConfigurationError("claude", "ANTHROPIC_API_KEY")
            # type: ignore needed - langchain-anthropic type stubs are incomplete
            return ChatAnthropic(  # type: ignore[call-arg]
                model_name=model,
                api_key=config.anthropic_api_key,
            )
        case "ollama":
            return ChatOllama(
                model=model,
                base_url=config.ollama_base_url,
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
    return base_model.bind_tools([dm_roll_dice])


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
        # Add long-term summary if available
        if pc_memory.long_term_summary:
            context_parts.append(f"## What You Remember\n{pc_memory.long_term_summary}")

        # Add recent events from short-term buffer
        if pc_memory.short_term_buffer:
            recent = "\n".join(
                pc_memory.short_term_buffer[-PC_CONTEXT_RECENT_EVENTS_LIMIT:]
            )
            context_parts.append(f"## Recent Events\n{recent}")

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
    """
    # Get DM config and create agent
    dm_config = state["dm_config"]
    dm_agent = create_dm_agent(dm_config)

    # Build context from all agent memories
    context = _build_dm_context(state)

    # Build messages for the model
    messages: list[BaseMessage] = [SystemMessage(content=DM_SYSTEM_PROMPT)]
    if context:
        messages.append(HumanMessage(content=f"Current game context:\n\n{context}"))
    messages.append(HumanMessage(content="Continue the adventure."))

    # Invoke the model
    response = dm_agent.invoke(messages)

    # Extract content from response (type ignore for langchain stubs)
    content = response.content  # type: ignore[union-attr]
    response_content: str = content if isinstance(content, str) else str(content)  # type: ignore[arg-type]

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
    """
    # Get character config from state
    character_config = state["characters"][agent_name]

    # Create agent with tools bound
    pc_agent = create_pc_agent(character_config)

    # Build system prompt personalized for this character
    system_prompt = build_pc_system_prompt(character_config)

    # Build context from PC's own memory only (strict isolation)
    context = _build_pc_context(state, agent_name)

    # Build messages for the model
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
    if context:
        messages.append(HumanMessage(content=f"Your current knowledge:\n\n{context}"))
    messages.append(HumanMessage(content="It's your turn. What do you do?"))

    # Invoke the model
    response = pc_agent.invoke(messages)

    # Extract content from response (type ignore for langchain stubs)
    content = response.content  # type: ignore[union-attr]
    response_content: str = content if isinstance(content, str) else str(content)  # type: ignore[arg-type]

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
    )
