import pandas as pd
import pymysql

# === DB 연결 설정 ===
DB_CONFIG = {
    "host": "211.51.163.232",
    "port": 19306,
    "user": "lgup3",
    "password": "lgup3P@ssw0rd",
    "database": "lgup3",
    "charset": "utf8mb4"
}

# === CSV 파일 경로 ===
CSV_PATH = r"C:\githome\Personalized_healthcare_Project\database\scripts\selected_recipe_dummy_fixed.csv"

# === CSV 불러오기 ===
print("📂 CSV 불러오는 중...")
df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
print(f"✅ 총 {len(df)}행 데이터 확인됨")

# 🔹 recommend_id, recipe_id를 정수형으로 변환 (문자열로 들어오는 문제 방지)
df["recommend_id"] = df["recommend_id"].astype(int)
df["recipe_id"] = df["recipe_id"].astype(int)
df["action"] = df["action"].astype(int)

# === DB 연결 ===
conn = pymysql.connect(**DB_CONFIG)
cur = conn.cursor()

insert_query = """
INSERT INTO selected_recipe (id, recommend_id, recipe_id, selected_date, action, updated_at)
VALUES (%s, %s, %s, %s, %s, NOW())
"""

# === 데이터 튜플 생성 ===
data = [
    (
        row["id"],
        row["recommend_id"],
        row["recipe_id"],
        row["selected_date"],
        row["action"]
    )
    for _, row in df.iterrows()
]

# === 데이터 삽입 ===
try:
    print("🚀 데이터 삽입 중...")
    cur.executemany(insert_query, data)
    conn.commit()
    print(f"✅ selected_recipe 테이블에 {len(data)}행 삽입 완료 (정상 recommend_id 포함)")
except Exception as e:
    print("❌ 오류 발생:", e)
    conn.rollback()
finally:
    cur.close()
    conn.close()
    print("🔒 DB 연결 종료")
