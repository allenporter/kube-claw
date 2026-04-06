import pytest
from unittest.mock import AsyncMock, MagicMock
from adk_claw.domain.models import EventType
from adk_claw.gateway.discord import ProgressTracker

@pytest.mark.asyncio
async def test_progress_tracker_splitting():
    """Test that ProgressTracker splits large buffers."""
    channel = MagicMock()
    channel.send = AsyncMock()
    
    adapter = MagicMock()
    # Mock message return value
    mock_msg = MagicMock()
    mock_msg.id = 123
    mock_msg.edit = AsyncMock()
    channel.send.return_value = mock_msg
    
    tracker = ProgressTracker(channel=channel, lane_key="lane-1", adapter=adapter)
    # Set a small max_len for testing
    tracker._max_len = 100
    tracker._edit_debounce = 0  # No debounce
    
    # Add a large thought
    large_thought = "a" * 150
    # Expected formatted: "> " + "a" * 150 (len 152)
    await tracker.add_event(EventType.THOUGHT, large_thought)
    
    # 1. full_text = len 152
    # 2. current_msg is None, so it enters the "No current message, but buffer too long" block
    # 3. chunk = full_text[:100]
    # 4. send(chunk)
    # 5. buffer = [remaining] (len 52)
    
    assert channel.send.call_count == 1
    sent_text = channel.send.call_args[0][0]
    assert len(sent_text) == 100
    assert sent_text == ("> " + large_thought)[:100]
    assert tracker._buffer == [("> " + large_thought)[100:]]
    assert len(tracker._buffer[0]) == 52

@pytest.mark.asyncio
async def test_progress_tracker_debounce():
    """Test that ProgressTracker debounces edits."""
    channel = MagicMock()
    channel.send = AsyncMock(return_value=MagicMock())
    adapter = MagicMock()
    
    tracker = ProgressTracker(channel=channel, lane_key="lane-1", adapter=adapter)
    tracker._edit_debounce = 10.0  # High debounce
    
    await tracker.add_event(EventType.STATUS, "Status 1")
    assert channel.send.call_count == 1
    
    await tracker.add_event(EventType.STATUS, "Status 2")
    # Should not send or edit yet due to debounce
    assert channel.send.call_count == 1
    assert channel.send.return_value.edit.call_count == 0
    
    # Finalize should force sync
    await tracker.finalize()
    # Finalize calls sync(force=True)
    # If buffer was ["`Status 1`", "`Status 2`"], and send was called with ["`Status 1`"]
    # Sync with force=True should call edit with full buffer
    assert channel.send.return_value.edit.call_count == 1
