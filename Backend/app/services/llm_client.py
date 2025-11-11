from __future__ import annotations

import json
import re
from typing import Any, Iterable, List, Sequence, Set

from openai import OpenAI, OpenAIError

from app.core.config import get_settings
from app.services.recommendation_prompt import build_recommendation_prompt


class LLMAdaptationError(Exception):
    """Raised when recipe adaptation via LLM fails."""


_settings = get_settings()
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    if not _settings.openai_api_key:
        raise LLMAdaptationError("OPENAI_API_KEY is not configured.")
    global _client  # pylint: disable=global-statement
    if _client is None:
        try:
            _client = OpenAI(api_key=_settings.openai_api_key)
        except TypeError as exc:
            msg = (
                "현재 설치된 httpx 버전에서 OpenAI SDK가 proxies 인자를 지원하지 않습니다. "
                "httpx==0.27.2 로 맞춘 후 다시 시도해 주세요."
            )
            raise LLMAdaptationError(msg) from exc
    return _client


def _strip_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        parts = [part.strip() for part in text.split("```") if part.strip()]
        if not parts:
            return ""
        candidate = parts[0]
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()
        return candidate
    return text


def _extract_json_payload(content: str) -> dict[str, Any]:
    cleaned = _strip_code_fence(content)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("JSON object not found in LLM response.")
    snippet = cleaned[start : end + 1]
    return json.loads(snippet)


def _candidate_ids(candidates: Sequence[dict[str, Any]]) -> Set[int]:
    ids: Set[int] = set()
    for candidate in candidates:
        recipe_id = candidate.get("recipe_id")
        try:
            ids.add(int(recipe_id))
        except (TypeError, ValueError):
            continue
    return ids


def adapt_recipes_with_llm(
    *,
    user_name: str,
    fridge_items: Iterable[dict[str, Any]],
    level: str,
    candidates: Sequence[dict[str, Any]],
    recent_emphasis: Iterable[Any] | None = None,
) -> List[dict[str, Any]]:
    """Call GPT to adapt candidate recipes to the fridge inventory."""

    candidate_list = list(candidates)
    if not candidate_list:
        return []

    prompt = build_recommendation_prompt(
        name=user_name,
        fridge_list=list(fridge_items),
        recent_emphasis=list(recent_emphasis or []),
        level=level,
        candidates=candidate_list,
    )

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a culinary assistant who ONLY outputs valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
    except OpenAIError as exc:  # pragma: no cover - network call
        raise LLMAdaptationError("LLM 호출에 실패했습니다.") from exc

    if not response.choices:
        raise LLMAdaptationError("LLM 응답이 비어 있습니다.")

    message = response.choices[0].message.content or ""
    if not message.strip():
        raise LLMAdaptationError("LLM 응답이 비어 있습니다.")

    try:
        payload = _extract_json_payload(message)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMAdaptationError("LLM 응답 JSON 파싱에 실패했습니다.") from exc

    recommendations = payload.get("recommendations")
    if not isinstance(recommendations, list):
        raise LLMAdaptationError("recommendations 키가 없습니다.")

    allowed_ids = _candidate_ids(candidate_list)
    cleaned: List[dict[str, Any]] = []
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        recipe_id = item.get("recipe_id")
        try:
            recipe_id_int = int(recipe_id)
        except (TypeError, ValueError):
            continue
        if recipe_id_int not in allowed_ids:
            continue

        cleaned.append(
            {
                "recipe_id": recipe_id_int,
                "recipe_nm_ko": item.get("recipe_nm_ko"),
                "ingredient_full": item.get("ingredient_full"),
                "step_text": item.get("step_text"),
            }
        )

    return cleaned[:7]




