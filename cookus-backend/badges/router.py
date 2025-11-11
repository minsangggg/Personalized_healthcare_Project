from fastapi import APIRouter, Depends, HTTPException, Path

from core import get_current_user
from notifications.service import notify
from .schemas import BadgeOverview, EarnedBadge, LockedBadge, Progress
from .repository import fetch_overview, own_badge, deactivate_all, activate_one, award_if_absent

router = APIRouter(prefix="/me/badges", tags=["badges"])


@router.get("/overview", response_model=BadgeOverview)
def get_overview(user_id: str = Depends(get_current_user)):
    earned_rows, locked_rows = fetch_overview(user_id)

    earned = [
        EarnedBadge(
            badge_id=r["badge_id"],
            name=r["name"],
            category=r["category"],
            earned_at=str(r["earned_at"]),
            is_active=bool(r["is_active"]),
            is_displayed=bool(r.get("is_displayed")),
        )
        for r in earned_rows
    ]

    locked: list[LockedBadge] = []
    for r in locked_rows:
        target = r["target_value"]
        prog = None
        if target is not None:
            cur = int(r["current_value"])
            tgt = int(target)
            prog = Progress(current=cur, target=tgt, remaining=max(tgt - cur, 0))
        locked.append(
            LockedBadge(
                badge_id=r["badge_id"],
                name=r["name"],
                category=r["category"],
                progress=prog,
            )
        )
    return BadgeOverview(earned=earned, locked=locked)


@router.post("/{badge_id}/activate")
def activate_badge(
    badge_id: int = Path(..., ge=1),
    user_id: str = Depends(get_current_user),
):
    if not own_badge(user_id, badge_id):
        raise HTTPException(status_code=404, detail="Badge not owned by user")
    deactivate_all(user_id)
    activate_one(user_id, badge_id)
    return {"ok": True}


@router.delete("/active")
def deactivate_badge(user_id: str = Depends(get_current_user)):
    deactivate_all(user_id)
    return {"ok": True}


@router.post("/{badge_id}/award")
def award_badge(
    badge_id: int = Path(..., ge=1),
    user_id: str = Depends(get_current_user),
):
    awarded = award_if_absent(user_id, badge_id)
    if awarded:
        notify(
            user_id=user_id,
            title="새 배지를 획득했어요!",
            body=f"{badge_id} 배지를 획득했습니다.",
            link_url="/me/badges",
            type="badge",
            related_id=badge_id,
        )
    return {"ok": True, "awarded": bool(awarded)}
