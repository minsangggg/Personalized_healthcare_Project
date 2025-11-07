from fastapi import APIRouter, Depends, HTTPException, Path
from .schemas import BadgeOverview, EarnedBadge, LockedBadge, Progress
from .repository import fetch_overview, own_badge, deactivate_all, activate_one

from notifications.service import notify
from core.database import get_conn
from .repository import award_if_absent

# ① 너희 인증 의존성에 맞게 import
#    - JWT에서 유저 꺼내는 함수가 있으면 그걸 사용
#    - 예: from auth.service import get_current_user  (있다면)
#    - 없으면 임시 헤더 버전:
from fastapi import Header
def get_current_user_id(x_user_id: str | None = Header(default=None)):
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_user_id
# ↑ 실제 배포 시엔 auth의 함수로 교체


router = APIRouter(prefix="/me/badges", tags=["badges"])

@router.get("/overview", response_model=BadgeOverview)
def get_overview(user_id: str = Depends(get_current_user_id)):
    earned_rows, locked_rows = fetch_overview(user_id)

    earned = [EarnedBadge(
        badge_id=r["badge_id"], name=r["name"], category=r["category"],
        earned_at=str(r["earned_at"]), is_active=bool(r["is_active"])
    ) for r in earned_rows]

    locked: list[LockedBadge] = []
    for r in locked_rows:
        target = r["target_value"]
        prog = None
        if target is not None:
            cur = int(r["current_value"])
            tgt = int(target)
            prog = Progress(current=cur, target=tgt, remaining=max(tgt - cur, 0))
        locked.append(LockedBadge(
            badge_id=r["badge_id"], name=r["name"], category=r["category"],
            progress=prog
        ))
    return BadgeOverview(earned=earned, locked=locked)

@router.post("/{badge_id}/activate")
def activate_badge(
    badge_id: int = Path(..., ge=1),
    user_id: str = Depends(get_current_user_id),
):
    if not own_badge(user_id, badge_id):
        raise HTTPException(status_code=404, detail="Badge not owned by user")
    deactivate_all(user_id)
    activate_one(user_id, badge_id)
    return {"ok": True}

@router.delete("/active")
def deactivate_badge(user_id: str = Depends(get_current_user_id)):
    deactivate_all(user_id)
    return {"ok": True}

@router.post("/{badge_id}/award")
def award_badge(
    badge_id: int = Path(..., ge=1),
    user_id: str = Depends(get_current_user_id),
):
    awarded = award_if_absent(user_id, badge_id)
    if awarded:
        # 알림 저장
        notify(
            user_id=user_id,
            title="배지 지급",
            body=f"축하합니다! {badge_id} 배지를 획득했어요.",
            link_url="/me/badges",
            type="badge",
            related_id=badge_id,
        )
    return {"ok": True, "awarded": bool(awarded)}

