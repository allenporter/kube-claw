# Design TODOs (Claw Core v3)

This document tracks the outstanding design gaps and tasks that need to be addressed before moving into implementation.

## 1. Kubernetes Controller & Resource Mapping
- [ ] **Define K8s Resource Strategy**: Determine if "Lanes" should be implemented as `Deployments`, `Jobs`, or a custom `ClawLane` CRD.
- [ ] **Binding Table to K8s Translation**: Design the logic that translates a Binding Table entry (Channel ID + User ID) into specific Pod specifications, including PVC mounts and Environment Variables.
- [ ] **PVC Management**: Define how persistent volumes for workspaces are provisioned and attached to lanes (e.g., dynamic vs. static provisioning).

## 2. Data Modeling & Identity
- [x] **Formal Binding Table Schema**: Define the Pydantic/SQL schema for the Binding Table. (Defined in `kube_claw/core_v3/interfaces/binding_table.py`)
- [ ] **Auth Profile Injection**: Design the secure mechanism for injecting credentials (like GitHub tokens) into the worker container (e.g., K8s Secrets or dynamic env injection).

## 3. Communication & Protocol (A2A & MCP)
- [x] **Orchestrator Handshake & Lifecycle**: Defined the state machine and connection flow. (See `08-orchestrator-handshake.md`)
- [ ] **A2A Worker Entrypoint Spec**: Define the behavior of the `agent_entrypoint.py` inside the worker container.
    - How it initializes the A2A state machine.
    - How it listens on the UDS (Unix Domain Socket).
- [x] **Tooling Protocol (Hybrid Model)**: Decided on a Hybrid Tooling Model (Direct vs. Proxied) with Host-side Hydration. (See `07-tool-schemas.md`)
- [x] **MCP Integration**: Adopted MCP as the tool dispatch protocol between Worker (Client) and Host (Server). (See ADR-003)
- [ ] **MCP Server Implementation**: Design the Host-side MCP server that hydrates tool calls using the `BindingTable`.
- [ ] **ADK MCP Client**: Implement the ADK Skill that connects to the Host's MCP socket and registers remote tools.
- [ ] **Interrupt & Concurrency Logic**: Define how the Host handles new user input while a worker is already processing an A2A task (e.g., `input.push` behavior).

## 4. Security & Isolation
- [ ] **Sandbox Boundary Specification**: Create a dedicated document covering:
    - Network Policies (Egress filtering).
    - Resource Limits (CPU/Memory).
    - Credential Sanitization (Preventing LLM from leaking injected tokens).

## 5. Scheduler & Autonomy ("The Pulse")
- [ ] **Pulse System Design**: Define the "Pulse" mechanism for proactive task triggers (e.g., daily triaging).
- [ ] **Retry & Failure Logic**: Design how the system handles worker crashes or long-running task timeouts in the "Warm Lane" model.

## 6. Implementation & Codebase
- [x] **Establish Core v3 Structure**: Set up the `kube_claw/core_v3` directory with domain, infrastructure, and interfaces.
- [x] **Define Core Interfaces**: Created `BindingTable` and `SandboxManager` ABCs.
- [x] **Create Testing Fakes**: Implemented `InMemoryBindingTable` and `FakeSandboxManager`.
- [ ] **Orchestrator Implementation**: Develop the `A2AOrchestrator` to bridge the gateway and the sandbox.

## 7. Research Tasks
- [x] **A2A Protocol Audit**: Decided to use A2A as the primary communication schema (ADR-001).
- [x] **A2A-Python Evaluation**: Determined that adopting A2A for Core v3 provides the necessary state management and interactivity.
