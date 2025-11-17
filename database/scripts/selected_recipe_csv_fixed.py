import pandas as pd
import pymysql

# === DB 연결 정보 ===
DB_CONFIG = {
    "host": "211.51.163.232",
    "port": 19306,
    "user": "lgup3",
    "password": "lgup3P@ssw0rd",
    "database": "lgup3",
    "charset": "utf8mb4"
}

# === 파일 경로 ===
SELECTED_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\selected_recipe_dummy.csv"
OUTPUT_CSV = r"C:\githome\Personalized_healthcare_Project\database\scripts\selected_recipe_dummy_fixed.csv"

# === 1️⃣ selected_recipe CSV 불러오기 ===
df_selected = pd.read_csv(SELECTED_CSV, encoding="utf-8-sig")

# 컬럼명 공백이나 대소문자 정리
df_selected.columns = [c.strip().lower() for c in df_selected.columns]

# === 2️⃣ DB에서 recommend_recipe 데이터 불러오기 ===
print("🔗 DB에서 recommend_recipe 데이터 불러오는 중...")
conn = pymysql.connect(**DB_CONFIG)
df_recommend = pd.read_sql("SELECT recommend_id, id, recipe_id FROM recommend_recipe", conn)
conn.close()
print(f"✅ recommend_recipe에서 {len(df_recommend)}행 불러옴")

# 컬럼명 정리
df_recommend.columns = [c.strip().lower() for c in df_recommend.columns]

# === 3️⃣ 병합 가능한지 확인 ===
print("🔎 병합 전 컬럼:", list(df_selected.columns))
print("🔎 recommend_recipe 컬럼:", list(df_recommend.columns))

# === 4️⃣ id와 recipe_id 기준으로 병합 ===
df_fixed = pd.merge(
    df_selected,
    df_recommend,
    on=["id", "recipe_id"],
    how="left",
    suffixes=('_csv', '_db')   # ✅ 컬럼 충돌 방지용 suffix 설정
)

# === 5️⃣ recommend_id 누락된 행 처리 ===
if "recommend_id_db" not in df_fixed.columns:
    raise KeyError("❌ 병합 후 recommend_id_db 컬럼이 생성되지 않았습니다. DB 컬럼명을 확인하세요!")

missing = df_fixed["recommend_id_db"].isna().sum()
if missing > 0:
    print(f"⚠️ recommend_id가 없는 행 {missing}개 발견 — 삭제 처리합니다.")
    df_fixed = df_fixed.dropna(subset=["recommend_id_db"])

# === 6️⃣ recommend_id_db를 recommend_id로 이름 변경 ===
df_fixed.rename(columns={"recommend_id_db": "recommend_id"}, inplace=True)

# === 7️⃣ 정리 및 저장 ===
df_out = df_fixed[["id", "recommend_id", "recipe_id", "selected_date", "action"]]
df_out["recommend_id"] = df_out["recommend_id"].astype(int)
df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print(f"✅ recommend_id 매칭 완료 → {len(df_out)}행 유지")
print(f"📁 새 파일 저장 위치: {OUTPUT_CSV}")

