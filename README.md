# adk-claw

An AI agent orchestrator built on [Google ADK](https://google.github.io/adk-docs/) and [adk-coder](https://github.com/allenporter/adk-coder).

## Architecture

```
┌──────────────────────────────────────────────┐
│  HOST PROCESS (ClawHost)                     │
│  Config (.adk-claw.yaml) → BindingTable      │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ Embedded Orchestrator                  │  │
│  │ adk-coder build_runner()               │  │
│  │   → LlmAgent + SqliteSessionService   │  │
│  │   → EventsCompaction + SecurityPlugin  │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Channel Adapters:                           │
│    ShellAdapter (TUI)  DiscordAdapter        │
│    GithubAdapter (PRs)                       │
└──────────────────────────────────────────────┘
```

The host runs an embedded ADK agent in-process — no subprocesses, no RPC.
Sessions persist via SQLite (`~/.adk/sessions.db`) with automatic compaction.

## Quickstart

### Prerequisites
- Python 3.14+
- A [Google AI API key](https://aistudio.google.com/apikey)
- [adk-coder](https://github.com/allenporter/adk-coder) installed

### 1. Bootstrap

```bash
./script/bootstrap
source .venv/bin/activate
```

### 2. Run the TUI

```bash
GOOGLE_API_KEY=<your-key> python3 script/local_tui.py
```

Optionally point to a workspace:

```bash
GOOGLE_API_KEY=<your-key> python3 script/local_tui.py --workspace /path/to/project
```

The TUI connects to `ClawHost`, which routes messages through the embedded
orchestrator. The agent has access to adk-coder's tools (bash, file editing,
web search, etc.) and loads project instructions from `AGENTS.md`.

### 3. Configuration (optional)

Create `.adk-claw.yaml` in your project root:

```yaml
agent:
  model: gemini-2.5-pro
  permission_mode: auto

queue:
  mode: collect
  debounce_ms: 1500
```

Global config at `~/.adk-claw/config.yaml` is merged with project config
(project settings take precedence).

### 4. Lint & Test

```bash
./script/lint
./script/test
```

### 5. Discord Bot (optional)

Run the agent as a Discord bot that responds to @mentions and DMs.

**Setup:**

1. Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Enable **Message Content Intent** under Bot → Privileged Gateway Intents
3. Invite the bot to your server with `bot` + `applications.commands` scopes
4. Copy the bot token

**Run:**

```bash
GOOGLE_API_KEY=<your-key> DISCORD_TOKEN=<bot-token> python3 script/discord_bot.py --workspace /tmp/workspace/
```

The bot will respond when @mentioned in a channel or sent a DM.
Messages are routed through the same orchestrator as the TUI.

### 6. GitHub PR Bot (optional)

Run the agent as a GitHub bot that responds to comments on a specific PR.

**Setup:**

1. Install the [GitHub CLI (gh)](https://cli.github.com/)
2. Authenticate: `gh auth login`
3. Ensure the bot has access to the repository

**Run:**

```bash
GOOGLE_API_KEY=<your-key> python3 script/github_bot.py --pr <pr-number> --workspace /tmp/workspace
```

The bot will poll the PR for comments (every 60s by default) and respond to
allowed authors. It uses the `gh` CLI to fetch comments and post replies.

## Project Structure

```
adk_claw/
  config.py          # YAML config loader (global + project)
  memory.py          # Cross-session key-value memory store
  domain/models.py   # Core domain types (InboundMessage, OrchestratorEvent)
  binding/           # Identity → workspace resolution
  gateway/           # Channel adapters (Discord, etc.)
  host/host.py       # Control plane — config, bindings, routing, cancellation
  runtime/           # Agent execution backends (embedded, subprocess, K8s Job)
  mcp/               # MCP server tools (git_info, github_api, etc.)
```

## Documentation

See `docs/` for design specs:
- `docs/design/v3-specification/` — Full architecture specification
- `docs/decisions/` — Architectural Decision Records (ADRs)
- `docs/research/` — Background research on agent frameworks
