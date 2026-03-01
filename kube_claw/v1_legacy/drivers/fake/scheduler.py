import asyncio
import uuid
from typing import Any, Dict
from kube_claw.v1_legacy.core.base import JobScheduler


class FakeJobScheduler(JobScheduler):
    """
    In-memory JobScheduler for local development.
    Simulates job lifecycles (pending -> running -> completed) using background tasks.
    """

    def __init__(self, transition_delay: float = 2.0):
        # job_id -> {"status": str, "task": str, "context": dict, "metadata": dict}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.transition_delay = transition_delay

    async def schedule_job(self, task: str, context: Dict[str, Any]) -> str:
        """Schedules a fake job and kicks off a transition simulation."""
        job_id = f"fake-{uuid.uuid4().hex[:8]}"

        async with self._lock:
            self._jobs[job_id] = {
                "status": "pending",
                "task": task,
                "context": context,
                "metadata": context.get("metadata", {}),
            }

        # Start the background simulation task
        asyncio.create_task(self._simulate_job_lifecycle(job_id))

        return job_id

    async def get_job_status(self, job_id: str) -> str:
        """Returns the current simulated status of a job."""
        async with self._lock:
            job = self._jobs.get(job_id)
            return job["status"] if job else "not_found"

    async def cancel_job(self, job_id: str) -> None:
        """Cancels a job by moving it to a terminal 'failed' state."""
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "failed"

    async def _simulate_job_lifecycle(self, job_id: str) -> None:
        """Simulates the state transitions with small delays."""
        # Pending -> Running
        await asyncio.sleep(0.5)
        async with self._lock:
            if self._jobs[job_id]["status"] == "pending":
                self._jobs[job_id]["status"] = "running"

        # Running -> Completed
        # Simulating some 'work' taking time
        await asyncio.sleep(self.transition_delay)
        async with self._lock:
            if self._jobs[job_id]["status"] == "running":
                self._jobs[job_id]["status"] = "completed"

    async def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Utility for recovery/discovery simulation."""
        async with self._lock:
            return self._jobs.copy()
