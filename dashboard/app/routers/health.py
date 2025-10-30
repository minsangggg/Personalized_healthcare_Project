from fastapi import APIRouter, Depends
from ..db import get_db
from ..schemas import DBTestResponse

router = APIRouter(tags=["default"])

@router.get("/", summary="서버 상태 확인")
def home():
    return {"message": "서버 정상 작동 중입니다 🚀"}

@router.get("/test-db", response_model=DBTestResponse, summary="DB 연결 테스트")
def test_db(db = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT NOW() AS now_time")
        row = cur.fetchone()
    return {"db_time": row["now_time"]}
