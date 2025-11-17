import logging
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import vision
from PIL import Image, ImageEnhance, ImageOps

from app.core.config import get_settings
from app.db.connection import connection_scope
from app.schemas.ingredient import IngredientItem
from app.services.ingredient_service import add_ingredient

settings = get_settings()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_vision_client: Optional[vision.ImageAnnotatorClient] = None
_BASE_DIR = Path(__file__).resolve().parents[2]
_MAX_REASONABLE_QTY = 99


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


def _normalize_qty(value: Optional[int]) -> Optional[int]:
    if value is None or value <= 0:
        return None
    if value > _MAX_REASONABLE_QTY:
        return None
    return value


def _extract_items(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Attempt to extract product lines such as:
    '오)고기왕교자 1 6,980 6,980' -> ingredient_name, quantity, price, total_price.
    Supports two-line structures (name line + qty/price line).
    """
    items: List[Dict[str, Any]] = []
    barcode_pattern = re.compile(r"^\d{10,}$")
    summary_keywords = re.compile(
        r"(번호뒤|면세|과세|세액|매출액|합계|총금액|카드|현금|VAT|부가세|결제|지불|거스름|PARKING|주차|적립)",
        re.IGNORECASE,
    )
    qty_price_total_pattern = re.compile(
        r"^(?:(?P<barcode>\d{8,})\s+)?(?P<qty>\d+)\s+(?P<price>[0-9,]+)(?:\s+(?P<total>[0-9,]+))?$"
    )
    price_total_pattern = re.compile(
        r"^(?:(?P<barcode>\d{8,})\s+)?(?P<price>[0-9,]+)\s+(?P<total>[0-9,]+)$"
    )

    pending_name: Optional[str] = None
    pending_qty: Optional[int] = None
    pending_price: Optional[int] = None
    pending_total: Optional[int] = None
    summary_reached = False
    floating_initial_totals: List[int] = []
    floating_deferred_totals: List[int] = []
    has_seen_item = False
    missing_total_indices: List[int] = []

    def _commit_item() -> None:
        nonlocal pending_name, pending_qty, pending_price, pending_total
        if not pending_name:
            pending_qty = None
            pending_price = None
            pending_total = None
            return
        normalized_qty = _normalize_qty(pending_qty)
        qty = normalized_qty if normalized_qty is not None else 1
        price = pending_price if pending_price is not None else 0
        total = pending_total if pending_total is not None else (price * qty if price else 0)
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
        if total <= 0:
            missing_total_indices.append(len(items) - 1)
        pending_name = None
        pending_qty = None
        pending_price = None
        pending_total = None

    for raw_line in lines:
        normalized = raw_line.strip()
        if not normalized:
            continue

        if summary_keywords.search(normalized):
            _commit_item()
            pending_name = None
            pending_qty = None
            pending_price = None
            pending_total = None
            summary_reached = True
            continue

        if summary_reached and not re.match(r"^[0-9,]+$", normalized):
            continue

        if barcode_pattern.match(normalized):
            continue

        combined_match = qty_price_total_pattern.match(normalized)
        if combined_match:
            pending_qty = _normalize_qty(int(combined_match.group("qty")))
            pending_price = _parse_amount(combined_match.group("price"))
            pending_total = _parse_amount(combined_match.group("total"))
            _commit_item()
            continue

        price_total_match = price_total_pattern.match(normalized)
        if price_total_match:
            if pending_price is None:
                pending_price = _parse_amount(price_total_match.group("price"))
            pending_total = _parse_amount(price_total_match.group("total"))
            _commit_item()
            continue

        if re.match(r"^\d+$", normalized):
            if pending_name is None:
                continue
            try:
                numeric_value = int(normalized)
            except ValueError:
                numeric_value = 1
            candidate_qty = _normalize_qty(numeric_value)
            if candidate_qty is not None:
                pending_qty = candidate_qty
                continue
            # 큰 숫자는 금액 가능성이 높으므로 다음 블록에서 처리.

        if re.match(r"^[0-9,]+$", normalized):
            value = _parse_amount(normalized)
            if value is None:
                continue
            if pending_name:
                if pending_price is None:
                    pending_price = value
                elif pending_total is None:
                    pending_total = value
                    _commit_item()
            else:
                if not has_seen_item:
                    floating_initial_totals.append(value)
                elif missing_total_indices:
                    if items and items[-1]["total_price"] == value:
                        continue
                    idx = missing_total_indices.pop(0)
                    items[idx]["total_price"] = value
                    qty = max(1, items[idx].get("quantity", 1))
                    if items[idx]["price"] <= 0:
                        items[idx]["price"] = max(1, value // qty)
                else:
                    floating_deferred_totals.append(value)
            continue

        m = re.match(r"^(?P<name>[가-힣A-Za-z0-9\s\-\(\)\*\+/]+?)\s+(?P<qty>\d+)\s+(?P<price>[0-9,]+)\s+(?P<total>[0-9,]+)", normalized)
        if m:
            pending_name = _clean_item_name(m.group("name"))
            pending_qty = _normalize_qty(int(m.group("qty")))
            pending_price = _parse_amount(m.group("price"))
            pending_total = _parse_amount(m.group("total"))
            _commit_item()
            continue

        cleaned_candidate = _clean_item_name(normalized)
        if cleaned_candidate and re.search(r"[가-힣A-Za-z]", cleaned_candidate):
            _commit_item()
            pending_name = cleaned_candidate
            has_seen_item = True

    _commit_item()
    items = _apply_initial_totals(items, floating_initial_totals)
    filled_items = _fill_missing_amounts(items, floating_deferred_totals)
    return filled_items[:30]


def _apply_initial_totals(
    items: List[Dict[str, Any]], early_totals: List[Optional[int]]
) -> List[Dict[str, Any]]:
    for idx, raw_value in enumerate(early_totals):
        if idx >= len(items):
            break
        if raw_value is None or raw_value <= 0:
            continue
        items[idx]["total_price"] = raw_value
        if items[idx].get("quantity"):
            qty = max(1, items[idx]["quantity"])
        else:
            qty = 1
        items[idx]["price"] = max(1, raw_value // qty)
    return items


def _fill_missing_amounts(
    items: List[Dict[str, Any]], floating_totals: List[Optional[int]]
) -> List[Dict[str, Any]]:
    totals_queue = [value for value in floating_totals if value is not None and value > 0]
    if not totals_queue:
        return items

    queue_index = 0
    for item in items:
        if item["total_price"] <= 0 and queue_index < len(totals_queue):
            item["total_price"] = totals_queue[queue_index]
            queue_index += 1
        if item["price"] <= 0 and item["total_price"] > 0:
            qty = max(1, item.get("quantity", 1))
            item["price"] = max(1, item["total_price"] // qty)
    return items


def _clean_item_name(raw: str) -> str:
    """Normalize item names by removing leading indices or barcode-like tokens."""
    name = re.sub(r"^[0-9]+(?:[+.)\s\-\*]+)?", "", raw).strip()
    tokens = [
        token
        for token in name.split()
        if not re.fullmatch(r"\d{8,}", token)
    ]
    cleaned = " ".join(tokens).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned


def _preprocess_image(file_bytes: bytes) -> bytes:
    """
    Normalize receipt images to boost OCR accuracy.
    Steps: EXIF 회전 보정 -> 그레이스케일 -> 대비/선명도 향상 -> 해상도 제한 -> PNG 재인코딩.
    """
    try:
        with Image.open(BytesIO(file_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode != "L":
                img = img.convert("L")
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = ImageEnhance.Sharpness(img).enhance(1.2)
            max_dim = 2000
            current_max = max(img.size)
            if current_max > max_dim:
                ratio = max_dim / current_max
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()
    except Exception as exc:  # pragma: no cover - best-effort preprocessing
        logger.warning("이미지 전처리에 실패했습니다: %s", exc)
        return file_bytes


def _build_image_context() -> Optional[vision.ImageContext]:
    text_params = None
    if hasattr(vision, "TextDetectionParams"):
        text_params = vision.TextDetectionParams(
            enable_text_detection_confidence_score=True,
            advanced_ocr_options=["legacy_layout"],
        )
    context_kwargs: Dict[str, Any] = {"language_hints": ["ko", "en"]}
    if text_params:
        context_kwargs["text_detection_params"] = text_params
    if hasattr(vision, "ImageContext"):
        return vision.ImageContext(**context_kwargs)
    return None


def _extract_text_from_response(response: Any) -> str:
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
    return ""


def _call_vision_api(image_bytes: bytes) -> str:
    client = _get_vision_client()
    vision_image = vision.Image(content=image_bytes)
    image_context = _build_image_context()
    detectors = (
        client.document_text_detection,
        client.text_detection,
    )
    for detector in detectors:
        try:
            kwargs = {"image": vision_image}
            if image_context is not None:
                kwargs["image_context"] = image_context
            response = detector(**kwargs)
        except GoogleAPIError as exc:  # pragma: no cover
            raise HTTPException(status_code=502, detail=f"OCR 호출에 실패했습니다: {exc}") from exc
        text = _extract_text_from_response(response)
        if text:
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

    processed_bytes = _preprocess_image(file_bytes)
    full_text = _call_vision_api(processed_bytes)
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
