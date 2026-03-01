# Scenario: The Multi-Project Cross-Channel Fix

This document illustrates how "Claw Core v3" handles switching between two different projects (Roborock and ical) across different communication channels (Discord and Email/TUI) and how it manages **Persistence vs. Ephemerality**.

---

## 1. The Context: A Cross-Project Maintainer
**User Context:** You are already using Claw for the **Roborock Integration** (managed on Discord). You now receive an email about a bug in your other project: **`ical` (Python library)**.

> **User (via Email or TUI):** "Claw, I just got an issue for `ical`. It's a parsing error with recurring events. Here's the issue link: `github.com/allenporter/ical/issues/123`. Can you fix this for me?"

---

## 2. Phase 1: The Context Switch (The Handshake)
The **Inbound Gateway** receives the email and performs the **Binding Handshake**:

1.  **Identity Match**: The Core recognizes your Email address as the same **Claw Identity** as your Discord account.
2.  **Workspace Resolution**: The agent parses "ical" and "github.com/allenporter/ical". It looks at the **Binding Table**:
    *   It finds (or creates) the `ical` workspace mapping.
    *   It retrieves your **Auth Profile** containing the GitHub OAuth token for `allenporter`.
3.  **Clean Slate Sandbox**: A **new** transient container is spawned.
    *   **Crucially**: This sandbox has **zero knowledge** of the Roborock code. It is mounted only with the `/workspaces/ical` folder and your global Python preferences.

---

## 3. Phase 2: Persistence vs. Ephemerality
This is where the distinction between what "stays" and what "goes" is vital for security and reliability.

| Feature | Type | Location | Why? |
| :--- | :--- | :--- | :--- |
| **The Sandbox Process** | **Ephemeral** | Container RAM/CPU | Once the fix is pushed or the session ends, the container is **deleted**. No leftover processes or credentials remain in memory. |
| **GitHub OAuth Token** | **Ephemeral (In-Sandbox)** | Env Var (`$GITHUB_TOKEN`) | It is injected into the sandbox for this run only. It is never "saved" inside the workspace files. |
| **`ical` Source Code** | **Persistent** | `/workspaces/ical` | The agent clones the repo here. This folder lives on the **Host** and is mounted into the sandbox every time you work on `ical`. |
| **`CLAUDE.md`** | **Persistent** | `/workspaces/ical/CLAUDE.md` | The agent's "Project Memory." It stores the fact that it's currently working on Issue #123. |
| **The Fix (The Code)** | **Persistent** | Git Branch | The agent creates a branch (e.g., `fix-issue-123`). This is the ultimate form of persistence. |

---

## 4. Phase 3: The Execution Loop
1.  **Analyze**: The agent reads the `ical` code and the issue description.
2.  **Reproduce**: It writes a new test case in the ephemeral sandbox: `tests/reproduce_issue_123.py`.
3.  **Fix**: It modifies the parsing logic in `ical/parsing.py`.
4.  **Verify**: It runs the tests. If they pass, it commits the changes.
5.  **Report**: It sends an email back: *"I've reproduced the recurring event bug and pushed a fix to the `fix-issue-123` branch. All tests passed. Ready for review!"*

---

## 5. Phase 4: Long-Term Memory
If you go back to **Discord** an hour later and ask about your "other project":

> **User (Discord):** "Hey, how's that ical fix going?"

1.  **Gateway**: Receives message on Discord.
2.  **Orchestrator**: Maps "ical" to the `/workspaces/ical` workspace.
3.  **Sandbox**: Spawns, mounts `ical` workspace, and reads `CLAUDE.md`.
4.  **Persistence in Action**: Even though it's a different channel (Discord vs. Email), the agent reads its own note in `CLAUDE.md`: *"Currently: Fixed Issue #123, awaiting PR review."*
5.  **Response**: *"The fix for the recurring event bug is pushed and verified. I'm just waiting for you to merge the PR."*

---

## 6. Summary: The Wall of Isolation
*   **The Roborock Sandbox** cannot see the **ical Sandbox**.
*   **The User** sees a unified assistant across **Email and Discord**.
*   **The System** remains secure because credentials (Auth Profiles) are only injected into **Ephemeral** environments, while work (Code/CLAUDE.md) is saved in **Persistent** volumes.
