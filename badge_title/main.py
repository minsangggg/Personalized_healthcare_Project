from fastapi import FastAPI
from router import router as badge_title_router  # ✅ 같은 폴더에 있으니까 상대 import
import os, sys

# 현재 디렉토리를 모듈 경로에 추가 (상위 import 방지용)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="CookUs Badge Title System")

# ✅ 라우터 등록
app.include_router(badge_title_router)
