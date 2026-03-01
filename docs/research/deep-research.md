# Deep Research: Claw Core Architectures

This document provides a deep-dive analysis of the core loop architectures and primary components found in **OpenClaw** and **NanoClaw**, serving as a foundation for the design of **KubeClaw**.

## 1. Core Principles of a "Claw" Core

A modern Claw architecture is defined by several foundational principles that ensure security, persistence, and extensibility.

1.  **Strict Isolation by Runtime**: Every interaction or project session must run in its own isolated environment (e.g., a K8s Pod). This prevents cross-talk between sessions and ensures a secure sandbox for tool execution.
2.  **Stateless Runtime, Persistent Workspace**: The agent's execution environment (the Pod) is ephemeral and can be reaped at any time. However, the **Workspace** (source code, memory, session history) must be persistent (e.g., on a PVC) so work can resume seamlessly.
3.  **Standardized IPC (Inter-Process Communication)**: The Gateway (Host) and the Agent (Sandbox) communicate via a robust, standardized protocol (e.g., JSON-RPC or a streaming WebSocket).
4.  **Channel-Agnostic Core**: The core logic should not care if it's being driven by a CLI, a WhatsApp bot, or a Discord integration. All inputs are normalized before reaching the Agent.
5.  **Security via Sanitization Hooks**: Every tool use—especially those with side effects like `Bash` or `Write`—should pass through a chain of hooks for logging, approval, and environment sanitization.

## 2. Big-Picture Architecture

The following flow illustrates how a request moves through a Claw system:

1.  **Interaction Entry**: A user sends a message via a "Channel" (CLI, WhatsApp, etc.).
2.  **Gateway Routing**: The Gateway identifies the session ID and the target workspace. It checks the **Node Registry** to see if a Sandbox is already active for this session.
3.  **Sandbox Provisioning**: If no active Sandbox exists, the **Provisioner** (e.g., K8s Job Controller) spawns one. It mounts the persistent workspace (PVC) and initializes the **Agent Runner**.
4.  **Agent Execution Loop**: The Agent Runner (running inside the Sandbox) takes the user input and starts the LLM Reasoning Loop. It leverages the **Anthropic Agent SDK** or **MCP** for tool use.
5.  **Streaming Feedback**: As the agent reasons or acts, results are streamed back to the Gateway, which routes them to the original Input Channel.
6.  **Idle & Persistence**: After a period of inactivity, the Sandbox is reaped. Because the Workspace is on a PVC, the next request will resume exactly where the previous one left off.

## 3. Component Requirements

### A. Gateway (The Brain)
- **Protocol Normalization**: Must translate various channel protocols (WhatsApp, Discord, CLI) into a unified internal message format.
- **Session Registry**: Must maintain a real-time mapping of `SessionID -> SandboxID/Node`.
- **Approval API**: Must provide a mechanism for the Agent to pause execution and request human-in-the-loop approval for risky tools (e.g., `Bash` with side-effects).

### B. Provisioner (The Orchestrator)
- **Lifecycle Management**: Must handle the automatic creation (on-demand) and deletion (on-idle) of sandboxed environments.
- **K8s Integration**: In KubeClaw, this component is a Kubernetes Controller that translates session requests into Pod/Job specifications.

### C. Agent Runner (The Executor)
- **Persistent Streaming**: Must implement the `AsyncIterable` pattern to keep the LLM reasoning session alive across multiple turns.
- **Tool Bridge (MCP)**: Must act as a bridge between the LLM and the local environment's tools.

## 4. Core Loop Architectures

### Host Orchestration Loop (System Level)

| Component | NanoClaw (Polling-Based) | OpenClaw (Event-Based) |
| :--- | :--- | :--- |
| **Trigger** | `startMessageLoop` polls SQLite for new messages every `POLL_INTERVAL`. | Real-time WebSocket events or HTTP callbacks. |
| **Concurrency** | `GroupQueue` manages a fixed pool of containers. | `AgentEventHandler` maps multiple async runs. |
| **Isolation** | One ephemeral container per group/session. | One gateway process (or sandboxed sub-processes). |
| **IPC** | Filesystem-based (writing JSON to `/workspace/ipc/input/`). | WebSocket/RPC-based via `NodeRegistry`. |

