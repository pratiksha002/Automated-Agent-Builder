"""
feedback_service.py

The prompt improvement engine. Analyses thumbs-down responses and
generates targeted improvements to the agent's system prompt using
the same inference pipeline already in place (works for both Groq
and Ollama — whichever model is configured for the agent).

Loop:
  1. Collect pending thumbs-down messages for an agent
  2. For each: ask the LLM to diagnose what went wrong and propose
     a concrete addition or change to the system prompt
  3. Store the suggestion on the feedback row
  4. Agent owner reviews, optionally edits, and applies
  5. Applying writes to agent.system_prompt — instantly affects
     ALL future turns on BOTH Groq and Ollama for that agent
"""

import logging
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.feedback import (
    get_pending_negative_feedback,
    save_suggestion,
    mark_applied,
)
from app.crud.agent import get_agent_by_id
from app.crud.message import get_conversation_history
from app.services.agent_service import build_agent_config
from app.services.inference_service import call_llm

logger = logging.getLogger(__name__)


def generate_suggestions(db: Session, agent_id: uuid.UUID) -> list[dict]:
    """
    For each unanswered thumbs-down on this agent, calls the LLM to
    produce a concrete prompt improvement suggestion and saves it.

    Uses the agent's own configured model (Groq or Ollama) for the
    meta-analysis — no separate model needed.

    Returns a list of suggestion dicts for the API response.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = build_agent_config(db, agent_id)
    provider        = cfg["model"]["provider"]
    model_id        = cfg["model"]["groq_model_id"] or cfg["model"]["ollama_model_id"]
    current_prompt  = agent.system_prompt

    pending = get_pending_negative_feedback(db, agent_id, limit=5)
    if not pending:
        return []

    results = []

    for fb in pending:
        message = fb.message
        if not message:
            continue

        # Find the user message that preceded the bad response
        history = get_conversation_history(db, message.conversation_id)
        user_msg_content = ""
        for i, m in enumerate(history):
            if str(m.id) == str(message.id) and i > 0:
                user_msg_content = history[i - 1].content
                break

        meta_messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert AI prompt engineer. "
                    "Your task is to analyse a case where an AI agent gave a response "
                    "the user rated negatively, then produce a single, concrete, actionable "
                    "improvement to the agent's system prompt.\n\n"
                    "Output ONLY the improved instruction text — no explanation, "
                    "no preamble, no labels. Under 80 words. "
                    "Write it as a direct instruction to be added to the system prompt."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"CURRENT SYSTEM PROMPT:\n{current_prompt}\n\n"
                    f"USER MESSAGE:\n{user_msg_content}\n\n"
                    f"BAD RESPONSE (rated thumbs-down):\n{message.content}\n\n"
                    "What specific instruction should be added or changed in the system "
                    "prompt to produce a better response? Output only the instruction text."
                ),
            },
        ]

        try:
            suggestion_text = call_llm(provider, model_id, meta_messages)
            save_suggestion(db, fb.id, suggestion_text)
            logger.info(f"generate_suggestions: saved suggestion feedback_id={fb.id}")
            results.append({
                "feedback_id":     str(fb.id),
                "message_id":      str(message.id),
                "message_content": message.content,
                "user_message":    user_msg_content,
                "suggestion":      suggestion_text,
            })
        except Exception as e:
            logger.error(f"generate_suggestions: failed feedback_id={fb.id}: {e}")
            continue

    return results


def apply_suggestion(
    db: Session,
    agent_id: uuid.UUID,
    feedback_id: uuid.UUID,
    new_prompt: str,
) -> dict:
    """
    Applies the (possibly owner-edited) suggestion as the agent's new
    system prompt and marks the feedback row as applied.

    The updated prompt takes effect immediately for ALL future turns
    on both Groq and Ollama — there is no separate per-provider prompt.
    """
    agent = get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not new_prompt or not new_prompt.strip():
        raise HTTPException(status_code=422, detail="new_prompt cannot be blank")

    agent.system_prompt = new_prompt.strip()
    db.commit()
    db.refresh(agent)

    mark_applied(db, feedback_id)

    logger.info(
        f"apply_suggestion: agent_id={agent_id} "
        f"prompt updated to {len(agent.system_prompt)} chars"
    )

    return {"agent_id": str(agent_id), "new_prompt": agent.system_prompt}