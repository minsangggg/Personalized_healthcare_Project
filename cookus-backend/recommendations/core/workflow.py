"""High level recommendation workflow."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

from .llm import RecommendationLLM
from . import repository
from .utils import (
    _norm,
    _tokens_from_ingredient_full,
    diversify_candidates,
    ensure_diverse_top,
    enforce_ingredients_with_fridge,
    fridge_token_set,
    pick_keywords_from_fridge_all,
    recent_items_from_fridge,
)


class RecommendationWorkflow:
    def __init__(self, llm: Optional[RecommendationLLM] = None) -> None:
        self._llm = llm or RecommendationLLM()

    def recommend_json(
        self,
        user_id: Optional[str],
        limit: int = 3,
        exclude_ids: Optional[Sequence[int]] = None,
    ) -> Dict[str, Any]:
        uid = user_id or repository.pick_random_user_with_fridge()
        profile = repository.get_user_profile(uid)
        fridge = repository.get_user_fridge_items(uid)

        keywords = pick_keywords_from_fridge_all(fridge, max_n=30)
        recent = recent_items_from_fridge(fridge, days=10, top=8)

        recent_exclude = repository.recent_recommend_recipe_ids(uid)

        candidates = repository.fetch_candidates_like(keywords, limit=300, and_top=3)
        if len(candidates) < limit:
            candidates = repository.fetch_candidates_like(keywords, limit=300, and_top=2)
        if len(candidates) < limit:
            candidates = repository.fetch_candidates_like(keywords, limit=300, and_top=1)
        if len(candidates) < limit:
            candidates = repository.fetch_candidates_or_only(keywords, limit=300)

        exclude_all = set(exclude_ids or []) | set(recent_exclude)
        if exclude_all:
            candidates = [c for c in candidates if c.get("recipe_id") not in exclude_all]

        user_level = (profile.get("cooking_level") or "").strip()
        if user_level:
            level_filtered = [c for c in candidates if (str(c.get("level_nm") or "").strip() == user_level)]
        else:
            level_filtered = candidates
        pool = level_filtered if level_filtered else candidates

        try:
            random.shuffle(pool)
        except Exception:
            pool = list(pool)

        diversified = diversify_candidates(pool, want=max(12, limit * 4), max_per_main=1)
        diverse_pool = ensure_diverse_top(diversified, want=max(6, limit * 2))
        final_three = ensure_diverse_top(diverse_pool, want=limit) if diverse_pool else []

        if len(final_three) < limit and pool:
            chosen_ids = {c.get("recipe_id") for c in final_three if c.get("recipe_id") is not None}
            chosen_titles = {_norm(c.get("recipe_nm_ko") or "") for c in final_three}
            for candidate in pool:
                recipe_id = candidate.get("recipe_id")
                if recipe_id in chosen_ids:
                    continue
                title_norm = _norm(candidate.get("recipe_nm_ko") or "")
                if title_norm in chosen_titles:
                    continue
                final_three.append(candidate)
                if recipe_id is not None:
                    chosen_ids.add(recipe_id)
                chosen_titles.add(title_norm)
                if len(final_three) >= limit:
                    break

        if len(final_three) < limit:
            need = limit - len(final_three)
            chosen_ids = {c.get("recipe_id") for c in final_three if c.get("recipe_id") is not None}
            extras = repository.random_recipes_excluding(chosen_ids, need)
            for candidate in extras:
                if len(final_three) >= limit:
                    break
                recipe_id = candidate.get("recipe_id")
                if recipe_id in chosen_ids:
                    continue
                final_three.append(candidate)
                if recipe_id is not None:
                    chosen_ids.add(recipe_id)

        fridge_tokens = fridge_token_set(fridge)
        for candidate in final_three:
            tokens = _tokens_from_ingredient_full(candidate.get("ingredient_full"))
            missing = [token for token in tokens if token and token not in fridge_tokens]
            candidate["missing"] = missing[:6]

        if not final_three:
            llm_text_result = "**추천 가능한 레시피 후보가 부족합니다.** (냉장고 재료를 추가해 주세요)"
            adapted_rows: List[Dict[str, Any]] = []
        else:
            repository.ensure_recommend_recipe_table()
            adapted_rows = self._llm.adapt_recipes_json(uid, profile, fridge, final_three, recent)
            id_to_candidate = {candidate.get("recipe_id"): candidate for candidate in final_three}

            enforced_rows: List[Dict[str, Any]] = []
            for row in adapted_rows:
                candidate = id_to_candidate.get(row.get("recipe_id")) or {}
                enforced = enforce_ingredients_with_fridge(candidate, fridge, row.get("ingredient_full") or {})
                new_row = dict(row)
                new_row["ingredient_full"] = enforced
                enforced_rows.append(new_row)

            if not enforced_rows:
                fallback_rows = [
                    {
                        "id": str(uid),
                        "recipe_nm_ko": str(candidate.get("recipe_nm_ko") or ""),
                        "ingredient_full": candidate.get("ingredient_full") or {},
                        "step_text": str(candidate.get("step_text") or ""),
                        "recipe_id": candidate.get("recipe_id"),
                    }
                    for candidate in final_three
                ]
                repository.insert_recommend_recipes(fallback_rows)
                llm_text_result = "LLM 미사용: DB 후보를 기준으로 추천을 구성했어요."
                adapted_rows = fallback_rows
            else:
                repository.insert_recommend_recipes(enforced_rows)
                llm_text_result = RecommendationLLM.format_for_display(enforced_rows, profile, final_three)
                adapted_rows = enforced_rows

        def _fmt_name_amount(row: pd.Series) -> str:
            name = str(row["item_name"])
            amount = row.get("amount")
            if pd.isna(amount) or str(amount).strip() == "":
                return name
            return f"{name}({amount})"

        fridge_sample = fridge.apply(_fmt_name_amount, axis=1).head(8).tolist()

        return {
            "userId": uid,
            "fridgeSample": fridge_sample,
            "recentEmphasis": recent,
            "llm_recommendation_text": llm_text_result,
            "recommended_db_candidates": final_three,
            "adapted_recipes_saved": [
                {"recipe_nm_ko": row.get("recipe_nm_ko"), "recipe_id": row.get("recipe_id")}
                for row in adapted_rows
            ],
        }


__all__ = ["RecommendationWorkflow"]
