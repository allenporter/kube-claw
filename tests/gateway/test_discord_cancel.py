"""Tests for Discord cancellation via 🛑 reaction."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import discord

from adk_claw.gateway.discord import DiscordAdapter


@pytest.fixture
def mock_host():
    host = MagicMock()
    host.cancel_run = AsyncMock()
    return host


@pytest.mark.asyncio
async def test_on_reaction_add_cancels_run(mock_host):
    """Test that 🛑 reaction on a registered message calls host.cancel_run."""
    adapter = DiscordAdapter(host=mock_host, token="fake-token")

    # Use patch to mock client.user which is a property
    with patch.object(
        discord.Client, "user", new_callable=PropertyMock
    ) as mock_user_prop:
        bot_user = MagicMock(spec=discord.ClientUser)
        mock_user_prop.return_value = bot_user

        # Register a message ID for a lane
        msg_id = 12345
        lane_key = "discord:channel:author"
        adapter.set_active_message(msg_id, lane_key)

        # Mock the reaction
        reaction = MagicMock(spec=discord.Reaction)
        reaction.emoji = "🛑"

        # Mock the message the reaction was added to
        message = MagicMock(spec=discord.Message)
        message.id = msg_id
        message.author = bot_user
        reaction.message = message

        # Mock the user who reacted (not the bot)
        user = MagicMock(spec=discord.User)

        # Call the event handler
        await adapter.on_reaction_add(reaction, user)

        # Verify cancel_run was called with the correct lane_key
        mock_host.cancel_run.assert_called_once_with(lane_key)


@pytest.mark.asyncio
async def test_on_reaction_add_ignores_other_emoji(mock_host):
    """Test that non-🛑 reactions are ignored."""
    adapter = DiscordAdapter(host=mock_host, token="fake-token")

    with patch.object(
        discord.Client, "user", new_callable=PropertyMock
    ) as mock_user_prop:
        bot_user = MagicMock(spec=discord.ClientUser)
        mock_user_prop.return_value = bot_user

        adapter.set_active_message(12345, "some-lane")

        reaction = MagicMock(spec=discord.Reaction)
        reaction.emoji = "👍"
        reaction.message.id = 12345
        reaction.message.author = bot_user

        await adapter.on_reaction_add(reaction, MagicMock(spec=discord.User))

        mock_host.cancel_run.assert_not_called()


@pytest.mark.asyncio
async def test_on_reaction_add_ignores_unregistered_message(mock_host):
    """Test that reactions on messages not in _active_progress_messages are ignored."""
    adapter = DiscordAdapter(host=mock_host, token="fake-token")

    with patch.object(
        discord.Client, "user", new_callable=PropertyMock
    ) as mock_user_prop:
        bot_user = MagicMock(spec=discord.ClientUser)
        mock_user_prop.return_value = bot_user

        reaction = MagicMock(spec=discord.Reaction)
        reaction.emoji = "🛑"
        reaction.message.id = 99999  # Not registered
        reaction.message.author = bot_user

        await adapter.on_reaction_add(reaction, MagicMock(spec=discord.User))

        mock_host.cancel_run.assert_not_called()
