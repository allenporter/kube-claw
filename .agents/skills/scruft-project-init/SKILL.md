name: scruft-project-init
description: Initialize a new Python project from a template using cruft (managed via uv). Use this when a user wants to start a new project based on a cookiecutter template while maintaining a link for future updates.

# Scruft Project Initialization

This skill guides you through initializing a new Python project using `cruft` (via `uv`) from a cookiecutter template.

## Workflow

1.  **Install Scruft**: Ensure `scruft` is installed in the environment.
    ```bash
    uv pip install scruft
    ```

2.  **Initialize Project**: Run `scruft create` with the desired template URL.
    ```bash
    uv run scruft create <template-url>
    ```
    *Example template*: `https://github.com/allenporter/cookiecutter-python`

3.  **Restructure (Optional)**: If the template creates a nested directory and the user wants a flat structure:
    *   Move files from the generated subdirectory to the root.
    *   Delete the now-empty subdirectory.
    *   **Crucial**: Update `.cruft.json` to reflect the new directory structure if necessary (though usually, cruft tracks the template relationship regardless of move, but check for path references).

4.  **Bootstrap Environment**: Run the project's setup scripts (if available).
    *   `./script/setup` or `./script/bootstrap`

5.  **Verify**: Run initial tests and linting to ensure the environment is healthy.
    *   `./script/test`
    *   `./script/lint`

## Best Practices

- Always use `uv` for package management and tool execution.
- If the project is moved to the root, ensure hidden files (like `.github`, `.gitignore`) are also moved.
- Verify that `pre-commit` hooks are installed during setup.
