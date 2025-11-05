from fastapi import HTTPException

from app.db.connection import connection_scope
from app.schemas.user import UpdateLevelRequest, UpdateProfileRequest


def get_user_name(user_id: str) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_name FROM user_info WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if not user:
                    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
                return {"name": user["user_name"]}
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def get_user_info(user_id: str) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_name, email, gender, date_of_birth, goal, cooking_level
                    FROM user_info
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                user = cur.fetchone()
                if not user:
                    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
                return user
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def update_level(payload: UpdateLevelRequest) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE user_info SET cooking_level = %s WHERE id = %s",
                    (payload.new_level, payload.id),
                )
            conn.commit()
        return {"message": "요리 난이도가 변경되었습니다."}
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def update_profile(payload: UpdateProfileRequest) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_info
                    SET goal = %s,
                        cooking_level = %s
                    WHERE id = %s
                    """,
                    (payload.goal, payload.cooking_level, payload.id),
                )
            conn.commit()
        return {"message": "프로필이 업데이트되었습니다."}
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def delete_user(user_id: str) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_info WHERE id = %s", (user_id,))
            conn.commit()
        return {"message": "회원 탈퇴가 완료되었습니다."}
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc
