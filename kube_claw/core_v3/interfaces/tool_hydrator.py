"""
# Tool Hydrator Interface (Strategy/Adapter Pattern)

The Tool Hydrator is responsible for "hydrating" tool calls that originate from
the sandboxed worker. This process involves mapping "magic strings" and "abstract
secret names" to actual, high-security credentials stored on the Host.

## Key Responsibilities:
- **Credential Injection**: Replacing `auth: "default"` or `secret: "github_token"`
  with real API keys or tokens.
- **Identity Resolution**: Determining the correct scope (e.g., Slack Channel ID)
  based on the `WorkspaceContext` of the calling worker.
- **Safety Policy**: Verifying that the current `WorkspaceContext` has permission
  to use the requested tool or access the specific secret.

## Architectural Role:
This component acts as a **Protective Wrapper** or **Adapter** in the Domain layer,
ensuring that high-risk secrets never enter the potentially compromised sandbox.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from .binding_table import WorkspaceContext


class ToolCall(ABC):
    """
    Representation of a tool execution request from the worker.
    """

    namespace: str  # e.g., "slack", "research", "infra"
    method: str  # e.g., "send_message", "web_search"
    params: Dict[str, Any]


class ToolHydrator(ABC):
    """
    Service for resolving magic strings and secrets into concrete tool parameters.
    """

    @abstractmethod
    async def hydrate_call(
        self, context: WorkspaceContext, tool_call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Takes a raw tool call from the worker and returns a 'hydrated' call
        with real credentials and resolved identifiers.

        Args:
            context: The WorkspaceContext associated with the calling sandbox.
            tool_call: The raw JSON-RPC tool call (e.g., {"method": "slack.send_message", "params": {"channel": "current"}})

        Returns:
            A new tool call dictionary with 'hydrated' parameters.

        Raises:
            PermissionError: If the context does not have access to the tool/secret.
            ValueError: If the tool_call is malformed or resolution fails.
        """
        pass

    @abstractmethod
    async def execute_hydrated_call(self, hydrated_call: Dict[str, Any]) -> Any:
        """
        Executes the tool call on the Host side using the hydrated parameters.
        """
        pass
