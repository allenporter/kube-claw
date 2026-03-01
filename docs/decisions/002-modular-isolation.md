# Architectural Decision Record (ADR-002): Modular Isolation & Testability

## Status
Proposed

## Context
Claw Core v3 aims to be a robust framework for orchestrating tool-capable agents. While Kubernetes (K8s) is the primary target for production scaling and security, the system must remain flexible enough for local development, alternative runtimes (Docker, Podman), and rigorous automated testing.

## Decision: The "Pluggable Runtime" Architecture

To achieve this, we will adopt the following architectural principles:

### 1. The "Sandbox" Abstraction
The Host logic will never interact with `kubectl` or the Kubernetes API directly. Instead, it will interact with a **`SandboxManager` Interface**.
- **`K8sSandboxManager`**: Handles Pod/PVC lifecycle.
- **`DockerSandboxManager`**: Handles container lifecycle.
- **`LocalProcessSandboxManager`**: For low-overhead testing (spawns a local sub-process).
- **`FakeSandboxManager`**: For unit tests (records calls without spawning anything).

### 2. Transport-Agnostic Communication
The communication layer (A2A) must not be hardcoded to Unix Domain Sockets (UDS).
- The **Worker Entrypoint** will accept a `--transport` flag (e.g., `uds`, `tcp`, `stdio`).
- The **Host Client** will use a connection factory to pick the right transport based on the `SandboxManager`'s output.

### 3. Dependency Injection & "Fake-First" Development
Every core component (Binding Table, Secret Store, Sandbox Manager) must have a **Mock/Fake implementation** available in the codebase.
- No component should require a running Kubernetes cluster or a live database to be instantiated for a test.
- We will use **In-Memory Fakes** (e.g., `InMemoryBindingTable`) rather than complex mocking libraries where possible, to ensure the fakes behave like the real thing.

### 4. Headless Testing of the "Agent Brain"
The "Agent Runtime" (the code running inside the worker) must be testable as a pure Python library.
- We should be able to "feed" it A2A messages via `stdin` and read `stdout` to verify its logic without any network or socket involvement.

## Consequences
- **Positive**: We can develop the entire "Agent Brain" on a laptop without Minikube or Docker.
- **Positive**: We can swap Kubernetes for a different orchestrator (or even a serverless model) by writing one new class.
- **Negative**: Adds a small layer of boilerplate (Interfaces/Abstract Base Classes) to the initial implementation.
- **Negative**: Requires careful management of "Environment-Specific Config" (e.g., K8s needs PVC names, Local needs folder paths).

## Implementation Strategy
1.  Define `claw.core.interfaces.SandboxManager`.
2.  Implement `claw.core.runtimes.local.LocalProcessManager`.
3.  Develop the `agent_entrypoint.py` using `stdio` transport first.
4.  Layer on UDS and Kubernetes once the core logic is stable.
