# ============================================================
# main.py — CookUs 자동 뱃지 시스템 (자동 스케줄러 통합)
# ============================================================

from fastapi import FastAPI
from .scheduler import start_scheduler                # ✅ 상대 경로 수정
from .scheduler_event import start_event_scheduler    # ✅ 상대 경로 수정
from .router import router as badge_router            # ✅ 상대 경로 수정

app = FastAPI(title="CookUs 자동 뱃지 시스템")

@app.on_event("startup")
def startup_event():
    start_scheduler()
    start_event_scheduler()
    print("✅ All schedulers started successfully.")

@app.get("/")
def root():
    return {"message": "CookUs Badge System running"}

# ✅ /me/badges/... 라우터 통합 등록
app.include_router(badge_router)
