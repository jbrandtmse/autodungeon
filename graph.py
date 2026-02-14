"""LangGraph state machine for game orchestration.

This module implements the turn-based game loop using LangGraph:
- Supervisor pattern with DM routing to PC nodes
- Conditional edges for turn-based progression
- Human intervention support (placeholder for Epic 3)
- Error handling and recovery (Story 4.5)
- Context management and memory compression (Story 5.2)

The game flow per invocation is:
  context_manager -> DM -> PC1 -> PC2 -> ... -> PCn -> END

Each workflow.invoke() executes ONE complete round. Call invoke() again
for subsequent rounds.
"""

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents import LLMError, dm_turn, pc_turn
from memory import MemoryManager
from models import CombatState, GameConfig, GameState, create_user_error

logger = logging.getLogger("autodungeon")

__all__ = [
    "GameStateWithError",
    "MAX_COMPRESSION_PASSES",
    "context_manager",
    "create_game_workflow",
    "human_intervention_node",
    "route_to_next_agent",
    "run_single_round",
]

# Maximum compression passes to prevent infinite loops (Story 5.5)
# After buffer compression, if total context still exceeds limit,
# the system will re-compress long_term_summary up to this many times.
MAX_COMPRESSION_PASSES = 2


# Type alias for GameState that may include an error field
# This allows run_single_round to return error information without corrupting game state
GameStateWithError = dict[str, object]  # GameState fields + optional "error" key


def context_manager(state: GameState) -> GameState:
    """Manage agent memory context before DM turn.

    Runs before the DM turn each round to check and compress memory
    buffers that are approaching their token limits. This ensures
    agents maintain relevant context without exceeding limits.

    Per architecture: compression runs synchronously (blocking) to
    ensure memory is compressed before the DM acts.

    Story 5.5 additions (FR16, AC #5):
    - Post-compression validation ensures total context fits within limit
    - Multi-pass compression: if still over limit, re-compress long_term_summary
    - MAX_COMPRESSION_PASSES limits compression attempts to prevent infinite loops

    Args:
        state: Current game state with agent_memories.

    Returns:
        Updated game state with compressed memories if needed.
        Sets summarization_in_progress flag during operation.
    """
    # Create a typed copy to avoid mutating original state
    updated_state: GameState = {
        **state,
        "summarization_in_progress": True,
    }

    # Get memory manager for this state
    memory_manager = MemoryManager(updated_state)

    # Check each agent's memory and compress if near limit
    agent_memories = updated_state["agent_memories"]
    for agent_name in agent_memories:
        passes = 0

        # Debug: log buffer sizes for all agents each round
        mem = agent_memories[agent_name]
        buf_chars = sum(len(s) for s in mem.short_term_buffer)
        buf_entries = len(mem.short_term_buffer)
        buf_tokens = memory_manager.get_buffer_token_count(agent_name)
        near_limit = memory_manager.is_near_limit(agent_name)
        if near_limit or buf_entries > 15:
            logger.info(
                "Memory check: %s — buffer=%d entries (%d chars, ~%d tokens), "
                "summary=%d chars, near_limit=%s",
                agent_name,
                buf_entries,
                buf_chars,
                buf_tokens,
                len(mem.long_term_summary),
                near_limit,
            )

        # Pass 1: Compress buffer if near limit
        if near_limit:
            logger.info(
                "Triggering compression for %s (buffer ~%d tokens, limit %d)",
                agent_name,
                buf_tokens,
                mem.token_limit,
            )
            memory_manager.compress_buffer(agent_name)
            passes += 1

            # Post-compression validation (Story 5.5, AC #5)
            # Pass 2: If still over limit, re-compress summary
            while (
                passes < MAX_COMPRESSION_PASSES
                and memory_manager.is_total_context_over_limit(agent_name)
            ):
                memory_manager.compress_long_term_summary(agent_name)
                passes += 1

            # Log warning if still over limit after max passes
            if memory_manager.is_total_context_over_limit(agent_name):
                logger.warning(
                    "Agent %s still over token limit after %d compression passes",
                    agent_name,
                    passes,
                )

    # Clear the summarization flag after completion
    updated_state["summarization_in_progress"] = False

    # Combat round tracking (Story 15-3)
    # Increment round_number at the start of each new round after the initial one.
    # _execute_start_combat() sets round_number=1 when combat begins mid-round.
    # Subsequent rounds (2, 3, ...) are incremented here.
    combat = updated_state.get("combat_state")
    if combat and isinstance(combat, CombatState) and combat.active and combat.round_number >= 1:
        updated_state["combat_state"] = combat.model_copy(
            update={"round_number": combat.round_number + 1}
        )

        # Story 15.6: Max round limit safety valve
        max_rounds = updated_state.get("game_config", GameConfig()).max_combat_rounds
        new_round = combat.round_number + 1
        if max_rounds > 0 and new_round > max_rounds:
            logger.warning(
                "Combat force-ended: round %d exceeded max_combat_rounds=%d",
                new_round,
                max_rounds,
            )
            # Restore turn queue from backup
            if combat.original_turn_queue:
                updated_state["turn_queue"] = list(combat.original_turn_queue)
            # Reset combat state
            updated_state["combat_state"] = CombatState()
            # Append system notification to ground truth log
            updated_state["ground_truth_log"] = [
                *updated_state["ground_truth_log"],
                "[System]: Combat ended after reaching the maximum round limit.",
            ]

    return updated_state


