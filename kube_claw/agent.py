import asyncio
import logging
from typing import Dict
from kube_claw.core.base import Communicator, JobScheduler, Message


class ClawAgent:
    """The main Claw Agent controller that bridges communication and scheduling."""

    def __init__(
        self,
        communicator: Communicator,
        scheduler: JobScheduler,
        polling_interval: float = 2.0,
    ):
        self.communicator = communicator
        self.scheduler = scheduler
        self.polling_interval = polling_interval
        self.logger = logging.getLogger(__name__)

        # Track jobs that we are currently monitoring for status changes
        self.active_jobs: Dict[str, Dict] = {}  # job_id -> {channel_id, last_status}
        self.monitoring_task: asyncio.Task | None = None

    async def on_message_received(self, message: Message) -> None:
        """Processes incoming messages from the communicator and schedules jobs."""
        self.logger.info(
            f"Received message from {message.author_id}: {message.content}"
        )

        content = message.content.strip()

        # Basic task interpretation logic
        if content.startswith("!run "):
            task = content[len("!run ") :]
            context = {
                "author_id": message.author_id,
                "channel_id": message.channel_id,
                "metadata": message.metadata,
            }

            job_id = await self.scheduler.schedule_job(task, context)

            # Record active job for monitoring
            self.active_jobs[job_id] = {
                "channel_id": message.channel_id,
                "last_status": "pending",
            }

            await self.communicator.send_message(
                message.channel_id, f"Job scheduled successfully. ID: {job_id}"
            )

        elif content == "!status":
            if not self.active_jobs:
                await self.communicator.send_message(
                    message.channel_id, "No active jobs."
                )
                return

            status_summary = []
            for jid, job_info in list(self.active_jobs.items()):
                status = await self.scheduler.get_job_status(jid)
                status_summary.append(f"Job {jid}: {status}")

            await self.communicator.send_message(
                message.channel_id, "\n".join(status_summary)
            )

    async def _monitor_jobs(self) -> None:
        """Background loop to poll the scheduler for job status changes."""
        self.logger.info("Starting background job monitoring loop...")
        while True:
            try:
                # Copy keys because we might modify active_jobs
                job_ids = list(self.active_jobs.keys())
                for job_id in job_ids:
                    job_info = self.active_jobs.get(job_id)
                    if not job_info:
                        continue

                    current_status = await self.scheduler.get_job_status(job_id)

                    if current_status != job_info["last_status"]:
                        self.logger.info(
                            f"Job {job_id} changed state: {job_info['last_status']} -> {current_status}"
                        )
                        job_info["last_status"] = current_status

                        # Notify the communicator on completion or failure
                        if current_status in ("completed", "failed", "cancelled"):
                            await self.communicator.send_message(
                                job_info["channel_id"],
                                f"Job {job_id} has {current_status}.",
                            )
                            # Stop monitoring finished jobs
                            self.active_jobs.pop(job_id, None)

                await asyncio.sleep(self.polling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in job monitoring loop: {e}")
                await asyncio.sleep(self.polling_interval)

    async def run(self) -> None:
        """Starts the agent's main execution loop."""
        self.logger.info("Starting Claw Agent main loop...")

        # Start monitoring loop
        self.monitoring_task = asyncio.create_task(self._monitor_jobs())

        try:
            # Start listening for incoming messages
            await self.communicator.listen(self.on_message_received)
        finally:
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
