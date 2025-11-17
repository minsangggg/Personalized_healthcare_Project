import pandas as pd
import random
import uuid
from datetime import datetime, timedelta

# === 경로 설정 ===
USER_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\user_info_dummy.csv"
OUTPUT_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\fridge_item_dummy.csv"

# === 연령대별 재료 세트 ===
ING_BY_AGE = {
    "20대": ["닭고기_가슴살", "계란", "햄/소시지", "만두"],
    "30대": ["닭고기_가슴살", "양배추", "바나나", "계란"],
    "40대": ["돼지고기", "두부", "계란", "생선"],
    "50대": ["두부", "계란", "현미", "미역", "생선"],
}

def get_age_group(birth_year: int):
    if 1996 <= birth_year <= 2005:
        return "20대"
    elif 1986 <= birth_year <= 1995:
        return "30대"
    elif 1976 <= birth_year <= 1985:
        return "40대"
    elif 1961 <= birth_year <= 1975:
        return "50대"
    return None

def pick_ingredients_for_group(group: str):
    """
    핵심 재료가 더 자주 등장하도록 가중치 반영:
    - 핵심 1~2개 우선 포함
    - 보조 2~4개는 전체 풀에서 선택
    - 중복 제거 후 4~6개 사이가 되도록 트리밍
    """
    pool = ING_BY_AGE[group]
    # 핵심 1~2개
    core_k = random.randint(1, 2)
    core = random.sample(pool, k=core_k)
    # 보조 2~4개
    others_k = random.randint(2, 4)
    others = random.choices(pool, k=others_k)  # 보조는 중복 가능
    merged = list(dict.fromkeys(core + others))  # 순서 유지하며 중복 제거

    # 최종 개수 4~6개로 맞추기
    if len(merged) < 4:
        # 부족하면 풀에서 추가
        extra = [x for x in pool if x not in merged]
        random.shuffle(extra)
        merged += extra[: 4 - len(merged)]
    elif len(merged) > 6:
        merged = merged[:6]

    random.shuffle(merged)
    return merged

# === CSV 로드 및 컬럼 정규화 ===
df = pd.read_csv(USER_CSV, encoding="utf-8-sig")

# 컬럼명 공백/대소문자 이슈 대비
norm_cols = {c: c.strip().lower() for c in df.columns}
df.columns = [norm_cols[c] for c in df.columns]

# id 컬럼 찾기 (case-insensitive)
id_col_candidates = [c for c in df.columns if c == "id"]
if not id_col_candidates:
    # 인덱스로 들어간 경우 (Unnamed: 0 등) 대비: 보조 탐색 (지양되지만 가드)
    raise ValueError("CSV에서 'id' 컬럼을 찾지 못했습니다. 헤더에 id 컬럼이 있는지 확인하세요.")
id_col = id_col_candidates[0]

# date_of_birth 컬럼 확인
dob_col_candidates = [c for c in df.columns if c in ("date_of_birth", "dob")]
if not dob_col_candidates:
    raise ValueError("CSV에서 'date_of_birth' 컬럼을 찾지 못했습니다.")
dob_col = dob_col_candidates[0]

# 결측/공백 제거 및 정리
df[id_col] = df[id_col].astype(str).str.strip()
df[dob_col] = df[dob_col].astype(str).str.strip()

# 유효한 id와 yyyy-mm-dd 형태 DOB만 필터
df = df[(df[id_col] != "") & (df[dob_col].str.len() >= 4)]
df["birth_year"] = df[dob_col].str.slice(0, 4).astype(int)

# 중복 제거
df = df.drop_duplicates(subset=[id_col]).copy()

# 연령대 매핑
df["age_group"] = df["birth_year"].apply(get_age_group)
df = df[~df["age_group"].isna()].copy()

# 기대치: 총 160명 (각 연령대 40명)
unique_ids = df[id_col].nunique()
if unique_ids == 0:
    raise ValueError("유효한 사용자 id를 1건도 찾지 못했습니다. CSV 내용을 확인하세요.")
print(f"✅ user_info ids 확보: {unique_ids}명")

# === fridge_item 레코드 생성 ===
records = []
now = datetime.now()

for _, row in df.iterrows():
    user_id = row[id_col]
    group = row["age_group"]

    # 사용자당 4~6개 재료
    ingredients = pick_ingredients_for_group(group)

    for ing in ingredients:
        rec = {
            "fridge_id": str(uuid.uuid4()),
            "id": user_id,
            "ingredient_name": ing,
            "quantity": random.randint(1, 7),
            "stored_at": (now - timedelta(days=random.randint(1, 30),
                                          hours=random.randint(0, 23),
                                          minutes=random.randint(0, 59),
                                          seconds=random.randint(0, 59))
                         ).strftime("%Y-%m-%d %H:%M:%S")
        }
        records.append(rec)

df_out = pd.DataFrame(records, columns=["fridge_id", "id", "ingredient_name", "quantity", "stored_at"])
df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print(f"✅ 생성 완료: {OUTPUT_CSV} (총 {len(df_out)}행)")
# 간단 검증 출력
print("샘플 5행:")
print(df_out.head(5).to_string(index=False))
