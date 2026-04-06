"""
Discord Channel Adapter.

Connects a Discord bot to the adk-claw host. Listens for
@mentions and DMs, routes messages through the host, and streams
agent responses back to the channel.
"""

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
        self, channel: discord.abc.Messageable, lane_key: str, adapter: "DiscordAdapter"
    ) -> None:
        self._channel = channel
        self._lane_key = lane_key
        self._adapter = adapter
        self._current_message: discord.Message | None = None
        self._buffer: list[str] = []
        self._last_edit_time = 0.0
        self._edit_debounce = 1.0  # seconds
        self._max_len = 1900  # Leave room for formatting

    async def add_event(self, event_type: EventType, content: str) -> None:
        """Add an event (thought, status, or token) to the tracker."""
        if event_type == EventType.THOUGHT:
            # Use blockquote for thoughts
            lines = content.splitlines()
            formatted = "\n".join([f"> {line}" for line in lines])
            self._buffer.append(formatted)
        elif event_type == EventType.STATUS:
            # Use code blocks for tool calls/status
            self._buffer.append(f"`{content}`")
        elif event_type == EventType.ERROR:
            self._buffer.append(f"⚠️ **Error:** {content}")

        await self._sync()

    async def finalize(self) -> None:
        """Ensure all buffered content is sent and clear the tracker."""
        await self._sync(force=True, is_finalizing=True)
        if self._current_message:
            self._adapter.clear_active_message(self._current_message.id)
            self._current_message = None
        self._buffer = []

    async def _sync(self, force: bool = False, is_finalizing: bool = False) -> None:
        """Sync the buffer to Discord, creating or editing messages as needed."""
        # Use a lock-like mechanism to prevent re-entry during a single sync call
        if getattr(self, "_is_syncing", False):
            return
        self._is_syncing = True

        try:
            now = time.time()
            if not force and (now - self._last_edit_time < self._edit_debounce):
                return

            full_text = "\n".join(self._buffer)
            if not full_text:
                return

            # If text is too long, we must split it or truncate it.
            # For progress tracking, if it's too long for a single edit,
            # it's usually better to start a new progress message.
            if len(full_text) > self._max_len:
                # Close out the current message with truncation notice
                truncated_text = (
                    full_text[: self._max_len] + "\n... (continued in next message)"
                )
                if self._current_message:
                    try:
                        await self._current_message.edit(content=truncated_text)
                    except Exception:
                        logger.warning("Failed to edit message for truncation")
                    self._adapter.clear_active_message(self._current_message.id)
                    self._current_message = None

                # Update buffer to only include what hasn't been sent yet
                # This is a bit tricky since we're appending.
                # Let's just start a fresh message for the overflow.
                self._buffer = [full_text[self._max_len :]]
                full_text = "\n".join(self._buffer)

            try:
                if not self._current_message:
                    self._current_message = await self._channel.send(full_text)
                    self._adapter.set_active_message(
                        self._current_message.id, self._lane_key
                    )
                    # Add the cancel reaction to the first progress message
                    try:
                        await self._current_message.add_reaction("🛑")
                    except Exception:
                        logger.debug("Could not add reaction to message")
                else:
                    await self._current_message.edit(content=full_text)
                self._last_edit_time = now
            except discord.errors.HTTPException as e:
                if e.code == 50035:  # Invalid Form Body (likely too long)
                    logger.warning(
                        "Discord message too long, clearing current message to start fresh"
                    )
                    self._current_message = None
                    # Try once more by sending as a new message
                    self._current_message = await self._channel.send(
                        full_text[: self._max_len]
                    )
                else:
                    raise
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
        self._active_progress_messages: dict[int, str] = {}  # msg_id -> lane_key

        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        self._client = discord.Client(intents=intents)

        self._client.event(self.on_ready)
        self._client.event(self.on_message)
        self._client.event(self.on_reaction_add)

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

    def set_active_message(self, message_id: int, lane_key: str) -> None:
        """Register a progress message for cancellation tracking."""
        self._active_progress_messages[message_id] = lane_key

    def clear_active_message(self, message_id: int) -> None:
        """Clear a progress message registration."""
        self._active_progress_messages.pop(message_id, None)

    async def on_ready(self) -> None:
        """Called when the bot connects to Discord."""
        logger.info("Discord adapter connected as %s", self._client.user)

    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.User | discord.Member
    ) -> None:
        """Listen for the stop reaction to cancel an in-progress run."""
        if user == self._client.user:
            return

        if str(reaction.emoji) == "🛑":
            # Check if this reaction is on a message we sent
            message = reaction.message
            if message.author != self._client.user:
                return

            # Determine the lane key for this message
            lane_key = self._get_lane_for_message(message.id)
            if lane_key:
                logger.info("Cancelling run for lane %s via 🛑 reaction", lane_key)
                await self._host.cancel_run(lane_key)
            else:
                logger.warning(
                    "Stop reaction on message %s, but no active lane found", message.id
                )

    def _get_lane_for_message(self, message_id: int) -> str | None:
        """Find the active lane key associated with a progress message."""
        return self._active_progress_messages.get(message_id)

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

            # Re-calculate lane_key to match host's internal logic
            lane_key = f"discord:{channel_id}:{author_id}"
            tracker = ProgressTracker(target_channel, lane_key, self)

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
