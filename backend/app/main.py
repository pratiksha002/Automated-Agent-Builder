from fastapi import FastAPI
from app.db.session import create_all_tables, SessionLocal
from app.db.seed import run_seed
from app.core.config import settings
from app.models import User, Model, Agent, AgentTool, Conversation, Message, APIKey
from app.api.v1.router import router as v1_router  # ADD THIS

app = FastAPI(title=settings.APP_NAME)

app.include_router(v1_router)  # ADD THIS


@app.on_event("startup")
def on_startup():
    create_all_tables()
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}