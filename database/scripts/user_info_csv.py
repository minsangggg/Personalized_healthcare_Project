import random
import csv
from datetime import datetime

# -----------------------------
# 설정
# -----------------------------
output_file = "user_info_dummy.csv"
num_per_age = 40
age_groups = [
    ("20대", (1996, 2005), "하"),
    ("30대", (1986, 1995), "하"),
    ("40대", (1976, 1985), "상"),
    ("50대", (1961, 1975), "상"),
]

# 이름 데이터 풀
first_names = ["김", "이", "박", "최", "정", "윤", "조", "한", "오", "신", "서", "임", "유", "홍", "양", "문", "노", "백", "권", "남"]
last_names = ["민수", "서연", "지후", "하늘", "도윤", "지민", "하은", "유진", "현우", "예린",
               "다빈", "시우", "지호", "수빈", "하윤", "태민", "은서", "연우", "서준", "나연"]

# 랜덤 비밀번호 생성
def random_pw():
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(8))

# 랜덤 생년월일
def random_birth(start_year, end_year):
    y = random.randint(start_year, end_year)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y}-{m:02d}-{d:02d}"

# 랜덤 성별
def random_gender():
    return random.choice(["남", "여"])

# -----------------------------
# 데이터 생성
# -----------------------------
records = []
used_names = set()

for group, (start, end), level in age_groups:
    for i in range(num_per_age):
        # 이름 중복 방지
        while True:
            name = random.choice(first_names) + random.choice(last_names)
            if name not in used_names:
                used_names.add(name)
                break
        
        # id는 영문 이름 + index
        eng_id = (
            name.encode("utf-8", errors="ignore").hex()[:6]
            + str(random.randint(100, 999))
        )
        email = f"{eng_id}@example.com"
        gender = random_gender()
        pw = random_pw()
        dob = random_birth(start, end)
        goal = random.randint(1, 6)
        
        records.append([eng_id, name, email, pw, gender, dob, level, goal, 0])

# -----------------------------
# CSV 저장
# -----------------------------
with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "user_name", "email", "password", "gender", "date_of_birth", "cooking_level", "goal", "is_deleted"])
    writer.writerows(records)

print(f"✅ {output_file} 파일이 생성되었습니다! (총 {len(records)}명)")