def _postprocess_steps(steps: List[str]) -> List[str]:
    action_keywords = [
        "썰", "다지", "손질", "씻", "넣", "섞", "만들", "끓", "볶", "굽", "구워", "익",
        "데치", "튀기", "재워", "비비", "담", "올리", "뿌리", "붓", "조리", "버무",
        "mix", "add", "stir", "cook", "boil", "fry", "grill", "saute", "bake", "slice",
        "chop", "pour", "season", "garnish", "top", "marinate", "serve",
    ]
    action_regex = re.compile("|".join(map(re.escape, action_keywords)), re.IGNORECASE)
    measure_regex = re.compile(
        r"(\d+(?:/\d+)?)\s*(큰술|작은술|스푼|수저|컵|g|그램|kg|킬로|ml|mL|L|l|리터|"
        r"tsp|tbsp|cup|oz|개|쪽|줌)",
        re.IGNORECASE,
    )
    narrative_noise = re.compile(
        r"("
        r"간단하게|간단하|생각보다|확실히|자취생|자극적|손색없|어울려|감칠맛|먹음직|"
        r"필요없|없어서|원래|분들은|수\s+있습니다|수\s+있어요|한끼|비린맛|취향에\s*따라"
        r")",
        re.IGNORECASE,
    )
    clause_with_condition = re.compile(r"(으면|시면|을때|을 때)")
    polite_ending = re.compile(r"(세요|십시오|습니다|니다|요)$")
    ending_regex = re.compile(r"(다|요|라|십시오|세요|줍니다|합니다)$")
    english_ending = re.compile(r"[A-Za-z]$")
    filtered: List[str] = []
    banned_patterns = re.compile(r"(\uC800\uB294|\uC81C\uAC00|\uC6B0\uB9AC\uB294|\uC6B0\uB9AC\uC9D1|\uCE5C\uAD6C|\uB0A8\uD3B8|\uC544\uB0B4|\uC544\uC774|\uBED4\uBED4)", re.IGNORECASE)
    personal_clause = re.compile(r"(\uC800\uB294|\uC81C\uAC00|\uC6B0\uB9AC\uB294|\uC6B0\uB9AC\uC9D1|\uCE5C\uAD6C|\uB0A8\uD3B8|\uC544\uB0B4|\uC544\uC774|\uBED4\uBED4)[^.!?\n]*", re.IGNORECASE)
    measurement_buffer: List[str] = []

    def _split_candidates(step: str) -> List[str]:
        if not step:
            return []
        normalized = re.sub(r"^(?:\d+[\.\)]\s*)+", "", step.strip())
        normalized = personal_clause.sub("", normalized)
        normalized = re.sub(r"[\(\[][^)\]]*[\)\]]", " ", normalized)
        normalized = re.sub(r"[^\w\s\uAC00-\uD7A3\/%\.!?\n]", " ", normalized)
        normalized = re.sub(r"\.{2,}", ". ", normalized)
        normalized = re.sub(r"[!?]+", ". ", normalized)
        normalized = re.sub(r"\n{2,}", ". ", normalized)
        normalized = normalized.replace("\n", " ")
        normalized = re.sub(r"\s{2,}", " ", normalized)
        decimal_placeholder = "__DECIMAL__"
        normalized = re.sub(r"(\d)\.(\d)", rf"\1{decimal_placeholder}\2", normalized)
        chunks = []
        for chunk in re.split(r"[.!?]+", normalized):
            restored = chunk.replace(decimal_placeholder, ".").strip()
            if restored:
                chunks.append(restored)
        return chunks

    for step in steps:
        for candidate in _split_candidates(step):
            text = re.sub(r"[,'\"]", "", candidate).strip()
            text = re.sub(r"주시구요$", "주세요", text)
            text = re.sub(r"구요$", "", text)
            text = re.sub(r"는데요$", "", text)
            text = re.sub(r"\s{2,}", " ", text).strip()
            if not text:
                continue
            if banned_patterns.search(text):
                continue
            has_action = bool(action_regex.search(text))
            only_measurement = bool(measure_regex.search(text)) and not has_action

            if narrative_noise.search(text) and not has_action:
                continue

            if only_measurement:
                measurement_buffer.append(text)
                continue

            if not has_action:
                continue

            if clause_with_condition.search(text) and not polite_ending.search(text):
                continue

            ending_ok = bool(ending_regex.search(text) or english_ending.search(text))
            if not ending_ok:
                continue

            if measurement_buffer:
                text = f"{' '.join(measurement_buffer)} {text}"
                measurement_buffer.clear()

            filtered.append(text)

    measurement_buffer.clear()
    return filtered






def sanitize_recipe_steps(steps: List[str]) -> List[str]:
    return _postprocess_steps(steps)


def clean_recipe_steps_with_llm(raw_text: str) -> List[str]:
    """Use the LLM to extract only meaningful cooking instructions."""

    cleaned_input = (raw_text or "").strip()
    if not cleaned_input:
        return []

    system_prompt = (
        "You are a culinary editor. Remove jokes, personal comments, ads, emoji, "
        "or anything unrelated to executing the recipe. Each step must be a single plain sentence "
        "describing only what the cook should do."
    )
    user_prompt = f"""You will receive raw recipe steps. Keep only the imperative instructions
and delete personal stories, jokes, reactions, ads, or any text inside parentheses.
Each step must be exactly one sentence and must not contain commas or quotes.
Return only JSON with a 'steps' array.

Input text:
{cleaned_input}

Output format example:
{{"steps": ["Prepare the ingredients.", "Add seasoning and cook."]}}
"""

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
    except OpenAIError as exc:  # pragma: no cover
        raise LLMAdaptationError("LLM 응답을 가져오지 못했습니다.") from exc

    if not response.choices:
        raise LLMAdaptationError("LLM 응답이 비어 있습니다.")

    message = response.choices[0].message.content or ""
    if not message.strip():
        raise LLMAdaptationError("LLM 응답이 비어 있습니다.")

    try:
        payload = _extract_json_payload(message)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMAdaptationError("LLM 응답 JSON 파싱에 실패했습니다.") from exc

    steps = payload.get("steps")
    if not isinstance(steps, list):
        raise LLMAdaptationError("steps 키가 없습니다.")

    cleaned_steps: List[str] = []
    for item in steps:
        if isinstance(item, str):
            normalized = item.strip()
            if normalized:
                cleaned_steps.append(normalized)
    return _postprocess_steps(cleaned_steps)


