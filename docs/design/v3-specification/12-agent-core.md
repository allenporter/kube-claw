# Claw Core v3: Agent Core — Reusing adk-coder as the Embedded Executor

This document specifies how KubeClaw's embedded executor ([ADR-004](../../decisions/ADR-004-embedded-executor.md)) will leverage the existing `adk-coder` codebase as its agent core — the "brain" that does the actual coding work.

---

## 1. The Analogy

OpenClaw calls `runEmbeddedPiAgent()` which invokes `pi-agent-core` — their full-featured LLM SDK with tools, plugins, and session management. KubeClaw should do the same with `adk-coder`:

| Layer | OpenClaw | KubeClaw |
|---|---|---|
| **Agent Core** | `pi-agent-core` (embedded library) | `adk-coder` agent factory + tools |
| **Invocation** | `runEmbeddedPiAgent()` | `build_adk_agent()` → `Runner.run_async()` |
| **Tools** | pi-agent built-in tools | `ls`, `cat`, `edit_file`, `bash`, `grep`, etc. |
| **Sub-Agents** | pi plugins | `explore_codebase`, `design_architecture`, `review_work` |
| **Skills** | — | `SkillToolset` (Markdown-based extensible skills) |
| **Security** | sandboxed execution | `CustomPolicyEngine` (`ask`/`auto`/`plan` modes) |
| **Session** | `SessionManager` (JSONL) | `SqliteSessionService` (SQLite) |
| **Compaction** | manual summarization | `EventsCompactionConfig` (auto at token threshold) |
| **Retry / Rate Limiting** | built-in | `AdkRetryGemini` (parses Google API retry headers) |
| **Settings** | `openclaw.json` | `~/.adk/settings.json` + project-local overrides |

---

## 2. What adk-coder Already Provides

### A. Agent Builder (`agent_factory.py`)
`build_adk_agent()` creates a fully-configured `LlmAgent`:
- Loads workspace instructions from `AGENTS.md`, `GEMINI.md`, or `CLAUDE.md`
- Configures `BuiltInPlanner` with `ThinkingConfig` (thinking budget)
- Wraps the model in `AdkRetryGemini` for rate-limit resilience
- Discovers and attaches `SkillToolset` from workspace and built-in skills
- Respects project-local settings (model override, permission mode)

### B. Tool Suite (`tools.py`)
12 production-hardened tools with output truncation, metadata decorators, and security annotations:

| Tool | Category | Policy |
|---|---|---|
| `ls`, `cat`, `read_many_files`, `grep` | Read | Allow |
| `write_file`, `edit_file` | Write | Confirm |
| `bash` | Shell | Confirm (with safe-command allowlist) |
| `explore_codebase` | Sub-Agent | Allow |
| `design_architecture`, `review_work` | Sub-Agent | Allow |
| `run_subagent` | Sub-Agent | Allow |
| `manage_todo_list` | Session State | Allow |

### C. Security Plugin (`policy.py`)
Three permission modes:
- **ask**: Confirm destructive tools (default)
- **auto**: Allow everything (for CI/automation)
- **plan**: Read-only (agent can only explore)

Session-level granular permissions (e.g., "always allow `bash git status`").

### D. Session & Compaction
- `SqliteSessionService` for persistent sessions across runs
- `EventsCompactionConfig`: Auto-summarizes history every N turns or at token threshold
- Project-aware session IDs via `find_project_root()` + `get_project_id()`

### E. Settings (`settings.py`)
Layered JSON config: `~/.adk/settings.json` (global) merged with `<project>/.adk/settings.json` (local overrides).

---

## 3. Integration Architecture

```
┌─────────────────────────────────────────────────────┐
│  KubeClaw Process                                   │
│                                                     │
│  Gateway ──► Lane Queue ──► Orchestrator            │
│                                │                    │
│                     ┌──────────▼──────────┐         │
│                     │  adk-coder Agent Core │         │
│                     │                     │         │
│                     │  build_adk_agent()  │         │
│                     │  ├─ LlmAgent        │         │
│                     │  ├─ Tools (12)      │         │
│                     │  ├─ SkillToolset    │         │
│                     │  ├─ PolicyEngine    │         │
│                     │  └─ Planner         │         │
│                     │                     │         │
│                     │  Runner.run_async() │         │
│                     │  ├─ Stream events   │         │
│                     │  └─ Summarize calls │         │
│                     └─────────────────────┘         │
│                                │                    │
│  Channels ◄── Stream ◄────────┘                     │
│  Binding Table │ SqliteSessionService               │
│  PVC Workspace                                      │
└─────────────────────────────────────────────────────┘
```

### Integration Points

| KubeClaw Component | Connects To | How |
|---|---|---|
| **Orchestrator** | `build_adk_agent()` | Import and call; agent core is a library |
| **Lane Queue** | `Runner` | Orchestrator calls `runner.run_async()` per dequeued message |
| **Gateway** | `summarize_tool_call/result` | Use adk-coder's summarizers for human-readable streaming |
| **Binding Table** | `SqliteSessionService` | Session ID = `f"{lane_key}:{workspace_id}"` |
| **PVC Workspace** | `find_project_root()` | Workspace path passed to agent; tools operate on it |
| **Channel Policy** | `CustomPolicyEngine` | Mode per-channel from KubeClaw config (not UI prompts) |

