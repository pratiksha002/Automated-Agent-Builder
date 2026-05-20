"""
api/v1/models.py

Exposes the models table so the frontend can build its
groq_model_id / ollama_model_id → UUID map for the create-agent form.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.model import Model

router = APIRouter(prefix="/models", tags=["models"])


class ModelRead(BaseModel):
    id:              uuid.UUID
    name:            str
    provider:        str
    groq_model_id:   Optional[str] = None
    ollama_model_id: Optional[str] = None
    description:     Optional[str] = None
    is_active:       bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ModelRead])
def list_models(db: Session = Depends(get_db)):
    """
    Returns all active models (both Groq and Ollama).
    No auth required — model list is public.
    Used by the create-agent form to resolve model UUIDs.
    """
    return (
        db.query(Model)
        .filter(Model.is_active == True)
        .order_by(Model.provider, Model.name)
        .all()
    )