def route_to_next_agent(state: GameState) -> str:
    """Route to the next agent based on turn_queue or initiative_order.

    Implements the supervisor routing pattern:
    - DM routes to first PC
    - Each PC routes to next PC
    - Last PC signals END (completing one round)
    - Human override routes to human node when human_active=True

    When combat_state.active is True (Story 15-3), uses
    combat_state.initiative_order instead of turn_queue. NPC entries
    (e.g., "dm:goblin_1") are routed to the "dm" node.

    The graph executes ONE complete round per invocation:
    DM -> PC1 -> PC2 -> ... -> PCn -> END

    To run continuously, invoke the graph multiple times.

    Args:
        state: Current game state with turn_queue and current_turn.

    Returns:
        Name of the next agent node to execute, "human" for human intervention,
        or END to signal round completion.
    """
    current = state["current_turn"]

    # Determine which order list to use (Story 15-3: combat-aware routing)
    combat = state.get("combat_state")
    if (
        combat
        and isinstance(combat, CombatState)
        and combat.active
        and combat.initiative_order
    ):
        order = combat.initiative_order
    else:
        order = state["turn_queue"]

    # Handle human override - only when it's the controlled character's turn
    if state["human_active"] and state["controlled_character"]:
        # Only route to human if current turn is the controlled character
        if current != "dm" and current == state["controlled_character"]:
            return "human"

    # Find current position in order
    try:
        current_idx = order.index(current)
    except ValueError:
        # If current agent not in order, default to DM
        return "dm"

    # Check if this is the last agent in the order (end of round)
    if current_idx == len(order) - 1:
        # Round complete - signal END
        return END  # type: ignore[return-value]

    # Get next agent in order
    next_agent = order[current_idx + 1]

    # Route NPC turns to DM node (Story 15-3)
    if next_agent.startswith("dm:"):
        return "dm"

    return next_agent


def human_intervention_node(state: GameState) -> GameState:
    """Process human input and add to game log.

    Reads the pending human action from the GameState dict first,
    falling back to Streamlit session state for backward compatibility.
    Formats it as a log entry with character attribution, and adds
    to ground_truth_log. Also updates the character's agent memory
    for consistency with PC turn behavior.

    Includes auto-checkpoint save after human action is processed (FR33)
    and transcript logging (FR39, Story 4.4).

    Args:
        state: Current game state.

    Returns:
        Updated game state with human action added to log and memory.
    """
    from datetime import UTC, datetime

    from models import AgentMemory, TranscriptEntry
    from persistence import (
        append_transcript_entry,
        save_checkpoint,
        save_fork_checkpoint,
    )

    # Get pending action from state dict first, fall back to st.session_state
    pending_action = state.get("human_pending_action")
    if pending_action is None:
        try:
            import streamlit as st

            pending_action = st.session_state.get("human_pending_action")
        except (ImportError, AttributeError):
            pass

    if not pending_action:
        # No action submitted yet - return state unchanged
        return state

    # Get controlled character
    controlled = state.get("controlled_character")
    if not controlled:
        return state

    # Format log entry like PC messages: "[agent_key]: content"
    log_entry = f"[{controlled}]: {pending_action}"

    # Add to ground truth log
    new_log = list(state.get("ground_truth_log", []))
    new_log.append(log_entry)

    # Update character's agent memory (matches PC turn behavior)
    agent_memories = state.get("agent_memories", {})
    new_memories = {k: v.model_copy() for k, v in agent_memories.items()}

    # Get character name for memory entry
    char_config = state.get("characters", {}).get(controlled)
    char_name = char_config.name if char_config else controlled.title()

    # Create memory if it doesn't exist
    if controlled not in new_memories:
        new_memories[controlled] = AgentMemory()

    # Add action to character's short-term buffer (like pc_turn does)
    memory_entry = f"{char_name}: {pending_action}"
    new_memories[controlled].short_term_buffer.append(memory_entry)

    # Build updated state (includes combat_state passthrough for Story 15-3)
    # Clear the pending action in state dict
    updated_state: GameState = {
        **state,
        "ground_truth_log": new_log,
        "agent_memories": new_memories,
        "combat_state": state.get("combat_state", CombatState()),
        "human_pending_action": None,
    }

    # Also clear from st.session_state for backward compatibility
    try:
        import streamlit as st

        st.session_state["human_pending_action"] = None
    except (ImportError, AttributeError, KeyError):
        pass

    # Get session_id and turn_number for persistence
    session_id = updated_state.get("session_id", "001")
    turn_number = len(new_log)

    # Append transcript entry for human action (FR39, Story 4.4)
    if turn_number > 0:
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        transcript_entry = TranscriptEntry(
            turn=turn_number,
            timestamp=timestamp,
            agent=controlled,
            content=pending_action,
            tool_calls=None,
        )
        try:
            append_transcript_entry(session_id, transcript_entry)
        except OSError:
            # Log error but don't fail (graceful degradation)
            pass

        # Auto-checkpoint: save after human action (FR33)
        # Fork-aware save routing (Story 12.2)
        active_fork_id = updated_state.get("active_fork_id")
        if active_fork_id is not None:
            save_fork_checkpoint(
                updated_state, session_id, active_fork_id, turn_number
            )
        else:
            save_checkpoint(updated_state, session_id, turn_number)

    return updated_state


