import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Iterable
import pandas as pd
from .consts import TEXT_COLS, OPTIONAL_COLS, GOAL_TO_CATS, INTAKE_TIPS, KID_EXCLUDE_PATTERNS
from .text import read_csv_any, norm, normalize_shape_text
from .tagging import match_categories, base_filter_categories


class NutritionEngine:
    def __init__(self, input_path: str | None = None):
        self.input_path = input_path
        self._df: pd.DataFrame | None = None
        self._rows: List[Dict[str, Any]] | None = None
        self._preferred_shapes: List[str] = []
        if input_path:
            self._load()

    def _load(self):
        if not self.input_path or not os.path.exists(self.input_path):
            raise FileNotFoundError(f"supplements CSV not found: {self.input_path}")
        df, _ = read_csv_any(self.input_path)
        self._init_from_dataframe(df)

    def _init_from_dataframe(self, df: pd.DataFrame):
        for c in list(TEXT_COLS.values()) + OPTIONAL_COLS:
            if c not in df.columns: df[c] = ""
        df["_name"] = df[TEXT_COLS["name"]].apply(norm)
        df["_func"] = df[TEXT_COLS["func"]].apply(norm)
        df["_raw"]  = df[TEXT_COLS["raw"]].apply(norm)

        if "LAST_UPDT_DTM" in df.columns:
            try:
                df["_last_dt"] = pd.to_datetime(df["LAST_UPDT_DTM"], errors="coerce")
            except Exception:
                df["_last_dt"] = pd.NaT
        else:
            df["_last_dt"] = pd.NaT

        cats_list, main_list, score_list = [], [], []
        for _, r in df.iterrows():
            cats, detail = match_categories({"name":r["_name"], "func":r["_func"], "raw":r["_raw"]})
            cats_list.append("; ".join(cats) if cats else "")
            main_list.append(cats[0] if cats else "")
            score_list.append(json.dumps(detail["scores"], ensure_ascii=False))

        df["categories"] = cats_list
        df["main_category"] = main_list
        df["category_scores"] = score_list

        self._df = df
        # also cache as rows for non-pandas flow
        self._rows = [
            {
                **r,
                "_name": r.get("_name"),
                "_func": r.get("_func"),
                "_raw": r.get("_raw"),
            }
            for r in df.to_dict(orient="records")
        ]
        self._preferred_shapes = ["캡슐","정","가루","액상","젤리","스틱","츄어블","환"]

    @property
    def preferred_shapes(self) -> List[str]:
        return self._preferred_shapes

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame):
        inst = cls(input_path=None)
        inst._init_from_dataframe(df)
        return inst

    @classmethod
    def from_records(cls, records: Iterable[Dict[str, Any]]):
        inst = cls(input_path=None)
        inst._init_from_records(records)
        return inst

    def _init_from_records(self, records: Iterable[Dict[str, Any]]):
        rows: List[Dict[str, Any]] = []
        for r in records:
            name = norm(r.get(TEXT_COLS["name"]))
            func = norm(r.get(TEXT_COLS["func"]))
            raw  = norm(r.get(TEXT_COLS["raw"]))
            cats, detail = match_categories({"name": name, "func": func, "raw": raw})
            main_category = cats[0] if cats else ""
            scores = detail["scores"]
            # parse update date
            last_dt_raw = r.get("LAST_UPDT_DTM") or r.get("LAST_UPDT_DT")
            last_dt: datetime | None = None
            try:
                if last_dt_raw:
                    last_dt = datetime.fromisoformat(str(last_dt_raw))
            except Exception:
                last_dt = None
            rows.append({
                **r,
                "_name": name,
                "_func": func,
                "_raw": raw,
                "main_category": main_category,
                "category_scores": json.dumps(scores, ensure_ascii=False),
                "_src_score": sum(scores.values()) if isinstance(scores, dict) else 0.0,
                "_last_dt": last_dt,
            })
        self._rows = rows
        self._df = None
        self._preferred_shapes = ["캡슐","정","가루","액상","젤리","스틱","츄어블","환"]

    def _filter_by_shapes_df(self, df_in: pd.DataFrame, selected_shapes: List[str]) -> pd.DataFrame:
        if not selected_shapes:
            return df_in
        tmp = df_in.copy()
        tmp["_shape_norm"] = tmp["PRDT_SHAP_CD_NM"].apply(normalize_shape_text)
        return tmp[tmp["_shape_norm"].isin([s.lower() for s in selected_shapes])]

    def _filter_by_shapes_rows(self, rows: List[Dict[str, Any]], selected_shapes: List[str]) -> List[Dict[str, Any]]:
        if not selected_shapes:
            return rows
        sel = set([s.lower() for s in selected_shapes])
        out = []
        for r in rows:
            v = normalize_shape_text(r.get("PRDT_SHAP_CD_NM"))
            if v.lower() in sel:
                out.append(r)
        return out

    def recommend(self, *, age_band: str, sex: str, pregnant_possible: bool = False,
                  shapes: List[str] | None = None, goals: List[str] | None = None,
                  top_k: int = 10) -> List[Dict[str, Any]]:
        # Ensure we have data
        rows = self._rows
        df = self._df
        if rows is None and df is None:
            self._load()
            rows = self._rows
            df = self._df

        base_cats = base_filter_categories(age_band, sex, pregnant_possible)

        results: List[Dict[str, Any]] = []
        if rows is not None:
            filtered = self._filter_by_shapes_rows(rows, shapes or [])
            # Exclude kid-targeted products for non-teen age bands
            if age_band != '10대':
                def is_kid(r: Dict[str, Any]) -> bool:
                    text = f"{r.get('_name','')} {r.get('_func','')}"
                    return any(re.search(p, text) for p in KID_EXCLUDE_PATTERNS)
                filtered = [r for r in filtered if not is_kid(r)]
            for goal in goals or []:
                cats = GOAL_TO_CATS.get(goal, [])
                if sex.upper().startswith('F') and pregnant_possible and 'Folate' not in cats:
                    cats = cats + ['Folate']
                target_cats = sorted(set(cats + base_cats))

                # gather candidates
                cands: List[Dict[str, Any]] = [r for r in filtered if r.get('main_category') in target_cats]
                # sort: last_dt desc, src_score desc, name asc
                def sort_key(r: Dict[str, Any]):
                    ld = r.get('_last_dt')
                    return (
                        0 if ld is None else -int(ld.timestamp()),
                        -(r.get('_src_score') or 0.0),
                        str(r.get('PRDLST_NM') or '')
                    )
                cands.sort(key=sort_key)
                items = []
                for r in cands[:top_k]:
                    items.append({
                        "category": r.get("main_category", ""),
                        "product_name": r.get("PRDLST_NM", ""),
                        "function": r.get("PRIMARY_FNCLTY", ""),
                        "shape": r.get("PRDT_SHAP_CD_NM", ""),
                        "timing": INTAKE_TIPS.get(r.get("main_category", ""), ""),
                    })
                results.append({"goal": goal, "items": items})
            return results

        # Fallback to DataFrame flow if rows not available
        if df is not None:
            df_filtered = self._filter_by_shapes_df(df, shapes or [])
            if age_band != '10대':
                def has_kid(row) -> bool:
                    text = f"{row.get('_name','')} {row.get('_func','')}"
                    return any(re.search(p, text) for p in KID_EXCLUDE_PATTERNS)
                df_filtered = df_filtered[~df_filtered.apply(has_kid, axis=1)]
            from .rank import pick_top_by_category  # local import to avoid hard dep when unused
            for goal in goals or []:
                cats = GOAL_TO_CATS.get(goal, [])
                if sex.upper().startswith('F') and pregnant_possible and 'Folate' not in cats:
                    cats = cats + ['Folate']
                target_cats = sorted(set(cats + base_cats))
                frames = []
                for c in target_cats:
                    picks = pick_top_by_category(df_filtered, c, k=top_k)
                    if not picks.empty:
                        frames.append(picks)
                items = []
                for _, r in (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()).iterrows():
                    items.append({
                        "category": r.get("main_category", ""),
                        "product_name": r.get("PRDLST_NM", ""),
                        "function": r.get("PRIMARY_FNCLTY", ""),
                        "shape": r.get("PRDT_SHAP_CD_NM", ""),
                        "timing": r.get("섭취_타이밍", ""),
                    })
                results.append({"goal": goal, "items": items[:top_k]})
            return results

        return []
