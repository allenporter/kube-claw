import asyncio
import anyio
from mcp.client.session import ClientSession
import mcp.types as types
import logging

logger = logging.getLogger(__name__)


class WorkerMCPClient:
    """
    Client for connecting to the Host-side MCP server over UDS.
    """

    def __init__(self, mcp_socket_path: str):
        self.mcp_socket_path = mcp_socket_path
        self._session: ClientSession | None = None

    async def connect(self):
        # We need a custom transport for UDS because mcp-python-sdk
        # primarily supports stdio or SSE.
        # We'll bridge asyncio UDS to AnyIO streams.
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.mcp_socket_path), timeout=5.0
            )
        except Exception as e:
            logger.error(f"Failed to connect to MCP UDS at {self.mcp_socket_path}: {e}")
            raise

        # Bridge to AnyIO streams for the MCP session
        read_stream_writer, read_stream = anyio.create_memory_object_stream(10)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(10)

        async def reader_task():
            async with read_stream_writer:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    try:
                        await read_stream_writer.send(
                            types.JSONRPCMessage.model_validate_json(line)
                        )
                    except Exception:
                        pass

        async def writer_task():
            async with write_stream_reader:
                async for msg in write_stream_reader:
                    try:
                        writer.write(
                            msg.model_dump_json(
                                by_alias=True, exclude_none=True
                            ).encode()
                            + b"\n"
                        )
                        await writer.drain()
                    except Exception:
                        break

        # Start background bridge tasks
        asyncio.create_task(reader_task())
        asyncio.create_task(writer_task())

        self._session = ClientSession(read_stream, write_stream)
        await asyncio.wait_for(self._session.initialize(), timeout=5.0)
        return self._session

    async def call_tool(self, name: str, arguments: dict):
        if not self._session:
            return None
        return await self._session.call_tool(name, arguments)
