# A2A Protocol Analysis for Claw Core v3

This document summarizes the findings from a deep dive into the [A2A (Agent-to-Agent) Protocol](https://a2a-protocol.org) specification and the `a2a-python` SDK implementation. It evaluates how these components can be leveraged for the **Claw Core v3** "Warm Lane" architecture.

## 1. Core Concepts & Lifecycle

The A2A protocol is centered around the **Task** as the primary unit of work.

### Task States (`TaskState`)
The protocol defines a robust state machine that maps well to long-running agentic workflows:
- **`TASK_STATE_WORKING`**: The agent is active.
- **`TASK_STATE_INPUT_REQUIRED`**: The "Interrupt" state. Perfect for Claw's need to ask the user for clarification or missing credentials.
- **`TASK_STATE_AUTH_REQUIRED`**: Specific state for credential injection.
- **Terminal States**: `COMPLETED`, `FAILED`, `CANCELED`, `REJECTED`.

### Communication Model
- **`SendMessage`**: The entry point. It can be a simple request-response or a **Streaming** call.
- **Streaming (`SendStreamingMessage`)**: Highly recommended for Claw to provide real-time "thoughts" (via `Message` parts) and incremental `Artifact` updates.
- **`SubscribeToTask`**: Allows a client (the Host Gateway) to reconnect to a long-running task if the initial connection is dropped.

## 2. Structural Alignment with Claw

### Workspaces and Persistence
- **A2A `context_id`**: Can be mapped directly to a **Claw Workspace**. Multiple tasks can share a `context_id`, allowing the agent to maintain continuity across different sub-tasks within the same project.
- **A2A `history`**: Managed within the `Task` object. The `a2a-python` SDK's `TaskManager` handles moving messages from `TaskStatus` to `history`, providing a standardized way to track the "conversation" between the Host and the Sandbox.

### Artifacts vs. Files
- **`Artifact`**: In A2A, artifacts are structured outputs (code snippets, URLs, status reports).
- **Claw Integration**: While the agent works on the filesystem (Project Memory), it should use A2A `Artifacts` to signal *meaningful* completions to the Host (e.g., "I have created the PR, here is the link").

## 3. SDK Implementation Insights (`a2a-python`)

### Agent Executor Pattern
The SDK provides an `AgentExecutor` abstract base class. For Claw Core v3, the worker entrypoint should implement this:
- **`execute(context, event_queue)`**: The main loop where the LLM is invoked.
- **`cancel(context, event_queue)`**: Essential for the Host to kill runaway processes.

### Task Management
The `TaskManager` class in the SDK handles the heavy lifting of:
- Loading/Saving tasks from a `TaskStore` (SQLAlchemy/SQLite supported).
- Appending artifacts.
- Managing status transitions.
- **Claw Recommendation**: Use a SQLite `DatabaseTaskStore` located in the persistent workspace mount (`/workspace/.claw/tasks.db`) to ensure the agent's state survives pod restarts.

### Transport Layer
- **Current SDK**: Primarily supports **JSON-RPC** over HTTP (FastAPI/Starlette) or **gRPC**.
- **Claw Gap**: The SDK does not natively implement **Unix Domain Sockets (UDS)**.
- **Workaround**: Since we want UDS for security/speed in the K8s pod, we can run the A2A Starlette app using `uvicorn` bound to a unix socket:
  ```bash
  uvicorn app:app --uds /tmp/a2a.sock
  ```

## 4. Identity and the "Binding Table"

A2A has a `tenant` field in most requests.
- **Mapping**: The `tenant` ID can be used to pass the `author_id` or a specific `binding_id` from the Host to the Worker.
- **Security**: The Worker can use this ID to verify it is accessing the correct workspace and using the correct `AuthProfile`.

## 5. Summary of Recommendations for Core v3

1.  **Adopt A2A Schema**: Use the `Task`, `Message`, and `Artifact` protobuf definitions as the "Language" of the Host-Worker interface.
2.  **Stateful Workers**: Use the `TASK_STATE_INPUT_REQUIRED` state to handle multi-turn interactions without killing the sandbox.
3.  **Local Persistence**: Use the SDK's `DatabaseTaskStore` backed by a SQLite file on the persistent volume.
4.  **UDS Transport**: Deploy the worker as a JSON-RPC server listening on a Unix Domain Socket, mounted via an `emptyDir` shared with the Host sidecar (if using sidecars) or the K8s Controller.
5.  **Event-Driven**: Leverage the `event_queue` pattern to stream logs and "thoughts" back to the user channel (Discord/WhatsApp) while the agent is still `WORKING`.
