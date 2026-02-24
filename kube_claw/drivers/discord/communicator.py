import discord
from typing import Any, Callable
from kube_claw.core.base import Communicator, Message


class DiscordMessage(Message):
    """Implementation of the Message protocol for Discord."""

    def __init__(self, message: discord.Message):
        self.content = message.content
        self.author_id = str(message.author.id)
        self.channel_id = str(message.channel.id)
        self.metadata = {
            "author_name": message.author.name,
            "created_at": message.created_at.isoformat(),
        }


class DiscordCommunicator(Communicator):
    """Communicator driver using the Discord API via discord.py."""

    def __init__(self, token: str):
        self.token = token
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.callback: Callable[[Message], Any] | None = None

        @self.client.event
        async def on_message(message: discord.Message) -> None:
            # Ignore messages from the bot itself
            if message.author == self.client.user:
                return
            if self.callback:
                await self.callback(DiscordMessage(message))

    async def send_message(self, channel_id: str, content: str) -> None:
        """Sends a message to the specified Discord channel."""
        channel = self.client.get_channel(int(channel_id))
        if not channel:
            # For cases where the channel is not yet in the cache, fetch it.
            channel = await self.client.fetch_channel(int(channel_id))

        if hasattr(channel, "send"):
            await channel.send(content)
        else:
            raise ValueError(f"Channel {channel_id} does not support sending messages.")

    async def listen(self, callback: Callable[[Message], Any]) -> None:
        """Starts the Discord bot and registers the message callback."""
        self.callback = callback
        async with self.client:
            await self.client.start(self.token)
