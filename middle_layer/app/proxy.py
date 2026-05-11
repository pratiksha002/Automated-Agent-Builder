import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from app.config import settings


async def forward_request(request: Request) -> Response:
    """
    Forwards the incoming request to the backend and streams the response back.
    Preserves method, path, query params, headers, and body exactly.
    Strips the 'host' header so httpx uses the backend host instead.
    """
    # Build the target URL
    target_url = f"{settings.BACKEND_URL}{request.url.path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    # Forward all headers except 'host'
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() != "host"
    }

    # Read request body
    body = await request.body()

    async with httpx.AsyncClient(timeout=60.0) as client:
        backend_response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
        )

    # Stream the backend response back to the frontend
    return Response(
        content=backend_response.content,
        status_code=backend_response.status_code,
        headers=dict(backend_response.headers),
        media_type=backend_response.headers.get("content-type"),
    )