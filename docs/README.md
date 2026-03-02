# Claw Core Project Documentation

This directory contains the documentation for the **Claw Core** project, an orchestration framework for tool-capable LLM agents.

## Directory Structure

### [📂 1. Use Cases](./use-cases/)
Scenarios and user stories that define the behavior and goals of the system.
*   [Roborock Maintainer](./use-cases/SCENARIO_ROBOROCK_MAINTAINER.md): Autonomous GitHub issue management.
*   [Multi-Project Fix](./use-cases/SCENARIO_MULTI_PROJECT_FIX.md): Handling identity and context across different repositories.

### [📂 2. Research](./research/)
Analyses of existing systems and foundational concepts.
*   [A2A Protocol Survey](./research/A2A_SURVEY_SUMMARY.md): Deep dive into the Agent-to-Agent protocol.
*   [Legacy Design Survey](./research/claw_design_survey.md): Learnings from the v1 prototype.
*   [Claw Core Architectures](./research/deep-research.md): Comparison of OpenClaw and NanoClaw models.
*   [Workspace Isolation](./research/WORKSPACE_ISOLATION.md): Deep dive into persistent vs. transient environments.

### [📂 3. Design](./design/)
Technical specifications and architectural blueprints for the current version.
*   [**v3 Specification (Core)**](./design/v3-specification/)
    *   [High-Level Spec](./design/v3-specification/01-high-level-spec.md)
    *   [Architecture Overview](./design/v3-specification/02-architecture-overview.md)
    *   [Open Questions](./design/v3-specification/04-open-questions.md)
    *   [Design TODOs](./design/v3-specification/05-design-todos.md)
    *   [Tool Strategy & Execution](./design/v3-specification/07-tool-schemas.md)
    *   [Orchestrator Lifecycle](./design/v3-specification/08-orchestrator-handshake.md)
    *   [Design Gaps & Remaining Work](./design/v3-specification/10-design-gaps.md)
    *   [Queue & Concurrency Model](./design/v3-specification/11-queue-concurrency.md)
    *   [Agent Core Integration](./design/v3-specification/12-agent-core.md)

### [📂 4. Decisions](./decisions/)
Formal Architectural Decision Records (ADRs) and finalized pivots.
*   [ADR-001: A2A Protocol](./decisions/ADR-001-A2A-Protocol.md) *(superseded)*
*   [ADR-002: Modular Isolation & Testability](./decisions/002-modular-isolation.md)
*   [ADR-003: Hybrid Tool Dispatch](./decisions/ADR-003-hybrid-mcp-a2a-tooling.md) *(superseded)*
*   [ADR-004: Embedded Executor Architecture](./decisions/ADR-004-embedded-executor.md) ✅

### [📂 Archive](./archive/)
Obsolete plans, historical notes, and old task lists.
*   [v3 Superseded](./archive/v3-superseded/) — Worker-Host RPC, UDS design, Worker Entrypoint

---
*Last Updated: 2026-03-02 — Architecture simplified to embedded executor (ADR-004)*
