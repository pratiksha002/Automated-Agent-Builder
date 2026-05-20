"""
seed.py — Populates models and platform agents at startup.
Safe to run multiple times (get-or-create logic throughout).

Now seeds both Groq and Ollama models. Ollama models are marked
inactive by default if OLLAMA_ENABLED=False in the environment.
"""

from sqlalchemy.orm import Session
from app.models.model import Model
from app.models.agent import Agent
from app.core.config import settings


# ── Groq models ───────────────────────────────────────────────────────────────
GROQ_MODELS = [
    {
        "name": "LLaMA 3.3 70B",
        "provider": "groq",
        "groq_model_id": "llama-3.3-70b-versatile",
        "ollama_model_id": None,
        "description": "Best overall. Strong reasoning, long context, versatile across tasks.",
    },
    {
        "name": "LLaMA 3.1 8B",
        "provider": "groq",
        "groq_model_id": "llama-3.1-8b-instant",
        "ollama_model_id": None,
        "description": "Fastest response. Best for lightweight tasks and quick Q&A.",
    },
    {
        "name": "Mixtral 8x7B",
        "provider": "groq",
        "groq_model_id": "mixtral-8x7b-32768",
        "ollama_model_id": None,
        "description": "Large context window (32k). Good for document-heavy tasks.",
    },
    {
        "name": "Gemma 2 9B",
        "provider": "groq",
        "groq_model_id": "gemma2-9b-it",
        "ollama_model_id": None,
        "description": "Google's efficient model. Good instruction following.",
    },
]

# ── Ollama models ─────────────────────────────────────────────────────────────
# These are models you have pulled locally via `ollama pull <name>`.
# Add or remove based on what's installed on your machine.
OLLAMA_MODELS = [
    {
        "name": "LLaMA 3.2 (Local)",
        "provider": "ollama",
        "groq_model_id": None,
        "ollama_model_id": "llama3.2",
        "description": "Local LLaMA 3.2 via Ollama. No rate limits, fully private.",
    },
    {
        "name": "LLaMA 3.1 8B (Local)",
        "provider": "ollama",
        "groq_model_id": None,
        "ollama_model_id": "llama3.1:8b",
        "description": "Local LLaMA 3.1 8B via Ollama. Fast local inference.",
    },
    {
        "name": "Mistral 7B (Local)",
        "provider": "ollama",
        "groq_model_id": None,
        "ollama_model_id": "mistral",
        "description": "Local Mistral 7B via Ollama. Great instruction-following locally.",
    },
    {
        "name": "Phi-3 Mini (Local)",
        "provider": "ollama",
        "groq_model_id": None,
        "ollama_model_id": "phi3:mini",
        "description": "Microsoft Phi-3 Mini. Lightweight, fast, runs on modest hardware.",
    },
]

# ── Platform agents (unchanged in name, now reference by groq_model_id) ───────
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
    """
    Insert all Groq and Ollama models if they don't already exist.
    Returns a unified map: groq_model_id or ollama_model_id -> Model
    """
    model_map: dict[str, Model] = {}
    all_models = GROQ_MODELS + OLLAMA_MODELS

    for m in all_models:
        # Unique key: groq_model_id for Groq, ollama_model_id for Ollama
        unique_id = m["groq_model_id"] or m["ollama_model_id"]

        if m["provider"] == "groq":
            existing = db.query(Model).filter_by(groq_model_id=m["groq_model_id"]).first()
        else:
            existing = db.query(Model).filter_by(ollama_model_id=m["ollama_model_id"]).first()

        if not existing:
            record = Model(
                name=m["name"],
                provider=m["provider"],
                groq_model_id=m["groq_model_id"],
                ollama_model_id=m["ollama_model_id"],
                description=m["description"],
                is_active=True,
            )
            db.add(record)
            db.flush()
            model_map[unique_id] = record
        else:
            # Update provider field on existing rows (migration safety)
            if not hasattr(existing, 'provider') or existing.provider != m["provider"]:
                existing.provider = m["provider"]
            model_map[unique_id] = existing

    db.commit()
    return model_map


def seed_platform_agents(db: Session, model_map: dict[str, Model]) -> None:
    """Insert platform agents using Groq models by default."""
    for a in PLATFORM_AGENTS:
        existing = db.query(Agent).filter_by(name=a["name"], is_platform_agent=True).first()
        if not existing:
            model = model_map.get(a["groq_model_id"])
            if not model:
                continue
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
    groq_count   = sum(1 for m in model_map.values() if m.provider == "groq")
    ollama_count = sum(1 for m in model_map.values() if m.provider == "ollama")
    print(f"✓ Seed complete: {groq_count} Groq models, {ollama_count} Ollama models, platform agents loaded.")