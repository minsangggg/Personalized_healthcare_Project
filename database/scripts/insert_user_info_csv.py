import pandas as pd
import pymysql

# 1️⃣ DB 연결 정보
DB_CONFIG = {
    "host": "211.51.163.232",
    "port": 19306,
    "user": "lgup3",
    "password": "lgup3P@ssw0rd",
    "database": "lgup3",
    "charset": "utf8mb4"
}

# 2️⃣ CSV 파일 경로
CSV_FILE = r"C:\githome\Personalized_healthcare_Project\database\scripts\user_info_dummy.csv"

# 3️⃣ CSV 읽기
try:
    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    print(f"✅ CSV 파일 로드 완료: {len(df)}행")
except Exception as e:
    print(f"❌ CSV 읽기 오류: {e}")
    exit()

# 4️⃣ MariaDB 연결
try:
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("✅ MariaDB 연결 성공")
except Exception as e:
    print(f"❌ DB 연결 실패: {e}")
    exit()

# 5️⃣ INSERT 쿼리 정의
insert_query = """
INSERT INTO user_info 
(id, user_name, email, password, gender, date_of_birth, cooking_level, goal, is_deleted)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# 6️⃣ 데이터 삽입
inserted = 0
for _, row in df.iterrows():
    try:
        cur.execute(insert_query, tuple(row))
        inserted += 1
    except pymysql.err.IntegrityError as e:
        print(f"⚠️ 중복 또는 무시된 행 (id={row['id']}): {e}")
    except Exception as e:
        print(f"❌ 오류 (id={row['id']}): {e}")

# 7️⃣ 커밋 및 종료
conn.commit()
cur.close()
conn.close()

print(f"✅ 총 {inserted}개의 행이 성공적으로 user_info 테이블에 삽입되었습니다!")
