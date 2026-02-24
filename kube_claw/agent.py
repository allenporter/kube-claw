import logging
from kube_claw.core.base import Communicator, JobScheduler, Message


class ClawAgent:
    """The main Claw Agent controller that bridges communication and scheduling."""

    def __init__(self, communicator: Communicator, scheduler: JobScheduler):
        self.communicator = communicator
        self.scheduler = scheduler
        self.logger = logging.getLogger(__name__)

    async def on_message_received(self, message: Message) -> None:
        """Processes incoming messages from the communicator and schedules jobs."""
        self.logger.info(
            f"Received message from {message.author_id}: {message.content}"
        )

        # Basic task interpretation logic (placeholder)
        if message.content.startswith("!run "):
            task = message.content[len("!run ") :]
            context = {
                "author_id": message.author_id,
                "channel_id": message.channel_id,
                "metadata": message.metadata,
            }

            job_id = await self.scheduler.schedule_job(task, context)
            await self.communicator.send_message(
                message.channel_id, f"Job scheduled successfully. ID: {job_id}"
            )
        elif message.content == "!status":
            # This would require tracking job IDs for a given user or channel
            # Placeholder response for now
            await self.communicator.send_message(
                message.channel_id, "Status checking is not yet implemented."
            )

    async def run(self) -> None:
        """Starts the agent's main execution loop."""
        self.logger.info("Starting Claw Agent main loop...")
        await self.communicator.listen(self.on_message_received)
