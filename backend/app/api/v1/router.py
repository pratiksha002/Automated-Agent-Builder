from fastapi import APIRouter
from app.api.v1 import auth, agents

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(agents.router)