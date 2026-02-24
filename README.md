# kube-claw (Claw Core)

**Claw Core** is a minimalist, model-agnostic AI agent framework based on the **NanoClaw** philosophy. It is designed to manage Kubernetes-based workloads, developer environments, and communication channels (starting with Discord) using the **Google ADK** (Agent Development Kit).

## 💡 Philosophy

- **Minimalist**: Prioritizes simple, readable, and maintainable solutions over complex abstractions.
- **Model Agnostic**: Designed to run across various LLMs (Gemini, Ollama, Claude, etc.) via the `adk-cli` or compatible drivers.
- **Environment-First**: Operates natively within a Kubernetes cluster, utilizing cluster resources (Jobs, PVCs, etc.) as its "body".
- **Human-in-the-Loop**: Built-in safety requirements for destructive or public-facing actions.
- **GitOps Driven**: All configurations and code changes are version-controlled.

## 🏗️ Architecture

Claw Core provides the foundational identity and system instructions for the NanoClaw ecosystem.

- **`kube_claw/core/`**: Contains the core identity and system instructions.
- **Kubernetes**: Used as the primary job execution engine for workers and isolated tasks.
- **Discord**: Initial communication hub for tasking and updates.
- **ADK Powered**: Built on top of the Google ADK for tool use and agent orchestration.

## 🚀 Getting Started

### Prerequisites

- Python 3.14+
- `uv` (recommended for dependency management)
- Access to a Kubernetes cluster (for full functionality)

### Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/allenporter/kube_claw.git
    cd kube_claw
    ```

2.  Run the setup script to initialize the virtual environment and pre-commit hooks:
    ```bash
    ./script/setup
    ```

### Testing & Linting

- Run tests: `./script/test`
- Run linters: `./script/lint`

## 🛠️ Usage

Claw Core is intended to be used with the `adk-cli`. You can load the core system instructions into your agent driver:

```python
from kube_claw.core.identity import get_system_instruction

instruction = get_system_instruction()
# Pass instruction to your ADK agent or LLM driver
```

## 🗺️ Roadmap

- [ ] Define abstract interfaces for "Job Scheduling" and "Communication".
- [ ] Implement Kubernetes-specific job management logic.
- [ ] Create the Discord connector.
- [ ] Enhance failure recovery and idempotency.

## 📄 License

Apache-2.0 - See [LICENSE](LICENSE) for details.
