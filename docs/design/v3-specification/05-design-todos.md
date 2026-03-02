# Design TODOs (Claw Core v3)

This document tracks the outstanding design gaps and tasks that need to be addressed.

## 1. Kubernetes Controller & Resource Mapping
- [ ] **Define K8s Resource Strategy**: Determine if "Lanes" should be implemented as `Deployments`, `Jobs`, or a custom `ClawLane` CRD.
- [ ] **Binding Table to K8s Translation**: Design the logic that translates a Binding Table entry (Channel ID + User ID) into specific Pod specifications, including PVC mounts and Environment Variables.
- [ ] **PVC Management**: Define how persistent volumes for workspaces are provisioned and attached to lanes (e.g., dynamic vs. static provisioning).

## 2. Data Modeling & Identity
- [x] **Formal Binding Table Schema**: Defined in `kube_claw/binding/table.py`.
- [ ] **Auth Profile Injection**: Design the secure mechanism for injecting credentials (like GitHub tokens) into the executor environment (e.g., K8s Secrets or dynamic env injection).

## 3. Communication & Protocol
- [x] **Orchestrator Lifecycle**: Defined the state machine and execution flow. See [08-orchestrator-handshake.md](./08-orchestrator-handshake.md).
- [x] **Embedded Executor**: Agent runs in-process via `adk-coder`. See [12-agent-core.md](./12-agent-core.md).
- [ ] **External MCP Server Config**: Design configuration for connecting to external MCP servers (GitHub, Slack, etc.).
- [ ] **Queue & Concurrency Implementation**: Implement the lane queue with `collect`/`followup`/`steer` modes. See [11-queue-concurrency.md](./11-queue-concurrency.md).

## 4. Security & Isolation
- [ ] **Security Policy Configuration**: Define how `CustomPolicyEngine` modes (`ask`/`auto`/`plan`) are configured per-channel.
- [ ] **Credential Sanitization**: Define how to prevent the LLM from leaking injected tokens.

## 5. Scheduler & Autonomy ("The Pulse")
- [ ] **Pulse System Design**: Define the "Pulse" mechanism for proactive task triggers (e.g., daily triaging).
- [ ] **Retry & Failure Logic**: Design how the system handles agent crashes or long-running task timeouts.

## 6. Implementation & Codebase
- [x] **Define Core Interfaces**: Created `BindingTable`, `Orchestrator` ABCs.
- [x] **Create Testing Fakes**: Implemented `InMemoryBindingTable`.
- [x] **Embedded Orchestrator**: Implemented `EmbeddedOrchestrator` with `adk-coder` integration.
- [ ] **Channel Adapters**: Implement `DiscordAdapter`, `A2AAdapter`, etc. using the `ChannelAdapter` protocol.
- [ ] **YAML Configuration**: Implement config loader for `.kube-claw.yaml`.
- [ ] **Memory Store**: Implement cross-session `MemoryStore` for agent notes.
