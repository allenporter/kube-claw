# Development Plan: Phase 1 (Minimalist Core & Mocking)

This document outlines the immediate implementation strategy for **KubeClaw**, focusing on a "Fake-first" approach to verify core logic before integrating with external services like Discord and Kubernetes.

## Goals
- Validate the `ClawAgent` orchestration logic without external dependencies.
- Establish a robust testing framework for drivers.
- Define the lifecycle of a Kubernetes-backed agent job.

---

## Milestones

### M1: Mock Driver Implementation
Create "Fake" versions of the core interfaces to allow for local, interactive development.
- **`FakeCommunicator`**:
    - Initially use a simple `input()` loop for CLI interaction.
    - Support a predefined script of messages for automated testing.
- **`FakeJobScheduler`**:
    - Manage "jobs" as local subprocesses or in-memory state.
    - **Persistence**: Use a local `jobs.json` file to simulate recovery across agent restarts.

### M2: Core Orchestration (The "Claw" Loop)
Develop the primary logic in `ClawAgent` to bridge communication and scheduling.
- Implement message parsing and task extraction.
- Manage job lifecycles: `PENDING` -> `RUNNING` -> `COMPLETED`/`FAILED`.
- Implement **Failure Recovery**: On startup, the agent must scan for existing jobs (via `jobs.json` or Kubernetes labels) and reconnect.

### M3: Discord Driver Verification
Transition from mock to real communication.
- Verify `DiscordCommunicator` in a sandbox server.
- **Multi-tenancy**: Determine if the agent should listen to all channels or be restricted via `config.yaml`.
- Implement basic command handling (e.g., `!status`, `!cancel`).

### M4: Kubernetes Integration & Job Spec
Finalize the production scheduler.
- Define the `PodSpec` for agent jobs (image, PVC mounts, environment variables).
- Implement label-based discovery in `KubernetesJobScheduler` for robust recovery.
- Configure PVC management for workspace persistence.

---

## Open Design Questions

1.  **Persistence Strategy**: Should we lean entirely on Kubernetes labels for state, or maintain a small metadata store (e.g., ConfigMap/PVC)?
2.  **CLI Interaction**: How interactive should the `FakeCommunicator` be for manual debugging?
3.  **Safety & Human-in-the-loop**: At what stage of the `ClawAgent` loop do we insert manual approval for "harmful" actions?
