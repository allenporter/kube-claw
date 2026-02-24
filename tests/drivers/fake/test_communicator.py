import pytest
from unittest.mock import AsyncMock, patch
from kube_claw.drivers.fake.communicator import FakeCommunicator, FakeMessage


@pytest.mark.asyncio
async def test_fake_communicator_send_message(capsys):
    communicator = FakeCommunicator()
    await communicator.send_message("cli-session", "Hello, User!")

    captured = capsys.readouterr()
    assert "[ClawBot]: Hello, User!" in captured.out
    assert "User> " in captured.out


@pytest.mark.asyncio
async def test_fake_communicator_listen_exit():
    # Mocking aioconsole.ainput to simulate user typing "exit"
    with patch("kube_claw.drivers.fake.communicator.ainput", side_effect=["exit"]):
        communicator = FakeCommunicator()
        # No callback needed for exit test
        await communicator.listen(AsyncMock())


@pytest.mark.asyncio
async def test_fake_communicator_listen_canned_response(capsys):
    # Mocking aioconsole.ainput to simulate typing "hello" then "exit"
    with patch(
        "kube_claw.drivers.fake.communicator.ainput", side_effect=["hello", "exit"]
    ):
        communicator = FakeCommunicator()
        await communicator.listen(AsyncMock())

    captured = capsys.readouterr()
    assert "[ClawBot]: Hi there! I'm the KubeClaw fake agent." in captured.out


@pytest.mark.asyncio
async def test_fake_communicator_callback():
    # Mocking aioconsole.ainput to simulate typing "!run something" then "exit"
    with patch(
        "kube_claw.drivers.fake.communicator.ainput",
        side_effect=["!run something", "exit"],
    ):
        communicator = FakeCommunicator()
        callback = AsyncMock()
        await communicator.listen(callback)

        # callback should have been called with a FakeMessage
        callback.assert_called_once()
        message = callback.call_args[0][0]
        assert isinstance(message, FakeMessage)
        assert message.content == "!run something"


@pytest.mark.asyncio
async def test_fake_message():
    message = FakeMessage("Test content")
    assert message.content == "Test content"
    assert message.author_id == "local-user"
    assert message.channel_id == "cli-session"
    assert message.metadata == {"platform": "cli"}
