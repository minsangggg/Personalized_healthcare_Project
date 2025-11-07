import re
import pandas as pd
from .consts import NEGATIVE_PATTERNS

def read_csv_any(path: str):
    for enc in ["utf-8","utf-8-sig","cp949","euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False), enc
        except Exception:
            pass
    return pd.read_csv(path, encoding="utf-8", low_memory=False), "utf-8"

def norm(s):
    if pd.isna(s): return ""
    return re.sub(r"\s+"," ",str(s).lower()).strip()

def has_negative(text):
    return any(re.search(p, text) for p in NEGATIVE_PATTERNS)

def normalize_shape_text(s: str) -> str:
    s = norm(s)
    mapping = {
        "캡슐": ["캡슐", "capsule", "gelcap", "softgel", "연질캡슐"],
        "정":   ["정", "tablet", "tab", "정제"],
        "가루": ["가루", "분말", "powder"],
        "액상": ["액상", "액체", "liquid", "drop", "드롭", "시럽"],
        "젤리": ["젤리", "구미", "젤", "gummy", "jelly", "젤리스틱"],
        "스틱": ["스틱", "스틱형", "포", "스틱포"],
        "츄어블": ["츄어블", "chew", "츄"],
        "환":   ["환", "pill"],
    }
    for k, keys in mapping.items():
        if any(kword in s for kword in keys):
            return k
    return s

