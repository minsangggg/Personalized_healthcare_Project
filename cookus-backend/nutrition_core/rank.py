import json
import pandas as pd
from .consts import INTAKE_TIPS

def source_weight_score(s):
    try:
        d = json.loads(s)
        return sum(d.values())
    except Exception:
        return 0.0

def pick_top_by_category(df_in: pd.DataFrame, category, k=10):
    sub = df_in[df_in["main_category"] == category].copy()
    if sub.empty:
        return sub
    sub["_src_score"] = sub["category_scores"].apply(source_weight_score)
    if sub["_last_dt"].notna().any():
        sub = sub.sort_values(["_last_dt","_src_score","PRDLST_NM"], ascending=[False, False, True])
    else:
        sub = sub.sort_values(["_src_score","PRDLST_NM"], ascending=[False, True])
    sub["섭취_타이밍"] = sub["main_category"].map(INTAKE_TIPS).fillna("")
    return sub.head(k)