def estimate_recipe_costs(recipes: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Ask LLM to estimate ingredient vs delivery costs for provided recipes."""
    if not recipes:
        return {
            "per_recipe": [],
            "total_ingredient_cost": 0,
            "total_delivery_cost": 0,
            "total_savings": 0,
            "notes": "no recipes provided",
        }

    client = _get_client()
    system_prompt = (
        "당신은 꼼꼼한 한국 비용 분석가입니다. "
        "목표: 각 레시피마다 ingredient_cost(한 번 조리 기준 재료비)와 delivery_price(동일 메뉴를 주문했을 때의 음식값, 배달비 제외)를 추정하고, "
        "savings = (delivery_price - ingredient_cost) * count 공식을 적용해 절약액을 계산합니다. "
        "원칙: (1) 한국의 중간 수준 물가를 사용합니다. "
        "(2) delivery_price는 음식값만 고려하고 배달비는 포함하지 않습니다. "
        "(3) 주어진 재료만 사용하고 새로운 재료를 상상하지 않습니다. "
        "(4) 정보가 부족하면 보수적으로 추정하고 'notes'에 근거를 적습니다. "
        "(5) 모든 금액은 쉼표 없는 정수 KRW입니다. "
        "(6) 사용자가 요구한 JSON 스키마를 정확히 지킵니다."
        "(7) 음식마다 들어가는 재료가 다르기 때문에 예상 재료비는 다르게 나옵니다."
    )
    user_payload = [
        {
            "name": item.get("name") or "레시피",
            "count": int(item.get("count", 1) or 1),
            "ingredients_text": item.get("ingredients_text") or "",
        }
        for item in recipes
    ]
    user_prompt = (
        "다음 JSON 배열은 사용자가 이번 달 직접 조리한 레시피와 재료입니다. "
        "각 항목은 name, count(조리 횟수), ingredients_text(문장 형태 재료 목록)를 포함합니다. "
        "다음 규칙을 반드시 따르세요:\n"
        "1) ingredient_cost = 해당 재료를 모두 장보는 실구매가의 합 (1회 기준). 재고가 남더라도 사용량에 맞춰 계산.\n"
        "2) delivery_price = 같은 메뉴를 음식점/배달앱에서 주문했을 때의 음식값(배달비 제외). "
        "3) savings = (delivery_price - ingredient_cost) * count. 음수가 되면 0으로 두지 말고 음수 그대로 둡니다.\n"
        "4) 모든 금액은 정수 KRW. 예: 8700\n"
        "5) per_recipe 배열의 각 항목에는 name, count, ingredient_cost, delivery_price, savings 를 포함.\n"
        "6) total_ingredient_cost, total_delivery_cost 는 각 항목 값에 count를 곱한 뒤 합산, total_savings 는 delivery - ingredient 의 총합.\n"
        "7) notes 필드에 근거 또는 보정 설명을 1~2문장으로 작성.\n"
        "반환 JSON 예시:\n"
        '{\n'
        '  "per_recipe": [\n'
        '    {"name": "김치찌개", "count": 2, "ingredient_cost": 4800, "delivery_price": 12500, "savings": 15400}\n'
        '  ],\n'
        '  "total_ingredient_cost": 9600,\n'
        '  "total_delivery_cost": 25000,\n'
        '  "total_savings": 15400,\n'
        '  "notes": "김치/돼지고기 시세 기준 추정"\n'
        '}\n'
        "위 JSON 스키마만 지켜 출력하세요. 아래는 입력 데이터입니다:\n"
        f"{json.dumps(user_payload, ensure_ascii=False, indent=2)}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
    except OpenAIError as exc:  # pragma: no cover
        raise LLMAdaptationError("LLM 호출에 실패했습니다.") from exc

    message = response.choices[0].message.content if response.choices else ""
    if not message:
        raise LLMAdaptationError("LLM 응답이 비어 있습니다.")

    try:
        payload = _extract_json_payload(message)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMAdaptationError("LLM 응답 JSON 파싱에 실패했습니다.") from exc

    return payload


__all__ = [
    "LLMAdaptationError",
    "adapt_recipes_with_llm",
    "estimate_recipe_costs",
    "clean_recipe_steps_with_llm",
    "sanitize_recipe_steps",
]