---

## 4. Extraction Strategy

Two viable approaches:

### Option A: Shared Library (Recommended)

Extract the reusable core of `adk-coder` into a package (e.g., `adk-coding-agent`):

```
adk-coding-agent/          # New shared package
├── agent.py               # build_adk_agent(), SUPERVISOR_INSTRUCTION
├── tools.py               # 12 tools (unchanged)
├── policy.py              # PolicyEngine (unchanged)
├── retry.py               # AdkRetryGemini (unchanged)
├── summarize.py           # Tool call summarizers
├── skills/                # Built-in skills
│   ├── _skills.py
│   └── builtin/
│       ├── feature-dev/
│       └── skill-creator/
└── settings.py            # Layered config loader

adk-coder/                   # CLI stays thin
├── main.py                # Click CLI, TUI
├── tui.py                 # Textual UI
└── depends on: adk-coding-agent

kube-claw/                 # Orchestrator
├── orchestrator/
├── gateway/
└── depends on: adk-coding-agent
```

**Pros**: Clean separation. Both projects share the same agent logic. No duplication.
**Cons**: Requires a separate package release cycle.

### Option B: Direct Dependency

KubeClaw depends on `adk-coder` as a library and imports from it directly:

```python
# kube_claw/orchestrator/orchestrator.py
from adk_coder.agent_factory import build_adk_agent
from adk_coder.summarize import summarize_tool_call
```

**Pros**: Zero extraction work. Immediate reuse.
**Cons**: Couples KubeClaw to adk-coder's CLI-specific code (Click, Textual). Package name is misleading.

---

## 5. Policy Adaptation for Headless Execution

In `adk-coder`, the `SecurityPlugin` prompts the **user via TUI** for confirmation. In KubeClaw (headless), this needs adaptation:

| adk-coder Mode | KubeClaw Equivalent | Behavior |
|---|---|---|
| `ask` | Channel confirm | Send confirmation request to user's channel; block until reply |
| `auto` | Fully autonomous | Allow all tools (for trusted workspaces) |
| `plan` | Read-only | Agent can explore but not modify (triage mode) |

The `CustomPolicyEngine` is already decoupled from the TUI — it returns `PolicyOutcome.CONFIRM`. KubeClaw's orchestrator interprets this by routing the confirmation to the user's channel instead of the terminal.

---

## 6. Configuration — Extending Settings for KubeClaw

`adk-coder`'s settings system supports two fields today: `default_model` and `permission_mode`. KubeClaw extends this with queue and channel config:

```yaml
# .kube-claw.yaml (project-level) or ~/.kube-claw/config.yaml (global)

agent:
  model: gemini-3-flash-preview
  thinking_budget: 1024
  permission_mode: ask       # ask | auto | plan
  compaction:
    interval: 5
    token_threshold: 50000

queue:
  mode: collect              # collect | followup | steer
  debounce_ms: 1500
  max_concurrent: 4

session:
  dm_scope: channel          # channel | per-sender
  store: sqlite              # sqlite | jsonl

workspace:
  instruction_files:         # Checked in order
    - AGENTS.md
    - GEMINI.md
    - CLAUDE.md

channels:
  discord:
    token: ${DISCORD_TOKEN}
    trigger_pattern: "@Assistant"

mcp:
  servers:
    - name: github
      command: ["npx", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_TOKEN: ${GITHUB_TOKEN}
```

---

## 7. What Changes in KubeClaw

### Replace
- `kube_claw/worker/executor.py` → Import `build_adk_agent()` from agent core
- `kube_claw/worker/` directory → No longer needed as separate module
- `kube_claw/sandbox/` directory → Drop entirely (no container lifecycle)

### Simplify
- `kube_claw/orchestrator/orchestrator.py` → Remove sandbox provisioning, UDS transport, A2A bridging. Call `Runner.run_async()` directly
- `kube_claw/domain/models.py` → Drop `SandboxStatus`. Keep `InboundMessage`, `OrchestratorEvent`, `WorkspaceContext`

### Keep
- `kube_claw/binding/` → Binding Table stays
- `kube_claw/mcp/` → Only if used for external MCP server config
- `kube_claw/orchestrator/base.py` → Orchestrator interface stays
- `kube_claw/domain/models.py` → Core domain models stay

---

## 8. Open Questions

1. **Package name**: `adk-coding-agent`? `adk-agent-core`? Or just keep importing from `adk-coder`?
2. **YAML vs JSON settings**: `adk-coder` uses JSON today. YAML is more readable for nested config. Migrate or support both?
3. **Session DB sharing**: Should KubeClaw's `SqliteSessionService` share the same `~/.adk/sessions.db` as `adk-coder`, or use a separate store?
