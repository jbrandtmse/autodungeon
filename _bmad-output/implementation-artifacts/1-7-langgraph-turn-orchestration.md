# Story 1.7: LangGraph Turn Orchestration

Status: done

## Story

As a **user**,
I want **a game loop that orchestrates turns between the DM and PC agents**,
so that **the narrative flows naturally with proper turn order**.

## Acceptance Criteria

1. **Given** a configured GameState with DM and 4 PC agents
   **When** I start a game session
   **Then** the LangGraph state machine initializes with all agents in the turn queue

2. **Given** the game is running
   **When** the DM completes their turn
   **Then** the supervisor pattern routes to the next PC in the turn queue

3. **Given** all PCs have taken their turns
   **When** the round completes
   **Then** control returns to the DM for the next narrative beat

4. **Given** the graph.py module
   **When** I examine the workflow definition
   **Then** it uses conditional edges with a `route_to_next_agent` function
   **And** the DM node acts as supervisor routing to PC nodes

5. **Given** the ground_truth_log in GameState
   **When** any agent generates a response
   **Then** the response is appended to the log with agent attribution

## Tasks / Subtasks

- [x] Task 1: Create game workflow state machine (AC: #1, #4)
  - [x] 1.1 Import StateGraph and START, END from langgraph.graph in graph.py
  - [x] 1.2 Create `create_game_workflow()` function returning a compiled StateGraph
  - [x] 1.3 Add "dm" node using `dm_turn` function
  - [x] 1.4 Add PC nodes dynamically based on turn_queue (excluding "dm")
  - [x] 1.5 Set START entry point to "dm" node
  - [x] 1.6 Export function in `__all__`

- [x] Task 2: Implement `route_to_next_agent` router (AC: #2, #3, #4)
  - [x] 2.1 Create `route_to_next_agent(state: GameState) -> str` function
  - [x] 2.2 Find current agent's position in turn_queue
  - [x] 2.3 If current is DM and turn_queue has PCs, route to first PC
  - [x] 2.4 If current is PC and not last, route to next PC
  - [x] 2.5 If current is last PC, route to END (round complete - invoke again for next round)
  - [x] 2.6 Handle human_active flag to route to "human" node if controlled_character matches
  - [x] 2.7 Export in `__all__`

- [x] Task 3: Add conditional edges (AC: #2, #3, #4)
  - [x] 3.1 Add conditional edge from "dm" node using route_to_next_agent
  - [x] 3.2 Add conditional edge from each PC node using route_to_next_agent
  - [x] 3.3 Create routing dict mapping agent names to node names
  - [x] 3.4 Include END as possible routing target when graph should terminate

- [x] Task 4: Create PC node wrapper functions (AC: #1, #2)
  - [x] 4.1 Create partial functions or lambdas wrapping `pc_turn(state, agent_name)`
  - [x] 4.2 Each PC gets a dedicated node: `{agent_name}_node`
  - [x] 4.3 Node IDs are lowercase agent names from turn_queue

- [x] Task 5: Implement `update_current_turn` state updater (AC: #2, #3)
  - [x] 5.1 Create node that updates `current_turn` field after each agent acts
  - [x] 5.2 Alternatively, integrate turn tracking directly into turn functions
  - [x] 5.3 Ensure turn_queue cycles properly (DM -> PC1 -> PC2 -> ... -> END)

- [x] Task 6: Add human intervention node placeholder (AC: #4)
  - [x] 6.1 Create `human_intervention_node(state: GameState) -> GameState` stub
  - [x] 6.2 For now, just return state unchanged (Epic 3 implements full functionality)
  - [x] 6.3 Router should detect `human_active=True` and route to this node
  - [x] 6.4 Export in `__all__`

- [x] Task 7: Create `run_single_round` convenience function (AC: #1, #2, #3)
  - [x] 7.1 Create function that executes one complete round (DM + all PCs)
  - [x] 7.2 Accept initial GameState, return final GameState after round
  - [x] 7.3 Useful for testing and CLI usage
  - [x] 7.4 Export in `__all__`

- [x] Task 8: Write comprehensive tests
  - [x] 8.1 Test create_game_workflow returns compiled StateGraph
  - [x] 8.2 Test route_to_next_agent returns correct next agent
  - [x] 8.3 Test route cycles from DM -> PC1 -> PC2 -> END
  - [x] 8.4 Test turn_queue with different party sizes (1-4 PCs)
  - [x] 8.5 Test human_active=True routes to human_intervention_node
  - [x] 8.6 Test ground_truth_log accumulates all agent responses (via agents.py)
  - [x] 8.7 Test state immutability through the graph
  - [x] 8.8 Test workflow with multiple party sizes (integration)
  - [x] 8.9 Test human node exists in workflow

## Dev Notes

### Architecture Compliance (MANDATORY)

**Module Location (CRITICAL)**

Per architecture.md:
- `graph.py` - LangGraph state machine, node functions, routing logic
- `agents.py` - Contains `dm_turn` and `pc_turn` node functions (already implemented)

[Source: architecture.md#Project Structure]

**Node Naming Convention**

Per architecture.md, node IDs are lowercase short names:
```python
workflow.add_node("dm", dm_turn)
workflow.add_node("fighter", fighter_node)
workflow.add_node("rogue", rogue_node)
```

Node functions follow `{agent}_turn` pattern (already implemented in agents.py).

[Source: architecture.md#Naming Patterns]

**Supervisor Pattern**

Per architecture.md, the DM acts as supervisor:
```python
workflow.add_conditional_edges(
    "dm",
    route_to_next_agent,
    {
        "fighter": "fighter",
        "rogue": "rogue",
        "wizard": "wizard",
        "human": "human_intervention_node",
        "dm": "dm",
    }
)
```

[Source: architecture.md#LangGraph State Machine Architecture]

### LangGraph 0.2+ API Requirements

**CRITICAL: Use LangGraph 0.2.0+ patterns, not outdated 0.1.x syntax**

```python
from langgraph.graph import StateGraph, START, END

# Create graph with state schema
workflow = StateGraph(GameState)

# Add nodes
workflow.add_node("dm", dm_turn)
workflow.add_node("fighter", lambda state: pc_turn(state, "fighter"))

# Add edges
workflow.add_edge(START, "dm")  # Entry point
workflow.add_conditional_edges(
    "dm",
    route_to_next_agent,
    {"fighter": "fighter", "rogue": "rogue", END: END}
)

# Compile
app = workflow.compile()
```

**Conditional Edge Routing:**
```python
def route_to_next_agent(state: GameState) -> str:
    """Route to the next agent based on turn_queue position."""
    current = state["current_turn"]
    turn_queue = state["turn_queue"]

    # Handle human override
    if state["human_active"] and state["controlled_character"]:
        if current != "dm" and current == state["controlled_character"]:
            return "human"

    # Find next in queue
    current_idx = turn_queue.index(current)
    next_idx = (current_idx + 1) % len(turn_queue)
    return turn_queue[next_idx]
```

[Source: LangGraph 0.2 documentation, architecture.md#Turn Management]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR8 | System manages turn order and routes narrative flow | LangGraph conditional edges + turn_queue |
| FR1 | User can start a new game session | create_game_workflow initializes state machine |

[Source: prd.md#Multi-Agent Game Loop, epics.md#Story 1.7]

### State Management Pattern

**Turn Queue Structure:**
```python
turn_queue = ["dm", "fighter", "rogue", "wizard", "cleric"]
```

The queue determines turn order. DM is always first (supervisor). PCs follow in order.

**current_turn Tracking:**
```python
# Before node executes, set current_turn
def update_turn(state: GameState, agent_name: str) -> GameState:
    return {**state, "current_turn": agent_name}
```

**Round Cycling:**
- DM takes turn
- Each PC in turn_queue (after DM) takes turn
- After last PC, control returns to DM
- This creates DM -> PC1 -> PC2 -> ... -> PCn -> DM cycle

[Source: architecture.md#Turn Management]

### PC Node Wrapping Pattern

Since `pc_turn(state, agent_name)` requires the agent_name parameter, wrap with lambda or functools.partial:

```python
from functools import partial

# Option 1: Lambda (simpler for this case)
workflow.add_node("fighter", lambda s: pc_turn(s, "fighter"))
workflow.add_node("rogue", lambda s: pc_turn(s, "rogue"))

# Option 2: Partial (more explicit)
workflow.add_node("fighter", partial(pc_turn, agent_name="fighter"))
```

[Source: Story 1.6 dev notes, LangGraph documentation]

### Human Intervention Placeholder

For MVP, create a stub that will be fully implemented in Epic 3:

```python
def human_intervention_node(state: GameState) -> GameState:
    """Placeholder for human input handling.

    In Epic 3, this will:
    1. Pause the graph
    2. Wait for Streamlit user input
    3. Return state with human's response added

    For now, just return state unchanged.
    """
    # TODO: Implement in Story 3.2 (Drop-In Mode)
    return state
```

[Source: epics.md#Epic 3, architecture.md#Human Intervention Flow]

### Previous Story Intelligence

**From Story 1.6 (PC Agent Implementation):**
- `pc_turn(state, agent_name)` function signature established
- PC nodes need agent_name parameter - must wrap
- Memory isolation pattern working correctly
- 211 tests passing, all validation tools pass

**From Story 1.5 (DM Agent Implementation):**
- `dm_turn(state)` returns new GameState
- DM system prompt and context building complete
- State immutability pattern proven

**Key Patterns Already Established:**
- GameState TypedDict structure (models.py)
- Node functions return new state, never mutate
- Agent memories dict keyed by lowercase name
- ground_truth_log append pattern with `[Agent]: content`

### Code Patterns to Follow

**Graph Creation Factory:**
```python
def create_game_workflow(turn_queue: list[str] | None = None) -> CompiledStateGraph:
    """Create a compiled game workflow.

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

    # Add PC nodes dynamically
    for agent_name in turn_queue:
        if agent_name != "dm":
            workflow.add_node(agent_name, lambda s, name=agent_name: pc_turn(s, name))

    # Add human intervention node
    workflow.add_node("human", human_intervention_node)

    # Add entry edge
    workflow.add_edge(START, "dm")

    # Add conditional edges from each node
    routing_map = {name: name for name in turn_queue}
    routing_map["human"] = "human"
    routing_map[END] = END

    for agent_name in turn_queue:
        workflow.add_conditional_edges(
            agent_name,
            route_to_next_agent,
            routing_map,
        )

    return workflow.compile()
```

**Round Execution Helper:**
```python
def run_single_round(state: GameState) -> GameState:
    """Execute one complete round (DM + all PCs).

    Useful for testing and programmatic game control.

    Args:
        state: Initial game state for this round.

    Returns:
        Updated state after all agents have acted once.
    """
    workflow = create_game_workflow(state["turn_queue"])

    # Run until we complete the queue once
    # Implementation depends on LangGraph recursion limit handling
    result = workflow.invoke(state)
    return result
```

### Testing Strategy

**Mock LLM for Deterministic Tests:**
```python
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

def test_workflow_routes_dm_to_pc():
    """Test that after DM turn, workflow routes to first PC."""
    # Create state with turn queue
    state = create_initial_game_state()
    state["turn_queue"] = ["dm", "fighter", "rogue"]
    state["current_turn"] = "dm"
    state["characters"]["fighter"] = CharacterConfig(
        name="Thor", character_class="Fighter", personality="Brave", color="#C45C4A"
    )

    # Test routing
    next_agent = route_to_next_agent(state)
    assert next_agent == "fighter"
```

**Test Turn Queue Cycling:**
```python
@pytest.mark.parametrize("current,expected", [
    ("dm", "fighter"),
    ("fighter", "rogue"),
    ("rogue", "wizard"),
    ("wizard", "dm"),  # Cycles back
])
def test_turn_queue_cycling(current, expected):
    state = create_initial_game_state()
    state["turn_queue"] = ["dm", "fighter", "rogue", "wizard"]
    state["current_turn"] = current

    next_agent = route_to_next_agent(state)
    assert next_agent == expected
```

**Test Human Override:**
```python
def test_human_active_routes_to_human_node():
    state = create_initial_game_state()
    state["turn_queue"] = ["dm", "rogue"]
    state["current_turn"] = "rogue"
    state["human_active"] = True
    state["controlled_character"] = "rogue"

    next_agent = route_to_next_agent(state)
    assert next_agent == "human"
```

**Integration Test with Mocked LLM:**
```python
def test_full_round_execution():
    """Test a complete round with mocked LLM responses."""
    with patch("agents.get_llm") as mock_llm:
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_llm.return_value = mock_model

        state = create_initial_game_state()
        state["turn_queue"] = ["dm", "fighter"]
        state["current_turn"] = "dm"
        state["characters"]["fighter"] = CharacterConfig(...)

        result = run_single_round(state)

        # Verify log has both DM and fighter entries
        assert len(result["ground_truth_log"]) == 2
        assert "[DM]:" in result["ground_truth_log"][0]
        assert "[Thor]:" in result["ground_truth_log"][1]
```

### Project Structure Notes

- All new code goes in `graph.py` (currently just a placeholder docstring)
- Import `dm_turn`, `pc_turn` from agents.py
- Import GameState from models.py
- Tests go in `tests/test_graph.py` (new file)
- Follow flat project layout per architecture

### Export Pattern

```python
# graph.py
__all__ = [
    "create_game_workflow",
    "human_intervention_node",
    "route_to_next_agent",
    "run_single_round",
]
```

### What NOT To Do

- Do NOT implement full human intervention (that's Epic 3)
- Do NOT add streaming/async (architecture says synchronous for MVP)
- Do NOT use LangGraph 0.1.x patterns (use 0.2.0+ API)
- Do NOT mutate GameState in node functions
- Do NOT hardcode party composition - read from turn_queue
- Do NOT forget to update current_turn as the graph executes
- Do NOT create circular imports (graph.py imports from agents.py, not vice versa)
- Do NOT use `add_edge(node, END)` for every node - use conditional edges

### Dependencies

This story depends on:
- Story 1.2: GameState TypedDict, models (done)
- Story 1.5: dm_turn function (done)
- Story 1.6: pc_turn function (done)

This story enables:
- Story 1.8: Character Configuration System (workflow can load configured characters)
- Story 2.x: UI integration with running game loop
- Story 3.x: Human intervention integration

### LangGraph Installation Check

Ensure langgraph is installed:
```bash
uv add langgraph
```

Version should be 0.2.0+ for the StateGraph API.

### References

- [architecture.md#LangGraph State Machine Architecture] - Supervisor pattern, state schema
- [architecture.md#Turn Management] - Conditional edges, routing
- [architecture.md#Naming Patterns] - Node function and ID naming
- [prd.md#Multi-Agent Game Loop] - FR1, FR8 requirements
- [epics.md#Story 1.7] - Full acceptance criteria
- [agents.py] - dm_turn, pc_turn implementations
- [models.py] - GameState TypedDict definition
- [LangGraph 0.2 Documentation] - StateGraph, conditional edges API

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - clean implementation

### Completion Notes List

- Implemented `graph.py` with LangGraph 0.2+ API using StateGraph, START, END
- Created `create_game_workflow()` factory that dynamically builds workflow from turn_queue
- Implemented `route_to_next_agent()` router with supervisor pattern:
  - DM routes to first PC
  - PCs route to next PC in turn_queue
  - Last PC routes to END (completing round)
  - Human override detection for Epic 3
- Created `human_intervention_node()` placeholder returning state unchanged
- Created `run_single_round()` convenience function with recursion limit
- Used lambdas with default argument capture to wrap pc_turn for dynamic PC nodes
- Added type: ignore comments for LangGraph's incomplete type stubs
- Wrote 25 comprehensive tests covering:
  - Workflow creation and node existence
  - Turn queue routing (DM->PC->PC->END)
  - Human intervention routing
  - State immutability
  - Multiple party sizes
- All 236 tests pass
- pyright: 0 errors (35 warnings - all from LangChain/LangGraph stubs)
- ruff: Clean (auto-formatted)

### Design Decision: Round-Based Execution

Changed from continuous cycling (DM->PC1->PC2->DM->...) to round-based (DM->PC1->PC2->END).
This design allows:
- Clearer round boundaries for UI updates
- Natural pause points for human intervention
- Invoke workflow multiple times for multiple rounds
- Better control over recursion limits

### File List

- graph.py (new) - LangGraph state machine implementation
- agents.py (modified) - Added current_turn updates in dm_turn and pc_turn
- tests/test_graph.py (new) - 27 comprehensive tests (including integration tests)

## Change Log

- 2026-01-26: Implemented Story 1.7 - LangGraph Turn Orchestration (graph.py, tests/test_graph.py)
- 2026-01-26: [Code Review Fix] Fixed critical bug - current_turn now updates after each agent acts (agents.py:455, agents.py:533)
- 2026-01-26: [Code Review Fix] Corrected module docstring to reflect round-based execution (graph.py)
- 2026-01-26: [Code Review Fix] Added 2 integration tests with mocked LLM (tests/test_graph.py)
