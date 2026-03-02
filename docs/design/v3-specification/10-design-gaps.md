# Design Gaps & Remaining Work

This document captures open design areas identified by comparing the KubeClaw v3 architecture against insights from the [OpenClaw Architecture blog post](https://theagentstack.substack.com/p/openclaw-architecture-part-1-control). Each section describes a concept that OpenClaw supports but KubeClaw has not yet formalized.

---

## 1. ✅ Queue Behavior Modes

**Status**: Resolved — see [11-queue-concurrency.md](./11-queue-concurrency.md) for the full design covering three queue modes (`collect`, `followup`, `steer`), two-stage queue model, and steer semantics.

---

## 2. Heartbeat as Input Trigger

**Problem**: Our `status.heartbeat` ([03-worker-host-rpc.md](./03-worker-host-rpc.md)) is Worker→Host liveness signaling. It does _not_ trigger agent reasoning.

**OpenClaw's Approach**: Host→Agent heartbeats are actual **input events** that trigger full agent turns. The agent either performs useful work or responds with `HEARTBEAT_OK`. Default cadence: 30 minutes.

**Our Gap**: The Pulse system ([01-high-level-spec.md §3.III](./01-high-level-spec.md)) covers Cron-based scheduling, but lacks a protocol-level heartbeat input. We should consider adding a Host→Worker `heartbeat.trigger` RPC method that the Pulse can use to wake idle agents for periodic checks.

**Status**: Open

---

## 3. Hook System (Filesystem-Discovered Automation)

**Problem**: We have no mechanism for workspace-level event automation.

**OpenClaw's Approach**: Hooks are event-driven scripts discovered from multiple directories:
- **Workspace hooks**: Agent-specific (in the workspace)
- **Managed hooks**: Admin-managed
- **Bundled hooks**: Built into the system

Hooks fire on events like `pre_tool_use`, `post_tool_use`, `on_message`, etc.

**Our Gap**: Our PreToolUse/PreCompact hooks are referenced in [deep-research.md §5](../../research/deep-research.md) but never formalized in the v3 spec. We need a hook discovery and execution model — especially for security sanitization (e.g., unsetting API keys before `bash` runs).

**Status**: Open

---

## 4. ✅ Secure DM Mode (Per-Sender Isolation)

**Status**: Resolved — see [11-queue-concurrency.md §6](./11-queue-concurrency.md) for lane key composition design. Default `lane_key = channel_id`; secure DM mode uses `lane_key = channel_id:author_id`, configurable via `session.dm_scope`.

---

## 5. Protocol Versioning

**Problem**: Our A2A/MCP handshakes don't include version negotiation.

**OpenClaw's Approach**: The WebSocket `connect` frame includes protocol version. Client and server negotiate capabilities at connection time.

**Our Gap**: The Worker `bootstrap` handshake ([09-worker-entrypoint.md](./09-worker-entrypoint.md)) sends identity, workspace, and LLM config but no protocol version. As the A2A and MCP interfaces evolve, we risk breaking backward compatibility with running workers during rolling upgrades.

**Recommendation**: Add a `protocol_version` field to the `bootstrap` message and define a version negotiation strategy.

**Status**: Open

---

## 6. Security Audit Tooling

**Problem**: No built-in way to surface dangerous configurations.

**OpenClaw's Approach**: Provides `openclaw security audit` CLI command that checks for:
- Exposed gateway without token auth
- DM mode settings
- Sandbox bypass risks
- Dangerous skill installations

**Our Gap**: We have a sandbox boundary spec TODO in [05-design-todos.md §4](./05-design-todos.md), but no CLI-level audit tool. A `kube-claw security audit` command should check:
- Network policies on agent pods
- PVC mount permissions
- Exposed MCP/A2A sockets
- Auth profile scoping
- Direct-mount credential exposure risk

**Status**: Open — depends on sandbox boundary specification

---

*Created from review of [OpenClaw Architecture — Part 1](https://theagentstack.substack.com/p/openclaw-architecture-part-1-control), 2026-03-01.*
