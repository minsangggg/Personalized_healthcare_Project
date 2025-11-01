"""Recommendation engine facade."""

from typing import Any, Optional, Sequence

from .core.workflow import RecommendationWorkflow


class RecommendationEngine:
    def __init__(self, workflow: Optional[RecommendationWorkflow] = None) -> None:
        self._workflow = workflow or RecommendationWorkflow()

    def recommend(self, user_id: str, limit: int, exclude_ids: Optional[Sequence[int]] = None) -> Any:
        return self._workflow.recommend_json(user_id=user_id, limit=limit, exclude_ids=exclude_ids)


engine = RecommendationEngine()
