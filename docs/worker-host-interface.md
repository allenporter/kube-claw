# Claw-RPC: Worker-Host Interface Specification

This document defines the communication protocol between the **Claw Host** (Gateway/Orchestrator) and the **Claw Worker** (Sandboxed Agent Runtime).

## 1. Overview

The interface follows a bidirectional JSON-RPC 2.0 pattern. In the Claw Core v3 architecture:
- **Host (Server/Client)**: Manages multi-channel I/O, identity, and sandbox lifecycle.
- **Worker (Client/Server)**: Runs the LLM reasoning loop and executes tools.

### Transport
- **Primary**: Unix Domain Socket (UDS) at `/tmp/claw.sock` inside the sandbox.
- **Secondary/Standard**: Stdin/Stdout for simple transient runs or local development.

---

## 2. Claw-RPC Methods

### A. Host-to-Worker (Inbound Intents)

The Host pushes user messages or system triggers to the Worker.

#### `input.push`
Sent when a new message arrives from a channel (Discord, WhatsApp, etc.).
```json
{
  "jsonrpc": "2.0",
  "method": "input.push",
  "params": {
    "message_id": "msg_123",
    "content": "Fix the bug in the auth module",
    "author": {"id": "user_456", "name": "Alice"},
    "timestamp": "2023-10-27T10:00:00Z"
  }
}
```

#### `lifecycle.shutdown`
Graceful shutdown request. Worker must checkpoint state before exiting.
```json
{
  "jsonrpc": "2.0",
  "method": "lifecycle.shutdown",
  "params": { "reason": "preempted" }
}
```

### B. Worker-to-Host (Outbound Actions)

The Worker streams its reasoning process and requests tool execution or approval.

#### `output.stream` (Notification)
Streaming thoughts or tokens back to the user channel.
```json
{
  "jsonrpc": "2.0",
  "method": "output.stream",
  "params": {
    "type": "thought",
    "content": "I need to check the logs first..."
  }
}
```

#### `tool.call` (Request)
Request to execute a tool. The host processes this and returns the result.
```json
{
  "jsonrpc": "2.0",
  "method": "tool.call",
  "id": "call_abc",
  "params": {
    "tool": "bash",
    "arguments": {"command": "ls -R"},
    "require_approval": false
  }
}
```

#### `tool.approval_request` (Request)
Explicitly asking the host to prompt the user for permission. Returns `{"approved": true/false}`.
```json
{
  "jsonrpc": "2.0",
  "method": "tool.approval_request",
  "id": "req_789",
  "params": {
    "tool": "bash",
    "arguments": {"command": "rm -rf /node_modules"},
    "risk_level": "high"
  }
}
```

### C. Control & Heartbeats

#### `status.heartbeat` (Notification)
Worker sends periodically to prove it's still alive.
```json
{
  "jsonrpc": "2.0",
  "method": "status.heartbeat",
  "params": { "status": "thinking", "cpu_usage": 0.45 }
}
```

---

## 3. Sandboxed Agent Runtime (agent_entrypoint.py)

The entrypoint is the "Brain" inside the container. It follows this lifecycle:

### Phase 1: Initialization
1.  **Environment Check**: Verify mount points (`/workspace/project`, `/workspace/session`).
2.  **Identity Loading**: Read `IDENTITY.json` injected by Host.
3.  **Memory Load**:
    -   Parse `CLAUDE.md` from project root (Rules of Engagement).
    -   Load `.claude/session.json` (Last known conversation state).
4.  **RPC Connect**: Establish connection to the Host via UDS.

### Phase 2: The Reasoning Loop
1.  Wait for `input.push` via RPC.
2.  Trigger LLM Turn:
    -   Format Prompt: Context (CLAUDE.md) + History + New Message.
    -   Stream tokens via `output.stream`.
    -   Handle Tool Calls:
        -   If local (e.g., `read_file`): Execute directly.
        -   If host-proxied (e.g., `send_email`): Send `tool.call` RPC and await response.
3.  Evaluate if task is complete.

### Phase 3: Final Turn & Checkpointing
When the loop finishes or a `lifecycle.shutdown` is received:
1.  **Summarize**: Create a "Diary Entry" of what was accomplished.
2.  **Checkpoint**: Write summary and compressed history to `.claude/session.json`.
3.  **Sync**: Ensure `CLAUDE.md` is updated if the worker learned new project rules.
4.  **Exit**: Send `lifecycle.exit_ready` and terminate.

---

## 4. Resilience & Recovery

-   **Connection Drop**: If the RPC socket closes unexpectedly, the Worker enters **Hibernation**. It persists state to `/workspace/session` and waits for a SIGTERM.
-   **Re-attachment**: If the Host restarts, it checks `/workspace/session`. If a checkpoint exists, it spawns a new Worker which resumes from the last known state.
-   **The Diary Model**: Every 5 turns, the Worker automatically writes a "Work Log" to `.claude/diary.md`. This ensures that even in a catastrophic failure, a human or a new agent can reconstruct the "Why" behind recent changes.
