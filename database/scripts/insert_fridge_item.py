import pandas as pd
import pymysql

# ✅ DB 연결정보
DB_CONFIG = {
    "host": "211.51.163.232",
    "port": 19306,
    "user": "lgup3",
    "password": "lgup3P@ssw0rd",
    "database": "lgup3",
    "charset": "utf8mb4"
}

# ✅ CSV 경로
CSV_FILE = r"C:\githome\Personalized_healthcare_Project\database\scripts\fridge_item_dummy.csv"

# ✅ CSV 읽기
df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")

# ✅ DB 연결
conn = pymysql.connect(**DB_CONFIG)
cur = conn.cursor()

# ✅ INSERT 쿼리
insert_query = """
INSERT INTO fridge_item (fridge_id, id, ingredient_name, quantity, stored_at)
VALUES (%s, %s, %s, %s, %s)
"""

# ✅ 한 줄씩 삽입
inserted = 0
for _, row in df.iterrows():
    cur.execute(insert_query, tuple(row))
    inserted += 1

conn.commit()
cur.close()
conn.close()

print(f"✅ 총 {inserted}행이 fridge_item 테이블에 성공적으로 추가되었습니다!")
