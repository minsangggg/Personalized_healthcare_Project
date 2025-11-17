import pandas as pd
import pymysql

# 🔹 DB 연결 설정
DB_CONFIG = {
    "host": "211.51.163.232",
    "port": 19306,
    "user": "lgup3",
    "password": "lgup3P@ssw0rd",
    "database": "lgup3",
    "charset": "utf8mb4"
}

# 🔹 CSV 파일 경로
CSV_FILE = r"C:\githome\Personalized_healthcare_Project\database\scripts\recommend_recipe_dummy.csv"

# 🔹 CSV 불러오기
print("📂 CSV 불러오는 중...")
df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
print(f"✅ 총 {len(df)}행 데이터 확인됨")

# 🔹 DB 연결
print("🔗 MariaDB 연결 중...")
conn = pymysql.connect(**DB_CONFIG)
cur = conn.cursor()

# 🔹 INSERT 쿼리 (recommend_id 제외!)
insert_query = """
INSERT INTO recommend_recipe (id, recipe_nm_ko, ingredient_full, step_text, recipe_id, recommend_date)
VALUES (%s, %s, %s, %s, %s, %s)
"""

# 🔹 한 줄씩 삽입
inserted = 0
for _, row in df.iterrows():
    cur.execute(insert_query, (
        row["id"],
        row["recipe_nm_ko"],
        row["ingredient_full"],
        row["step_text"],
        int(row["recipe_id"]),
        row["recommend_date"]
    ))
    inserted += 1
    if inserted % 100 == 0:
        print(f"🟢 {inserted}행 삽입 완료...")

conn.commit()
cur.close()
conn.close()

print(f"✅ recommend_recipe 테이블에 총 {inserted}행이 성공적으로 추가되었습니다!")
