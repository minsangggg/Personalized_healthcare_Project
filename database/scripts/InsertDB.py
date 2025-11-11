import pandas as pd
import pymysql

# ------------------------------------------
# 1️⃣ DB 연결 함수 (이미 가지고 계신 정보 그대로 사용)
# ------------------------------------------
def get_connection():
    return pymysql.connect(
        host="211.51.163.232",
        port=19306,
        user="lgup3",
        password="lgup3P@ssw0rd",
        database="lgup3",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

# ------------------------------------------
# 2️⃣ CSV 파일 경로
# ------------------------------------------
csv_path = r"C:\githome\Personalized_healthcare_Project\코드\recipe.csv"

# CSV 불러오기
df = pd.read_csv(csv_path)

print(f"CSV 파일 로드 완료 — 총 {len(df)}행")

# ------------------------------------------
# 3️⃣ DB 연결 및 삽입
# ------------------------------------------
conn = get_connection()
cursor = conn.cursor()

try:
    # ✅ 기존 데이터 삭제
    cursor.execute("TRUNCATE TABLE recipe;")
    conn.commit()
    print("기존 recipe 테이블 데이터 전체 삭제 완료")

    # ✅ 컬럼 자동 매핑
    cols = ",".join(df.columns)
    placeholders = ",".join(["%s"] * len(df.columns))
    insert_sql = f"INSERT INTO recipe ({cols}) VALUES ({placeholders})"

    # ✅ 삽입 실행
    for _, row in df.iterrows():
        cursor.execute(insert_sql, tuple(row))

    conn.commit()
    print(f"✅ {len(df)}개의 행이 recipe 테이블에 성공적으로 삽입되었습니다!")

except Exception as e:
    print("❌ 에러 발생:", e)
    conn.rollback()

finally:
    cursor.close()
    conn.close()
    print("🔒 DB 연결 종료 완료")
