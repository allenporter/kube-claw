import asyncio
import os
import anyio
from mcp.shared.message import SessionMessage
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions
import mcp.types as types
from .server import create_mcp_server


async def run_mcp_server_on_uds(socket_path: str, lane_id: str, workspace_path: str):
    """
    Starts an MCP server listening on a Unix Domain Socket.
    Uses AnyIO memory streams to bridge asyncio streams to the MCP SDK's expectations.
    """
    if os.path.exists(socket_path):
        os.remove(socket_path)

    mcp_instance = create_mcp_server(lane_id, workspace_path)
    low_level_server = mcp_instance._mcp_server

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        # Create AnyIO memory streams to bridge to MCP
        # We use a TaskGroup to manage the reader/writer loops and the MCP server itself.
        read_stream_writer, read_stream = anyio.create_memory_object_stream(10)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(10)

        async def reader_task():
            try:
                async with read_stream_writer:
                    while True:
                        line = await reader.readline()
                        if not line:
                            break
                        try:
                            # Parse the JSON-RPC message and wrap it for MCP
                            message = types.JSONRPCMessage.model_validate_json(line)
                            await read_stream_writer.send(SessionMessage(message))
                        except Exception as e:
                            print(f"MCP Server Reader Error: {e}")
            except anyio.ClosedResourceError:
                pass

        async def writer_task():
            try:
                async with write_stream_reader:
                    async for session_message in write_stream_reader:
                        # Serialize and write back to the UDS
                        json_str = session_message.message.model_dump_json(
                            by_alias=True, exclude_none=True
                        )
                        writer.write(json_str.encode() + b"\n")
                        await writer.drain()
            except anyio.ClosedResourceError:
                pass
            except Exception as e:
                print(f"MCP Server Writer Error: {e}")

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(reader_task)
                tg.start_soon(writer_task)
                # Run the MCP server logic
                await low_level_server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="claw-mcp-server",
                        server_version="0.2.0",
                        capabilities=low_level_server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_unix_server(handle_client, path=socket_path)
    async with server:
        await server.serve_forever()
