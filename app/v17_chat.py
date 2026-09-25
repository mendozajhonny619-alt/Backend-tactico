from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.v17.ai.v17_assistant_ai import V17AssistantAI


router = APIRouter(prefix="/v17", tags=["V17 Chat Assistant"])

assistant_ai = V17AssistantAI()


class V17ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    dashboard_snapshot: Optional[Dict[str, Any]] = None
    selected_match: Optional[Dict[str, Any]] = None
    mode: str = "quick"
    conversation: Optional[List[Dict[str, Any]]] = None


@router.post("/chat")
def v17_chat(payload: V17ChatRequest) -> Dict[str, Any]:
    result = assistant_ai.answer(
        question=payload.question,
        dashboard_snapshot=payload.dashboard_snapshot or {},
        selected_match=payload.selected_match,
        mode=payload.mode,
        conversation=payload.conversation or [],
    )

    return {
        "ok": result.get("ok", True),
        "mode": result.get("mode", payload.mode),
        "answer": result.get("answer"),
        "model": result.get("model"),
        "used_openai": result.get("used_openai", False),
        "context_summary": result.get("context_summary", {}),
        "error": result.get("error"),
}
