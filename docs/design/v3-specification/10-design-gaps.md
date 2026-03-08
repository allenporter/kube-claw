# Design Gaps & Remaining Work

This document captures open design areas identified by comparing the KubeClaw architecture against insights from the [OpenClaw Architecture blog post](https://theagentstack.substack.com/p/openclaw-architecture-part-1-control).

---

## 1. ✅ Queue Behavior Modes

**Status**: Resolved — see [11-queue-concurrency.md](./11-queue-concurrency.md) for the full design covering three queue modes (`collect`, `followup`, `steer`), two-stage queue model, and steer semantics.

---

## 2. Heartbeat as Input Trigger

**Problem**: Heartbeats should be actual **input events** that trigger agent reasoning, not just liveness checks.

**OpenClaw's Approach**: Host→Agent heartbeats trigger full agent turns. The agent either performs useful work or responds with `HEARTBEAT_OK`. Default cadence: 30 minutes.

**Gap**: The Pulse system ([01-high-level-spec.md §3.III](./01-high-level-spec.md)) covers Cron-based scheduling, but lacks a protocol-level heartbeat input. A `heartbeat.trigger` event type should be supported by the orchestrator so the Pulse can wake idle agents for periodic checks.

**Status**: Open

---

## 3. Hook System (Filesystem-Discovered Automation)

**Problem**: No mechanism for workspace-level event automation.

**OpenClaw's Approach**: Hooks are event-driven scripts discovered from multiple directories:
- **Workspace hooks**: Agent-specific (in the workspace)
- **Managed hooks**: Admin-managed
- **Bundled hooks**: Built into the system

Hooks fire on events like `pre_tool_use`, `post_tool_use`, `on_message`, etc.

**Gap**: We need a hook discovery and execution model — especially for security sanitization (e.g., unsetting API keys before `bash` runs).

**Status**: Open

---

## 4. ✅ Secure DM Mode (Per-Sender Isolation)

**Status**: Resolved — see [11-queue-concurrency.md §6](./11-queue-concurrency.md) for lane key composition design. Default `lane_key = channel_id`; secure DM mode uses `lane_key = channel_id:author_id`, configurable via `session.dm_scope`.

---

## 5. Protocol Versioning

**Problem**: As internal APIs evolve, we risk breaking backward compatibility during rolling upgrades.

**Recommendation**: Add a `protocol_version` field to configuration and define a version negotiation strategy for external MCP server connections.

**Status**: Open

---

## 6. Security Audit Tooling

**Problem**: No built-in way to surface dangerous configurations.

**OpenClaw's Approach**: Provides `openclaw security audit` CLI command that checks for:
- Exposed gateway without token auth
- DM mode settings
- Dangerous skill installations

**Gap**: A `adk-claw security audit` command should check:
- Network policies on agent pods
- PVC mount permissions
- Auth profile scoping
- Permission mode configuration

**Status**: Open

---

*Created from review of [OpenClaw Architecture — Part 1](https://theagentstack.substack.com/p/openclaw-architecture-part-1-control), 2026-03-01.*
