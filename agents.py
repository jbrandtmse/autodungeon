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
from models import AgentMemory, DMConfig, GameState
from tools import dm_roll_dice

__all__ = [
    "DEFAULT_MODELS",
    "DM_CONTEXT_PLAYER_ENTRIES_LIMIT",
    "DM_CONTEXT_RECENT_EVENTS_LIMIT",
    "DM_SYSTEM_PROMPT",
    "LLMConfigurationError",
    "SUPPORTED_PROVIDERS",
    "_build_dm_context",
    "create_dm_agent",
    "dm_turn",
    "get_default_model",
    "get_llm",
]

# Context building limits for DM
DM_CONTEXT_RECENT_EVENTS_LIMIT = 10  # Max recent events from DM's buffer
DM_CONTEXT_PLAYER_ENTRIES_LIMIT = 3  # Max entries per PC agent's buffer

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

    # Return new state
    return GameState(
        ground_truth_log=new_log,
        turn_queue=state["turn_queue"],
        current_turn=state["current_turn"],
        agent_memories=new_memories,
        game_config=state["game_config"],
        dm_config=state["dm_config"],
        whisper_queue=state["whisper_queue"],
        human_active=state["human_active"],
        controlled_character=state["controlled_character"],
    )
