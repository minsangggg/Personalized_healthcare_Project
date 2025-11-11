from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from core import get_conn, get_current_user
from core.security import bearer, token_service
from notifications.service import notify
import os
import uuid
from datetime import datetime
import json
import re
from pymysql.err import ProgrammingError
try:
    import boto3
    from botocore.config import Config as BotoConfig
except Exception:
    boto3 = None
    BotoConfig = None


router = APIRouter()


def _parse_imgs(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, str):
        txt = raw.strip()
        if not txt:
            return []
        if txt.startswith("["):
            try:
                arr = json.loads(txt)
                if isinstance(arr, list):
                    return [str(x) for x in arr if x]
            except Exception:
                return []
        return [txt]
    return []


def _user_id_variants(raw: str) -> List[str]:
    base = (raw or "").strip()
    if not base:
        return []
    variants = {base}
    prefix_pattern = re.compile(r"^(?:사용자|user)\s*#", re.IGNORECASE)
    stripped = prefix_pattern.sub("", base).strip()
    if stripped:
        variants.update({
            stripped,
            f"사용자#{stripped}",
            f"user#{stripped}",
        })
    return [v for v in variants if v]


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

def _get_optional_user(request: Request) -> Optional[str]:
  auth = request.headers.get("Authorization", "").strip()
  if not auth:
    return None
  token = auth
  if token.lower().startswith("bearer "):
    token = token.split(None, 1)[1].strip()
  try:
    payload = token_service.decode(token)
    sub = payload.get("sub")
    return str(sub) if sub else None
  except Exception:
    return None


@router.get("/events/{event_id}/posts")
def list_posts(event_id: int, request: Request, view: Optional[str] = None) -> List[Dict[str, Any]]:
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
        """
    )
    with get_conn() as conn, conn.cursor() as cur:
        params: List[Any] = [event_id]
        if view == "mine":
            current_user = _get_optional_user(request)
            if not current_user:
                raise HTTPException(status_code=401, detail="Login required")
            sql += " AND user_id=%s"
            params.append(current_user)
        elif view == "liked":
            current_user = _get_optional_user(request)
            if not current_user:
                raise HTTPException(status_code=401, detail="Login required")
            sql += " AND content_id IN (SELECT content_id FROM board_likes WHERE user_id=%s)"
            params.append(current_user)
        sql += " ORDER BY created_at DESC"
        cur.execute(sql, tuple(params))
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
            raise HTTPException(status_code=400, detail="At most 7 images allowed")
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


@router.put("/events/{event_id}/posts/{post_id}")
def update_post(
    event_id: int,
    post_id: int,
    body: Dict[str, Any],
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    title = (body.get("content_title") or "").strip()
    text = (body.get("content_text") or "").strip()
    if not title or not text:
        raise HTTPException(status_code=400, detail="Invalid payload")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT user_id FROM board WHERE content_id=%s AND event_id=%s",
            (post_id, event_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        if str(row["user_id"]) != str(current_user):
            raise HTTPException(status_code=403, detail="Not allowed")
        cur.execute(
            """
            UPDATE board
            SET content_title=%s, content_text=%s
            WHERE content_id=%s AND event_id=%s
            """,
            (title, text, post_id, event_id),
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
            WHERE content_id=%s
            """,
            (post_id,),
        )
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Post not found")
        raw = updated.get("img_url")
        imgs: List[str] = []
        if isinstance(raw, str) and raw.strip().startswith("["):
            try:
                imgs = json.loads(raw)
            except Exception:
                imgs = []
        elif isinstance(raw, str) and raw.strip():
            imgs = [raw.strip()]
        updated["img_urls"] = imgs
        updated["img_url"] = imgs[0] if imgs else None
        return updated


