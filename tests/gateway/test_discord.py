"""Tests for Discord channel adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from adk_claw.gateway.discord import DiscordAdapter, _split_message


def test_split_message_short() -> None:
    """Short messages are returned as-is."""
    assert _split_message("hello") == ["hello"]


def test_split_message_long() -> None:
    """Long messages are split at the limit."""
    text = "a" * 3000
    chunks = _split_message(text, max_len=2000)
    assert len(chunks) == 2
    assert len(chunks[0]) == 2000
    assert len(chunks[1]) == 1000


def test_split_message_at_newline() -> None:
    """Splitting prefers newline boundaries."""
    # First line is 100 chars, then a newline, then enough to exceed 200
    first_line = "a" * 100
    second_line = "b" * 150
    text = first_line + "\n" + second_line
    chunks = _split_message(text, max_len=200)
    assert chunks[0] == first_line
    assert chunks[1] == second_line


@pytest.fixture
def mock_host() -> MagicMock:
    host = MagicMock()
    host.setup_default_binding = AsyncMock()
    host.handle_message = AsyncMock()
    return host


def test_adapter_creates_client(mock_host: MagicMock) -> None:
    """DiscordAdapter should create a discord client."""
    adapter = DiscordAdapter(host=mock_host, token="fake-token")
    assert adapter.client is not None


@pytest.mark.asyncio
async def test_adapter_ignores_own_messages(mock_host: MagicMock) -> None:
    """Bot should ignore its own messages."""
    adapter = DiscordAdapter(host=mock_host, token="fake-token")

    # Simulate the bot's own user
    bot_user = MagicMock()
    adapter._client._connection.user = bot_user

    message = MagicMock()
    message.author = bot_user  # Message from the bot itself

    await adapter.on_message(message)
    mock_host.handle_message.assert_not_called()


@pytest.mark.asyncio
async def test_adapter_ignores_non_mention(mock_host: MagicMock) -> None:
    """Bot should ignore messages that don't mention it."""
    adapter = DiscordAdapter(host=mock_host, token="fake-token")

    bot_user = MagicMock()
    adapter._client._connection.user = bot_user

    message = MagicMock()
    message.author = MagicMock()  # Different user
    message.mentions = []  # No mentions
    message.channel = MagicMock()  # Not a DM
    message.channel.__class__ = type("TextChannel", (), {})  # Not DMChannel

    await adapter.on_message(message)
    mock_host.handle_message.assert_not_called()
