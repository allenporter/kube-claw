from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol


class Message(Protocol):
    """Protocol for messages exchanged via Communicator."""

    content: str
    author_id: str
    channel_id: str
    metadata: Dict[str, Any]


class JobScheduler(ABC):
    """Abstract base class for scheduling and managing agent execution jobs."""

    @abstractmethod
    async def schedule_job(self, task: str, context: Dict[str, Any]) -> str:
        """
        Schedules a new execution job.
        Returns a unique job identifier.
        """
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> str:
        """Returns the current status of a job (e.g., 'pending', 'running', 'completed', 'failed')."""
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> None:
        """Cancels a scheduled or running job."""
        pass


class Communicator(ABC):
    """Abstract base class for external communication (e.g., Discord, Slack)."""

    @abstractmethod
    async def send_message(self, channel_id: str, content: str) -> None:
        """Sends a message to a specific channel."""
        pass

    @abstractmethod
    async def listen(self, callback: Any) -> None:
        """Starts listening for incoming messages and invokes the callback."""
        pass
