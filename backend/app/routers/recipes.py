from __future__ import annotations

import re
from typing import List

from fastapi import APIRouter

from app.schemas.recipe import CleanStepsRequest, CleanStepsResponse
from app.services.llm_client import LLMAdaptationError, clean_recipe_steps_with_llm, sanitize_recipe_steps


router = APIRouter(tags=["recipes"])


def _fallback_steps(raw_text: str) -> List[str]:
    if not raw_text:
        return []
    normalized = raw_text.replace("\\r\\n", "\\n").replace("\\n", "\n")
    chunks = re.split(r"\n+|\s*\d+[\.\)]\s*", normalized)
    cleaned = []
    for chunk in chunks:
        text = chunk.strip().strip("[]'\"")
        if text:
            cleaned.append(text)
    return cleaned


@router.post("/clean_recipe_steps", response_model=CleanStepsResponse)
def clean_recipe_steps_endpoint(payload: CleanStepsRequest) -> CleanStepsResponse:
    text = payload.text or ""
    if not text.strip():
        return CleanStepsResponse(steps=[])

    try:
        steps = clean_recipe_steps_with_llm(text)
    except LLMAdaptationError:
        steps = sanitize_recipe_steps(_fallback_steps(text))
    return CleanStepsResponse(steps=steps)


__all__ = ["router"]
