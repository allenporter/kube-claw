import asyncio
from typing import Any, Callable
from aioconsole import ainput
from kube_claw.v1_legacy.core.base import Communicator, Message


class FakeMessage(Message):
    """Simple implementation of the Message protocol for the CLI."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.author_id = "local-user"
        self.channel_id = "cli-session"
        self.metadata = {"platform": "cli"}


class FakeCommunicator(Communicator):
    """
    Communicator driver for local development using terminal input/output.
    Uses aioconsole to ensure the input loop doesn't block the asyncio event loop.
    """

    def __init__(self) -> None:
        self.callback: Callable[[Message], Any] | None = None
        self._canned_responses = {
            "hello": "Hi there! I'm the KubeClaw fake agent.",
            "help": "Available commands: !run <task>, !status, hello, help",
        }

    async def send_message(self, channel_id: str, content: str) -> None:
        """Prints the message to the console with formatting."""
        print(f"\n[ClawBot]: {content}")
        # Re-print the prompt to maintain UI consistency
        print("User> ", end="", flush=True)

    async def listen(self, callback: Callable[[Message], Any]) -> None:
        """Starts the interactive CLI loop."""
        self.callback = callback
        print("=== KubeClaw Fake Communicator Started ===")
        print("Type '!run <task>' to schedule a job or 'exit' to quit.")

        while True:
            try:
                user_input = await ainput("User> ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    print("Shutting down...")
                    return

                # Handle hardcoded canned responses first
                if user_input.lower() in self._canned_responses:
                    await self.send_message(
                        "cli-session", self._canned_responses[user_input.lower()]
                    )
                    continue

                if self.callback:
                    await self.callback(FakeMessage(user_input))

            except EOFError:
                break
            except Exception as e:
                print(f"Error in CLI loop: {e}")
                await asyncio.sleep(1)
