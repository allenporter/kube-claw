# Design: Worker Entrypoint & Sandbox Boundary

This document details the internal design of the **Worker Entrypoint** for Claw Core v3, which serves as the "Hand" inside the execution sandbox.

## 1. Lifecycle & Connectivity

The Worker follows a **Server-First** lifecycle to support "Warm Lanes" in Kubernetes.

1.  **Boot**: The container starts and enters `worker/entrypoint.py`.
2.  **Discovery**: It identifies the shared UDS volume (e.g., `/rpc/`).
3.  **Bind**: It starts a Unix Domain Socket server at `/rpc/worker.sock`.
4.  **Handshake (A2A)**:
    *   **CONNECT**: Host connects to the socket.
    *   **BOOTSTRAP**: Host sends a `bootstrap` message containing:
        *   `identity`: User/Channel mapping.
        *   `workspace_path`: Where to perform work.
        *   `llm_config`: Model name, temperature, etc.
    *   **READY**: Worker acknowledges and is ready for tasks.

## 2. Component: Session Manager

The `SessionManager` (`worker/session.py`) maintains the state of the "Warm Lane."

*   **Soft Reset**: Between tasks (or upon explicit request), the worker performs a `soft_reset()`. This clears the conversation history and temporary variables but keeps the UDS connection and workspace mounts alive.
*   **Context Isolation**: Ensures that if a lane is re-used for a different user (though unlikely in current design), no residual memory leaks between sessions.

## 3. Component: Tool Registry & ADK Integration

The Worker uses a dual-path execution model for tools:

### A. Local Tools (Direct)
Tools that run inside the sandbox using the worker's local environment.
*   **Examples**: `bash`, `read_file`, `write_file`, `git`.
*   **Execution**: Handled via `adk-cli` or direct subprocess calls.
*   **Security**: Restricted by the container's PID/Network namespace.

### B. Proxied Tools (Host-Hydrated)
Tools that require sensitive credentials or host-side state.
*   **Examples**: `slack_send`, `stripe_charge`, `github_api_call`.
*   **Execution**: The Worker returns a `PROXIED_TOOL_REQUEST` response via A2A. The Host intercepts this, injects secrets from the `BindingTable`, executes the tool, and sends the result back to the Worker.

## 4. Signal Handling & Persistence

*   **SIGTERM**: The worker performs a "Graceful Exit." It flushes any pending logs to the workspace and notifies the Host via a `worker_shutdown` event before closing the socket.
*   **Persistence of Intent**: Because the `workspace_path` is mounted from a PVC, the agent's progress (logs, `CLAUDE.md`, modified files) survives even if the worker pod is restarted.

## 5. Directory Structure (`kube_claw/core_v3/worker/`)

*   `entrypoint.py`: Main process loop and signal configuration.
*   `server.py`: Asyncio UDS server and JSON-RPC dispatcher.
*   `session.py`: `SessionState` and bootstrap logic.
*   `tool_registry.py`: Routing logic for Local vs. Proxied tools.
*   `handlers/`: Specific logic for different A2A message types (input, interrupt, etc.).