def create_game_workflow(  # type: ignore[return-value]
    turn_queue: list[str] | None = None,
) -> CompiledStateGraph:  # type: ignore[type-arg]
    """Create a compiled game workflow.

    Factory function that builds the LangGraph state machine with:
    - DM node as supervisor
    - PC nodes for each character in turn_queue
    - Human intervention node for Epic 3 integration
    - Conditional edges implementing turn-based routing

    Args:
        turn_queue: List of agent names in turn order.
                    First should be "dm", rest are PC names.
                    If None, uses default ["dm"].

    Returns:
        Compiled LangGraph state machine ready for execution.
    """
    if turn_queue is None:
        turn_queue = ["dm"]

    workflow = StateGraph(GameState)

    # Add context_manager node (Story 5.2)
    # Runs before DM to check and compress memory buffers
    workflow.add_node("context_manager", context_manager)

    # Add DM node
    workflow.add_node("dm", dm_turn)

    # Add PC nodes dynamically based on turn_queue
    # Use default argument capture to avoid late binding issues with lambdas
    for agent_name in turn_queue:
        if agent_name != "dm":
            # type: ignore needed due to langgraph's complex generic typing
            workflow.add_node(
                agent_name,
                lambda s, name=agent_name: pc_turn(s, name),  # type: ignore[misc, arg-type]
            )

    # Add human intervention node (placeholder for Epic 3)
    workflow.add_node("human", human_intervention_node)

    # Add entry edges: START -> context_manager -> DM
    workflow.add_edge(START, "context_manager")
    workflow.add_edge("context_manager", "dm")

    # Build routing map for conditional edges
    # Maps return values of route_to_next_agent to node names
    routing_map: dict[str, str] = {name: name for name in turn_queue}
    routing_map["human"] = "human"
    routing_map[END] = END  # type: ignore[index]

    # Add conditional edges from each node to enable turn cycling
    # type: ignore needed due to langgraph's dict typing requirements
    for agent_name in turn_queue:
        workflow.add_conditional_edges(
            agent_name,
            route_to_next_agent,
            routing_map,  # type: ignore[arg-type]
        )

    # Human intervention node routes back based on turn queue
    workflow.add_conditional_edges(
        "human",
        route_to_next_agent,
        routing_map,  # type: ignore[arg-type]
    )

    return workflow.compile()


def _append_transcript_for_new_entries(
    state: GameState, result: GameState, session_id: str
) -> None:
    """Append transcript entries for new log entries added during round.

    Compares state before and after round execution to identify new entries,
    then appends a TranscriptEntry for each. Tool calls are not captured
    at this level (would require agent-level integration).

    Args:
        state: GameState before round execution.
        result: GameState after round execution.
        session_id: Session ID for transcript file.
    """
    from datetime import UTC, datetime

    from models import TranscriptEntry
    from persistence import append_transcript_entry

    old_log = state.get("ground_truth_log", [])
    new_log = result.get("ground_truth_log", [])

    # Find new entries added during this round
    old_count = len(old_log)
    new_entries = new_log[old_count:]

    for i, entry in enumerate(new_entries):
        turn_number = old_count + i + 1  # 1-indexed

        # Parse agent from log entry format "[agent]: content"
        agent = "dm"  # default
        content = entry

        if entry.startswith("["):
            bracket_end = entry.find("]")
            if bracket_end > 0:
                agent = entry[1:bracket_end]
                # Content is everything after "]: " or just after "]"
                rest = entry[bracket_end + 1 :]
                content = rest.lstrip(": ").strip()

        # Generate ISO timestamp
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        # Create and append transcript entry
        transcript_entry = TranscriptEntry(
            turn=turn_number,
            timestamp=timestamp,
            agent=agent,
            content=content,
            tool_calls=None,  # Tool calls not captured at graph level
        )

        try:
            append_transcript_entry(session_id, transcript_entry)
        except OSError:
            # Log error but don't fail game execution (graceful degradation)
            pass


