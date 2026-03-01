# AI Agent Guidance (AGENTS.md)

Welcome, fellow agent! This file serves as a map to help you find critical context for understanding the design, architecture, and goals of the **Claw Core** project.

## Where to find context

If you need to understand *why* things are built the way they are, or what the system's goals are, please refer to the `docs/` directory:

### 🎯 [Use Cases](./docs/use-cases/)
Start here to understand the **scenarios and user stories** that define system behavior.
- Useful for: Understanding high-level goals and intended user experience.

### 🧪 [Research](./docs/research/)
Contains **deep dives into existing systems** and foundational concepts.
- Useful for: Context on how Claw Core compares to OpenClaw/NanoClaw, and the reasoning behind architectural foundations like workspace isolation.

### 🏗️ [Design](./docs/design/)
The **current technical specifications** and blueprints.
- Useful for: Understanding the **v3 Specification**, including RPC protocols and core architecture.

### ⚖️ [Decisions](./docs/decisions/)
**Architectural Decision Records (ADRs)** documenting finalized pivots and major choices.
- Useful for: Finding definitive answers on protocols (e.g., A2A) and modular isolation strategies.

### 📜 [Archive](./docs/archive/)
Historical notes and obsolete plans.
- Useful for: Avoiding past mistakes or understanding the project's evolution.

---

## 🛠️ Coding Preferences

This project targets **Python 3.14+**. We prefer modern Pythonic syntax:
- **Type Hints**: Use `| None` instead of `Optional`. Use `dict` and `list` instead of `Dict` and `List`.
- **Return Types**: Explicitly annotate methods that return nothing with `-> None`.
- **Asynchronous Programming**: Use `asyncio` for I/O bound tasks.
- **Clarity over Cleverness**: Keep logic simple and well-documented.

---

**Note to Agents:** Always check the `docs/README.md` for a more detailed map of available documentation.
