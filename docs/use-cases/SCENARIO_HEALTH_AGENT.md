# Scenario: The Health Agent

This document illustrates how "Claw Core v3" operates when the agent is acting as a personal assistant managing data, tasks, and documents, rather than acting as a software engineer modifying a source code repository.

This scenario highlights the blending of "Agent Memory" and "User Data" and challenges strict code-centric workspace assumptions.

---

## 1. The Setup: "My New Trainer"
**User Context:** A user wants to track their physical health, diet, and fitness goals. They do not want to manage a git repository; they just want an intelligent entity.

They create a dedicated communication channel (e.g., a Telegram chat, a Discord channel `#health-project`, or an empty GitHub repository they connect to the service).

> **User:** "Claw, I want you to be my health and fitness assistant. I'm going to upload my diet plan and some lab results. Remind me what I need to buy, and check in on my goals."

---

## 2. Phase 1: Provisioning & Document Upload
1. **JIT Workspace Creation**: The Gateway receives the message, maps the channel to a new intent, and provisions a fresh **Session Workspace (Tier 2)** (e.g. `/workspaces/health_session_1/`). The Orchestrator also mounts the **Global Brain (Tier 1)** (`~/.adk-claw/`).
2. **The Upload**: The user uploads a PDF (`diet_plan.pdf`). The Gateway receives the attachment and saves it into the Session Workspace.
3. **The Agent Run**: The agent is invoked. It reads the PDF using document-processing tools.
4. **Memory Update**: The agent updates its persistent session state to reflect the new goals. It writes to `SESSION.md` in the Session Workspace to track the required grocery items, keeping the global `MEMORY.md` clean.

> **Claw:** "I've reviewed the diet plan. I've added Whey Protein and Spinach to your shopping list. Let me know when you buy them."

---

## 3. Phase 2: Proactive Reminders (The Pulse)
1. **Task Registration**: The agent realizes it needs to follow up and calls `schedule_task(cron="0 18 * * *", intent="health-checkin")`.
2. **The Pulse**: At 6:00 PM, the background scheduler triggers the `health-checkin` intent.
3. **The Wake Up**: The Orchestrator mounts the `/workspaces/health_session_1/` workspace to a sandbox.
4. **Action**: The agent reads its session sequence in `SESSION.md`, sees the shopping list is incomplete, and sends a message to the channel:

> **Claw:** "Don't forget to buy that protein powder on your way home today!"

---

## 4. Phase 3: Task Completion & The Data Blurring
1. **User Action:** The user replies to the message, *"Bought the protein and spinach."*
2. **Update**: The agent wakes up, parses the message, and checks those items off its internal `SESSION.md` session list.

### Resolving Architectural Friction via the 3-Tier Model
In this scenario, there is no Python codebase housed in a **Tier 3 (`src/`)** directory. The user's shopping list, workout schedule, and lab results in the Session Workspace **are the entirety of the project**.

If the user subsequently connects this channel to a GitHub repository for backup purposes:
- The agent can safely execute `git init` directly inside the **Session Workspace (Tier 2)**.
- The agent's session scratchpad (`SESSION.md`) and the uploaded `diet_plan.pdf` *become* the Target Project for this intent.
- Because the core agent persona (`SOUL.md`) is physically isolated in the **Global Brain (Tier 1)**, the agent can commit and push its session notes to GitHub without ever accidentally leaking its system prompts.
