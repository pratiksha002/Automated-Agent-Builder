from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.auth import verify_token
from app.proxy import forward_request

# ─── Rate Limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title=settings.APP_NAME)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "layer": "middle"}


# ─── Catch-all proxy route ────────────────────────────────────────────────────
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
)
@limiter.limit(settings.RATE_LIMIT)
async def gateway(request: Request, path: str) -> Response:
    """
    Single catch-all route that:
    1. Verifies the JWT (skips public paths)
    2. Forwards the request to the backend
    3. Returns the backend response to the frontend
    """
    verify_token(request)
    return await forward_request(request)