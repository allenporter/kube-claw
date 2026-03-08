# Design: Queue & Concurrency Model

This document formalizes KubeClaw's queue and concurrency system. It defines the invariants that
prevent state corruption, the two-stage queue model, queue behavior modes, and transport-level
semantics for deduplication and debouncing.

Based on analysis of [OpenClaw Architecture — Part 2](https://substack.com/home/post/p-188864034).

---

## 1. Invariants

KubeClaw enforces three concurrency guarantees. Violating any of these produces the "haunted agent" failure modes: interleaved tool calls, duplicate replies, corrupted session transcripts.

| # | Invariant | Enforced By |
|---|---|---|
| **I-1** | **Single-writer per session**: Only one agent run may touch a given session lane at a time | Per-lane FIFO queue |
| **I-2** | **Global concurrency cap**: Total concurrent runs across all lanes ≤ `max_concurrent` | Global semaphore |
| **I-3** | **Deterministic mid-run behavior**: What happens when input arrives mid-run is defined by explicit policy, never undefined | Queue mode config |

---

## 2. Two-Stage Queue Model

Every inbound event (user message, heartbeat, webhook) passes through two stages before becoming an active agent run.

```
 ┌──────────────────────────────────────────────────────────┐
 │  Inbound Event                                          │
 │  (message / heartbeat / webhook / cron)                 │
 └──────────────┬───────────────────────────────────────────┘
                │
                ▼
 ┌──────────────────────────────────┐
 │  Stage 1: Per-Session Lane       │
 │  FIFO queue keyed by lane_key    │
 │  ┌─────┐ ┌─────┐ ┌─────┐       │
 │  │ ev3 │→│ ev2 │→│ ev1 │→ RUN  │
 │  └─────┘ └─────┘ └─────┘       │
 │  Guarantee: 1 active run/lane   │
 └──────────────┬───────────────────┘
                │
                ▼
 ┌──────────────────────────────────┐
 │  Stage 2: Global Throttle        │
 │  Semaphore: max_concurrent       │
 │  Caps total parallel runs        │
 └──────────────────────────────────┘
```

### UX Note
Typing indicators and "thinking..." status updates fire **on enqueue** (Stage 1), not when the run actually starts (Stage 2). This prevents the UI from appearing frozen when a run is waiting for global capacity.

### Configuration

```yaml
# adk-claw agent config
queue:
  max_concurrent: 4        # Global cap across all lanes
  mode: collect            # Default queue mode (see §3)
  debounce_ms: 1500        # Inbound debounce window (see §5)
```

---

## 3. Queue Modes

Queue modes define **what happens when a new message arrives while the agent is mid-run** in the same session lane. This is the single most impactful concurrency decision.

| Mode | Behavior | Best For |
|---|---|---|
| **`collect`** (default) | Coalesce all queued messages into **one** follow-up turn after the active run completes | Async channels (email, webhooks, group chats) |
| **`followup`** | Each message becomes its own **sequential** turn — no coalescing | Interactive chat (DMs, CLI) |
| **`steer`** | Inject queued message into the **current run** at tool boundaries | Real-time correction ("stop, do X instead") |

### Mode: `collect`

```
 Run 1 active ──────────────────────► Run 1 completes
   msg-A arrives → queued                │
   msg-B arrives → queued                │
   msg-C arrives → queued                ▼
                              ┌──────────────────────┐
                              │ Run 2: single turn    │
                              │ context = A + B + C   │
                              │ (coalesced)           │
                              └──────────────────────┘
```

**Rationale**: Reduces LLM invocations. The agent sees all pending context at once and can plan a coherent response rather than responding to each individually.

### Mode: `followup`

```
 Run 1 active ──────────────────────► Run 1 completes
   msg-A arrives → queued                │
   msg-B arrives → queued                ▼
                              Run 2 (msg-A) ─► Run 3 (msg-B)
```

**Rationale**: Preserves message ordering and individual turn boundaries. Each message gets its own full agent turn.

### Mode: `steer`

```
 Run 1 active ─── tool_1 ✓ ─── tool_2 ✓ ─── [check queue] ─── STEER
   msg-A arrives → queued                         │
                                                  ▼
                                    ┌──────────────────────────┐
                                    │ Skip remaining tool calls │
                                    │ Inject msg-A as user msg  │
                                    │ Resume with new context   │
                                    └──────────────────────────┘
```

**Rationale**: Allows real-time course correction without aborting mid-tool-call (unsafe) or waiting for a full run to finish (unresponsive).

---

## 4. Steer Semantics (Detailed Contract)

The `steer` mode requires careful coordination within the orchestrator.

### Protocol

1. New message arrives at the Gateway for a lane with an active run
2. Orchestrator enqueues the message as a **steer event** for the active run
3. At the next tool boundary, the executor checks its steer queue
4. If a steer message exists:
   - **Skip** remaining tool calls from the current assistant message
   - **Inject** the user message into conversation history
   - **Resume** the LLM loop with the new context
5. If no steer message: continue with the next tool call normally

### Safety Guarantees
- Tool calls that are **in-flight** are never aborted mid-execution
- Steering only happens at **tool boundaries** (between tool calls)
- The skipped tool calls are logged for audit purposes

### Worker Implementation Pattern

```python
async def execute_tool_calls(self, tool_calls: list[ToolCall]) -> None:
    for tool_call in tool_calls:
        result = await self.execute_tool(tool_call)
        self.append_tool_result(result)

        # Check steer queue at tool boundary
        steer_msg = self.check_steer_queue()
        if steer_msg:
            skipped = tool_calls[tool_calls.index(tool_call) + 1:]
            self.log_skipped_tools(skipped, reason="steered")
            self.inject_user_message(steer_msg)
            return  # Break out; LLM loop resumes with new context
```

---

## 5. Inbound Dedupe & Debouncing

Real channels redeliver. Humans type in bursts. Both must be handled before events reach the queue.

### 5.1 Inbound Dedupe

| Property | Value |
|---|---|
| **Key** | `(channel_id, message_id)` |
| **TTL** | 60 seconds |
| **Behavior** | If a message with the same key arrives within TTL, silently drop it |

**Why**: Channel reconnects (Discord, Slack) can replay recent messages. Without dedupe, the agent runs a duplicate turn.

### 5.2 Inbound Debouncing

| Property | Value |
|---|---|
| **Window** | `debounce_ms` (default: 1500ms) |
| **Scope** | Per-lane (same `lane_key`) |
| **Behavior** | Buffer rapid text messages; flush as single combined event after window expires |

**Bypass rules** — these message types flush immediately regardless of debounce:
- Messages with **attachments** (files, images)
- **Control commands** (e.g., `!stop`, `!reset`)
- **Steer events** (user corrections should not be delayed)

---

## 6. Lane Key Composition

The `lane_key` determines isolation boundaries. It's computed by the Gateway when an event arrives.

### Default Mode

```
lane_key = f"{channel_id}"
```

All users in the same channel share one session lane. Appropriate for group chats and public channels.

### Secure DM Mode (`per-sender`)

```
lane_key = f"{channel_id}:{author_id}"
```

Each user gets their own session lane, even within the same DM channel. Prevents context leakage between users.

### Configuration

```yaml
session:
  dm_scope: channel       # "channel" (default) or "per-sender"
```

### Binding Table Integration

The Gateway resolves `lane_key` using the Binding Table:

```
Event(channel_id, author_id)
    → BindingTable.resolve(channel_id, author_id)
    → LaneKey(channel_id[:author_id])
    → Queue.enqueue(lane_key, event)
```

This also resolves [design gap §4 (Secure DM Mode)](./10-design-gaps.md).

---

## 7. Idempotency

Side-effecting operations should support optional idempotency keys to ensure retries don't produce duplicate actions.

### Applicable Operations

| Operation | Risk Without Idempotency |
|---|---|
| Event streaming to channel | Duplicate message fragments sent to user |
| External tool call | Tool executed twice (e.g., double Slack message) |
| Final response delivery | Duplicate final responses |

The orchestrator maintains a short-lived result cache keyed by idempotency key. If a duplicate request arrives, it returns the cached result without re-executing.

---

*Based on analysis of [OpenClaw Architecture — Part 2: Concurrency, Isolation, and the Invariants That Keep Agents Sane](https://substack.com/home/post/p-188864034), 2026-03-01.*
