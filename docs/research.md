# Research: OpenClaw vs. NanoClaw vs. KubeClaw

This document summarizes the research into the existing AI agent ecosystems and how they inform the design of **KubeClaw (Claw Core)**.

## Comparison Matrix

| Feature | OpenClaw | NanoClaw | **KubeClaw (Claw Core)** |
| :--- | :--- | :--- | :--- |
| **Philosophy** | "Universal Gateway" for all devices. | "Small enough to understand." | **"Minimalist Kubernetes Native."** |
| **Language** | TypeScript (Node.js) | TypeScript (Node.js) | **Python (3.14+)** |
| **Deployment** | Host / Docker Compose | Single process / Docker | **Kubernetes (Jobs/Pods)** |
| **Sandboxing** | App-level / Optional Docker | Hard Linux Container Isolation | **K8s Job Isolation** |
| **Storage** | Local disk / SQLite | Local disk (Groups folder) | **Kubernetes PVCs** |
| **Customization** | Configuration files | Code changes (AI-native) | **Driver/Tool Based** |

## Key Insights from OpenClaw
- **Gateway Model:** OpenClaw uses a central hub to manage connections. While powerful, it introduces a single point of failure and significant complexity.
- **Process Registry:** Manages background tasks. KubeClaw will replace this with native **Kubernetes Job tracking**.

## Key Insights from NanoClaw
- **Isolation by Default:** NanoClaw's use of true container isolation (Docker/Apple Container) is a security gold standard. KubeClaw will adopt this by running every task in a dedicated **K8s Pod**.
- **Filesystem IPC:** Using simple directory structures for IPC is robust and easy to debug. KubeClaw will use **PVC-based state** to allow different Pods to share the same workspace.
- **AI-Native Customization:** Rejecting "configuration sprawl" in favor of code-level changes or specialized "Skills". KubeClaw will focus on lean **Drivers** that are easy to modify or replace.

## KubeClaw Design Principles

1. **Kubernetes Native:** If a feature exists in K8s (Scheduling, Secrets, Volume Management), use it. Do not reinvent it in Python.
2. **Ephemeral Agent, Persistent Workspace:** The agent runtime is a Job that dies when done. The workspace is a PVC that lives on.
3. **Driver-Agnostic Core:** The core logic should not care if it's being driven by a CLI, a Discord bot, or a Slack connector.
4. **Pythonic Minimalism:** Strictly Python 3.14, leveraging the ADK for standardized tool and communication interfaces.
