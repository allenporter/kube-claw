# Claw Core v3: The Unified Specification

This document defines the "Gold Standard" for a tool-capable LLM orchestrator, synthesizing the strengths of **OpenClaw** (stateful management, logical lanes) and **NanoClaw** (clean filesystem isolation, transient execution).

---

## 1. System Philosophy

1.  **Logical Serialization**: A user session is a "Lane." No two runs in the same lane should interleave.
2.  **Embedded Execution**: The orchestrator and agent executor run in a single process. There is no container boundary for the agent—K8s Pod isolation is sufficient. See [ADR-004](../../decisions/ADR-004-embedded-executor.md).
3.  **Strict Capability Tiers**:
    *   **Tier 0 (Read-Only)**: Global memory/knowledge.
    *   **Tier 1 (Workspace)**: Project-specific files (PVC mount).
    *   **Tier 2 (External)**: API-based tools via external MCP servers.

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
*   **Session Lifecycle Manager**: Manages "Session Handles" — resolves workspace, enforces queue invariants, invokes executor.
*   **Queue Modes**: Defines mid-run behavior via `collect`, `followup`, or `steer` modes ([11-queue-concurrency.md](./11-queue-concurrency.md)).
*   **Context Compaction**: Monitors token usage and triggers a "Compaction Step" (summarization) before the next turn if limits are exceeded.

### C. The Execution Layer (Embedded Executor)
*   **In-Process**: The agent executor runs as an async function call from the orchestrator — no container, no IPC.
*   **Workspace**: PVC-mounted project files; `AGENTS.md` loaded for system prompt.
*   **Direct Tools**: Bash, git, and file operations run as subprocesses.
*   **External MCP Tools**: Connects to configured MCP servers for API-based tools (GitHub, Slack, etc.).

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

### III. Tool Execution
Tools are invoked either as **subprocesses** (bash, git) or via **external MCP servers** (GitHub, Slack). All tool calls are:
*   **Audited**: Logged for review and debugging.
*   **Observable**: Tool start/end events are streamed to the orchestrator.

---

## 4. Implementation Guidelines (The "Claw" Checklist)

- [ ] Use **Logical Lanes** for concurrency control.
- [ ] Implement an **Embedded Executor** (single-process model).
- [ ] Mount **PVC-backed workspaces** for persistence.
- [ ] Support **Multi-Channel Input** (normalization).
- [ ] Provide a **Background Scheduler** for proactive tasks.
- [ ] Connect to **external MCP servers** for API-based tools.
- [ ] Include an **Audit Log** of all tool executions.
