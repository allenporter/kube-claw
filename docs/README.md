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
*   [NanoClaw Research](./research/deep-research.md): Just-in-Time bootstrapping and isolation models.

### [📂 3. Design](./design/)
The technical specifications and architectural blueprints for the current version.
*   [Core v3 Specification](./design/CORE_V3_SPECIFICATION.md): The unified system spec.
*   [Architecture Overview](./design/CLAW_CORE_ARCHITECTURE.md): High-level structural diagrams.
*   [Worker-Host Interface](./design/worker-host-interface.md): Communication protocols and transport layers.
*   [Architectural Questions](./design/ARCHITECTURAL_QUESTIONS.md): Pending design decisions and open research.

### [📂 4. Decisions](./decisions/)
Log of ADRs (Architectural Decision Records) and finalized design pivots.
*   *Pending: ADR-001 - Adoption of A2A Protocol.*

### [📂 Archive](./archive/)
Obsolete plans, historical notes, and old task lists.

---
*Last Updated: Design Phase - Transition to Core v3*
