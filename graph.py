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
    """Placeholder for human input handling.

    In Epic 3, this will:
    1. Pause the graph execution
    2. Wait for Streamlit user input
    3. Return state with human's response added

    For now, just return state unchanged.

    Args:
        state: Current game state.

    Returns:
        Unchanged game state (placeholder behavior).
    """
    # TODO: Implement in Story 3.2 (Drop-In Mode)
    return state


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
                agent_name, lambda s, name=agent_name: pc_turn(s, name)  # type: ignore[misc, arg-type]
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
    completing one full cycle of the turn queue.

    Note: This function creates a new workflow each time. For repeated
    execution, consider caching the compiled workflow.

    Args:
        state: Initial game state for this round.

    Returns:
        Updated state after all agents have acted once.
    """
    workflow = create_game_workflow(state["turn_queue"])

    # Run the workflow with recursion limit to prevent infinite loops
    # The limit is set to turn_queue length + 1 to allow one full round
    result = workflow.invoke(
        state,
        config={"recursion_limit": len(state["turn_queue"]) + 2},
    )
    return result  # type: ignore[return-value]
