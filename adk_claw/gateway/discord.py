"""
Discord Channel Adapter.

Connects a Discord bot to the adk-claw orchestrator. Listens for
@mentions and DMs, routes messages through the host, and streams
agent responses back to the channel.
"""

import logging

import discord

from adk_claw.domain.models import EventType
from adk_claw.host.host import ClawHost

logger = logging.getLogger(__name__)


class DiscordAdapter:
    """
    Channel adapter for Discord using discord.py.

    Listens for messages where the bot is mentioned or receives a DM,
    then routes them through ``ClawHost.handle_message()`` and sends
    the agent's response back to the originating channel.
    """

    def __init__(self, host: ClawHost, token: str) -> None:
        self._host = host
        self._token = token

        intents = discord.Intents.default()
        intents.message_content = True
        self._client = discord.Client(intents=intents)

        self._client.event(self.on_ready)
        self._client.event(self.on_message)

    @property
    def client(self) -> discord.Client:
        """The underlying discord.py client."""
        return self._client

    async def start(self) -> None:
        """Start the Discord bot."""
        await self._client.start(self._token)

    async def stop(self) -> None:
        """Disconnect the Discord bot."""
        await self._client.close()

    async def on_ready(self) -> None:
        """Called when the bot connects to Discord."""
        logger.info("Discord adapter connected as %s", self._client.user)

    async def on_message(self, message: discord.Message) -> None:
        """Handle an incoming Discord message."""
        # Ignore messages from the bot itself
        if message.author == self._client.user:
            return

        # Only respond to @mentions or DMs
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = (
            self._client.user in message.mentions if self._client.user else False
        )

        if not is_dm and not is_mentioned:
            return

        # Strip the bot mention from the content
        content = message.content
        if self._client.user and not is_dm:
            content = content.replace(f"<@{self._client.user.id}>", "").strip()

        if not content:
            return

        logger.info(
            "Discord message from %s in %s: %s",
            message.author.name,
            message.channel,
            content[:80],
        )

        # Ensure binding exists for this channel
        channel_id = str(message.channel.id)
        author_id = str(message.author.id)

        await self._host.setup_default_binding(
            protocol="discord",
            channel_id=channel_id,
            author_id=author_id,
        )

        # Stream agent response back to the channel
        response_parts: list[str] = []

        async with message.channel.typing():
            async for event in self._host.handle_message(
                text=content,
                protocol="discord",
                channel_id=channel_id,
                author_id=author_id,
            ):
                if event.type == EventType.TOKEN:
                    response_parts.append(event.content)
                elif event.type == EventType.ERROR:
                    response_parts.append(f"⚠️ {event.content}")

        # Send the collected response
        if response_parts:
            full_response = "\n".join(response_parts)
            # Discord has a 2000 char limit per message
            for chunk in _split_message(full_response):
                await message.reply(chunk)


def _split_message(text: str, max_len: int = 2000) -> list[str]:
    """Split text into chunks that fit Discord's message limit."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split at a newline
        split_at = text.rfind("\n", 0, max_len)
        if split_at <= 0:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
