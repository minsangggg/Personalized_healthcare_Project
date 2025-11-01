"""LLM integration helpers for recommendations."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from openai import OpenAI


class RecommendationLLM:
    def __init__(self, client: Optional[OpenAI] = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY") if client is None else None
        self._client = client or OpenAI(api_key=api_key)

    def adapt_recipes_json(
        self,
        user_id: str,
        profile: Dict[str, Any],
        fridge_df: pd.DataFrame,
        candidates: List[Dict[str, Any]],
        recent_emphasis: List[str],
    ) -> List[Dict[str, Any]]:
        name = profile.get("name") or "사용자"
        level = profile.get("cooking_level") or "-"
        fridge_list = ", ".join(fridge_df["item_name"].map(str).head(24).tolist())

        schema_instruction = {
            "type": "json_schema",
            "json_schema": {
                "name": "adapted_recipes_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "recipes": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {
                                "type": "object",
                                "required": ["recipe_nm_ko", "ingredient_full", "step_text", "recipe_id"],
                                "properties": {
                                    "recipe_nm_ko": {"type": "string"},
                                    "ingredient_full": {
                                        "type": "object",
                                        "additionalProperties": {"type": "string"},
                                    },
                                    "step_text": {"type": "string"},
                                    "recipe_id": {"type": "integer"},
                                },
                            },
                        }
                    },
                    "required": ["recipes"],
                    "additionalProperties": False,
                },
            },
        }

        user_msg = f"""
[요약]
- {name}님의 냉장고 재료: {fridge_list}
- 최근 저장 재료: {recent_emphasis}
- 사용자 요리 레벨: {level}

[목표]
- 아래 후보 레시피 3개 각각에 대해, 냉장고 보유 재료를 최대한 활용하고 부족한 재료는 상식적인 대체재료로 치환하여
  (1) 최종 레시피명(recipe_nm_ko), (2) 최종 재료 딕셔너리(ingredient_full: 재료명->권장용량 문자열), (3) 최종 조리문(step_text), (4) 원본 recipe_id 를 JSON으로 반환.
- 과장된 새로운 재료를 창작하지 말고, 원문 재료 범위 내에서 합리적인 대체만 수행.

[재료 가용성 규칙]
- 사용자가 실제로 가진 재료(또는 합리적 대체)만 사용하여 레시피를 완성해야 합니다. 
- 만약 특정 후보 레시피가 사용자의 재료로는 조리가 어려우면, 해당 후보를 참고하되 사용자의 보유 재료로 만들 수 있도록 레시피를 새로 구성하세요.
- 최종 ingredient_full과 step_text는 사용자 보유 재료만으로 완성되어야 하며, step_text에 등장하는 모든 항목은 ingredient_full에 존재해야 합니다.

[일관성 요구]
- step_text에 등장하는 모든 재료/양념/부재료는 ingredient_full 키에 반드시 존재해야 하며, 
  ingredient_full의 모든 항목은 step_text 어딘가에서 실제로 사용되어야 합니다. 누락/유령 재료 금지.
  이 일관성을 만족하지 못하면 출력을 수정하여 반드시 만족시키세요.

[후보(원문)]
{json.dumps(candidates, ensure_ascii=False)}
"""

        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": "너는 한국어 요리 어시스턴트야. 냉장고 재료 우선, 부족분은 합리적 대체를 적용하고, 결과는 정확한 JSON으로.",
                    },
                    {"role": "user", "content": user_msg},
                ],
                response_format=schema_instruction,
            )
            content = response.choices[0].message.content
            payload = json.loads(content or "{}")
            recipes = payload.get("recipes", [])

            cleaned: List[Dict[str, Any]] = []
            for idx, recipe in enumerate(recipes[:3]):
                if idx < len(candidates):
                    fallback_id = int(candidates[idx]["recipe_id"])
                    fallback_title = str(candidates[idx].get("recipe_nm_ko") or "")
                else:
                    fallback_id = None
                    fallback_title = ""

                recipe_id = recipe.get("recipe_id")
                try:
                    recipe_id = int(recipe_id) if recipe_id is not None else fallback_id
                except Exception:
                    recipe_id = fallback_id

                cleaned.append(
                    {
                        "id": str(user_id),
                        "recipe_nm_ko": str(recipe.get("recipe_nm_ko") or fallback_title),
                        "ingredient_full": recipe.get("ingredient_full") or {},
                        "step_text": str(recipe.get("step_text") or ""),
                        "recipe_id": fallback_id,
                    }
                )
            return cleaned
        except Exception:
            return []

    @staticmethod
    def format_for_display(
        adapted_rows: List[Dict[str, Any]],
        profile: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> str:
        name = profile.get("name") or "사용자"
        id_to_meta = {
            candidate["recipe_id"]: {
                "level_nm": candidate.get("level_nm"),
                "cooking_time": candidate.get("cooking_time"),
            }
            for candidate in candidates
        }

        output_parts = [
            f"**{name}님! 냉장고 속 재료로 만들 수 있는 세 가지 레시피를 추천해 드릴게요!**"
        ]

        for idx, recipe in enumerate(adapted_rows, 1):
            recipe_id = recipe.get("recipe_id")
            meta = id_to_meta.get(recipe_id, {})
            level = meta.get("level_nm") or "정보 없음"
            cooking_time = meta.get("cooking_time") or ""

            meta_text = f"({level}"
            if cooking_time:
                meta_text += f"/{cooking_time} 소요"
            meta_text += ")"

            ingredients = recipe.get("ingredient_full") or {}
            ingredient_lines = []
            for ingredient_name, amount in ingredients.items():
                if amount and str(amount).strip():
                    ingredient_lines.append(f"{ingredient_name} {amount}")
                else:
                    ingredient_lines.append(str(ingredient_name))

            ingredient_text = "\n\t\t\t".join(ingredient_lines)

            block = f"""
{idx}. {recipe.get('recipe_nm_ko')} {meta_text}
   - [필요 재료]
     {ingredient_text}
   - [조리 순서]
     {recipe.get('step_text')}
"""
            output_parts.append(block)

        return "\n".join(output_parts)


__all__ = ["RecommendationLLM"]
