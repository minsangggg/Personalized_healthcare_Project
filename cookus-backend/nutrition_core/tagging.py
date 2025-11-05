import re
from collections import defaultdict
from .consts import CATEGORY_PATTERNS, SOURCE_WEIGHT, AGE_BASE_CATS, AGE_EXTRA_60PLUS
from .text import has_negative

def match_categories(text_by_source):
    scores = defaultdict(float)
    flags  = defaultdict(set)
    for src, text in text_by_source.items():
        if not text or has_negative(text):
            continue
        for cat, pats in CATEGORY_PATTERNS.items():
            for p in pats:
                if re.search(p, text):
                    scores[cat] += SOURCE_WEIGHT.get(src,1.0)
                    flags[cat].add(src)
                    break
    cats_sorted = sorted(scores, key=lambda c:(-scores[c], c))
    return cats_sorted, {"scores":dict(scores), "flags":{k:sorted(v) for k,v in flags.items()}}

def base_filter_categories(age_band:str, sex:str, pregnant_possible:bool=False):
    sex = sex.upper()[0]
    base = set(["Vitamin D","Omega-3","Probiotics"])  # 공통 베이스
    base.update(AGE_BASE_CATS.get(age_band, []))
    if age_band == "50대 이상":
        base.update(AGE_EXTRA_60PLUS)
    if sex == "F" and pregnant_possible:
        base.add("Folate")
    return sorted(base)

