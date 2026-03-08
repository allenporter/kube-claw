# Project TODOs


## Phase 0: More detailed design
- [x] Research notification trigger and exit logic
- [ ] Answer design questions in `docs/ARCHITECTURAL_QUESTIONS.md`
- [ ] Define "Watcher" vs "Poller" trade-offs in `docs/deep-research.md`

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
- [ ] Fix `adk-coder` built-in skill packaging.
- [ ] Fix `adk-coder` bug where if a subprocess is killed the whole program crashes. maybe need an option to handle timeouts or canceling command in flight.
- [ ] Add `adk-coder` support for switching models in the middle of conversation
- [ ] Add `code-explorer` skill if missing.

- [ ] Implement Claw-RPC Handler in `adk_claw/agent.py` (Host side).
- [ ] Implement Unix Domain Socket listener in `KubernetesJobScheduler`.
- [ ] Refine `agent_entrypoint.py` with actual LLM integration (LiteLLM/Claude API).
- [ ] Add `CLAUDE.md` auto-discovery and persistence logic to Worker.
