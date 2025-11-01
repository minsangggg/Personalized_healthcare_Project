import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .settings import settings
from .security import utc_now


class VerificationStore:
    """In-memory verification code store keyed by (purpose, email)."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def make_key(purpose: str, email: str) -> str:
        return f"{purpose}:{email}"

    @staticmethod
    def generate_code(length: int = 6) -> str:
        return "".join(random.choices(string.digits, k=length))

    def store_code(self, purpose: str, email: str, code: str, **extra: Any) -> Dict[str, Any]:
        record = {
            "code": code,
            "expires_at": utc_now() + timedelta(minutes=settings.code_ttl_minutes),
        }
        record.update(extra)
        self._store[self.make_key(purpose, email)] = record
        return record

    def get_record(self, purpose: str, email: str) -> Optional[Dict[str, Any]]:
        return self._store.get(self.make_key(purpose, email))

    def pop_record(self, purpose: str, email: str) -> Optional[Dict[str, Any]]:
        return self._store.pop(self.make_key(purpose, email), None)

    @staticmethod
    def is_expired(record: Dict[str, Any]) -> bool:
        expires_at = record.get("expires_at")
        if not isinstance(expires_at, datetime):
            return True
        return utc_now() > expires_at


verification_store = VerificationStore()
