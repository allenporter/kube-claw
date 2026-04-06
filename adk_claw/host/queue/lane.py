import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any, Protocol

from adk_claw.domain.models import OrchestratorEvent

logger = logging.getLogger(__name__)


class ExecutionFunc(Protocol):
    """Protocol for the function that executes a message turn."""

    def __call__(
        self, text: str, lane_key: str, **kwargs: Any
    ) -> AsyncIterator[OrchestratorEvent]: ...


class LaneQueue:
    """
    Manages a single execution lane, ensuring sequential message processing.

    It provides an execution loop that polls an internal queue and runs
    the agent turn via the provided execution function.
    """

    def __init__(self, lane_key: str, execute_fn: ExecutionFunc) -> None:
        self.lane_key = lane_key
        self._execute_fn = execute_fn
        self._queue: asyncio.Queue[
            tuple[str, asyncio.Queue[OrchestratorEvent | None], dict[str, Any]]
        ] = asyncio.Queue()
        self._loop_task: asyncio.Task | None = None
        self._is_running = False
        self._current_cancel_event: asyncio.Event | None = None

    async def start(self) -> None:
        """Start the background execution loop."""
        if self._is_running:
            return
        self._is_running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.debug(f"LaneQueue[{self.lane_key}] started")

    async def stop(self) -> None:
        """Stop the background execution loop and cancel current task."""
        self._is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.debug(f"LaneQueue[{self.lane_key}] stopped")

    async def handle_message(
        self, text: str, **kwargs: Any
    ) -> AsyncIterator[OrchestratorEvent]:
        """
        Enqueue a message and return an iterator for the streamed events.
        """
        if not self._is_running:
            await self.start()

        # Internal queue to bridge the execution loop back to this caller
        event_queue: asyncio.Queue[OrchestratorEvent | None] = asyncio.Queue()

        await self._queue.put((text, event_queue, kwargs))

        while True:
            event = await event_queue.get()
            if event is None:  # End of stream sentinel
                break
            yield event

    def request_cancel(self) -> None:
        """Cancel the current active run in this lane."""
        if self._current_cancel_event:
            self._current_cancel_event.set()
            logger.info(f"LaneQueue[{self.lane_key}] cancellation requested")

    async def _run_loop(self) -> None:
        """The main loop that processes messages sequentially."""
        while self._is_running:
            try:
                text, event_out, kwargs = await self._queue.get()
                self._current_cancel_event = asyncio.Event()

                try:
                    async for event in self._execute_fn(
                        text=text, lane_key=self.lane_key, **kwargs
                    ):
                        if self._current_cancel_event.is_set():
                            logger.info(f"LaneQueue[{self.lane_key}] cancelling run")
                            break
                        await event_out.put(event)
                except Exception as e:
                    logger.exception(f"Error in LaneQueue[{self.lane_key}] execution")
                    # Optionally yield an error event here if the execute_fn didn't catch it
                finally:
                    # Signal end of stream
                    await event_out.put(None)
                    self._current_cancel_event = None
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(f"Unexpected error in LaneQueue[{self.lane_key}] loop")
                await asyncio.sleep(1)  # Avoid tight error loop
