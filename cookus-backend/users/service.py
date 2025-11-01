from typing import Any, Dict, List, Tuple

from fastapi import HTTPException

from core import get_conn


class UserService:
    """Profile management helpers."""

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id             AS user_id,
                    user_name      AS user_name,
                    email          AS email,
                    gender         AS gender,
                    date_of_birth  AS date_of_birth,
                    goal           AS goal,
                    cooking_level  AS cooking_level
                FROM user_info
                WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        return row

    def update_profile(self, user_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        if not fields:
            raise HTTPException(400, "no fields to update")

        assignments: List[str] = []
        params: List[Any] = []
        for column, value in fields.items():
            assignments.append(f"{column}=%s")
            params.append(value)

        with get_conn() as conn, conn.cursor() as cur:
            sql = f"UPDATE user_info SET {', '.join(assignments)} WHERE id=%s"
            cur.execute(sql, (*params, user_id))
            cur.execute(
                """
                SELECT
                    id AS user_id,
                    user_name,
                    email,
                    gender,
                    date_of_birth,
                    goal,
                    cooking_level
                FROM user_info
                WHERE id=%s
                """,
                (user_id,),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(404, "user not found")
        return row

    def delete_account(self, user_id: str, password: str, password_confirm: str) -> Dict[str, Any]:
        password = password.strip()
        password_confirm = password_confirm.strip()
        if not password or not password_confirm:
            raise HTTPException(400, "password / password_confirm required")
        if password != password_confirm:
            raise HTTPException(400, "passwords do not match")

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, password
                FROM user_info
                WHERE id=%s
                  AND (is_deleted IS NULL OR is_deleted = 0)
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "account already deleted or not found")
            if str(row["password"]) != password:
                raise HTTPException(401, "invalid password")

            cur.execute(
                """
                UPDATE user_info
                SET user_name = %s,
                    email = %s,
                    password = %s,
                    is_deleted = 1
                WHERE id=%s
                """,
                ("**", "**", "**", user_id),
            )
            conn.commit()

        return {
            "ok": True,
            "message": "그동안 이용해주셔서 감사합니다. 계정이 삭제 처리되었습니다.",
        }


user_service = UserService()
