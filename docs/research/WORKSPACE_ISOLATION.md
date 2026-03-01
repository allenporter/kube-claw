# Research: Workspace Isolation and Context Switching

This document explores how "Claw" systems handle multiple projects/apps and isolate their environments, with a focus on `openclaw`'s "Lanes" and `nanoclaw`'s simpler approach.

## 1. The Workspace Problem
An agent needs to switch between different projects (e.g., "Home Automation", "Work Project A", "Personal Website") without mixing:
-   **Filesystem Context**: `CLAUDE.md` and local files.
-   **Conversation History**: Previous tasks and decisions.
-   **Tooling State**: Environment variables, installed packages (if persistent).
-   **Identity**: Which user/group is authorized to access which workspace.

## 2. OpenClaw: The "Lane" and "ACP" System
OpenClaw uses a two-tier approach for isolation:

### A. Command Lanes (`src/process/command-queue.ts`)
-   **Purpose**: Serialize execution within a specific "logical path."
-   **Mechanism**: An in-process queue that ensures tasks in the same lane (e.g., `session:XYZ`) run one at a time.
-   **Concurrency**: Different lanes can run in parallel (e.g., a `cron` lane doesn't block a `main` session lane).
-   **Global vs Session**:
    -   `Global Lanes`: (e.g., `main`, `cron`, `subagent`) handle shared resources.
    -   `Session Lanes`: (e.g., `session:chat-id`) isolate specific user conversations.

### B. ACP (Agent Control Plane) (`src/acp/`)
-   **Purpose**: Physical isolation and "Brain" management.
-   **Mechanism**: The `AcpSessionManager` handles "Backends" (runtimes).
-   **Handle Persistence**: It maintains an `AcpRuntimeHandle` per session. This handle points to a specific container or process.
-   **Context Switching**: When a message comes in for `session-A`, the manager:
    1.  Resolves the session key.
    2.  Fetches/Ensures a `RuntimeHandle` (container).
    3.  If the container is idle, it "wakes" it.
    4.  The container has its own `cwd` (Project Path) and `env`.

## 3. NanoClaw: The "Transient Container" Approach
NanoClaw uses a simpler, more "stateless" approach to isolation:

### A. One Container Per Message (`src/container-runner.ts`)
-   **Mechanism**: Every time the agent runs, a *fresh* container is spawned via `docker run --rm`.
-   **Isolation**: Physical isolation is guaranteed by the container lifecycle.
-   **Workspace Mounting**:
    -   The `groupFolder` (workspace) is mounted to `/workspace/group`.
    -   If it's the `Main` group, the entire project root is mounted to `/workspace/project`.
    -   `.claude/` (session memory) is isolated per group via a dedicated host directory.

### B. IPC via Host Mounts
-   **Mechanism**: Instead of long-lived network sockets, NanoClaw uses a shared directory (`/workspace/ipc`) to pass state and tasks between the host and the transient container.

## 4. Comparison

| Feature | OpenClaw (ACP/Lanes) | NanoClaw (Transient) |
| :--- | :--- | :--- |
| **Persistence** | Persistent Containers (Long-lived) | Transient (Ephemeral) |
| **Startup Cost** | Low (Container is already warm) | High (New container per run) |
| **Parallelism** | Managed by Lanes (In-process) | Managed by Host (Spawned processes) |
| **Complexity** | High (Stateful management) | Low (Stateless/Filesystem-based) |
| **Security** | High (Hardened ACP) | Very High (Fresh sandbox every time) |

## 5. Synthesis for "Core v3"
A "Core v3" should likely adopt:
1.  **Logical Lanes**: For in-process serialization and multi-channel routing.
2.  **ACP-like Handle Management**: To allow for *both* persistent and transient backends.
3.  **Strict Filesystem Mapping**: NanoClaw's clear separation of `/workspace/group`, `/workspace/project`, and `/workspace/global` is a great model for hierarchical memory.
