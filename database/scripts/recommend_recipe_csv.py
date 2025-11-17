import pandas as pd
import random
import pymysql
from datetime import datetime, timedelta

# === DB 연결 설정 ===
DB_CONFIG = {
    "host": "211.51.163.232",
    "port": 19306,
    "user": "lgup3",
    "password": "lgup3P@ssw0rd",
    "database": "lgup3",
    "charset": "utf8mb4"
}

# === 파일 경로 ===
USER_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\user_info_dummy.csv"
RECIPE_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\recipe.csv"
OUTPUT_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\recommend_recipe_dummy.csv"

# === 연령대별 선호 재료 ===
preferred_ingredients = {
    "20대": ["닭고기_가슴살", "계란", "햄", "소시지", "만두"],
    "30대": ["닭고기_가슴살", "양배추", "바나나", "계란"],
    "40대": ["돼지고기", "두부", "계란", "생선"],
    "50대": ["두부", "계란", "현미", "미역", "생선"]
}

# === DB에서 실제 존재하는 recipe_id 목록 가져오기 ===
print("🔗 DB에서 recipe_id 목록 가져오는 중...")
conn = pymysql.connect(**DB_CONFIG)
valid_ids = pd.read_sql("SELECT recipe_id FROM recipe", conn)["recipe_id"].astype(int).tolist()
conn.close()

# === CSV 불러오기 ===
df_users = pd.read_csv(USER_CSV, encoding="utf-8-sig")
df_recipes = pd.read_csv(RECIPE_CSV, encoding="utf-8-sig")

# 🔹 recipe_id 필터링 (DB 존재하는 것만)
df_recipes = df_recipes[df_recipes["recipe_id"].isin(valid_ids)]
print(f"✅ DB에 존재하는 recipe_id만 남김 → {len(df_recipes)}개")

# 🔹 데이터 정리
df_recipes["cooking_time"] = pd.to_numeric(df_recipes["cooking_time"], errors="coerce")
df_recipes["level_nm"] = df_recipes["level_nm"].fillna("하")
df_recipes["ingredient_full"] = df_recipes["ingredient_full"].fillna("")

# === 연령대 계산 함수 ===
def get_age_group(birth_year):
    if 1996 <= birth_year <= 2005:
        return "20대"
    elif 1986 <= birth_year <= 1995:
        return "30대"
    elif 1976 <= birth_year <= 1985:
        return "40대"
    elif 1961 <= birth_year <= 1975:
        return "50대"
    else:
        return None

# === 주말 오후~저녁 시간대 생성 ===
def random_recommend_datetime():
    base_date = datetime.now() - timedelta(days=random.randint(0, 14))
    while base_date.weekday() not in [5, 6]:
        base_date -= timedelta(days=1)
    hour = random.randint(18, 21)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return base_date.replace(hour=hour, minute=minute, second=second)

# === 추천 데이터 생성 ===
records = []

for _, user in df_users.iterrows():
    user_id = user["id"]
    birth_year = int(str(user["date_of_birth"])[:4])
    age_group = get_age_group(birth_year)
    if not age_group:
        continue

    # 1️⃣ 난이도 조건
    if age_group in ["20대", "30대"]:
        recipes = df_recipes[(df_recipes["level_nm"] == "하") & (df_recipes["cooking_time"] <= 30)]
    else:
        recipes = df_recipes[(df_recipes["level_nm"] == "상") & (df_recipes["cooking_time"] > 30)]

    # 2️⃣ 재료 일치 점수 계산
    keywords = preferred_ingredients[age_group]
    recipes["match_score"] = recipes["ingredient_full"].apply(
        lambda text: sum(1 for kw in keywords if kw in str(text))
    )

    # 3️⃣ 점수 높은 순으로 정렬 후 상위 N개 중 랜덤 선택
    recipes = recipes.sort_values(by="match_score", ascending=False)
    top_recipes = recipes.head(30) if len(recipes) > 30 else recipes
    selected = top_recipes.sample(min(random.randint(2, 4), len(top_recipes)))

    for _, r in selected.iterrows():
        records.append({
            "id": user_id,
            "recipe_nm_ko": r["recipe_nm_ko"],
            "ingredient_full": r["ingredient_full"],
            "step_text": r["step_text"],
            "recipe_id": int(r["recipe_id"]),
            "recommend_date": random_recommend_datetime().strftime("%Y-%m-%d %H:%M:%S")
        })

# === CSV 저장 ===
df_out = pd.DataFrame(records)
df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print(f"✅ recommend_recipe_dummy.csv 생성 완료 ({len(df_out)}행)")
print("📁 파일 위치:", OUTPUT_CSV)
