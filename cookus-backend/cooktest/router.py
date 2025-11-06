from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from core import get_conn, get_current_user
import os
import uuid
from datetime import datetime
import json
try:
    import boto3
    from botocore.config import Config as BotoConfig
except Exception:
    boto3 = None
    BotoConfig = None


router = APIRouter()


# -------- Events --------

@router.get("/events")
def list_events() -> List[Dict[str, Any]]:
    """Return all events with post counts for the CookTest tab."""
    sql = (
        """
        SELECT
          e.event_id,
          e.event_name,
          e.event_description,
          e.start_date,
          e.end_date,
          COUNT(b.content_id) AS post_count
        FROM event e
        LEFT JOIN board b ON e.event_id = b.event_id
        GROUP BY e.event_id, e.event_name, e.event_description, e.start_date, e.end_date
        ORDER BY e.start_date DESC
        """
    )
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return rows


@router.get("/events/{event_id}")
def get_event(event_id: int) -> Dict[str, Any]:
    """Return event detail used by the CookTest modal header."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT event_id, event_name, event_description, start_date, end_date
            FROM event
            WHERE event_id=%s
            """,
            (event_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")
        return row


# -------- Posts --------

@router.get("/events/{event_id}/posts")
def list_posts(event_id: int) -> List[Dict[str, Any]]:
    """Return posts for an event in feed format expected by the frontend.

    Supports multiple images stored as JSON array in `img_url` column. Adds both
    `img_urls` (list) and `img_url` (first or null) to each row for compatibility.
    """
    sql = (
        """
        SELECT
          content_id AS post_id,
          event_id,
          user_id,
          content_title,
          content_text,
          img_url,
          like_count AS likes,
          created_at
        FROM board
        WHERE event_id=%s
        ORDER BY created_at DESC
        """
    )
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (event_id,))
        rows = cur.fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        raw = r.get("img_url")
        imgs: List[str] = []
        if isinstance(raw, str) and raw.strip().startswith("["):
            try:
                imgs = json.loads(raw)
            except Exception:
                imgs = []
        elif isinstance(raw, str) and raw.strip():
            imgs = [raw.strip()]
        r["img_urls"] = imgs
        r["img_url"] = imgs[0] if imgs else None
        out.append(r)
    return out


