# Operational Guidelines (AGENTS.md)

Welcome, agent. This is your "Standard Operating Procedure." These rules are non-negotiable and define how you operate within this workspace.

## 🧠 Think First
- **Chain of Thought**: Always reason through a problem before you reach for a tool. Explain your plan clearly.
- **Verification**: Never assume a file exists or has certain content because you *think* it should. Read it first.
- **Contextual Awareness**: Before starting a task, read the relevant documentation (e.g., `README.md`, `docs/`) to understand the "why".

## 🛠️ Tool Usage
- **Atomic Changes**: Prefer small, focused edits over massive rewrites.
- **Safety**: Do not run destructive or irreversible commands without multi-turn confirmation.
- **Performance**: Be mindful of token count. Don't read massive files unless necessary; use targeted reads.
- **Git Strategy**: Always use branches and Pull Requests. NEVER commit to `main`.
    1. `git checkout -b <branch-name>`
    2. `git add` / `git commit`
    3. `git push origin <branch-name>`
    4. `gh pr create --title "<summary>" --body "<details>"`

## 📝 Communication
- **Clarity**: Be concise but comprehensive. Avoid fluff.
- **Transparency**: If you make a mistake, acknowledge it and explain how you'll fix it.
- **Proactivity**: If you see a better way to do something, suggest it.

---

## 🏗️ Project Context & Architecture

If you need to understand *why* things are built the way they are, or what the system's goals are, please refer to the `docs/` directory:

### 🎯 [Use Cases](./docs/use-cases/)
Start here to understand the **scenarios and user stories** that define system behavior.

### 🧪 [Research](./docs/research/)
Contains **deep dives into existing systems** and foundational concepts.

### 🏗️ [Design](./docs/design/)
The **current technical specifications** and blueprints.

### ⚖️ [Decisions](./docs/decisions/)
**Architectural Decision Records (ADRs)** documenting finalized pivots and major choices.

---

## 🛠️ Coding Preferences

This project targets **Python 3.14+**. We prefer modern Pythonic syntax:
- **Type Hints**: Use `| None` instead of `Optional`. Use `dict` and `list` instead of `Dict` and `List`.
- **Return Types**: Explicitly annotate methods that return nothing with `-> None`.
- **Asynchronous Programming**: Use `asyncio` for I/O bound tasks.
- **Clarity over Cleverness**: Keep logic simple and well-documented.
