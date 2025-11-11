import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import vision

from app.core.config import get_settings
from app.db.connection import connection_scope
from app.schemas.ingredient import IngredientItem
from app.services.ingredient_service import add_ingredient

settings = get_settings()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_vision_client: Optional[vision.ImageAnnotatorClient] = None
_BASE_DIR = Path(__file__).resolve().parents[2]


def _resolve_credentials_path(raw_path: str) -> str:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return str(candidate)
    return str((_BASE_DIR / raw_path).resolve())


def _get_vision_client() -> vision.ImageAnnotatorClient:
    global _vision_client  # noqa: PLW0603
    if _vision_client:
        return _vision_client

    credentials_path = settings.google_application_credentials
    if credentials_path:
        resolved = _resolve_credentials_path(credentials_path)
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", resolved)

    try:
        _vision_client = vision.ImageAnnotatorClient()
    except DefaultCredentialsError as exc:  # pragma: no cover - dependency error path
        raise HTTPException(
            status_code=500, detail="Google OCR 인증 정보를 찾을 수 없습니다."
        ) from exc
    except Exception as exc:  # pragma: no cover - initialization edge cases
        raise HTTPException(
            status_code=500, detail=f"OCR 클라이언트 초기화에 실패했습니다: {exc}"
        ) from exc
    return _vision_client


