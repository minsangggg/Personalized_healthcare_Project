from typing import Optional

from fastapi import APIRouter, Query

from .service import faq_service


router = APIRouter(prefix="/faq", tags=["faq"])


@router.get("")
def list_faq(
    query: Optional[str] = Query(None, description="검색어 (질문/답변/분류)"),
    category: Optional[str] = Query(None, description="카테고리 정확히 일치 필터"),
    limit: int = Query(30, ge=1, le=100),
):
    return faq_service.list_faq(query, category, limit)


@router.get("/categories")
def list_faq_categories():
    return faq_service.list_categories()
