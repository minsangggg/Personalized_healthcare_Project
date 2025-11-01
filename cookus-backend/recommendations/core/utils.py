"""Utility helpers for recommendation workflow."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _norm(value: str) -> str:
    text = str(value)
    text = re.sub(r"\(.*?\)", "", text)
    return text.replace("/", " ").strip()


def pick_keywords_from_fridge_all(fridge_df: pd.DataFrame, max_n: int = 30) -> List[str]:
    return (
        fridge_df["item_name"]
        .map(_norm)
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .head(max_n)
        .tolist()
    )


def recent_items_from_fridge(fridge_df: pd.DataFrame, days: int = 10, top: int = 8) -> List[str]:
    df = fridge_df.copy()
    df["saved_at"] = pd.to_datetime(df["saved_at"], errors="coerce")
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = df[df["saved_at"] >= cutoff].sort_values("saved_at", ascending=False)
    return recent["item_name"].map(_norm).head(top).tolist()


def _tokens_from_ingredient_full(val: Any) -> List[str]:
    return _extract_tokens_from_ingredients_text(val)


def guess_main_ingredient(candidate: Dict[str, Any]) -> str:
    tokens = _tokens_from_ingredient_full(candidate.get("ingredient_full"))
    if tokens:
        return tokens[0]
    title = candidate.get("recipe_nm_ko") or "기타"
    return _norm(str(title).split()[0])


def _primary_group(candidate: Dict[str, Any]) -> str:
    ty_name = (candidate.get("ty_nm") or "").strip()
    if ty_name:
        return _norm(ty_name)
    return guess_main_ingredient(candidate)


def ensure_diverse_top(candidates: List[Dict[str, Any]], want: int = 3) -> List[Dict[str, Any]]:
    seen_ids: set = set()
    seen_titles: set = set()
    seen_groups: set = set()
    output: List[Dict[str, Any]] = []

    for candidate in candidates:
        recipe_id = candidate.get("recipe_id")
        title = _norm(candidate.get("recipe_nm_ko") or "")
        group = _primary_group(candidate)
        if recipe_id in seen_ids:
            continue
        if title and title in seen_titles:
            continue
        if group and group in seen_groups:
            continue
        output.append(candidate)
        seen_ids.add(recipe_id)
        if title:
            seen_titles.add(title)
        if group:
            seen_groups.add(group)
        if len(output) >= want:
            break
    return output


def diversify_candidates(candidates: List[Dict[str, Any]], want: int = 12, max_per_main: int = 1) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for candidate in candidates:
        main = guess_main_ingredient(candidate) or "기타"
        buckets.setdefault(main, [])
        if len(buckets[main]) < max_per_main:
            buckets[main].append(candidate)

    output: List[Dict[str, Any]] = []
    for group_candidates in buckets.values():
        output.extend(group_candidates)
        if len(output) >= want:
            break
    return output[:want]


def _extract_tokens_from_ingredients_text(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, dict):
        return [_norm(k) for k in val.keys() if _norm(k)]
    if isinstance(val, list):
        return [_norm(x) for x in val if _norm(x)]

    text = str(val)
    if not text:
        return []

    hits = re.findall(r"'([^']+)'", text)
    if hits:
        return [_norm(hit) for hit in hits if _norm(hit)]

    parts = [part.strip() for part in text.replace("\n", ",").split(",")]
    return [_norm(part) for part in parts if _norm(part)]


def _substitute_with_fridge(token: str, fridge_tokens: set) -> str:
    return token if token in fridge_tokens else token


def _enforce_ingredients_full(
    original_ingredients_text: Any,
    fridge_tokens: set,
    llm_ingredient_full: Dict[str, Any],
) -> Dict[str, Any]:
    required = _extract_tokens_from_ingredients_text(original_ingredients_text)
    enforced: Dict[str, Any] = {}
    for token in required:
        substitute = _substitute_with_fridge(token, fridge_tokens)
        if substitute in fridge_tokens:
            if substitute in llm_ingredient_full:
                enforced[substitute] = llm_ingredient_full.get(substitute)
            elif token in llm_ingredient_full:
                enforced[substitute] = llm_ingredient_full.get(token)
            else:
                enforced[substitute] = ""
    return enforced


def _fridge_token_set(fridge_df: pd.DataFrame) -> set:
    names = (
        fridge_df["item_name"]
        .map(_norm)
        .dropna()
        .astype(str)
    )
    return set(names.tolist())


def enforce_ingredients_with_fridge(
    candidate: Dict[str, Any],
    fridge_df: pd.DataFrame,
    llm_ingredient_full: Dict[str, Any],
) -> Dict[str, Any]:
    fridge_tokens = _fridge_token_set(fridge_df)
    enforced = _enforce_ingredients_full(
        candidate.get("ingredient_full") or {},
        fridge_tokens,
        llm_ingredient_full or {},
    )
    if enforced:
        return enforced

    # fallback: keep only LLM ingredients that user actually has
    filtered = {k: v for k, v in (llm_ingredient_full or {}).items() if _norm(k) in fridge_tokens}
    return filtered


def fridge_token_set(fridge_df: pd.DataFrame) -> set:
    return _fridge_token_set(fridge_df)



__all__ = [
    "_norm",
    "pick_keywords_from_fridge_all",
    "recent_items_from_fridge",
    "_tokens_from_ingredient_full",
    "ensure_diverse_top",
    "diversify_candidates",
    "enforce_ingredients_with_fridge",
    "fridge_token_set",
]
