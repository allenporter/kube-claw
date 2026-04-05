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
    *   **Crucially**: This sandbox has **zero knowledge** of the Roborock code. It is mounted only with the `/workspaces/ical-session-2` folder and your global Python preferences.

---

## 3. Phase 2: Persistence vs. Ephemerality
This is where the distinction between what "stays" and what "goes" is vital for security and reliability.

| Feature | Type | Location | Why? |
| :--- | :--- | :--- | :--- |
| **The Sandbox Process** | **Ephemeral** | Container RAM/CPU | Once the fix is pushed or the session ends, the container is **deleted**. No leftover processes or credentials remain in memory. |
| **GitHub Access** | **Ephemeral** | Env Var (`$GITHUB_TOKEN`) | It is injected into the sandbox for this run only. It is never "saved" inside the workspace files. |
| **Global Brain (Tier 1)** | **Persistent** | `~/.adk-claw/` | A unified identity and global memory mount shared across all execution sessions regardless of channel. |
| **Session Scratchpad (Tier 2)**| **Persistent** | `/workspaces/ical-session-2/SESSION.md` | The agent's "Private Memory" for this chat channel specifically. It tracks the progress on Issue #123. |
| **`ical` Repo (Tier 3)** | **Persistent** | `/workspaces/ical-session-2/src/ical` | The agent clones the objective repo into the `src/` directory. This isolates the public code from the agent's memory. |
| **The Fix (The Code)** | **Persistent** | Git Branch | The agent creates a branch (e.g., `fix-issue-123`) in the `src/ical` repo. This is the ultimate form of persistence. |

---

## 4. Phase 3: The Execution Loop
1.  **Analyze**: The agent reads the `ical` code in the `src/` dir and the issue description.
2.  **Reproduce**: It writes a new test case in the ephemeral sandbox: `src/ical/tests/reproduce_issue_123.py`.
3.  **Fix**: It modifies the parsing logic in `src/ical/ical/parsing.py`.
4.  **Verify**: It runs the tests. If they pass, it commits the changes.
5.  **Report**: It sends an email back: *"I've reproduced the recurring event bug and pushed a fix to the `fix-issue-123` branch. All tests passed. Ready for review!"*

---

## 5. Phase 4: Long-Term Memory
If you go back to **Discord** an hour later and ask about your "other project":

> **User (Discord):** "Hey, how's that ical fix going?"

1.  **Gateway**: Receives message on Discord.
2.  **Orchestrator**: Maps "ical" to the `/workspaces/ical-session-2` workspace.
3.  **Sandbox**: Spawns, mounts the workspace, and reads `SESSION.md`.
4.  **Persistence in Action**: Even though it's a different channel (Discord vs. Email), the agent reads its own note in `SESSION.md`: *"Currently: Fixed Issue #123, awaiting PR review."*
5.  **Response**: *"The fix for the recurring event bug is pushed and verified. I'm just waiting for you to merge the PR."*

---

## 6. Summary: The Wall of Isolation
*   **The Roborock Workspace Instance** cannot see the **ical Workspace Instance**.
*   **The User** sees a unified assistant across **Email and Discord**.
*   **The System** remains secure because credentials (Auth Profiles) are only injected into **Ephemeral** environments, while work (Code/SESSION.md) is saved in **Persistent** volumes.
