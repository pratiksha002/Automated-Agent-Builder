import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.seed import run_seed
from app.db.session import SessionLocal, create_all_tables
from app.models import Agent, AgentTool, APIKey, Conversation, Message, Model, User
from slowapi import _rate_limit_exceeded_handler
from app.core.limiter import limiter
# ─── STEP 5.5 — LOGGING SETUP ────────────────────────────────────────────────
# Configured before anything else so every module that calls
# logging.getLogger(__name__) at import time inherits this config.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── STEP 5.3 — RATE LIMITER SETUP ───────────────────────────────────────────
# Limiter is created before the FastAPI app so it can be attached to app.state.
# get_remote_address is the default key function — limits are per client IP.
# For authenticated endpoints, swap to a user-ID key function in a future pass.



# ─── APP INIT ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach limiter to app state so slowapi middleware can find it.
app.state.limiter = limiter


# ─── STEP 5.4 — CORS ─────────────────────────────────────────────────────────
# Must be registered BEFORE routers so preflight OPTIONS requests are
# handled correctly. Without this the browser blocks every request from
# the frontend with a CORS error.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,   # set in config.py / .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── STEP 5.1 — ERROR HANDLERS ───────────────────────────────────────────────

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Overrides slowapi's default plain-text 429 response with a clean
    JSON body consistent with all other error responses in this API.
    """
    logger.warning(
        f"rate_limit_exceeded: {request.method} {request.url} "
        f"client={request.client.host if request.client else 'unknown'}"
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Too many requests. Please slow down and try again shortly."
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic 422 validation errors (wrong types, missing fields,
    failed validators like content_must_not_be_blank).

    FastAPI's default 422 response buries the error inside a nested
    'loc'/'msg'/'type' structure. This flattens it into readable strings
    that the frontend can display directly.
    """
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"] if loc != "body")
        message = error["msg"]
        errors.append(f"{field}: {message}" if field else message)

    logger.info(
        f"validation_error: {request.method} {request.url} errors={errors}"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """
    Catches both explicit HTTPException(404) raises and FastAPI's automatic
    404 for unrecognised routes, and returns a consistent JSON body.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail if hasattr(exc, "detail") else "Not found"},
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.detail if hasattr(exc, "detail") else "Forbidden"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for any exception that isn't an HTTPException and wasn't
    caught closer to the source. Returns a clean 500 JSON response instead
    of leaking a Python stack trace to the client.

    The full traceback is logged server-side so it's available for debugging
    without being exposed to the caller.
    """
    logger.exception(
        f"unhandled_exception: {request.method} {request.url} "
        f"error={type(exc).__name__}: {exc}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal error occurred."},
    )


# ─── ROUTERS ─────────────────────────────────────────────────────────────────

app.include_router(v1_router)


# ─── STARTUP ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    logger.info("startup: creating tables and running seed...")
    create_all_tables()
    db = SessionLocal()
    try:
        run_seed(db)
        logger.info("startup: seed complete")
    finally:
        db.close()


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health():
    """
    Lightweight liveness probe. Load balancers and container orchestrators
    (Railway, Render, ECS) ping this to verify the app is running.
    No DB call — if the app is up enough to respond, this returns 200.
    """
    return {"status": "ok"}