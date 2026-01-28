"""LangGraph state machine for game orchestration.

This module implements the turn-based game loop using LangGraph:
- Supervisor pattern with DM routing to PC nodes
- Conditional edges for turn-based progression
- Human intervention support (placeholder for Epic 3)

The game flow per invocation is: DM -> PC1 -> PC2 -> ... -> PCn -> END
Each workflow.invoke() executes ONE complete round. Call invoke() again
for subsequent rounds.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents import dm_turn, pc_turn
from models import GameState

__all__ = [
    "create_game_workflow",
    "human_intervention_node",
    "route_to_next_agent",
    "run_single_round",
]


def route_to_next_agent(state: GameState) -> str:
    """Route to the next agent based on turn_queue position.

    Implements the supervisor routing pattern:
    - DM routes to first PC
    - Each PC routes to next PC
    - Last PC signals END (completing one round)
    - Human override routes to human node when human_active=True

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
    turn_queue = state["turn_queue"]

    # Handle human override - only when it's the controlled character's turn
    if state["human_active"] and state["controlled_character"]:
        # Only route to human if current turn is the controlled character
        if current != "dm" and current == state["controlled_character"]:
            return "human"

    # Find current position in queue
    try:
        current_idx = turn_queue.index(current)
    except ValueError:
        # If current agent not in queue, default to DM
        return "dm"

    # Check if this is the last agent in the turn queue (end of round)
    if current_idx == len(turn_queue) - 1:
        # Round complete - signal END
        return END  # type: ignore[return-value]

    # Route to next agent in queue
    next_idx = current_idx + 1
    return turn_queue[next_idx]


def human_intervention_node(state: GameState) -> GameState:
    """Process human input and add to game log.

    Reads the pending human action from Streamlit session state,
    formats it as a log entry with character attribution, and adds
    to ground_truth_log. Also updates the character's agent memory
    for consistency with PC turn behavior.

    Includes auto-checkpoint save after human action is processed (FR33).

    Args:
        state: Current game state.

    Returns:
        Updated game state with human action added to log and memory.
    """
    import streamlit as st

    from models import AgentMemory
    from persistence import save_checkpoint

    # Get pending action from session state
    pending_action = st.session_state.get("human_pending_action")

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

    # Clear the pending action from session state
    st.session_state["human_pending_action"] = None

    # Build updated state
    updated_state: GameState = {
        **state,
        "ground_truth_log": new_log,
        "agent_memories": new_memories,
    }

    # Auto-checkpoint: save after human action (FR33)
    session_id = updated_state.get("session_id", "001")
    turn_number = len(new_log)
    if turn_number > 0:
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

    # Add entry edge from START to DM
    workflow.add_edge(START, "dm")

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


def run_single_round(state: GameState) -> GameState:
    """Execute one complete round (DM + all PCs).

    Convenience function that runs the workflow until the DM's next turn,
    completing one full cycle of the turn queue. Now includes auto-checkpoint
    save after round completion (FR33, NFR11).

    Note: This function creates a new workflow each time. For repeated
    execution, consider caching the compiled workflow.

    Args:
        state: Initial game state for this round.

    Returns:
        Updated state after all agents have acted once.
    """
    from persistence import save_checkpoint

    workflow = create_game_workflow(state["turn_queue"])

    # Run the workflow with recursion limit to prevent infinite loops
    # The limit is set to turn_queue length + 1 to allow one full round
    result: GameState = workflow.invoke(
        state,
        config={"recursion_limit": len(state["turn_queue"]) + 2},
    )  # type: ignore[assignment]

    # Auto-checkpoint: save after each round (FR33, NFR11)
    session_id = result.get("session_id", "001")
    turn_number = len(result["ground_truth_log"])
    if turn_number > 0:  # Only save if there's content
        save_checkpoint(result, session_id, turn_number)

    return result
