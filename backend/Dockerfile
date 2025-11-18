FROM python:3.10

# 작업 디렉터리 설정
WORKDIR /app

# requirements.txt 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 코드 복사
COPY . .

# 8080 포트 개방
EXPOSE 8080

# Uvicorn 실행 (FastAPI 서버)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
