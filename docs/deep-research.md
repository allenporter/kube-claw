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

To implement a robust Claw Core, each component must satisfy a specific set of functional and security requirements.

### A. Gateway (The Brain)
- **Protocol Normalization**: Must translate various channel protocols (WhatsApp, Discord, CLI) into a unified internal message format.
- **Session Registry**: Must maintain a real-time mapping of `SessionID -> SandboxID/Node`.
- **Approval API**: Must provide a mechanism for the Agent to pause execution and request human-in-the-loop approval for risky tools (e.g., `Bash` with side-effects).
- **Heartbeat Monitor**: Must track sandbox health and restart or reap them based on activity.

### B. Provisioner (The Orchestrator)
- **Lifecycle Management**: Must handle the automatic creation (on-demand) and deletion (on-idle) of sandboxed environments.
- **K8s Integration**: In KubeClaw, this component is a Kubernetes Controller that translates session requests into Pod/Job specifications.
- **Resource Quotas**: Must enforce CPU/Memory limits on sandboxes to prevent resource exhaustion.

### C. Agent Runner (The Executor)
- **Persistent Streaming**: Must implement the `AsyncIterable` pattern to keep the LLM reasoning session alive across multiple turns.
- **Tool Bridge (MCP)**: Must act as a bridge between the LLM and the local environment's tools (Filesystem, Shell, external APIs).
- **History Management**: Must handle the loading and saving of session history to ensure task continuity.

### D. Sandbox Environment (The Jail)
- **Zero-Trust Networking**: By default, sandboxes should have limited or no outbound internet access except for authorized API endpoints.
- **Clean Slate**: Every new session should start from a "known good" image, but with the persistent workspace mounted.
- **Sanitized Environment**: Sensitive host information (like the Gateway's internal API keys) must be scrubbed from the environment before the LLM takes control.

### E. Persistence Layer (The Memory)
- **Durable Workspaces**: Use Kubernetes PVCs to ensure that the user's files are never lost, even if the pod is killed.
- **State Snapshots**: Periodically snapshot session state to allow for "rollback" or branching in conversation history.

## 4. Core Loop Architectures

There are two distinct layers of "core loops" in a Claw implementation: the **Host Orchestration Loop** and the **Agent Session Loop**.

### Host Orchestration Loop (System Level)

The host level manages the lifecycle of agent environments and routes messages between channels and active agents.

| Component | NanoClaw (Polling-Based) | OpenClaw (Event-Based) |
| :--- | :--- | :--- |
| **Trigger** | `startMessageLoop` polls SQLite for new messages every `POLL_INTERVAL`. | Real-time WebSocket events or HTTP callbacks from channel plugins. |
| **Concurrency** | `GroupQueue` manages a fixed pool of containers. | `AgentEventHandler` maps multiple async runs to WebSocket clients. |
| **Isolation** | One ephemeral container per group/session. | One gateway process (optionally spawning sandboxed sub-processes). |
| **IPC** | Filesystem-based (writing JSON to `/workspace/ipc/input/`). | WebSocket/RPC-based via a central `NodeRegistry`. |

### Agent Session Loop (Running Inside Sandbox)

The session level is where the LLM actually "loops" through reasoning and tool-use turns.

- **Persistence via AsyncIterables**: Both implementations use an `AsyncIterable` (e.g., `MessageStream` in NanoClaw) passed to the SDK's `query` function. This prevents the session from terminating after a single turn, allowing for persistent, "hot" sessions.
- **Draining & Piping**: During an active query, the agent runner must "drain" the IPC input channel to pipe follow-up user messages directly into the LLM's active context without restarting the session.

## 2. Primary Components

### Workspace Management
- **NanoClaw**: Uses group-specific directories mounted as volumes. Session state (`.claude/`) is isolated per group.
- **OpenClaw**: Uses `resolveAgentWorkspaceDir` to map agent IDs to persistent paths, ensuring that multiple runs of the same agent share the same state.

### Security & Sanitization
- **PreToolUse Hooks**: Critical for sanitizing environments. NanoClaw uses a hook to `unset` sensitive API keys before the `Bash` tool executes a command.
- **PreCompact Hooks**: NanoClaw uses this to archive full conversation transcripts to markdown before the SDK performs context compaction.

### Communication Gateway
- **NodeRegistry (OpenClaw)**: A sophisticated system for tracking connected "Nodes" (devices, browsers, or sub-agents). This is the "Universal Gateway" philosophy.
- **Filesystem IPC (NanoClaw)**: Robust, "small enough to understand." It uses simple file existence checks (`_close` sentinel) and directory watches for communication.

## 3. Design Recommendations for KubeClaw

To build a "Kubernetes Native" Claw Core, we should adapt these patterns:

1. **Host Loop -> K8s Controller**: Replace the polling message loop with a Kubernetes Controller or Operator pattern. New messages can trigger the creation of a **K8s Job**.
2. **IPC -> K8s exec/attach**: Instead of filesystem IPC, leverage `kubectl exec` or WebSocket-based container attachment to stream inputs/outputs to the running Pod.
3. **Sandbox -> Pod Isolation**: Use Pod-level security policies and ephemeral containers for the highest isolation standard.
4. **Agent Loop -> Sidecar/Primary**: Run the `agent-runner` as the primary container in the Pod, using the `AsyncIterable` pattern to handle long-running interactions within the Job's lifecycle.
5. **Session State -> PersistentVolumeClaims (PVC)**: Mount PVCs to `/home/node/.claude` to allow session persistence across Job restarts.
