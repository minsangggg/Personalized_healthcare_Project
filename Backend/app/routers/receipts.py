from fastapi import APIRouter, File, Form, Query, UploadFile

from app.services.receipt_service import delete_receipt_item, list_receipts, upload_receipt

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("/upload")
async def upload_receipt_endpoint(
    id: str = Form(..., description="사용자 ID"),
    file: UploadFile = File(..., description="영수증 이미지"),
) -> dict:
    """영수증 이미지를 업로드하고 OCR 결과를 저장합니다."""
    return await upload_receipt(id, file)


@router.get("")
def list_receipts_endpoint(
    id: str = Query(..., description="사용자 ID"),
) -> dict:
    """사용자가 업로드한 영수증 목록을 반환합니다."""
    return list_receipts(id)


@router.delete("/{receipt_id}")
def delete_receipt_endpoint(
    receipt_id: int,
    id: str = Query(..., description="사용자 ID"),
) -> dict:
    """영수증 항목을 삭제합니다."""
    return delete_receipt_item(id, receipt_id)
