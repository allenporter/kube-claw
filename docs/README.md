# Claw Core Project Documentation

This directory contains the documentation for the **Claw Core** project, an orchestration framework for tool-capable LLM agents in sandboxed environments.

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
    *   [Worker-Host RPC](./design/v3-specification/03-worker-host-rpc.md)
    *   [Open Questions](./design/v3-specification/04-open-questions.md)

### [📂 4. Decisions](./decisions/)
Formal Architectural Decision Records (ADRs) and finalized pivots.
*   [ADR-001: Adoption of A2A Protocol](./decisions/ADR-001-A2A-Protocol.md)

### [📂 Archive](./archive/)
Obsolete plans, historical notes, and old task lists.

---
*Last Updated: Design Phase - Transition to Core v3*