@router.delete("/events/{event_id}/posts/{post_id}")
def delete_post(
    event_id: int,
    post_id: int,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT user_id FROM board WHERE content_id=%s AND event_id=%s",
            (post_id, event_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        if str(row["user_id"]) != str(current_user):
            raise HTTPException(status_code=403, detail="Not allowed")
        cur.execute("DELETE FROM board_likes WHERE content_id=%s", (post_id,))
        cur.execute("DELETE FROM board WHERE content_id=%s AND event_id=%s", (post_id, event_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Post not found")
    return {"status": "deleted"}


def _ensure_likes_table(cur) -> None:
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


@router.get("/events/{event_id}/likes/me", dependencies=[Depends(get_current_user)])
def get_my_likes(event_id: int, current_user: str = Depends(get_current_user)) -> Dict[str, Any]:
    with get_conn() as conn, conn.cursor() as cur:
        _ensure_likes_table(cur)
        cur.execute(
            """
            SELECT bl.content_id AS post_id
            FROM board_likes bl
            JOIN board b ON b.content_id = bl.content_id
            WHERE bl.user_id=%s AND b.event_id=%s
            """,
            (current_user, event_id),
        )
        rows = cur.fetchall()
    return {"liked_post_ids": [row["post_id"] for row in rows]}


@router.get("/users/{user_id}/cooktest-posts")
@router.get("/cooktest/users/{user_id}/posts")
def list_user_cooktest_posts(user_id: str, request: Request) -> Dict[str, Any]:
    variants = _user_id_variants(user_id)
    if not variants:
        variants = [user_id]
    placeholders = ", ".join(["%s"] * len(variants))
    viewer = _get_optional_user(request)
    like_join = ""
    like_select = "0 AS liked_by_me"
    params: List[Any] = list(variants)
    if viewer:
        like_join = " LEFT JOIN board_likes bl ON bl.content_id = b.content_id AND bl.user_id=%s"
        like_select = "CASE WHEN bl.user_id IS NULL THEN 0 ELSE 1 END AS liked_by_me"
        params.append(viewer)

    with get_conn() as conn, conn.cursor() as cur:
        sql_posts = f"""
            SELECT
              b.content_id AS post_id,
              b.event_id,
              b.user_id,
              COALESCE(up.user_name, '') AS user_name,
              b.content_title,
              b.content_text,
              b.img_url,
              b.like_count AS likes,
              b.created_at,
              e.event_name,
              {like_select}
            FROM board b
            JOIN event e ON e.event_id = b.event_id
            LEFT JOIN user_profile up ON up.user_id = b.user_id
            {like_join}
            WHERE b.user_id IN ({placeholders})
            ORDER BY b.like_count DESC, b.created_at DESC
        """
        sql_posts_no_profile = f"""
            SELECT
              b.content_id AS post_id,
              b.event_id,
              b.user_id,
              '' AS user_name,
              b.content_title,
              b.content_text,
              b.img_url,
              b.like_count AS likes,
              b.created_at,
              e.event_name,
              {like_select}
            FROM board b
            JOIN event e ON e.event_id = b.event_id
            {like_join}
            WHERE b.user_id IN ({placeholders})
            ORDER BY b.like_count DESC, b.created_at DESC
        """
        try:
            cur.execute(sql_posts, tuple(params))
        except ProgrammingError as exc:
            if exc.args and exc.args[0] == 1146:
                cur.execute(sql_posts_no_profile, tuple(params))
            else:
                raise
        rows = cur.fetchall()
        posts: List[Dict[str, Any]] = []
        for row in rows:
            imgs = _parse_imgs(row.get("img_url"))
            row["img_urls"] = imgs
            row["img_url"] = imgs[0] if imgs else row.get("img_url")
            posts.append(row)

        cur.execute(
            f"""
            SELECT DISTINCT
              e.event_id,
              e.event_name,
              e.start_date,
              e.end_date
            FROM event e
            JOIN board b ON b.event_id = e.event_id
            WHERE b.user_id IN ({placeholders})
            ORDER BY e.start_date DESC
            """,
            tuple(variants),
        )
        events = cur.fetchall()

    return {"posts": posts, "events": events}


@router.post("/posts/{post_id}/like", dependencies=[Depends(get_current_user)])
def like_post(post_id: int, current_user: str = Depends(get_current_user)) -> Dict[str, Any]:
    uid = current_user
    with get_conn() as conn, conn.cursor() as cur:
        _ensure_likes_table(cur)
        cur.execute(
            """
            INSERT IGNORE INTO board_likes (content_id, user_id)
            VALUES (%s, %s)
            """,
            (post_id, uid),
        )
        new_like = (cur.rowcount == 1)
        if new_like:
            cur.execute(
                "UPDATE board SET like_count = like_count + 1 WHERE content_id=%s",
                (post_id,),
            )
        cur.execute("SELECT user_id, like_count AS likes FROM board WHERE content_id=%s", (post_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        owner_id, like_count = row["user_id"], row["likes"]
    # Notify on every new like (except self-like)
    if new_like and str(uid) != str(owner_id):
        notify(
            user_id=str(owner_id),
            title="새 좋아요",
            body=f"{uid}님이 게시글에 좋아요를 눌렀어요.",
            link_url=f"/boards/{post_id}",
            type="like",
            related_id=post_id,
        )
    return {"likes": like_count, "liked": True}


@router.delete("/posts/{post_id}/like", dependencies=[Depends(get_current_user)]) 
def unlike_post(post_id: int, current_user: str = Depends(get_current_user)) -> Dict[str, Any]:
    uid = current_user
    with get_conn() as conn, conn.cursor() as cur:
        _ensure_likes_table(cur)
        cur.execute(
            "DELETE FROM board_likes WHERE content_id=%s AND user_id=%s",
            (post_id, uid),
        )
        if cur.rowcount == 1:
            cur.execute(
                """
                UPDATE board
                SET like_count = CASE WHEN like_count > 0 THEN like_count - 1 ELSE 0 END
                WHERE content_id=%s
                """,
                (post_id,),
            )
        cur.execute("SELECT like_count AS likes FROM board WHERE content_id=%s", (post_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        return {"likes": row["likes"], "liked": False}


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
        raise HTTPException(status_code=400, detail="Up to 7 files allowed")

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
            raise HTTPException(status_code=400, detail=f"Unsupported extension {ext}")
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
            raise HTTPException(status_code=500, detail=f"Presign failed: {e}")
        file_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        upload_list.append({"upload_url": url, "file_url": file_url, "file_name": file_name})

    return {"status": "ready", "event_id": event_id, "user_id": current_user, "upload_list": upload_list, "expires_in": 300}
