# Design TODOs (Claw Core v3)

This document tracks the outstanding design gaps and tasks.

## Done

- [x] **Embedded Executor**: Agent runs in-process via `adk-coder`. See [ADR-004](../../decisions/ADR-004-embedded-executor.md).
- [x] **Binding Table**: `adk_claw/binding/table.py`
- [x] **YAML Configuration**: `config.py` — global + project merge
- [x] **Memory Store**: `memory.py` — cross-session key-value
- [x] **Discord Adapter**: `gateway/discord.py` — @mention/DM handling
- [x] **Runtime Protocol**: `runtime/` — `Runtime` protocol + `EmbeddedRuntime` with `os.chdir()` workspace isolation
- [x] **Host/Orchestrator Merge**: `ClawHost` owns routing, cancellation, and lifecycle directly

---

## Phase 1: Make It Useful

The platform provides workspace isolation, credential injection, and tool wiring.
Task-specific behavior lives in each workspace's `AGENTS.md` and skills — not in the claw.

```text
~/.adk-claw/                  ← (Tier 1) Global Brain (Persistent Persona)
  MEMORY.md                   ← Global facts ("User prefers bullet points")
  SOUL.md

/workspaces/ha-maintenance-session/ ← (Tier 2) Session Workspace
  .adk-claw.yaml              ← mcp: [github], env: [GITHUB_TOKEN]
  SESSION.md                  ← Agent scratchpad for this session
  .git/                       ← Session state tracking
  src/                        ← (Tier 3) Code target (e.g. src/core)

/workspaces/inbox-triage-session/   ← (Tier 2)
  .adk-claw.yaml              ← mcp: [gmail], env: [GMAIL_TOKEN]
```

### Platform Infrastructure (task-agnostic)

- [ ] **Per-workspace `.adk-claw.yaml`**: Load config from the workspace root, not just global/project. Workspace config specifies credentials and MCP servers.
- [ ] **Credential injection**: Pass workspace-level env vars (from config or K8s Secrets) into the Runtime before agent execution.
- [ ] **External MCP wiring**: Connect external MCP servers (GitHub, Gmail, etc.) based on workspace config → `McpToolset`.
- [ ] **Binding management**: CLI command or Discord command to bind a channel to a workspace path (e.g., `/bind /workspaces/ha-maintenance`).
- [ ] **K8s Deployment manifest**: Deployment + Secret + PVC for persistent Discord bot hosting.

### Not Platform Concerns (workspace-level, via AGENTS.md + skills)

These are examples of task-specific behavior that should **not** be hardcoded:
- Git clone/branch/PR workflows → workspace AGENTS.md
- Calendar management → workspace AGENTS.md + calendar MCP
- Triage instructions → workspace AGENTS.md

---

## Phase 2: Multi-Workspace

- [ ] **SubprocessRuntime**: Per-workspace subprocess with own CWD for parallel execution.
- [ ] **Lane Queue**: `collect`/`followup`/`steer` modes. See [11-queue-concurrency.md](./11-queue-concurrency.md).
- [ ] **Config-driven runtime selection**: `.adk-claw.yaml` specifies which runtime to use.

---

## Phase 3: Production

- [ ] **KubeJobRuntime**: K8s Job + PVC per workspace.
- [ ] **The Pulse**: Cron-based proactive triggers (daily triage, monitoring).
- [ ] **A2A Adapter**: Expose the host as an A2A-compliant agent.
- [ ] **Security policy per channel**: Configure `permission_mode` per workspace/channel.
- [ ] **Auth profile management**: Scoped credentials injected per workspace from a secure store.
