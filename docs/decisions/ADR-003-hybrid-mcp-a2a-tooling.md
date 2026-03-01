# ADR-003: Hybrid Tool Dispatch via MCP and A2A

## Status
Proposed

## Context
The "Claw Core v3" architecture requires a way for sandboxed workers to execute tools. Some tools (e.g., `bash`, `git`) should run locally within the sandbox for performance and direct filesystem access. Other tools (e.g., Slack, GitHub API) require high-security credentials that should never enter the sandbox.

Previous designs suggested a custom JSON-RPC "Proxy" mechanism, but this lacks standardization and creates tight coupling between the worker and the host's tool implementation.

## Decision
We will adopt a **Dual-Protocol Hybrid Tooling Model**:

1.  **A2A (Agent-to-Agent) for Orchestration**: The Host and Worker communicate high-level tasks, state transitions, and user interruptions via the A2A protocol over a Unix Domain Socket (UDS).
2.  **MCP (Model Context Protocol) for Tooling**: The Host will act as an **MCP Server** for sensitive/proxied tools. The Worker (running an ADK Agent) will act as an **MCP Client**.
3.  **ADK (Agent Development Kit) for Execution**: The Worker uses the ADK framework to manage its internal reasoning loop and dispatch tool calls.
    *   **Local Tools**: Registered as native ADK Skills.
    *   **Proxied Tools**: Discovered and executed via the Host's MCP Socket.

## Technical Details

### Connectivity
Two separate Unix Domain Sockets will be mounted into the sandbox via a shared `emptyDir` volume:
- `/rpc/worker.sock`: A2A Control Plane (Host = Client, Worker = Server).
- `/rpc/mcp.sock`: MCP Tool Plane (Host = Server, Worker = Client).

### Security (The "Hydration" Principle)
- When a worker calls an MCP tool, the Host receives the request over the UDS.
- Because the UDS is unique to that sandbox instance, the Host can look up the `WorkspaceContext` (and associated secrets) in its `BindingTable`.
- The Host "hydrates" the call with the actual API keys and executes it, returning only the result to the worker.

## Consequences

### Positive
- **Standardization**: Uses MCP, a growing industry standard for tool interoperability.
- **Security**: Credentials remain physically isolated on the Host.
- **Portability**: Any MCP-compliant tool server can be plugged into the Claw Core Host.
- **Native ADK Support**: Leverages ADK's built-in capabilities for tool discovery and execution.

### Negative
- **Complexity**: Managing two separate protocol state machines (A2A and MCP) over two sockets.
- **Overhead**: Every proxied tool call requires a context switch and IPC.
