# Claw Core v3: Tool Strategy & Execution Model

This document defines how tools are classified and executed in the Claw Core v3 architecture. To balance security with developer productivity, we use a **Hybrid Tooling Model**.

---

## 1. The Hybrid Model: "Direct" vs. "Proxied"

| Category | **Direct Execution (Local)** | **Host-Proxied (RPC)** |
| :--- | :--- | :--- |
| **Location** | Inside the Sandbox (Container) | Outside the Sandbox (Host) |
| **Credential** | **Directly Mounted** (Env Vars / `.netrc`) | **Host-Stored** (Never enters sandbox) |
| **Examples** | `bash`, `ls`, `git`, `gh` CLI, `python` | `slack.send_message`, `stripe.create_invoice` |
| **Mechanism** | Standard Python `subprocess` | JSON-RPC `tool.call` to Host |
| **Risk** | Token exfiltration possible if sandbox is compromised. | Token is physically unreachable from the sandbox. |

---

## 2. Direct Tools (Mounted Credentials)

For tools with powerful CLIs (like GitHub or AWS), we mount **Short-Lived, Scoped Credentials** directly into the sandbox. This allows the LLM to use the full power of existing ecosystems without us writing a custom API wrapper for every function.

### GitHub Strategy:
- **Credential**: Fine-grained GitHub PAT or GitHub App Installation Token.
- **Scope**: Restricted to only the repositories associated with the current `WorkspaceContext`.
- **Injection**: Mounted as `GITHUB_TOKEN` environment variable.

---

## 3. Host-Proxied Tools (Hydrated via RPC)

For messaging platforms (Slack, Discord) or infrastructure (DigitalOcean, AWS Route53), we keep the credentials on the Host. The worker requests execution via RPC using "magic values" for addressing.

- **`"current"`**: Resolves to the specific Channel or User ID associated with the active session.
- **`"auto"`**: Let the host decide the best default.

### Slack Tools (`slack.*`)

#### `slack.send_message`
Sends a message to a Slack channel.
**Request:**
```json
{
  "channel": "current", // or "#channel-name"
  "text": "Task complete!"
}
```

---

## 4. The "Hacker Suite" (Hacker-Relevant Proxied Tools)

### Research & Intelligence (`research.*`)

#### `research.web_search`
Perform a web search using a search engine API (Hydrated by Host).
**Request:**
```json
{
  "query": "CVE-2023-XXXX exploit POC",
  "engine": "auto"
}
```

#### `research.screenshot`
Capture a screenshot of a URL using a headless browser (Executed on Host).
**Request:**
```json
{
  "url": "https://example.com/target-page",
  "full_page": true
}
```

### Infrastructure & Networking (`infra.*`)

#### `infra.provision_lab`
Spin up a temporary research environment (e.g., via Terraform/Cloud Hydrated by Host).
**Request:**
```json
{
  "template": "basic-vps",
  "provider": "auto",
  "tags": ["temp-lab", "project-x"]
}
```

#### `infra.get_secret`
Retrieve a secret from the Host's vault (Hydrated with Identity Check).
**Request:**
```json
{
  "secret_name": "target_api_key",
  "scope": "read-only"
}
```

---

## 5. Security Enforcement & Auditing

1.  **Identity Check**: Every RPC request is verified against the `SandboxID -> BindingTable` mapping.
2.  **Scope Check**: The Host verifies that the `AuthProfile` contains the necessary scopes before executing a proxied tool.
3.  **Approval Flow**: High-risk tools (e.g., `git push` to `main` or `aws.terminate_instance`) trigger a `tool.approval_request` RPC back to the user before the Host/Worker proceeds.
