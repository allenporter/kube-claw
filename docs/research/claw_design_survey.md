# Claw Design Survey & Learnings

This document summarizes the current design patterns and architectural decisions found in the `v1_legacy/kube_claw` codebase. These learnings serve as a foundation for the evolution of the Claw agent.

## 1. Core Architecture: The "Controller" Pattern
The Claw agent acts as a **bridge/controller** between two primary abstractions:
- **Communicator**: Handles external input/output (e.g., Discord).
- **JobScheduler**: Handles execution of tasks (e.g., Kubernetes).

### Learnings:
- **Separation of Concerns**: The `ClawAgent` class (`v1_legacy/kube_claw/agent.py`) doesn't know *how* a message is received or *how* a job is run. It only knows how to coordinate them.
- **Asynchronous Loop**: The agent maintains a background monitoring task (`_monitor_jobs`) to poll for status changes, decoupling task submission from result reporting.

## 2. Abstraction via Protocols and ABCs
The system heavily utilizes Python's `abc.ABC` and `Protocol` to define strict interfaces for drivers.

### Learnings:
- **Message Protocol**: A lightweight `Message` protocol (`v1_legacy/kube_claw/core/base.py`) ensures that the agent can work with any communication platform as long as it provides content, author ID, and channel ID.
- **Driver Pluggability**: Drivers for Discord and Kubernetes are isolated in `v1_legacy/kube_claw/drivers/`. This makes it trivial to swap Kubernetes for a "Fake" scheduler for testing or local development.

## 3. Kubernetes-Native Execution
The `KubernetesJobScheduler` (`v1_legacy/kube_claw/drivers/kubernetes/scheduler.py`) treats Kubernetes as the "operating system" for the agent.

### Learnings:
- **Ephemeral Workers**: Each task (`!run <task>`) spawns a new `V1Job`. This provides strong isolation between tasks.
- **State via PVCs**: The system instruction (`system_instruction.md`) mentions using Persistence Volume Claims (PVCs) for state, suggesting a model where state persists across ephemeral job executions.
- **Identity & Context**: Context (like `author_id`) is passed into the Kubernetes jobs via Environment Variables, allowing the worker to know who triggered it.

## 4. Safety and Human-in-the-Loop (HITL)
The `system_instruction.md` outlines a philosophy for the agent's behavior.

### Learnings:
- **Explicit Confirmation**: The design requires the agent to ask for confirmation for "destructive, public-facing, or external communication" actions.
- **Minimalism**: A core philosophy is "Prioritize simple, readable, and maintainable solutions over complex abstractions."
- **GitOps**: All significant changes must be version-controlled, implying that the agent's primary "memory" or "record of truth" should be a Git repository.

## 5. Technical Constraints & Stack
- **Framework**: Driven by `adk-coder` (Google ADK).
- **Communication**: Discord (`discord.py`) is the primary interface.
- **Orchestration**: Kubernetes (`kubernetes` python client).
- **Asyncio**: The entire system is built on `asyncio` for non-blocking I/O across communication and polling.

## Summary for Future Design
When evolving Claw, we should maintain the **Controller-Driver** separation, but potentially improve:
1.  **Polling Efficiency**: Move from active polling of Kubernetes jobs to event-based watching using Kubernetes Informers/Watchers.
2.  **Tool Integration**: Deeper integration with `adk-coder` tools (ls, cat, edit) as first-class capabilities within the scheduled jobs.
3.  **Unified State**: formalize how PVCs are shared or partitioned between the main agent and the worker jobs.
