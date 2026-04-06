"""
Discord Channel Adapter.

Connects a Discord bot to the adk-claw host. Listens for
@mentions and DMs, routes messages through the host, and streams
agent responses back to the channel.
"""

from collections.abc import Callable
import logging
import time

import discord

from adk_claw.domain.models import EventType
from adk_claw.host.host import ClawHost

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Manages a live-updating Discord message for agent progress.

    Handles editing the message with "thoughts" and tool summaries,
    splitting messages when they hit Discord's 2000-char limit,
    and debouncing edits to avoid rate-limiting.
    """

    def __init__(
        self,
        channel: discord.abc.Messageable,
        lane_key: str | None = None,
        on_cancel: Callable | None = None,
    ) -> None:
        self._channel = channel
        self._lane_key = lane_key
        self._on_cancel = on_cancel
        self._current_message: discord.Message | None = None
        self._buffer: list[str] = []
        self._last_edit_time = 0.0
        self._edit_debounce = 1.0  # seconds
        self._max_len = 1900  # Leave room for formatting
        self._is_syncing = False
        self._interrupted = False

    @property
    def current_message_id(self) -> int | None:
        """The ID of the current progress message."""
        return self._current_message.id if self._current_message else None

    async def interrupt(self) -> None:
        """Mark the tracker as interrupted and update the message."""
        self._interrupted = True
        prefix = "🛑 **Interruption requested...**"
        self._buffer.append(prefix)
        await self._sync(force=True)

    async def add_event(self, event_type: EventType, content: str) -> None:
        """Add an event (thought, status, or token) to the tracker."""
        prefix = ""
        if event_type == EventType.THOUGHT:
            prefix = "💭 "
        elif event_type == EventType.STATUS:
            prefix = "⚙️ "
        elif event_type == EventType.ERROR:
            prefix = "⚠️ "

        formatted = f"{prefix}{content}"
        self._buffer.append(formatted)
        await self._sync()

    async def finalize(self) -> None:
        """Ensure all buffered content is sent and clear the tracker."""
        await self._sync(force=True, is_finalizing=True)
        self._current_message = None
        self._buffer = []

    async def _sync(self, force: bool = False, is_finalizing: bool = False) -> None:
        """Sync the buffer to Discord, creating or editing messages as needed."""
        if self._is_syncing:
            return

        now = time.time()
        if not force and (now - self._last_edit_time < self._edit_debounce):
            return

        full_text = "\n".join(self._buffer)
        if not full_text:
            return

        # If text is too long, flush the current message and start a new one
        if len(full_text) > self._max_len:
            # Prevent infinite recursion if we're already finalizing
            if not is_finalizing:
                self._is_syncing = True
                try:
                    await self.finalize()
                finally:
                    self._is_syncing = False
            return

        self._is_syncing = True
        try:
            if not self._current_message:
                self._current_message = await self._channel.send(full_text)
                # Add the cancel reaction to the first progress message
                try:
                    await self._current_message.add_reaction("🛑")
                except Exception:
                    logger.debug("Could not add reaction to message")

                # If this message belongs to a lane, notify the adapter
                if self._lane_key and self._on_cancel:
                    await self._on_cancel(self._current_message.id, self._lane_key)
            else:
                await self._current_message.edit(content=full_text)
            self._last_edit_time = now
        except Exception:
            logger.exception("Failed to sync progress to Discord")
        finally:
            self._is_syncing = False


class DiscordAdapter:
    """
    Channel adapter for Discord using discord.py.

    Listens for messages where the bot is mentioned or receives a DM,
    then routes them through ``ClawHost.handle_message()`` and sends
    the agent's response back to the channel.
    """

    def __init__(self, host: ClawHost, token: str) -> None:
        self._host = host
        self._token = token
        self._message_to_lane: dict[int, str] = {}
        self._lane_to_tracker: dict[str, ProgressTracker] = {}

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        # Explicitly enable history to ensure message objects are fully populated
        intents.value |= 1 << 16

        self._client = discord.Client(intents=intents)

        self._client.event(self.on_ready)
        self._client.event(self.on_message)
        self._client.event(self.on_reaction_add)

    async def _register_tracker(self, message_id: int, lane_key: str) -> None:
        """Link a progress message to its execution lane for cancellation."""
        self._message_to_lane[message_id] = lane_key
        logger.debug(f"Registered message {message_id} to lane {lane_key}")

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

    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.User | discord.Member
    ) -> None:
        """Listen for the stop reaction to cancel an in-progress run."""
        if user == self._client.user:
            return

        emoji = str(reaction.emoji)
        message = reaction.message
        message_id = message.id

        # Log all reactions at INFO level for now to debug
        logger.info(
            "REACTION: %s by %s (%s) on message %s (Author: %s)",
            emoji,
            user.name,
            user.id,
            message_id,
            message.author.name if message.author else "Unknown",
        )

        if emoji == "🛑":
            # 1. Primary Lookup: Direct mapping (bot's progress message)
            lane_key = self._message_to_lane.get(message_id)

            # 2. Secondary Lookup: Thread context (reaction on ANY message in the thread)
            if not lane_key and isinstance(message.channel, discord.Thread):
                logger.info(
                    "DEBUG: 🛑 on thread, checking lane mapping for thread ID %s",
                    message.channel.id,
                )
                # We need a way to link the thread back to the lane.
                # Since lane_key is protocol:channel_id:author_id, and channel_id is the thread ID...
                # Let's try to find a lane that ends with this channel_id.
                thread_id_str = str(message.channel.id)
                for lk in self._lane_to_tracker.keys():
                    if f":{thread_id_str}:" in lk or lk.endswith(f":{thread_id_str}"):
                        lane_key = lk
                        logger.info("DEBUG: Found lane %s via thread context", lane_key)
                        break

            if lane_key:
                logger.info(
                    "🛑 Cancellation requested via Discord on lane %s", lane_key
                )
                await self._host.cancel_run(lane_key)

                # Visual feedback: Ack the stop reaction with a checkmark
                try:
                    await reaction.message.add_reaction("✅")
                except Exception:
                    pass

                tracker = self._lane_to_tracker.get(lane_key)
                if tracker:
                    await tracker.interrupt()

                self._message_to_lane.pop(message_id, None)
            else:
                logger.debug("Stop reaction on unmapped message %s", message_id)

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

        try:
            # Use a thread for the conversation if possible
            target_channel: discord.abc.Messageable = message.channel
            if (
                not is_dm
                and hasattr(message.channel, "create_thread")
                and not isinstance(message.channel, discord.Thread)
            ):
                try:
                    thread_name = (
                        content[:50] + "..." if len(content) > 50 else content
                    ) or "Agent Conversation"
                    target_channel = await message.create_thread(
                        name=thread_name, auto_archive_duration=60
                    )
                except Exception:
                    logger.warning("Failed to create thread, falling back to channel")
                    target_channel = message.channel

            await self._host.setup_default_binding(
                protocol="discord",
                channel_id=channel_id,
                author_id=author_id,
            )

            # Generate the lane key for this session
            lane_key = f"discord:{channel_id}:{author_id}"

            tracker = ProgressTracker(
                target_channel,
                lane_key=lane_key,
                on_cancel=self._register_tracker,
            )
            self._lane_to_tracker[lane_key] = tracker

            async with target_channel.typing():
                async for event in self._host.handle_message(
                    text=content,
                    protocol="discord",
                    channel_id=channel_id,
                    author_id=author_id,
                ):
                    if event.type in [
                        EventType.THOUGHT,
                        EventType.STATUS,
                        EventType.ERROR,
                    ]:
                        await tracker.add_event(event.type, event.content)
                    elif event.type == EventType.TOKEN:
                        # Once we get a real response token, finalize the progress log
                        await tracker.finalize()
                        # Send token-based response in chunks
                        for chunk in _split_message(event.content):
                            await target_channel.send(chunk)

            await tracker.finalize()
            self._lane_to_tracker.pop(lane_key, None)

        except Exception:
            logger.exception("Error handling Discord message")
            try:
                await message.reply("⚠️ An error occurred processing your message.")
            except Exception:
                logger.exception("Failed to send error reply")


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
