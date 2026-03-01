# Claw Core v3: A2A Orchestrator Handshake & Lifecycle

This document defines the state machine and connection handshake for the **A2A Orchestrator**, which serves as the "Brain" of the Claw Core v3 architecture.

---

## 1. The Handshake Sequence

The Orchestrator manages the transition from an inbound message (e.g., from Discord) to an active, tool-capable agent session.

### Sequence Diagram (Conceptual)

1.  **Gateway** (Discord) -> `Orchestrator.handle_message(msg)`
2.  **Orchestrator** -> `BindingTable.resolve_workspace(msg)` -> `WorkspaceContext`
3.  **Orchestrator** -> `SandboxManager.ensure_sandbox(ctx)` -> `SandboxAddress` (UDS Path)
4.  **Orchestrator** -> `A2AProtocol.connect(uds_path)` -> `SessionHandle`
5.  **Orchestrator** -> `SessionHandle.push_task(msg.content)`
6.  **Worker** (Sandbox) -> `SessionHandle.stream_thoughts()` -> **Orchestrator**
7.  **Orchestrator** -> **Gateway** (Updates user with "Thinking...")

---

## 2. Orchestrator State Machine

To handle long-running tasks and interruptions, the Orchestrator maintains a state for each active `ChannelID`.

| State | Description | Transition Trigger |
| :--- | :--- | :--- |
| `IDLE` | No active task for this channel. | Inbound Message -> `RESOLVING` |
| `RESOLVING` | Mapping identity to workspace/PVC. | Success -> `PROVISIONING` |
| `PROVISIONING` | Starting K8s Pod / Mounting UDS. | Pod Ready -> `CONNECTING` |
| `CONNECTING` | Establishing UDS handshake. | Connected -> `WORKING` |
| `WORKING` | LLM is generating or running tools. | `tool_call` -> `HYDRATING` |
| `HYDRATING` | Host is resolving secrets for a tool. | Hydrated -> `EXECUTING` |
| `EXECUTING` | Tool is running on the Host/Sandbox. | Result -> `WORKING` |
| `INTERRUPTED` | User sent a follow-up mid-task. | Resume -> `WORKING` |
| `COMPLETED` | Task finished; worker is warm/idling. | Timeout -> `TERMINATING` |

---

## 3. The Tool Hydration Loop (The "Middleware")

When the Worker requests a `proxied` tool, the Orchestrator acts as a secure middleware:

1.  **Intercept**: Orchestrator catches `tool_call` from the A2A stream.
2.  **Hydrate**: Calls `ToolHydrator.hydrate(ctx, call)` to inject secrets.
3.  **Execute**: Runs the tool (either on Host or via RPC back to Sandbox).
4.  **Inject**: Sends the `tool_result` back into the A2A stream for the Worker to resume.

---

## 4. Handling Interruption & Concurrency

### "Stop & Resume" Logic
If a user sends a message while the Orchestrator is in `WORKING` state:
- **Immediate Interruption**: Send a `SIGINT` or `A2A.abort` to the worker?
- **Queueing**: Append the new message to a "Next Turn" queue.
- **Design Choice**: For Core v3, we will implement **A2A Interrupts**. The Host sends an `interrupt` packet. The worker checkpoints its state and waits for the new prompt.

### Concurrency
- Each `ChannelID` (Discord Channel) maps to a unique **UDS Socket**.
- The Orchestrator uses an **Asyncio Task Group** to manage multiple concurrent channels.
- **Persistence**: Active `ChannelID -> SandboxID` mappings are stored in the `InMemoryBindingTable` (and eventually a DB).

---

## 5. Next Steps for Implementation

1.  **Draft `core_v3/domain/orchestrator.py`**: A concrete implementation of the `A2AOrchestrator` interface.
2.  **Flesh out `A2ASession`**: A protocol-agnostic wrapper for the A2A JSON-RPC communication.
3.  **Unit Test**: Create a test that uses `FakeSandboxManager` and `InMemoryBindingTable` to simulate a full message-to-result loop.
