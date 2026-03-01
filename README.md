# Claw Core v3: Architecture & Research

This directory contains the design and implementation for the next generation of the Claw orchestration framework.

## Status: Design Phase
The project has been reset to a clean state to avoid legacy assumptions from the previous "One-Job-per-Task" model.

### Core Principles (v3)
- **A2A Protocol**: Every worker (sandbox) is an A2A-compliant agent.
- **Warm Lanes**: Persistent communication channels between Host and Sandbox.
- **Binding Table**: Just-in-Time resolution of identity to workspace/credentials.
- **Opaque Execution**: Sandbox internals are hidden; interaction is via standardized A2A Artifacts and Tasks.

### Legacy Code
Previous iterations and proof-of-concepts have been moved to `v1_legacy/`.