def run_single_round(state: GameState) -> GameStateWithError:
    """Execute one complete round (DM + all PCs).

    Convenience function that runs the workflow until the DM's next turn,
    completing one full cycle of the turn queue. Now includes auto-checkpoint
    save after round completion (FR33, NFR11), transcript logging (FR39),
    and error handling (Story 4.5).

    If an LLM error occurs during the round:
    - The game state is NOT corrupted (original state preserved)
    - A UserError is created and included in the returned dict under "error" key
    - The last successful checkpoint turn number is included for recovery

    Note: This function creates a new workflow each time. For repeated
    execution, consider caching the compiled workflow.

    Args:
        state: Initial game state for this round.

    Returns:
        Updated state after all agents have acted once. If an error occurred,
        the dict will include an "error" key with a UserError instance.
        The original state fields are preserved in case of error for recovery.
    """
    from persistence import get_latest_checkpoint, save_checkpoint, save_fork_checkpoint

    # Determine last successful checkpoint for error recovery
    session_id = state.get("session_id", "001")
    last_checkpoint_turn = get_latest_checkpoint(session_id)

    import sys
    import time as _time

    _round_start = _time.time()
    log = state.get("ground_truth_log", [])
    print(
        f"[{_time.strftime('%H:%M:%S')}] run_single_round: START — "
        f"turn {len(log)}, queue={state.get('turn_queue', [])}",
        file=sys.stderr,
        flush=True,
    )

    workflow = create_game_workflow(state["turn_queue"])

    # Compute recursion limit: use the longer of turn_queue or initiative_order (Story 15-3)
    combat = state.get("combat_state")
    if combat and isinstance(combat, CombatState) and combat.active and combat.initiative_order:
        turn_count = max(len(state["turn_queue"]), len(combat.initiative_order))
    else:
        turn_count = len(state["turn_queue"])
    recursion_limit = turn_count + 2

    try:
        # Run the workflow with recursion limit to prevent infinite loops
        # The limit is set to turn count + 2 to allow one full round
        result: GameState = workflow.invoke(
            state,
            config={"recursion_limit": recursion_limit},
        )  # type: ignore[assignment]
        print(
            f"[{_time.strftime('%H:%M:%S')}] run_single_round: COMPLETE — "
            f"elapsed {_time.time() - _round_start:.1f}s",
            file=sys.stderr,
            flush=True,
        )

    except LLMError as e:
        # Create user-friendly error without corrupting game state (Story 4.5)
        detail = str(e)
        if e.original_error:
            detail += f"\nOriginal error: {e.original_error}"
        user_error = create_user_error(
            error_type=e.error_type,
            provider=e.provider,
            agent=e.agent,
            retry_count=0,
            last_checkpoint_turn=last_checkpoint_turn,
            detail_message=detail,
        )

        # Return original state with error attached
        # This ensures game state is not corrupted by partial turn (Task 3.4)
        error_result: GameStateWithError = dict(state)
        error_result["error"] = user_error
        return error_result

    except Exception as e:
        # Handle unexpected errors gracefully
        from agents import categorize_error

        error_type = categorize_error(e)
        user_error = create_user_error(
            error_type=error_type,
            provider="unknown",
            agent="unknown",
            retry_count=0,
            last_checkpoint_turn=last_checkpoint_turn,
            detail_message=str(e),
        )

        error_result = dict(state)
        error_result["error"] = user_error
        return error_result

    # Get session_id for persistence operations
    session_id = result.get("session_id", "001")
    turn_number = len(result["ground_truth_log"])

    # Append transcript entries for new log entries (FR39, Story 4.4)
    _append_transcript_for_new_entries(state, result, session_id)

    # Auto-checkpoint: save after each round (FR33, NFR11)
    if turn_number > 0:  # Only save if there's content
        active_fork_id = result.get("active_fork_id")
        if active_fork_id is not None:
            # Fork-aware save: route to fork directory (Story 12.2)
            save_fork_checkpoint(result, session_id, active_fork_id, turn_number)
        else:
            # Main timeline save
            save_checkpoint(result, session_id, turn_number)

    # Return result without error key
    return dict(result)
