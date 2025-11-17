import pandas as pd
import random
from datetime import datetime, timedelta

# === 파일 경로 ===
USER_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\user_info_dummy.csv"
RECOMMEND_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\recommend_recipe_dummy.csv"
OUTPUT_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\selected_recipe_dummy.csv"

# === 연령대별 주요 재료 (선택 확률 가중용) ===
preferred_ingredients = {
    "20대": ["닭고기_가슴살", "계란", "햄", "소시지", "만두"],
    "30대": ["닭고기_가슴살", "양배추", "바나나", "계란"],
    "40대": ["돼지고기", "두부", "계란", "생선"],
    "50대": ["두부", "계란", "현미", "미역", "생선"]
}

# === 연령대 판별 함수 ===
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

# === 앱 사용 시각 생성 (18~21시 중심) ===
def random_selected_time(base_time):
    base = datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")
    # 주로 18~21시 사이로 조정
    hour = random.choices(
        [18, 19, 20, 21, 22],  # 살짝 분산 허용
        weights=[0.3, 0.3, 0.25, 0.1, 0.05]
    )[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return base.replace(hour=hour, minute=minute, second=second)

# === CSV 불러오기 ===
df_users = pd.read_csv(USER_CSV, encoding="utf-8-sig")
df_recommend = pd.read_csv(RECOMMEND_CSV, encoding="utf-8-sig")

records = []

# === 추천 레시피 중 일부만 선택(action=1) ===
for _, rec in df_recommend.iterrows():
    user_id = rec["id"]
    recipe_id = int(rec["recipe_id"])
    recommend_date = rec["recommend_date"]
    ingredient_text = str(rec["ingredient_full"])

    # 사용자 연령대 판별
    user_row = df_users[df_users["id"] == user_id]
    if user_row.empty:
        continue
    birth_year = int(str(user_row.iloc[0]["date_of_birth"])[:4])
    age_group = get_age_group(birth_year)
    if not age_group:
        continue

    # 1️⃣ 기본 선택 확률 (기본 30%)
    prob = 0.3

    # 2️⃣ 재료 일치 시 선택 확률 증가
    for ing in preferred_ingredients[age_group]:
        if ing in ingredient_text:
            prob += 0.1  # 재료 포함 시 10% 추가
    prob = min(prob, 0.9)  # 최대 90% 제한

    # 3️⃣ 선택 여부 결정
    action = 1 if random.random() < prob else 0

    # 4️⃣ selected_date 생성 (recommend_date 기준 ±0~2시간 내)
    selected_time = random_selected_time(recommend_date)

    # 레코드 저장
    records.append({
        "id": user_id,
        "recommend_id": None,  # DB 삽입 시 자동 매핑
        "recipe_id": recipe_id,
        "selected_date": selected_time.strftime("%Y-%m-%d %H:%M:%S"),
        "action": action
    })

# === CSV 저장 ===
df_out = pd.DataFrame(records)
df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print(f"✅ selected_recipe_dummy.csv 생성 완료 ({len(df_out)}행)")
print("📁 파일 위치:", OUTPUT_CSV)
