# User Preferences

## 🛠️ Code Standards
- Prefer clean, documented code.
- Use modern Python type hinting (`|` instead of `Union`).
- **NEVER** use `from __future__ import annotations`; it can cause issues with runtime type evaluation (e.g., in Pydantic or specific library integrations).
- Adhere strictly to the existing architectural patterns of the repo (e.g., lane-queuing logic).

## 🧪 Operational Workflow
- **Verify before pushing**: Always run the project's verification suite (e.g., `pytest`, `tox`, or repository-specific scripts like `script/test`) before declaring a task finished or pushing to remote.
- **Pre-commit Awareness**: Check for and respect `.pre-commit-config.yaml` or other automated linting hooks to ensure style consistency.
- **Skill Awareness**: Review available `skills` in the workspace (via `list_skills`) to see if there is a specialized workflow or toolset relevant to the current task.
- **Atomic Commits**: Group related changes into small, logical commits with clear descriptions.
- **Sub-Agent Usage**: If a task is complex (e.g., "fix build failures in project X"), use a sub-agent specialized for that project's architecture rather than hacking on the main context.
