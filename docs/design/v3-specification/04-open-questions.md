# Architectural Questions & Open Design Decisions

## 1. Orchestrator Lifecycle
These questions pertain to the orchestrator's session management and agent execution.

1.  **Session Longevity (Warm vs. Cold)**: Should a session keep the agent context alive for multiple turns, or should it start fresh after every task?
    *   *Implication*: A warm session allows for faster follow-up messages but consumes more memory.
2.  **Tool Execution Authority**: Should the agent execute tools locally and just log results, or should the orchestrator gate high-risk commands?
    *   *Recommendation*: Local execution for low latency, with policy-based approval for high-risk commands (see `CustomPolicyEngine` modes: `ask`, `auto`, `plan`).
3.  ✅ **Input Interruption**: What happens if a user sends a follow-up ("Oh, also fix X") while the agent is already processing?
    *   *Resolved*: Formalized via queue modes (`collect`, `followup`, `steer`). See [11-queue-concurrency.md](./11-queue-concurrency.md).
4.  **The "Final Turn" Trigger**: When does the agent checkpoint and exit?
    *   *Options*: LLM-driven completion, orchestrator-driven shutdown, or inactivity timeout.

## 2. Notification & Lifecycle Management
5.  **Persistence of Tracking**: Should the active session tracking be moved to a persistent store (e.g., SQLite/Redis)? This ensures that if the host crashes, it can resume monitoring and notifying for runs that were already active.
6.  **Granular Feedback**: Should the orchestrator provide granular "In-Progress" feedback (like tool usage or partial logs) to the channel, or only final results?

## 3. Identity, Secrets & Networking
7.  **Multi-Project Context**: How should the system handle a user switching projects mid-conversation? Should the Binding Table be strictly one-to-one per channel, or should the agent be able to "checkout" different workspaces dynamically?
8.  ✅ **Auth Injection**: Should we favor **Direct Injection** (Env Vars) for performance or **MCP-proxied** access for high-security secrets?
    *   *Resolved*: Hybrid model. CLI-heavy tools get Direct Injection; API-heavy tools are accessed via external MCP servers.
9.  **Network Policy**: Should the agent pod have access to the public internet by default, or should we use a whitelisted proxy to audit outbound traffic?

## 4. Cross-Agent Communication
10. **Cross-Agent Collaboration**: How can Claw agents communicate with other specialized agents (e.g., a "Security Agent" or a "Cloud Provisioning Agent")?
11. **A2A as External API**: Should KubeClaw expose an A2A endpoint so external agents can send tasks? (Answer: yes, as a ChannelAdapter — see [12-agent-core.md](./12-agent-core.md))
