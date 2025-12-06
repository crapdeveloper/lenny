import uuid
from typing import Dict

from fastapi import APIRouter, Request, Response
from sse_starlette.sse import EventSourceResponse

from mcp.server.sse import SseServerTransport

from .server import mcp_server

router = APIRouter(prefix="/mcp", tags=["mcp"])

# Global dictionary to hold active transports
active_transports: Dict[str, SseServerTransport] = {}


@router.get("/sse")
async def handle_sse(request: Request):
    transport = SseServerTransport("/mcp/messages")

    # Generate a session ID
    session_id = str(uuid.uuid4())
    active_transports[session_id] = transport

    async def event_generator():
        try:
            # Send the endpoint event so the client knows where to send messages
            yield {"event": "endpoint", "data": f"/mcp/messages?session_id={session_id}"}

            # Run the server loop
            # Note: mcp_server.run is a context manager that runs the server
            async with mcp_server.run(
                transport.read_stream, transport.write_stream, transport.initial_messages
            ):
                async for message in transport.outgoing_messages:
                    yield message
        finally:
            if session_id in active_transports:
                del active_transports[session_id]

    return EventSourceResponse(event_generator())


@router.post("/messages")
async def handle_messages(request: Request):
    session_id = request.query_params.get("session_id")
    if not session_id or session_id not in active_transports:
        return Response(status_code=404, content="Session not found")

    transport = active_transports[session_id]

    async def dummy_send(message):
        pass

    # Forward the request to the transport
    # SseServerTransport.handle_post_message expects a Starlette-compatible scope, receive, send
    await transport.handle_post_message(request.scope, request.receive, dummy_send)

    return Response(status_code=202)
