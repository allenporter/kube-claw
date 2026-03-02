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
| `WORKING` | LLM is generating or running tools. | `tool_call` -> `PROXYING` |
| `PROXYING` | Host is resolving secrets for an MCP tool. | Hydrated -> `EXECUTING` |
| `EXECUTING` | Tool is running on the Host/Sandbox. | Result -> `WORKING` |
| `INTERRUPTED` | User sent a follow-up mid-task. | Resume -> `WORKING` |
| `COMPLETED` | Task finished; worker is warm/idling. | Timeout -> `TERMINATING` |

---

## 3. The MCP Tool Proxy Loop (The "Middleware")

When the Worker requests a `proxied` tool, the Orchestrator acts as a secure middleware:

1.  **Intercept**: Orchestrator catches `tool_call` from the A2A stream.
2.  **Proxy**: Routes the call to an MCP (Model Context Protocol) Server on the Host.
3.  **Inject**: The Host-side MCP Server injects credentials from the `AuthProfile` and executes the tool.
4.  **Return**: Sends the `tool_result` back into the A2A stream for the Worker to resume.

---

## 4. Handling Interruption & Concurrency

### Mid-Run Input Behavior
If a user sends a message while the Orchestrator is in `WORKING` state, behavior is determined by the **queue mode** configured for the session. See [11-queue-concurrency.md](./11-queue-concurrency.md) for the full specification of `collect`, `followup`, and `steer` modes.

### Concurrency
- Each `ChannelID` (Discord Channel) maps to a unique **UDS Socket**.
- The Orchestrator uses an **Asyncio Task Group** to manage multiple concurrent channels.
- **Persistence**: Active `ChannelID -> SandboxID` mappings are stored in the `InMemoryBindingTable` (and eventually a DB).

---

## 5. Next Steps for Implementation

1.  **Draft `core_v3/domain/orchestrator.py`**: A concrete implementation of the `A2AOrchestrator` interface.
2.  **Flesh out `A2ASession`**: A protocol-agnostic wrapper for the A2A JSON-RPC communication.
3.  **Unit Test**: Create a test that uses `FakeSandboxManager` and `InMemoryBindingTable` to simulate a full message-to-result loop.

## 6. Worker Entrypoint and Sandbox Boundary

### Worker as Server (UDS)
The Worker starts an RPC server listening on a Unix Domain Socket (UDS) at a path specified by the `SOCKET_PATH` environment variable (e.g., `/rpc/worker.sock`). The Host container connects to this socket as a client to initiate the handshake.

### Bootstrap Data (JIT Config)
The worker receives its initial identity, workspace paths, and LLM configuration via the `bootstrap` A2A request. This "Just-In-Time" configuration is preferred over static mounts to allow for dynamic role-switching and security isolation.

### Signal and Session Handling
- **Soft Resets**: Triggered via the `soft_reset` A2A method. This clears the current `SessionState`, environment overrides, and tool registries, ensuring the "Warm Lane" is ready for a new turn without a full container restart.
- **OS Signals**: The worker handles `SIGTERM` and `SIGINT` to gracefully shut down the UDS server and clean up the socket file.

### Tool Execution Flow
- **Local Tools**: Tools like `bash`, `read_file`, and `write_file` are executed within the sandbox. The worker uses `asyncio.create_subprocess_shell` for non-blocking execution in the workspace.
- **Proxied Tools**: Sensitive tools (e.g., `slack_send`, `github_pr_create`) are identified as "proxied" in the `ToolRegistry`. When called, the worker routes these via the MCP Tool Proxy Loop on the Host.
