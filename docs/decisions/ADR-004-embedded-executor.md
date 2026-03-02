# ADR-004: Embedded Executor Architecture

## Status
Accepted

## Context
The original Claw Core v3 design specified a **two-container pod** with the Host (Gateway/Orchestrator) and Worker (Sandboxed Agent) communicating via:
- **A2A Protocol** over a Unix Domain Socket (`/rpc/worker.sock`) for orchestration
- **MCP Protocol** over a second UDS (`/rpc/mcp.sock`) for tool dispatch

After reviewing [OpenClaw's actual architecture](https://docs.openclaw.ai/concepts/architecture), we discovered that OpenClaw runs the agent **embedded in the Gateway process** via `runEmbeddedPiAgent()`. There is no separate container, no IPC protocol, and no handshake — the agent is an async function call.

Our own codebase already trends this way: `ClawAgentExecutor` runs ADK's `Runner.run_async()` in-process using the `a2a-python` SDK's in-memory event queue.

The two-container + dual-socket design adds significant complexity (handshake sequences, transport management, socket lifecycle, event bridging) without meaningful security benefit — the LLM API key and tool credentials are accessible regardless of container boundaries.

## Decision
We adopt an **Embedded Executor** architecture:

1. **Single process**: Gateway, Orchestrator, and Agent Executor run in one process.
2. **No SandboxManager**: No container lifecycle management. K8s Pod-level isolation is sufficient.
3. **A2A dropped internally**: `InboundMessage` / `OrchestratorEvent` domain models replace A2A for internal orchestration. A2A is retained only as a potential *external-facing API* for inter-agent communication.
4. **MCP for external tools only**: `McpToolset` connects to *external* MCP servers (GitHub, Slack, etc.) when configured. No in-process MCP server for "hydration."
5. **Queue invariants preserved**: Lane-based serialization, global throttle, and queue modes remain unchanged.

## Consequences

### Positive
- **Dramatically simpler**: Eliminates ~3 design docs, 2 protocols, and 2 transport layers
- **Lower latency**: No container startup, no socket handshake, no serialization/deserialization overhead
- **Matches reality**: The codebase already runs the executor in-process
- **Easier testing**: No socket infrastructure needed for unit tests

### Negative
- **No container-level isolation**: Agent code runs in the same process as the gateway. Mitigated by K8s Pod isolation and tool-level sandboxing (subprocess for bash).
- **Reduced future flexibility**: Adding container isolation later would require significant rearchitecting. However, the current design never actually used it.

## Supersedes
- **ADR-001** (A2A Protocol): A2A is no longer used for internal host-worker communication
- **ADR-003** (Hybrid MCP/A2A Tooling): Dual-socket model dropped; MCP is external-only
