# main.py
from fastapi import FastAPI
from scheduler import start_scheduler

app = FastAPI(title="CookUs 자동 뱃지 시스템")

# ✅ 스케줄러 자동 시작
start_scheduler()

@app.get("/")
def root():
    return {"message": "CookUs Badge System running 🚀"}
