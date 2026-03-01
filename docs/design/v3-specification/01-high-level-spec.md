# Claw Core v3: The Unified Specification

This document defines the "Gold Standard" for a tool-capable LLM orchestrator, synthesizing the strengths of **OpenClaw** (stateful management, logical lanes) and **NanoClaw** (clean filesystem isolation, transient execution).

---

## 1. System Philosophy

1.  **Logical Serialization**: A user session is a "Lane." No two runs in the same lane should interleave.
2.  **Stateless Host, Stateful Sandbox**: The host process manages the "Brain" and "Mouth" (API/Channels). The "Hand" (Sandbox) is the only place where state (files/code) lives.
3.  **Strict Capability Tiers**:
    *   **Tier 0 (Read-Only)**: Global memory/knowledge.
    *   **Tier 1 (Workspace)**: Project-specific files (`/workspace/group`).
    *   **Tier 2 (System)**: Restricted access to host tools (via sanctioned IPC).

---

## 2. Core Architecture: The "Triad" Refined

### A. The Reachability Layer (Multi-Channel)
*   **Protocol Neutrality**: All inputs (WhatsApp, Discord, TUI) are mapped to a `StandardIntent`:
    ```json
    {
      "laneId": "session:user-123",
      "text": "fix the build",
      "attachments": [...],
      "context": { "projectId": "alpha", "userId": "user-456" }
    }
    ```
*   **Logical Queuing**: The host enqueues this intent into the `CommandLane`.

### B. The Orchestration Layer (The Controller)
*   **Session Lifecycle Manager**: Instead of just starting a container, the controller manages "Session Handles."
*   **Backends**: A pluggable system where a backend can be:
    *   `Transient`: (NanoClaw style) Spawns a fresh container, runs a task, and exits.
    *   `Persistent`: (OpenClaw style) Keeps a container warm for low-latency turns.
*   **Context Compaction**: The controller monitors token usage and triggers a "Compaction Step" (summarization) before the next turn if limits are exceeded.

### C. The Execution Layer (The Sandbox)
*   **Hierarchical Mounts**: Every sandbox must have three standard mount points:
    1.  `/workspace/global`: Read-only system-wide knowledge.
    2.  `/workspace/project`: Read/Write project-specific files.
    3.  `/workspace/session`: Read/Write ephemeral turn-specific state (e.g., `.claude/`).
*   **No Network by Default**: Tools must be proxied through the host to enforce safety and observability.

---

## 3. Key Functional Innovations

### I. The "Lane" Handshake (Identity & Auth)
When an intent enters a lane, the controller performs a **Session Handshake** to resolve identity and inject capabilities:

1.  **Resolve Actor Identity**:
    *   Map the inbound protocol ID (e.g., Discord Snowflake `12345`) to a **Claw Identity**.
    *   **Scenario (Discord)**: User A in `#project-alpha` maps to `Identity: Dev-A` with `Workspace: /repo/alpha`.
2.  **Authorize Capabilities**:
    *   Fetch the **Auth Profile** associated with the Identity.
    *   **Direct Credentials**: For CLI tools (e.g., GitHub `gh`), inject scoped tokens (e.g., `GITHUB_TOKEN`) into sandbox environment variables.
    *   **Proxied Capabilities**: For API-based tools (e.g., Slack, Stripe), keep tokens on the Host. The Host will "hydrate" these calls via RPC during execution.
3.  **Spawn/Wake Sandbox**:
    *   Initialize the backend with the correct mounts (Project Alpha).
    *   Inject the `Auth Profile` credentials into the sandbox shell environment.
4.  **Contextual Memory**:
    *   Load the `CLAUDE.md` from the project root and the session-specific history from `.claude/`.

### II. Multi-Channel Identity Mapping
To handle a user working across multiple projects/channels, the Core uses a **Binding Table**:

| Channel | Channel ID | User ID | Agent ID | Workspace | Auth Profile |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Discord | `#alpha-dev` | `Dev-A` | `Alpha-Bot` | `/repos/alpha` | `github-token-A` |
| Discord | `#beta-dev` | `Dev-A` | `Beta-Bot` | `/repos/beta` | `github-token-A` |
| WhatsApp| `Personal` | `Dev-A` | `Personal-Bot`| `/repos/home` | `personal-key` |
| Email   | `allenporter@`| `Dev-A` | `Library-Bot` | `/repos/ical` | `github-token-A` |

*   **Key Insight**: A single user (`Dev-A`) can have multiple **Agent Personalities** and **Workspaces** depending on *where* they are talking to the Core. The `Auth Profile` (credentials) follows the user, while the `Workspace` follows the channel/context.
*   **Case Study**: See `docs/SCENARIO_MULTI_PROJECT_FIX.md` for an illustration of how a user switches between projects via Email and Discord.

### III. Proactive Autonomy (The Pulse)
A background scheduler (Cron) that can inject intents into any lane.
*   **Example**: "Every Monday at 9 AM, run a `morning-briefing` intent in the `session:team-alpha` lane."
*   **Case Study**: See `docs/SCENARIO_ROBOROCK_MAINTAINER.md` for a walkthrough of how an agent transitions from reactive chat to proactive daily triage.

### III. Tool IPC (The Nerve)
All tools inside the sandbox communicate with the host via a standard JSON-RPC interface over a Unix socket or named pipe. This allows:
*   **Host-side Approval**: User can approve/deny a `bash` command before it runs.
*   **Audit Logging**: Every tool call is recorded outside the sandbox.

---

## 4. Implementation Guidelines (The "Claw" Checklist)

- [ ] Use **Logical Lanes** for concurrency control.
- [ ] Use **Docker/Podman** for mandatory sandbox isolation.
- [ ] Implement **Hierarchical Filesystem Mounts**.
- [ ] Support **Multi-Channel Input** (normalization).
- [ ] Provide a **Background Scheduler** for proactive tasks.
- [ ] Include an **Audit Log** of all tool executions.
