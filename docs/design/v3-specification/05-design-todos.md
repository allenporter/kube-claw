# Design TODOs (Claw Core v3)

This document tracks the outstanding design gaps and tasks that need to be addressed before moving into implementation.

## 1. Kubernetes Controller & Resource Mapping
- [ ] **Define K8s Resource Strategy**: Determine if "Lanes" should be implemented as `Deployments`, `Jobs`, or a custom `ClawLane` CRD.
- [ ] **Binding Table to K8s Translation**: Design the logic that translates a Binding Table entry (Channel ID + User ID) into specific Pod specifications, including PVC mounts and Environment Variables.
- [ ] **PVC Management**: Define how persistent volumes for workspaces are provisioned and attached to lanes (e.g., dynamic vs. static provisioning).

## 2. Data Modeling & Identity
- [ ] **Formal Binding Table Schema**: Define the Pydantic/SQL schema for the Binding Table. It must map:
    - Protocol/Channel Identity (e.g., Discord/WhatsApp ID)
    - Workspace Path (PVC)
    - Auth Profile (GitHub/Docker credentials)
    - Current A2A Session/Context ID
- [ ] **Auth Profile Injection**: Design the secure mechanism for injecting credentials (like GitHub tokens) into the worker container (e.g., K8s Secrets or dynamic env injection).

## 3. Communication & Protocol (A2A)
- [ ] **A2A Worker Entrypoint Spec**: Define the behavior of the `agent_entrypoint.py` inside the worker container.
    - How it initializes the A2A state machine.
    - How it listens on the UDS (Unix Domain Socket).
- [ ] **Tooling Protocol**: Decide if tools are executed via Model Context Protocol (MCP) or native A2A artifacts.
- [ ] **Interrupt & Concurrency Logic**: Define how the Host handles new user input while a worker is already processing an A2A task (e.g., `input.push` behavior).

## 4. Security & Isolation
- [ ] **Sandbox Boundary Specification**: Create a dedicated document covering:
    - Network Policies (Egress filtering).
    - Resource Limits (CPU/Memory).
    - Credential Sanitization (Preventing LLM from leaking injected tokens).

## 5. Scheduler & Autonomy ("The Pulse")
- [ ] **Pulse System Design**: Define the "Pulse" mechanism for proactive task triggers (e.g., daily triaging).
- [ ] **Retry & Failure Logic**: Design how the system handles worker crashes or long-running task timeouts in the "Warm Lane" model.

## 6. Research Tasks
- [ ] **A2A Protocol Audit**: Perform a "Pragmatism Audit" comparing a custom RPC vs. full A2A implementation.
- [ ] **A2A-Python Evaluation**: Review the existing `/workspaces/A2A` codebase for integration readiness.
