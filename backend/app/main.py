import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.limiter import limiter
from app.db.seed import run_seed
from app.db.session import SessionLocal, create_all_tables

# Import ALL models so create_all_tables() picks them up at startup.
# MessageFeedback must be here so the feedback table is auto-created.
from app.models import (  # noqa: F401
    Agent, AgentTool, APIKey, Conversation,
    Message, MessageFeedback, Model, User,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title=settings.APP_NAME, docs_url="/docs", redoc_url="/redoc")
app.state.limiter = limiter

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://automated-agent-builder.vercel.app",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:5500"  # For VS Code Live Server if you use it
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers ────────────────────────────────────────────────────────────
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"rate_limit: {request.method} {request.url}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please slow down and try again shortly."},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"] if loc != "body")
        msg   = error["msg"]
        errors.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"detail": exc.detail if hasattr(exc, "detail") else "Not found"},
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=403,
        content={"detail": exc.detail if hasattr(exc, "detail") else "Forbidden"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"unhandled: {request.method} {request.url} {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal error occurred."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(v1_router)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    logger.info("startup: creating tables...")
    create_all_tables()   # creates message_feedback table automatically
    db = SessionLocal()
    try:
        run_seed(db)
        logger.info("startup: seed complete")
    finally:
        db.close()


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}