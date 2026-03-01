import uuid
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ClawIdentity:
    """Represents a user's identity across different protocols."""

    protocol: str  # e.g., "discord", "shell", "whatsapp"
    author_id: str
    name: str | None = None


@dataclass(frozen=True)
class InboundMessage:
    """A normalized message from any gateway/protocol."""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    identity: ClawIdentity = field(
        default_factory=lambda: ClawIdentity(protocol="unknown", author_id="unknown")
    )
    channel_id: str = "default"
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def lane_id(self) -> str:
        """The stable identifier for this conversation lane."""
        return f"{self.identity.protocol}:{self.channel_id}:{self.identity.author_id}"


class WorkspaceContext(BaseModel):
    """
    Metadata about the execution environment (Lane).
    """

    workspace_id: str
    pvc_name: str | None = None
    auth_profile: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SandboxStatus(BaseModel):
    """
    The current state of a sandbox/lane.
    """

    is_running: bool
    last_known_status: str
    connection_endpoint: str | None = None  # A2A UDS path or TCP address
    mcp_endpoint: str | None = None  # MCP UDS path
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class OrchestratorEvent:
    """An event emitted by the Orchestrator to be sent back to the Gateway."""

    type: str  # "thought", "token", "artifact", "status", "error"
    content: Any
    message_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