def _parse_amount(value: str | None) -> Optional[int]:
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _extract_items(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Attempt to extract product lines such as:
    '오)고기왕교자 1 6,980 6,980' -> ingredient_name, quantity, price, total_price.
    Supports two-line structures (name line + qty/price line).
    """
    items: List[Dict[str, Any]] = []
    barcode_pattern = re.compile(r"^\d{10,}$")
    total_keywords = re.compile(r"(합계|총금액|카드|현금|VAT|부가세|결제)")

    pending_name: Optional[str] = None
    seen_raw_lines: set[str] = set()
    pending_qty: Optional[int] = None
    pending_price: Optional[int] = None
    pending_total: Optional[int] = None

    def _commit_item() -> None:
        nonlocal pending_name, pending_qty, pending_price, pending_total
        if not pending_name:
            return
        qty = max(1, pending_qty or 1)
        price = pending_price if pending_price is not None else 0
        total = pending_total if pending_total is not None else (price * qty if price else 0)
        if price <= 0 and total <= 0:
            pending_name = None
            pending_qty = None
            pending_price = None
            pending_total = None
            return
        if price <= 0 and total > 0:
            if qty > 0:
                price = max(1, total // qty)
        if total <= 0 and price > 0:
            total = price * qty
        items.append(
            {
                "ingredient_name": pending_name[:120],
                "quantity": qty,
                "price": price,
                "total_price": total,
            }
        )
        pending_name = None
        pending_qty = None
        pending_price = None
        pending_total = None

    for raw_line in lines:
        normalized = raw_line.strip()
        if not normalized or normalized in seen_raw_lines:
            continue
        seen_raw_lines.add(normalized)

        if total_keywords.search(normalized):
            _commit_item()
            pending_name = None
            pending_qty = None
            pending_price = None
            pending_total = None
            continue

        if barcode_pattern.match(normalized):
            continue

        if re.match(r"^\d+$", normalized):
            try:
                pending_qty = int(normalized)
            except ValueError:
                pending_qty = 1
            continue

        if re.match(r"^[0-9,]+$", normalized):
            if pending_price is None:
                pending_price = _parse_amount(normalized)
            elif pending_total is None:
                pending_total = _parse_amount(normalized)
                _commit_item()
            continue

        m = re.match(r"^(?P<name>[가-힣A-Za-z0-9\s\-\(\)\*\+/]+?)\s+(?P<qty>\d+)\s+(?P<price>[0-9,]+)\s+(?P<total>[0-9,]+)", normalized)
        if m:
            pending_name = _clean_item_name(m.group("name"))
            pending_qty = int(m.group("qty"))
            pending_price = _parse_amount(m.group("price"))
            pending_total = _parse_amount(m.group("total"))
            _commit_item()
            continue

        cleaned_candidate = _clean_item_name(normalized)
        if cleaned_candidate and re.search(r"[가-힣A-Za-z]", cleaned_candidate):
            _commit_item()
            pending_name = cleaned_candidate

    _commit_item()
    return items[:30]


def _clean_item_name(raw: str) -> str:
    """Normalize item names by removing leading indices or barcode-like tokens."""
    name = re.sub(r"^[0-9]+[.)\s\-\*]+", "", raw).strip()
    tokens = [
        token
        for token in name.split()
        if not re.fullmatch(r"\d{8,}", token)
    ]
    cleaned = " ".join(tokens).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned


def _call_vision_api(image_bytes: bytes) -> str:
    client = _get_vision_client()
    vision_image = vision.Image(content=image_bytes)
    try:
        response = client.document_text_detection(image=vision_image)
    except GoogleAPIError as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"OCR 호출에 실패했습니다: {exc}") from exc

    if response.error.message:  # pragma: no cover - API level error
        raise HTTPException(
            status_code=502, detail=f"OCR 오류: {response.error.message}"
        )

    if response.full_text_annotation and response.full_text_annotation.text:
        text = response.full_text_annotation.text
        logger.debug("OCR full text:\n%s", text)
        print("OCR full text:\n", text)
        return text

    if response.text_annotations:
        text = response.text_annotations[0].description
        logger.debug("OCR text annotation:\n%s", text)
        print("OCR text annotation:\n", text)
        return text

    raise HTTPException(status_code=400, detail="영수증 텍스트를 감지하지 못했습니다.")


def _persist_receipt_items(user_id: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []

    persisted: List[Dict[str, Any]] = []
    with connection_scope() as conn:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO receipt (id, ingredient_name, quantity, price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """
            for item in items:
                cur.execute(
                    sql,
                    (
                        user_id,
                        item["ingredient_name"],
                        item["quantity"],
                        item["price"],
                        item["total_price"],
                    ),
                )
                persisted.append(
                    {
                        "receipt_id": cur.lastrowid,
                        "id": user_id,
                        **item,
                    }
                )
        conn.commit()
    return persisted


def _sync_fridge_items(user_id: str, items: List[Dict[str, Any]]) -> None:
    for item in items:
        ingredient = IngredientItem(
            user_id=user_id,
            name=item["ingredient_name"],
            amount=str(item.get("quantity", 1)),
        )
        add_ingredient(ingredient)


async def upload_receipt(user_id: str, upload: UploadFile) -> dict:
    if not user_id:
        raise HTTPException(status_code=400, detail="id가 필요합니다.")
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드할 수 있습니다.")

    file_bytes = await upload.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="비어있는 파일입니다.")

    full_text = _call_vision_api(file_bytes)
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    items = _extract_items(lines)
    if not items:
        raise HTTPException(status_code=400, detail="영수증에서 품목 정보를 찾지 못했습니다.")

    persisted = _persist_receipt_items(user_id, items)
    try:
        _sync_fridge_items(user_id, persisted)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - fridge sync failure
        logger.exception("Failed to sync fridge items from receipt", exc_info=exc)
        raise HTTPException(status_code=500, detail="냉장고 재료 반영에 실패했습니다.") from exc

    return {"receipt_items": persisted}


def list_receipts(user_id: str) -> dict:
    if not user_id:
        raise HTTPException(status_code=400, detail="id가 필요합니다.")
    with connection_scope() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    receipt_id,
                    id,
                    ingredient_name,
                    quantity,
                    price,
                    total_price
                FROM receipt
                WHERE id = %s
                ORDER BY receipt_id DESC
                LIMIT 50
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return {"receipt_items": rows}


def delete_receipt_item(user_id: str, receipt_id: int) -> dict:
    if not user_id:
        raise HTTPException(status_code=400, detail="id가 필요합니다.")
    if not receipt_id:
        raise HTTPException(status_code=400, detail="receipt_id가 필요합니다.")
    with connection_scope() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM receipt WHERE receipt_id = %s AND id = %s",
                (receipt_id, user_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="삭제할 영수증 항목을 찾을 수 없습니다.")
        conn.commit()
    return {"message": "삭제되었습니다."}
