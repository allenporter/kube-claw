# Claw Core v3: Orchestrator Lifecycle

This document defines the state machine and execution flow for the **Orchestrator**, which coordinates the Gateway, Binding Table, and Agent Executor.

> **Note**: This document was significantly revised to reflect the [Embedded Executor Architecture](../../decisions/ADR-004-embedded-executor.md). The original handshake sequence (UDS, A2A, MCP proxy) has been replaced with an in-process model.

---

## 1. The Execution Flow

The Orchestrator manages the transition from an inbound message to an active agent run.

### Sequence

1.  **Gateway** (Discord) -> `Orchestrator.handle_message(msg)`
2.  **Orchestrator** -> `BindingTable.resolve_workspace(msg)` -> `WorkspaceContext`
3.  **Orchestrator** -> `LaneQueue.enqueue(lane_key, msg)` (waits for lane availability)
4.  **Orchestrator** -> `AgentExecutor.execute(workspace_context, msg)` (in-process async call)
5.  **AgentExecutor** -> yields `OrchestratorEvent` (thoughts, tool calls, results)
6.  **Orchestrator** -> streams events back to **Gateway** -> user channel

---

## 2. Orchestrator State Machine

The Orchestrator maintains a state for each active lane.

| State | Description | Transition Trigger |
| :--- | :--- | :--- |
| `IDLE` | No active run for this lane. | Inbound Message -> `RESOLVING` |
| `RESOLVING` | Mapping identity to workspace. | Success -> `QUEUED` |
| `QUEUED` | Waiting for lane availability. | Lane free -> `WORKING` |
| `WORKING` | Agent is reasoning or executing tools. | Agent complete -> `COMPLETED` |
| `COMPLETED` | Run finished; lane released. | New message -> `RESOLVING` |

---

## 3. Tool Execution

Tools are invoked by the Agent Executor during the `WORKING` state:

*   **Direct Tools** (bash, git, file I/O): Run as subprocesses via `asyncio.create_subprocess_shell`.
*   **External MCP Tools** (GitHub, Slack): Accessed via `McpToolset` connecting to external MCP servers.

All tool calls are logged for audit purposes.

---

## 4. Handling Interruption & Concurrency

### Mid-Run Input Behavior
If a user sends a message while the Orchestrator is in `WORKING` state, behavior is determined by the **queue mode** configured for the session. See [11-queue-concurrency.md](./11-queue-concurrency.md) for the full specification of `collect`, `followup`, and `steer` modes.

### Concurrency
- Each `lane_key` gets its own FIFO queue (single-writer guarantee).
- The Orchestrator uses a global semaphore (`max_concurrent`) to cap total parallel runs.
- The Orchestrator uses an **Asyncio Task Group** to manage multiple concurrent lanes.
- Active lane state is tracked in the `BindingTable` (eventually a DB).