### LLM Placement & Tool Execution (The "Brain" Location)

A critical distinction between these architectures is where the LLM "Reasoning Loop" actually resides relative to the sandbox boundary:

| Feature | Model A: Host-Managed LLM | Model B: Sandboxed LLM (NanoClaw) |
| :--- | :--- | :--- |
| **LLM Location** | Host Process (Gateway) | Inside the Sandbox (Container/Pod) |
| **Tool Execution** | Host sends command *into* sandbox via `exec`. | Runner calls tools *locally* within sandbox. |
| **Security** | Host is "the brain"; if compromised, host is at risk. | Host is "the orchestrator"; brain is isolated. |
| **Latency** | Low (no container startup for "thinking"). | Higher (container must boot to start thinking). |
| **Tool Complexity**| High (requires robust IPC/Exec bridge). | Low (uses standard `subprocess` or `os` calls). |

**NanoClaw Philosophy**: By placing the LLM client *inside* the sandbox, NanoClaw treats the agent's "thoughts" and "actions" as a single unit of isolated execution. This eliminates the need for a complex "Command Bridge" and ensures that even the LLM's logic (and any credentials it uses for tool execution) are contained within the ephemeral environment.

### Session Bootstrapping & Identity (NanoClaw Analysis)

In the NanoClaw model, a **Session** is not a long-lived process but a **Stateful Interaction** defined by its environment. Our research reveals a specific pattern for bootstrapping these in a channel-agnostic way:

1.  **The Context Handshake**:
    Every inbound message from a channel (Discord, WhatsApp, etc.) is wrapped in a `Context` object containing `author_id`, `channel_id`, and `metadata`.

2.  **Dynamic Workspace Binding**:
    NanoClaw uses a **Binding Table** to map the `channel_id` to a `WorkspacePath`.
    - If a channel is already bound, it mounts that volume.
    - If it's a new channel, it performs an **Automatic Bootstrap**, creating a unique persistent directory for that channel ID.

3.  **Credential Injection (Auth Profiles)**:
    NanoClaw maps the `author_id` to an **Auth Profile**. During the "Boot" of the sandbox, it pulls keys (like `GITHUB_TOKEN`) from a secure store and injects them as **Environment Variables** into the sandbox.

4.  **The "Handshake" Entrypoint**:
    When a container starts, it runs a specialized `entrypoint` script that verifies workspace access, reads the injected identity, and loads `CLAUDE.md` to restore memory.

## 5. Primary Components (Implementation Patterns)

### Workspace Management
- **NanoClaw**: Uses group-specific directories mounted as volumes. Session state (`.claude/`) is isolated per group.
- **OpenClaw**: Uses `resolveAgentWorkspaceDir` to map agent IDs to persistent paths.

### Security & Sanitization
- **PreToolUse Hooks**: Critical for sanitizing environments. NanoClaw uses a hook to `unset` sensitive API keys before the `Bash` tool executes.
- **PreCompact Hooks**: NanoClaw uses this to archive conversation transcripts before context compaction.

## 6. Design Recommendations for KubeClaw

1. **Host Loop -> K8s Controller**: Replace the polling loop with a K8s Controller. New messages trigger a **K8s Job**.
2. **IPC -> K8s exec/attach**: Leverage `kubectl exec` or WebSocket attachment for streaming inputs/outputs.
3. **Sandbox -> Pod Isolation**: Use Pod security policies and ephemeral containers.
4. **Agent Loop -> Sidecar/Primary**: Run the `agent-runner` using the `AsyncIterable` pattern within the Job's lifecycle.
5. **Session State -> PersistentVolumeClaims (PVC)**: Mount PVCs to `/home/node/.claude` for persistence across restarts.
