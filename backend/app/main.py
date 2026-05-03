from fastapi import FastAPI
from app.db.session import create_all_tables, SessionLocal
from app.db.seed import run_seed
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME)


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