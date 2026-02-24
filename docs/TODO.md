# Project TODOs

## Core Development
- [x] Initial project setup and verification
- [x] Research OpenClaw and NanoClaw architectures
- [ ] Define Job Scheduling and Communication interfaces in `kube_claw/core/`
- [ ] Implement Kubernetes Job driver
- [ ] Implement Discord connector driver

## Tooling & Infrastructure
- [ ] Fix `adk-cli` built-in skill packaging.
    - Currently, built-in skills like `feature-dev` and `skill-creator` are present in the source but may not be correctly packaged or accessible via the `load_skill` tool in all environments.
- [ ] Add `code-explorer` skill if missing.
