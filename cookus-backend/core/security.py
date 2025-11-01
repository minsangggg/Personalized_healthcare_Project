import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from .settings import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TokenService:
    """Issue and decode JWT access/refresh tokens."""

    def __init__(self):
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm

    def create_access_refresh(self, sub: str) -> Tuple[str, str]:
        now = utc_now()
        access = jwt.encode(
            {
                "sub": sub,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=settings.access_minutes)).timestamp()),
            },
            self._secret,
            algorithm=self._algorithm,
        )
        refresh = jwt.encode(
            {
                "sub": sub,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=settings.refresh_days)).timestamp()),
            },
            self._secret,
            algorithm=self._algorithm,
        )
        return access, refresh

    def issue_tokens(self, sub: str) -> Tuple[str, str, str, datetime]:
        """Return access, refresh, jti, and refresh expiration timestamp."""
        jti = secrets.token_urlsafe(24)
        now = utc_now()
        access = jwt.encode(
            {
                "sub": sub,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=settings.access_minutes)).timestamp()),
            },
            self._secret,
            algorithm=self._algorithm,
        )
        refresh_exp = now + timedelta(days=settings.refresh_days)
        refresh = jwt.encode(
            {
                "sub": sub,
                "jti": jti,
                "iat": int(now.timestamp()),
                "exp": int(refresh_exp.timestamp()),
            },
            self._secret,
            algorithm=self._algorithm,
        )
        return access, refresh, jti, refresh_exp

    def decode(self, token: str) -> dict:
        return jwt.decode(token, self._secret, algorithms=[self._algorithm])


token_service = TokenService()
bearer = HTTPBearer(auto_error=False)


def hash_value(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def get_current_user(request: Request, _=Depends(bearer)) -> str:
    auth = request.headers.get("Authorization", "").strip()
    if not auth:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth
    if token.lower().startswith("bearer "):
        token = token.split(None, 1)[1].strip()
        if token.lower().startswith("bearer "):
            token = token.split(None, 1)[1].strip()

    try:
        payload = token_service.decode(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid payload")
        return str(sub)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
