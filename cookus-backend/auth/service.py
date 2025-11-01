from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException
from jose import ExpiredSignatureError

from core import (
    email_service,
    get_conn,
    hash_value,
    settings,
    token_service,
    verification_store,
)


@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str
    jti: str
    refresh_expires_at: datetime


class AuthService:
    """Business logic for authentication workflows."""

    refresh_cookie_path = "/auth/refresh"

    def login(self, user_id: str, password: str, user_agent: Optional[str]) -> Tuple[Dict[str, Any], AuthTokens]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id AS user_id, user_name, password
                FROM user_info
                WHERE id=%s
                  AND (is_deleted IS NULL OR is_deleted = 0)
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()

        if not row or row["password"] != password:
            raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다.")

        tokens = self._issue_tokens(row["user_id"], user_agent)
        user_payload = {"user_id": row["user_id"], "user_name": row["user_name"]}
        return user_payload, tokens

    def signup(self, payload: Dict[str, Any], user_agent: Optional[str]) -> Tuple[Dict[str, Any], AuthTokens]:
        user_id = payload["id"]

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM user_info WHERE id=%s LIMIT 1", (user_id,))
            if cur.fetchone():
                raise HTTPException(409, "user exists")

            cur.execute(
                """
                INSERT INTO user_info
                  (id, user_name, gender, email, date_of_birth, password, goal, cooking_level)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload["id"],
                    payload["user_name"],
                    payload["gender"],
                    payload["email"],
                    payload.get("date_of_birth") or "1999-12-31",
                    payload["password"],
                    payload["goal"],
                    payload["cooking_level"],
                ),
            )

        tokens = self._issue_tokens(user_id, user_agent)
        return {"user_id": user_id, "user_name": payload["user_name"]}, tokens

    def refresh(self, refresh_token: str, user_agent: Optional[str]) -> Tuple[str, str]:
        try:
            payload = token_service.decode(refresh_token)
        except ExpiredSignatureError as exc:
            raise HTTPException(401, "Refresh expired") from exc
        except Exception as exc:  # pragma: no cover - maintain compatibility
            raise HTTPException(401, "Invalid refresh") from exc

        sub = payload.get("sub")
        jti = payload.get("jti")
        if not sub or not jti:
            raise HTTPException(401, "Invalid refresh")

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, revoked, expires_at FROM user_refresh_token WHERE user_id=%s AND jti_hash=%s",
                (sub, hash_value(jti)),
            )
            row = cur.fetchone()

            if not row or row["revoked"] or row["expires_at"] < datetime.utcnow():
                raise HTTPException(401, "Refresh invalid")

            cur.execute("UPDATE user_refresh_token SET revoked=1 WHERE id=%s", (row["id"],))

        tokens = self._issue_tokens(sub, user_agent)
        return tokens.access_token, tokens.refresh_token

    def logout(self, refresh_token: Optional[str]) -> None:
        if not refresh_token:
            return
        try:
            payload = token_service.decode(refresh_token)
        except Exception:
            return

        sub = payload.get("sub")
        jti = payload.get("jti")
        if not sub or not jti:
            return

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE user_refresh_token SET revoked=1 WHERE user_id=%s AND jti_hash=%s",
                (sub, hash_value(jti)),
            )

    async def send_find_id_code(self, email: str, username: Optional[str]) -> Dict[str, Any]:
        email = email.strip()
        username = (username or "").strip()
        if not email:
            raise HTTPException(400, "email required")

        with get_conn() as conn, conn.cursor() as cur:
            if username:
                cur.execute("SELECT id FROM user_info WHERE email=%s AND user_name=%s", (email, username))
            else:
                cur.execute("SELECT id FROM user_info WHERE email=%s", (email,))
            row = cur.fetchone()

        if not row:
            raise HTTPException(404, "no user with that email (and name)")

        code = verification_store.generate_code()
        verification_store.store_code("find_id", email, code, user_id=row["id"])
        try:
            await email_service.send_email(
                to_email=email,
                subject="[CookUS] 아이디 찾기 인증코드",
                body_text=f"인증코드: {code}\n(유효기간 {settings.code_ttl_minutes}분)\n이 코드를 앱에 입력하면 아이디를 확인할 수 있어요.",
            )
        except Exception:
            # The EmailService already logs; continue to keep behaviour consistent.
            pass

        response: Dict[str, Any] = {"ok": True}
        if settings.dev_return_codes:
            response["dev_code"] = code
            response["expires_in_sec"] = settings.code_ttl_minutes * 60
        return response

    def verify_find_id_code(self, email: str, code: str) -> Dict[str, Any]:
        email = email.strip()
        code = code.strip()
        if not email or not code:
            raise HTTPException(status_code=400, detail="email/code required")

        record = verification_store.get_record("find_id", email)
        if not record:
            raise HTTPException(status_code=400, detail="no pending verification")
        if verification_store.is_expired(record):
            verification_store.pop_record("find_id", email)
            raise HTTPException(status_code=400, detail="code expired")
        if code != record.get("code"):
            raise HTTPException(status_code=400, detail="invalid code")

        user_id = record.get("user_id")
        verification_store.pop_record("find_id", email)
        return {"user_id": user_id}

    async def send_password_code(self, user_id: str, email: str) -> Dict[str, Any]:
        user_id = user_id.strip()
        email = email.strip()
        if not user_id or not email:
            raise HTTPException(400, "id/email required")

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM user_info WHERE id=%s AND email=%s", (user_id, email))
            row = cur.fetchone()

        if not row:
            raise HTTPException(404, "no match for id+email")

        code = verification_store.generate_code()
        verification_store.store_code("find_pw", email, code, user_id=user_id)
        await email_service.send_email(
            to_email=email,
            subject="[CookUS] 비밀번호 재설정 인증코드",
            body_text=f"인증코드: {code}\n(유효기간 {settings.code_ttl_minutes}분)\n이 코드를 앱에 입력하면 비밀번호를 변경할 수 있어요.",
        )

        response: Dict[str, Any] = {"ok": True}
        if settings.dev_return_codes:
            response["dev_code"] = code
            response["expires_in_sec"] = settings.code_ttl_minutes * 60
        return response

    def reset_password(self, user_id: str, email: str, code: str, new_password: str) -> Dict[str, Any]:
        user_id = user_id.strip()
        email = email.strip()
        code = code.strip()
        new_password = new_password.strip()
        if not user_id or not email or not code or not new_password:
            raise HTTPException(400, "id/email/code/new_password required")

        record = verification_store.get_record("find_pw", email)
        if not record:
            raise HTTPException(400, "no pending verification")
        if verification_store.is_expired(record):
            verification_store.pop_record("find_pw", email)
            raise HTTPException(400, "code expired")

        if code != record.get("code") or record.get("user_id") != user_id:
            raise HTTPException(400, "invalid code")

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("UPDATE user_info SET password=%s WHERE id=%s AND email=%s", (new_password, user_id, email))
        verification_store.pop_record("find_pw", email)
        return {"ok": True}

    def set_refresh_cookie(self, response, refresh_token: str) -> None:
        response.set_cookie(
            key="refresh",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="lax",
            path=self.refresh_cookie_path,
            max_age=settings.refresh_days * 24 * 3600,
        )

    def clear_refresh_cookie(self, response) -> None:
        response.delete_cookie(key="refresh", path=self.refresh_cookie_path)

    def _issue_tokens(self, user_id: str, user_agent: Optional[str]) -> AuthTokens:
        access, refresh, jti, refresh_exp = token_service.issue_tokens(user_id)
        self._save_refresh_jti(user_id, jti, refresh_exp, user_agent)
        return AuthTokens(access, refresh, jti, refresh_exp)

    def _save_refresh_jti(self, user_id: str, jti: str, exp: datetime, user_agent: Optional[str]) -> None:
        expires_at = exp
        if exp.tzinfo is not None:
            expires_at = exp.astimezone(timezone.utc).replace(tzinfo=None)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_refresh_token(user_id, jti_hash, expires_at, user_agent, revoked)
                VALUES (%s, %s, %s, %s, 0)
                """,
                (user_id, hash_value(jti), expires_at, user_agent),
            )


auth_service = AuthService()
