import logging
from collections.abc import AsyncIterator
from typing import Any

from adk_claw.domain.models import OrchestratorEvent
from adk_claw.host.queue.lane import LaneQueue, ExecutionFunc

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Manages multiple LaneQueues.
    """

    def __init__(self, execute_fn: ExecutionFunc) -> None:
        self._execute_fn = execute_fn
        self._lanes: dict[str, LaneQueue] = {}

    async def handle_message(
        self, lane_key: str, text: str, **kwargs: Any
    ) -> AsyncIterator[OrchestratorEvent]:
        """
        Routes a message to its corresponding LaneQueue.
        """
        lane = self._get_or_create_lane(lane_key)
        async for event in lane.handle_message(text=text, **kwargs):
            yield event

    def cancel_run(self, lane_key: str) -> None:
        """
        Signals the specified LaneQueue to cancel its current run.
        """
        lane = self._lanes.get(lane_key)
        if lane:
            lane.request_cancel()

    def _get_or_create_lane(self, lane_key: str) -> LaneQueue:
        """Helper to retrieve or initialize a LaneQueue."""
        if lane_key not in self._lanes:
            logger.info(f"Creating new LaneQueue for {lane_key}")
            self._lanes[lane_key] = LaneQueue(
                lane_key=lane_key, execute_fn=self._execute_fn
            )
        return self._lanes[lane_key]

    async def shutdown(self) -> None:
        """Shuts down all active LaneQueues."""
        for lane in self._lanes.values():
            await lane.stop()
        self._lanes.clear()
