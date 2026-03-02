# Architectural Questions & Open Design Decisions

## 1. Claw-RPC & Worker Lifecycle
These questions pertain to the interface between the **Host** (Gateway) and the **Worker** (Sandbox).

1.  ✅ **RPC Transport in Kubernetes**: Should we use **Unix Domain Sockets (UDS)** mounted via `emptyDir` or **TCP/HTTP**?
    *   *Resolved*: UDS via `emptyDir`. See [06-uds-k8s-design.md](./06-uds-k8s-design.md).
2.  **Session Longevity (Warm vs. Cold)**: Should a single `!run` start a long-lived "Warm Lane" where the worker stays alive for multiple turns, or should it exit after every task?
    *   *Implication*: A warm lane allows for faster follow-up messages but consumes more resources.
3.  **Tool Execution Authority**: Does the Worker execute tools locally and just log results, or does it request permission via RPC for every call?
    *   *Recommendation*: Local execution for low latency, with Host-side "Sanity Check" or "Approval" for high-risk commands.
4.  ✅ **Input Interruption**: What happens if a user sends a follow-up ("Oh, also fix X") while the worker is already processing?
    *   *Resolved*: Formalized via queue modes (`collect`, `followup`, `steer`). See [11-queue-concurrency.md](./11-queue-concurrency.md).
5.  **The "Final Turn" Trigger**: When does the worker checkpoint and exit?
    *   *Options*: LLM-driven completion, Host-driven shutdown, or inactivity timeout.

## 2. Notification & Lifecycle Management
6.  **Polling vs. Watching**: Should we move to a **Kubernetes Watcher** (event-driven) instead of polling? This would reduce notification latency to near-zero and be more efficient for many concurrent jobs.
7.  **Persistence of Tracking**: Should the `active_jobs` tracking be moved to a persistent store (e.g., SQLite/Redis)? This ensures that if the Gateway crashes, it can resume monitoring and notifying for jobs that were already running.
8.  **Sandbox "Call Home"**: Do you want the Sandbox container itself to push updates (e.g., via a webhook or IPC socket back to the Gateway) to provide more granular "In-Progress" feedback (like tool usage or partial logs)?

## 3. Identity, Secrets & Networking
9.  **Multi-Project Context**: How should the system handle a user switching projects mid-conversation? Should the "Binding Table" be strictly one-to-one per channel, or should the agent be able to "checkout" different workspaces dynamically?
10. ✅ **Auth Injection (The Hydration Model)**: Should we favor **Direct Injection** (Env Vars) for performance or **Host Proxying** (RPC) for high-security secrets?
    *   *Resolved*: Hybrid model adopted. CLI-heavy tools get Direct Injection; API-heavy/High-risk tools are Host-Proxied via MCP. See [07-tool-schemas.md](./07-tool-schemas.md) and [ADR-003](../../decisions/ADR-003-hybrid-mcp-a2a-tooling.md).
11. **Network Namespace Isolation**: For a "Hacker Assistant," should the sandbox have access to the public internet by default, or should we use a **Whitelisted Proxy** on the Host to log and audit all outbound research/scanning traffic?
12. **Browser Isolation**: Should the sandbox run a local headless browser (heavy) or request a **Browser-as-a-Service** RPC call to the Host (lightweight but complex state)?

## 4. Agent-to-Agent (A2A) Protocol
13. **Cross-Agent Collaboration**: How can Claw agents communicate with other specialized agents (e.g., a "Security Agent" or a "Cloud Provisioning Agent")?
14. ✅ **A2A Integration**: Is the [A2A Protocol](https://a2a-protocol.org/) a suitable standard for Claw?
    *   *Resolved*: A2A adopted as the primary Host-Worker protocol. See [ADR-001](../../decisions/ADR-001-A2A-Protocol.md).
