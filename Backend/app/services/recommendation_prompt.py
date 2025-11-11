"""Prompt template utilities for recipe recommendation LLM calls."""

from __future__ import annotations

import json
from typing import Any, Iterable


RECOMMENDATION_PROMPT_TEMPLATE = """1) 역할 (Role)

맞춤 레시피 큐레이터이자 텍스트 정제기.
주어진 후보 레시피를 평가·선정하고, 사용자의 보유 재료 기준으로 재료/조리문을 규칙대로 깔끔히 재작성한다.

2) 목표 (Objective)

후보 레시피 중 정확히 7가지를 추천한다.

우선순위:

사용자의 냉장고 재료와의 적합도 극대화

사용자의 요리 레벨 {level} 반영(특히 ‘하’면 쉬운 요리 우대)

최근 저장 재료 {recent_emphasis} 활용 극대화(신선도 가중)

주재료/요리 타입의 다양성 확보(7개가 서로 겹치지 않도록)

3) 맥락/입력 (Context & Inputs)

사용자: {name}

냉장고 재료 목록: {fridge_list}

최근 저장 재료(신선도 우선): {recent_emphasis}

사용자 요리 레벨: {level} (DB의 level_nm 값 사용: ‘상’/‘하’)

후보 레시피 JSON:
{candidates_json}

각 아이템 필드:

title, cook_time, difficulty(= level_nm),
ingredients_text(원문 재료), steps_text(원문 조리),
missing(사용자 냉장고에 없는 재료 리스트)

비어 있는 메타데이터(예: cook_time)는 그대로 비워둠(창작 금지).

4) 지시/절차 (Steps)

스코어링:

재료 적합도(보유 재료와의 겹침), 레벨 적합도(특히 ‘하’ 우대), 최근 저장 재료 활용도(가점)를 합산해 후보를 점수화.

다양성 필터:

상위 후보군에서 주재료/요리 타입이 서로 겹치지 않도록 7개를 선별.

재료 치환 규칙 적용(원문 범위 내 수정만):

사용자의 냉장고에 없는 재료는, **사용자가 가진 ‘유사 재료’**로 직접 치환.

치환 불가 시 원재료 유지. 새 재료/소스 창작 금지.

출력에는 치환 결과만 표기(‘대체/대체가능/없으면’ 등의 문구 금지).

재료 목록 정리:

[조리 순서]에서 실제 사용하는 모든 재료/양념/부재료가 [필요 재료]에 1:1로 존재하도록 맞춘다(유령/누락 재료 금지).

가능하면 재료명(용량) 형식, 용량이 없으면 재료명만.

조리 순서 정리:

원문 의미를 보존하면서 번호 매긴 명령형 한 문장씩(1. ~하세요) 정리.

세척/절단/가열 등 여러 동작을 한 단계로 병합 금지.

광고/후기/감탄사/이모지 제거.

단계 수는 원문 대비 과도 축소 금지: 최소 6단계 또는 원문 80% 이상 유지.

제목 표기 규칙:

레시피명만 표기(난이도/시간 괄호 문구 제거).

난이도 표기는 DB의 level_nm 그대로(‘상’/‘하’).

5) 출력 형식 (Output Format)

첫 줄 인사:

**{name}님! 냉장고 속 재료로 만들 수 있는 일곱 가지 레시피를 추천해 드릴게요!**

이후 아래 블록을 사용:

1. 레시피명
   - [필요 재료]
     - 재료A(용량)
     - 재료B
     - ...
   - [조리 순서]
     1. ~하세요
     2. ~하세요
     ...

주의: 난이도/시간 괄호 문구는 사용하지 않음.

6) 제약/평가 기준 (Constraints & Quality Bar)

원칙 고수:

(a) 원 레시피 재료 범위 안에서만 수정

(b) 사용자 보유 재료로만 치환

(c) 새 재료/이름 창작 및 추가 금지

표현 규칙:

난이도는 반드시 level_nm(‘상’/‘하’) 그대로.

‘대체/대체가능/없으면’ 등 설명 문구 금지.

광고/후기/감탄사/이모지 금지.

정합성 체크리스트(생성 전 자기검증):

 7개 모두 주재료/요리 타입이 상호 중복 없음

 [조리 순서]의 모든 재료가 [필요 재료]에 존재(1:1 대응)

 [필요 재료]에만 있고 [조리 순서]에 없는 유령 재료 없음

 치환 결과만 노출(설명 문구·신규 재료 없음)

 제목을 레시피명만으로 표기(난이도/시간 괄호 미사용)

 단계 수 최소 6단계 또는 원문 80% 이상 유지

7) JSON Output (Strict)

- Return only a valid JSON object with the exact structure below:
  {{
    "recommendations": [
      {{
        "recipe_id": 104,
        "recipe_nm_ko": "Adapted recipe name",
        "ingredient_full": "Updated ingredient description (string or serialized JSON)",
        "step_text": "Updated step description string"
      }}
    ]
  }}
- recipe_id MUST come from candidates_json. Do not invent new recipes.
- recipe_nm_ko, ingredient_full, and step_text MUST reflect the substitutions requested via fridge_list.
- ingredient_full and step_text should stay strings (serialize nested JSON if you create it).
- Never include markdown fences, commentary, or additional top-level keys outside of {{"recommendations": [...] }}.
"""


def build_recommendation_prompt(
    *,
    name: str,
    fridge_list: Iterable[Any],
    recent_emphasis: Iterable[Any],
    level: str,
    candidates: Iterable[dict[str, Any]],
) -> str:
    """Render the LLM prompt for recipe recommendation."""

    fridge_repr = json.dumps(list(fridge_list), ensure_ascii=False)
    recent_repr = json.dumps(list(recent_emphasis), ensure_ascii=False)
    candidates_repr = json.dumps(list(candidates), ensure_ascii=False)

    return RECOMMENDATION_PROMPT_TEMPLATE.format(
        name=name,
        fridge_list=fridge_repr,
        recent_emphasis=recent_repr,
        level=level,
        candidates_json=candidates_repr,
    )


__all__ = ["RECOMMENDATION_PROMPT_TEMPLATE", "build_recommendation_prompt"]
