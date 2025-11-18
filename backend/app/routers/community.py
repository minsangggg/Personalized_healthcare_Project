from pathlib import Path
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.db.connection import connection_scope
from app.schemas.community import BoardLikeRequest

router = APIRouter(tags=["community"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "event_photos"


@router.get("/events")
def list_events():
    with connection_scope() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    event_id,
                    event_name,
                    event_description,
                    start_date,
                    end_date
                FROM event
                ORDER BY start_date DESC, event_id DESC
                """
            )
            rows = cur.fetchall()
    return {"events": rows}


@router.get("/board")
def list_board():
    with connection_scope() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    content_id,
                    event_id,
                    id AS user_id,
                    content_title,
                    content_text,
                    like_count,
                    created_at
                FROM board
                ORDER BY created_at DESC, content_id DESC
                """
            )
            rows = cur.fetchall()
    return {"posts": rows}


@router.post("/board/like")
def like_post(payload: BoardLikeRequest):
    user_id = payload.user_id
    content_id = payload.content_id
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO board_likes (content_id, id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE created_at = CURRENT_TIMESTAMP
                    """,
                    (content_id, user_id),
                )
                cur.execute(
                    """
                    UPDATE board
                    SET like_count = like_count + 1
                    WHERE content_id = %s
                    """,
                    (content_id,),
                )
            conn.commit()
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc
    return {"message": "좋아요가 반영되었습니다."}


@router.get("/progress/{user_id}")
def get_progress(user_id: str):
    summary = {
        "user_id": user_id,
        "total_posts": 0,
        "likes_received": 0,
        "likes_given": 0,
        "rewards": 0,
        "last_goal": 0,
        "goal_updated_at": None,
    }
    with connection_scope() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(like_count),0) AS likes FROM board WHERE id = %s", (user_id,))
            row = cur.fetchone() or {}
            summary["total_posts"] = int(row.get("cnt") or 0)
            summary["likes_received"] = int(row.get("likes") or 0)

            cur.execute("SELECT COUNT(*) AS cnt FROM board_likes WHERE id = %s", (user_id,))
            row = cur.fetchone() or {}
            summary["likes_given"] = int(row.get("cnt") or 0)

            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM like_reward_cache
                WHERE content_id IN (
                    SELECT content_id FROM board WHERE id = %s
                )
                """,
                (user_id,),
            )
            row = cur.fetchone() or {}
            summary["rewards"] = int(row.get("cnt") or 0)

            cur.execute("SELECT last_goal, updated_at FROM goal_state_cache WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                summary["last_goal"] = int(row.get("last_goal") or 0)
                summary["goal_updated_at"] = row.get("updated_at")
    return summary


@router.post("/events/{event_id}/upload")
async def upload_event_photo(
    event_id: int,
    user_id: str = Form(..., description="업로드 사용자 ID"),
    file: UploadFile = File(..., description="이벤트 업로드 이미지"),
):
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = file.filename or "upload"
        dest = UPLOAD_DIR / f"event_{event_id}_{user_id}_{safe_name}"
        with dest.open("wb") as fout:
            shutil.copyfileobj(file.file, fout)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"업로드 실패: {exc}") from exc
    return {"message": "업로드 완료", "path": str(dest)}