@router.get("/events/{event_id}/posts/{post_id}")
def get_post(event_id: int, post_id: int) -> Dict[str, Any]:
    """Return a single post detail (for modal view)."""
    sql = (
        """
        SELECT
          content_id AS post_id,
          event_id,
          user_id,
          content_title,
          content_text,
          img_url,
          like_count AS likes,
          created_at
        FROM board
        WHERE event_id=%s AND content_id=%s
        """
    )
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (event_id, post_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        raw = row.get("img_url")
        imgs: List[str] = []
        if isinstance(raw, str) and raw.strip().startswith("["):
            try:
                imgs = json.loads(raw)
            except Exception:
                imgs = []
        elif isinstance(raw, str) and raw.strip():
            imgs = [raw.strip()]
        row["img_urls"] = imgs
        row["img_url"] = imgs[0] if imgs else None
        return row


@router.post("/events/{event_id}/posts")
def create_post(
    event_id: int,
    body: Dict[str, Any],
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new post in an event. Requires authentication for user id."""
    title = (body.get("content_title") or "").strip()
    text = (body.get("content_text") or "").strip()
    img_url: Optional[str] = body.get("img_url")
    img_urls: Optional[List[str]] = body.get("img_urls") if isinstance(body.get("img_urls"), list) else None
    if not title or not text:
        raise HTTPException(status_code=400, detail="Invalid payload")
    # normalize image payload (0..7)
    if img_urls is not None:
        if len(img_urls) > 7:
            raise HTTPException(status_code=400, detail="이미지는 최대 7장까지 가능합니다")
        img_column_value: Optional[str] = json.dumps(img_urls)
    else:
        img_column_value = img_url

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO board (event_id, user_id, content_title, content_text, img_url, like_count, created_at)
            VALUES (%s, %s, %s, %s, %s, 0, NOW())
            """,
            (event_id, current_user, title, text, img_column_value),
        )
        cur.execute(
            """
            SELECT
              content_id AS post_id,
              event_id,
              user_id,
              content_title,
              content_text,
              img_url,
              like_count AS likes,
              created_at
            FROM board
            WHERE content_id=LAST_INSERT_ID()
            """
        )
        row = cur.fetchone()
        raw = row.get("img_url")
        imgs: List[str] = []
        if isinstance(raw, str) and raw.strip().startswith("["):
            try:
                imgs = json.loads(raw)
            except Exception:
                imgs = []
        elif isinstance(raw, str) and raw.strip():
            imgs = [raw.strip()]
        row["img_urls"] = imgs
        row["img_url"] = imgs[0] if imgs else None
        return row


@router.post("/posts/{post_id}/like", dependencies=[Depends(get_current_user)])
def like_post(post_id: int, current_user: str = Depends(get_current_user)) -> Dict[str, Any]:
    uid = current_user
    with get_conn() as conn, conn.cursor() as cur:
        # Ensure helper table exists
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS board_likes (
              content_id INT NOT NULL,
              user_id VARCHAR(255) NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (content_id, user_id),
              INDEX (content_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        # Try to create like entry; ignore if already liked
        cur.execute(
            """
            INSERT IGNORE INTO board_likes (content_id, user_id)
            VALUES (%s, %s)
            """,
            (post_id, uid),
        )
        if cur.rowcount == 1:
            # First like by this user -> increment aggregate counter
            cur.execute(
                "UPDATE board SET like_count = like_count + 1 WHERE content_id=%s",
                (post_id,),
            )
        # Return current likes
        cur.execute("SELECT like_count AS likes FROM board WHERE content_id=%s", (post_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        # augment response
        return {"likes": row["likes"], "liked": True}


# -------- S3 Presigned Uploads --------

@router.post("/events/{event_id}/presigned-urls")
def generate_presigned_urls(event_id: int, body: Dict[str, Any], current_user: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Generate S3 presigned PUT URLs for images and return their final file URLs.

    Request body: { "file_exts": ["jpg", "png", ...] }
    Returns: { upload_list: [ { upload_url, file_url, file_name } ], expires_in }
    """
    if boto3 is None:
        raise HTTPException(status_code=500, detail="boto3 not available on server")

    file_exts = body.get("file_exts") or []
    if not isinstance(file_exts, list) or not all(isinstance(x, str) for x in file_exts):
        raise HTTPException(status_code=400, detail="file_exts must be a string array")
    if len(file_exts) == 0:
        raise HTTPException(status_code=400, detail="no files requested")
    if len(file_exts) > 7:
        raise HTTPException(status_code=400, detail="理쒕? 7媛쒓퉴吏留??낅줈??媛?ν빀?덈떎")

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-northeast-2"
    bucket = os.getenv("AWS_S3_BUCKET") or os.getenv("S3_BUCKET")
    if not bucket:
        raise HTTPException(status_code=500, detail="S3 bucket not configured")

    # Use region-specific S3 endpoint to avoid 301 redirects that break CORS preflight
    s3 = boto3.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://s3.{region}.amazonaws.com",
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_list: List[Dict[str, str]] = []
    for ext in file_exts:
        ext = ext.strip(".").lower()
        if ext not in ("jpg", "jpeg", "png"):
            raise HTTPException(status_code=400, detail=f"吏?먰븯吏 ?딅뒗 ?뺤옣?? {ext}")
        file_name = f"{current_user}_{event_id}_{now}_{uuid.uuid4()}.{ext}"
        key = f"uploads/{event_id}/{file_name}"
        try:
            url = s3.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ContentType": ("image/png" if ext == "png" else "image/jpeg"),
                },
                ExpiresIn=300,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"URL ?앹꽦 ?ㅽ뙣: {e}")
        file_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        upload_list.append({"upload_url": url, "file_url": file_url, "file_name": file_name})

    return {"status": "ready", "event_id": event_id, "user_id": current_user, "upload_list": upload_list, "expires_in": 300}
