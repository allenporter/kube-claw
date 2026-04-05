# Scenario: The Autonomous Project Maintainer

This document illustrates the end-to-end lifecycle of a "Claw Core v3" agent—from initial contact on a communication channel to long-term, proactive project management.

---

## 1. The Setup: "Hello Claw"
**User Context:** A developer (Maintainer of a Home Assistant Roborock integration) sends a message via **Discord**.

> **User:** "Hello Claw, I maintain the home assistant roborock integration. I'd like you to help me stay on top of the top pressing issues reported. Can you help me triage top incoming issues and make sure I'm focused on the right ones? Make sure to check each day."

---

## 2. Phase 1: Immediate Handshake & Provisioning
When the message hits the **Inbound Gateway**, the following sequence occurs:

1.  **Identity Resolution**: The Gateway maps the Discord Snowflake ID to the user's **Claw Identity**.
2.  **JIT Workspace Creation**: Finding no existing project for "Roborock," the Orchestrator provisions a new **Workspace Instance**: `/workspaces/roborock-session-1`.
    *   *Note: This Workspace acts as the persistent umbrella for this entire context. It is not a code repository itself.*
3.  **Sandbox Spawning**: A transient execution container (the "Hand") is started. It is mounted with:
    *   **Global Brain (Tier 1)**: The user's global `~/.adk-claw/` memory mount.
    *   **Session Workspace (Tier 2)**: The `/workspaces/roborock-session-1` instance containing a root for the session scratchpad and a `src/` directory for code.
4.  **Initial Tooling & Memory Encoding**:
    *   It initializes the **`SESSION.md`** file (Project Memory) at the Workspace Root `/workspaces/roborock-session-1/SESSION.md` to store its mission statement.
    *   The agent uses `github_search` to locate the home assistant repository. If it chooses to clone the repo, it places it inside the isolated `/workspaces/roborock-session-1/src/` folder.
    *   **Immediate Response**: The agent replies on Discord: *"I've initialized a workspace for the Roborock integration. I'm scanning the repository now to build a baseline of current issues."*

---

## 3. Phase 2: Persistence & Memory State
Before the sandbox shuts down, the agent "writes down" its status so it doesn't forget.

**`SESSION.md` (Project Memory) update:**
```markdown
# Project: Roborock Integration
## Mission
Triage and prioritize GitHub issues daily to ensure the maintainer focuses on high-impact bugs.

## Current Context
- Repository: `https://github.com/home-assistant/core` (Roborock integration components)
- Last Triage: 2023-10-27
- Top Issues: [List of IDs fetched during initial scan]
```

---

## 4. Phase 3: Transition to Autonomy (The Pulse)
To fulfill the "check each day" requirement, the agent registers a **Proactive Intent**.

1.  **Task Registration**: The agent calls an internal tool `schedule_task(cron="0 9 * * *", intent="daily-triage")`.
2.  **The Scheduler**: The Core's background pulse-engine adds a recurring job linked to this specific **Lane** (User + Project + Discord Channel).

---

## 5. Phase 4: The "Later" (The Daily Pulse)
At 9:00 AM the next morning, without any user interaction:

1.  **Wake Up**: The Scheduler triggers the `daily-triage` intent.
2.  **Hydration**: The Orchestrator spawns a new sandbox and mounts the `/workspaces/roborock-session-1` folder.
3.  **Autonomous Thought**: The agent reads the `SESSION.md` file. It "remembers" its mission and the state of the repo from yesterday.
4.  **Tool Execution**: It fetches new issues via the GitHub API and compares them against its "Top Issues" list in the workspace.
5.  **Proactive Reachability**: The agent sends a message to the original Discord channel:
    > **Claw:** "Good morning! I've scanned the Roborock repo. There are 3 new issues. Issue #402 (Vacuum mapping error) seems most urgent as it affects multiple users. Should I draft a response or look into the logs for you?"

---

## 6. Key Takeaways
*   **No "Separate Bots"**: The user experiences a single consistent identity. The complexity of "switching" between projects is handled by the **Orchestrator** swapping the **Workspace Mounts**.
*   **Stateless Execution**: The sandbox is destroyed after every run. Memory lives in the **Filesystem (SESSION.md)** and the **Host Database (Binding Table)**.
*   **Proactive vs. Reactive**: The system moves from reacting to Discord messages to initiating its own "runs" based on the **Pulse** scheduler.
