# Project TODOs

- [ ] Fix `adk-cli` built-in skill packaging.
    - Currently, built-in skills like `feature-dev` and `skill-creator` are present in the source but may not be correctly packaged or accessible via the `load_skill` tool in all environments.
    - Ensure `adk-cli` can properly discover and load these skills from its internal installation path.
