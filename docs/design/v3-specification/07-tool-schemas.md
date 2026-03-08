# Claw Core v3: Tool Strategy & Execution Model

This document defines how tools are classified and executed in the Claw Core architecture. To balance security with developer productivity, we use a **Hybrid Tooling Model**.

---

## 1. The Hybrid Model: "Direct" vs. "External MCP"

| Category | **Direct Execution (Local)** | **External MCP (Remote)** |
| :--- | :--- | :--- |
| **Location** | In the agent process (subprocess) | External MCP server |
| **Credential** | **Environment Variables** (scoped tokens) | **MCP server-managed** (tokens configured in server config) |
| **Examples** | `bash`, `ls`, `git`, `gh` CLI, `python` | `slack.send_message`, `stripe.create_invoice` |
| **Mechanism** | Standard Python `subprocess` via adk-coder tools | MCP client via `McpToolset` |
| **Risk** | Token exfiltration possible if workspace is compromised | Token is managed by the MCP server, not exposed to the agent |

---

## 2. Direct Tools (adk-coder Built-ins)

The agent executor uses adk-coder's 12 built-in tools for workspace operations:

| Tool | Category | Default Policy |
|---|---|---|
| `ls`, `cat`, `read_many_files`, `grep` | Read | Allow |
| `write_file`, `edit_file` | Write | Confirm |
| `bash` | Shell | Confirm (with safe-command allowlist) |
| `explore_codebase` | Sub-Agent | Allow |
| `design_architecture`, `review_work` | Sub-Agent | Allow |

For tools that need credentials (like GitHub `gh` CLI), **Short-Lived, Scoped Credentials** are injected as environment variables.

### GitHub Strategy:
- **Credential**: Fine-grained GitHub PAT or GitHub App Installation Token.
- **Scope**: Restricted to only the repositories associated with the current `WorkspaceContext`.
- **Injection**: Mounted as `GITHUB_TOKEN` environment variable.

---

## 3. External MCP Tools (Remote Servers)

For messaging platforms (Slack, Discord) or infrastructure (DigitalOcean, AWS), tools are accessed via external MCP servers configured in `.adk-claw.yaml`:

```yaml
mcp:
  servers:
    - name: github
      command: ["npx", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_TOKEN: ${GITHUB_TOKEN}
    - name: slack
      command: ["npx", "@modelcontextprotocol/server-slack"]
      env:
        SLACK_BOT_TOKEN: ${SLACK_BOT_TOKEN}
```

The agent connects to these via `McpToolset` at startup.

---

## 4. Security Enforcement & Auditing

1.  **Policy Engine**: The `CustomPolicyEngine` gates tool execution based on the configured mode (`ask`/`auto`/`plan`).
2.  **Scope Check**: Auth profiles contain scoped credentials — the agent can only access resources within its assigned workspace.
3.  **Approval Flow**: In `ask` mode, high-risk tools (e.g., `bash git push`, `write_file`) trigger a confirmation request routed to the user's channel.
