# Claw Core v3: Architecture & Research

This directory contains the design and implementation for the next generation of the Claw orchestration framework.

## Status: Milestone 1 — The Local Loop

A single-worker local development loop using ADK + A2A + MCP.

### Core Principles (v3)
- **A2A Protocol**: Every worker (sandbox) is an A2A-compliant agent.
- **Warm Lanes**: Persistent communication channels between Host and Sandbox.
- **Binding Table**: Just-in-Time resolution of identity to workspace/credentials.
- **Opaque Execution**: Sandbox internals are hidden; interaction is via standardized A2A Artifacts and Tasks.

---

## Getting Started (Local Development)

### Prerequisites
- Python 3.14+
- A [Google AI API key](https://aistudio.google.com/apikey) (for Gemini)

### 1. Bootstrap the environment

```bash
./script/bootstrap
source .venv/bin/activate
```

### 2. Run the local TUI

```bash
GOOGLE_API_KEY=<your-key> python3 script/local_tui.py
```

This starts the full local loop:
- **Host process** — manages the binding table, spawns workers, hosts MCP tools.
- **Worker subprocess** — runs an ADK `LlmAgent` with Gemini 2.0 Flash inside a sandboxed process.
- **TUI** — interactive terminal for sending messages and viewing streamed responses.

You can optionally point to a specific workspace directory:

```bash
GOOGLE_API_KEY=<your-key> python3 script/local_tui.py --workspace /path/to/your/project
```

### 3. Lint & Test

```bash
./script/lint
./script/test
```

> **Note:** Two A2A handshake integration tests require `GOOGLE_API_KEY` to be set and will be skipped otherwise.

---

## Architecture

```
┌─────────────────────────────────────┐
│  HOST PROCESS                       │
│  TUI → Orchestrator → SandboxMgr   │
│  MCP Server (git_info, github_api,  │
│              host_approve)          │
└──────────────┬──────────────────────┘
               │ A2A (UDS) + MCP (UDS)
┌──────────────▼──────────────────────┐
│  WORKER PROCESS (subprocess)        │
│  ADK LlmAgent (Gemini 2.0 Flash)   │
│  Loads prompt from AGENTS.md        │
│  Calls host tools via MCP           │
└─────────────────────────────────────┘
```

See `docs/design/v3-specification/` for the full specification.

### Legacy Code
Previous iterations and proof-of-concepts have been moved to `v1_legacy/`.
