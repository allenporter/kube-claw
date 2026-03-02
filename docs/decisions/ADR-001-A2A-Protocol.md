# ADR-001: Adoption of A2A Protocol for Host-Worker Communication

## Status
Superseded by [ADR-004: Embedded Executor Architecture](./ADR-004-embedded-executor.md)

> **Note**: A2A is no longer used for internal host-worker communication. It may be used in the future as an external-facing API for inter-agent interoperability.

## Context
Claw Core v3 requires a robust, bidirectional communication protocol between the **Host** (orchestrator) and the **Worker** (sandboxed agent). Initially, we considered a custom JSON-RPC schema ("Claw-RPC"). However, we need to handle:
-   Multi-turn conversations.
-   Streaming "thoughts" and tokens.
-   Task state transitions (Working, Input Required, Completed).
-   User interruptions and cancellations.

## Decision
We will adopt the **A2A (Agent-to-Agent) Protocol** as the primary schema for all Host-Worker interactions.

## Consequences
-   **Standardization**: We use the `Task`, `Message`, and `Artifact` protobuf/JSON definitions from a documented standard.
-   **Capability**: A2A natively handles "Interrupted" states (`TASK_STATE_INPUT_REQUIRED`), which simplifies the logic for asking users for clarification or credentials.
-   **Tooling**: We can leverage the `a2a-python` SDK for task management and state persistence (SQLite-backed `TaskStore`).
-   **Transport**: While A2A is often used over HTTP, we will implement it over **Unix Domain Sockets (UDS)** for security and performance within the Kubernetes pod environment.
-   **Interoperability**: Claw workers can potentially interact with other A2A-compliant agents in the future.

## Alternatives Considered
-   **Custom JSON-RPC**: Lower overhead but requires re-implementing task state machines and history management.
-   **MCP (Model Context Protocol)**: Great for tool definitions, but less focused on the higher-level "Task" lifecycle and multi-agent coordination. We may still use MCP *within* the worker for tool discovery.
