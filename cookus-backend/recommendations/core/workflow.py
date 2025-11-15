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

        recent_exclude = repository.recent_recommend_recipe_ids(uid)

        # 1차: 최소 2개의 재료가 겹치는 레시피를 AND 조건으로 검색
        candidates = repository.fetch_candidates_like(keywords, limit=300, and_top=2)
        # 2차: 그래도 부족하면 최소 1개 재료만 AND로 완화해서 검색
        if len(candidates) < limit:
            candidates = repository.fetch_candidates_like(keywords, limit=300, and_top=1)
        # fetch_candidates_or_only(OR-only 검색)는 더 이상 사용하지 않는다.

        exclude_all = set(exclude_ids or []) | set(recent_exclude)
        if exclude_all:
            candidates = [c for c in candidates if c.get("recipe_id") not in exclude_all]

        user_level = (profile.get("cooking_level") or "").strip()
        if user_level:
            level_filtered = [c for c in candidates if (str(c.get("level_nm") or "").strip() == user_level)]
        else:
            level_filtered = candidates
        pool = level_filtered if level_filtered else candidates

        # 후보 섞기
        try:
            random.shuffle(pool)
        except Exception:
            pool = list(pool)

        # --------------------------------------------
        # 1차: 주재료(또는 제목의 첫 단어)가 서로 다른 레시피를 우선적으로 고르기
        # --------------------------------------------
        def _main_group(candidate: Dict[str, Any]) -> str:
            # ingredient_full에서 첫 번째 토큰을 주재료로 사용
            tokens = _tokens_from_ingredient_full(candidate.get("ingredient_full"))
            if tokens:
                return tokens[0]
            # 없다면 레시피 제목의 첫 단어 사용
            title = candidate.get("recipe_nm_ko") or ""
            parts = str(title).split()
            return _norm(parts[0]) if parts else ""
        
        final_three: List[Dict[str, Any]] = []
        seen_main: set = set()
        
        # 먼저 주재료가 서로 다른 것들만 모아서 최대 limit개까지 채우기
        for candidate in pool:
            if len(final_three) >= limit:
                break
            main = _main_group(candidate)
            if main and main in seen_main:
                continue
            final_three.append(candidate)
            if main:
                seen_main.add(main)
            
        # --------------------------------------------
        # 2차: 그래도 3개가 안 채워지면, 주재료 중복 허용하고
        #      같은 레시피/같은 제목만 피하면서 추가로 채우기
        # --------------------------------------------

        if len(final_three) < limit and pool:
            chosen_ids = {c.get("recipe_id") for c in final_three if c.get("recipe_id") is not None}
            chosen_titles = {_norm(c.get("recipe_nm_ko") or "") for c in final_three}
            
            for candidate in pool:
                if len(final_three) >= limit:
                    break
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
            adapted_rows = self._llm.adapt_recipes_json(uid, profile, fridge, final_three)
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
            "recentEmphasis": [],
            "llm_recommendation_text": llm_text_result,
            "recommended_db_candidates": final_three,
            "adapted_recipes_saved": [
                {"recipe_nm_ko": row.get("recipe_nm_ko"), "recipe_id": row.get("recipe_id")}
                for row in adapted_rows
            ],
        }


__all__ = ["RecommendationWorkflow"]
