# Project TODOs


## Phase 0: More detailed design
- [ ] The plan below is good for just testing out the interfaces below, however does not really have a "driver" to drive everything. The claw agent orchestration idea is not fully fleshed out. Do more research.

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
- [ ] Fix `adk-cli` bug where if a subprocess is killed the whole program crashes. maybe need an option to handle timeouts or canceling command in flight.
- [ ] Add `adk-cli` support for switching models in the middle of conversation
- [ ] Add `code-explorer` skill if missing.
