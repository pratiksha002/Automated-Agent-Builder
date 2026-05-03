"""
seed.py — Run once at startup (or manually) to populate:
  - The models table with supported Groq models
  - The agents table with the 3 platform pre-built agents

Safe to run multiple times (uses get-or-create logic).
"""

from sqlalchemy.orm import Session
from app.models.model import Model
from app.models.agent import Agent


GROQ_MODELS = [
    {
        "name": "LLaMA 3.3 70B",
        "groq_model_id": "llama-3.3-70b-versatile",
        "description": "Best overall. Strong reasoning, long context, versatile across tasks.",
    },
    {
        "name": "LLaMA 3.1 8B",
        "groq_model_id": "llama-3.1-8b-instant",
        "description": "Fastest response. Best for lightweight tasks and quick Q&A.",
    },
    {
        "name": "Mixtral 8x7B",
        "groq_model_id": "mixtral-8x7b-32768",
        "description": "Large context window (32k). Good for document-heavy tasks.",
    },
    {
        "name": "Gemma 2 9B",
        "groq_model_id": "gemma2-9b-it",
        "description": "Google's efficient model. Good instruction following.",
    },
]


PLATFORM_AGENTS = [
    {
        "name": "General Assistant",
        "description": "A helpful, general-purpose assistant. Good starting point for any task.",
        "system_prompt": (
            "You are a helpful, accurate, and concise assistant. "
            "Answer questions clearly, ask for clarification when needed, "
            "and always be honest about what you don't know."
        ),
        "groq_model_id": "llama-3.3-70b-versatile",
    },
    {
        "name": "Code Helper",
        "description": "Specialized in writing, reviewing, and debugging code across languages.",
        "system_prompt": (
            "You are an expert software engineer. Help users write clean, efficient code. "
            "When reviewing code, identify bugs, suggest improvements, and explain your reasoning. "
            "Always specify the language and provide working examples."
        ),
        "groq_model_id": "llama-3.3-70b-versatile",
    },
    {
        "name": "Document Analyst",
        "description": "Summarizes, extracts, and answers questions from long documents.",
        "system_prompt": (
            "You are a precise document analyst. When given text or documents, "
            "summarize key points, extract structured information, and answer specific questions. "
            "Be factual and cite the relevant section when referencing document content."
        ),
        "groq_model_id": "mixtral-8x7b-32768",
    },
]


def seed_models(db: Session) -> dict[str, Model]:
    """Insert models if they don't already exist. Returns a groq_model_id -> Model map."""
    model_map = {}
    for m in GROQ_MODELS:
        existing = db.query(Model).filter_by(groq_model_id=m["groq_model_id"]).first()
        if not existing:
            record = Model(**m)
            db.add(record)
            db.flush()
            model_map[m["groq_model_id"]] = record
        else:
            model_map[m["groq_model_id"]] = existing
    db.commit()
    return model_map


def seed_platform_agents(db: Session, model_map: dict[str, Model]) -> None:
    """Insert platform agents if they don't already exist."""
    for a in PLATFORM_AGENTS:
        existing = db.query(Agent).filter_by(name=a["name"], is_platform_agent=True).first()
        if not existing:
            model = model_map[a["groq_model_id"]]
            agent = Agent(
                name=a["name"],
                description=a["description"],
                system_prompt=a["system_prompt"],
                model_id=model.id,
                owner_user_id=None,
                is_platform_agent=True,
                is_public=True,
            )
            db.add(agent)
    db.commit()


def run_seed(db: Session) -> None:
    model_map = seed_models(db)
    seed_platform_agents(db, model_map)
    print("✓ Seed complete: models and platform agents loaded.")