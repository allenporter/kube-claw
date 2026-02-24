# Project TODOs

## Phase 1: Core Logic & Mocking (Current)
- [ ] Implement `FakeCommunicator` with CLI interaction support
- [ ] Implement `FakeJobScheduler` with local state persistence
- [ ] Develop `ClawAgent` orchestration loop and failure recovery
- [ ] Define Kubernetes `PodSpec` and Job lifecycle requirements

## Phase 2: Production Drivers
- [ ] Finalize `DiscordCommunicator` with multi-tenancy and config support
- [ ] Finalize `KubernetesJobScheduler` with label-based discovery
- [ ] Implement PVC-based workspace persistence for jobs

## Tooling & Infrastructure
- [ ] Fix `adk-cli` built-in skill packaging.
- [ ] Add `code-explorer` skill if missing.
