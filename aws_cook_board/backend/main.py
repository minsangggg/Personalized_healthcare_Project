import os
import uuid
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Body
from typing import List
from dotenv import load_dotenv
import pymysql
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# ============================================
# ✅ 환경 변수 로드
# ============================================
load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("AWS_S3_BUCKET")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

# ============================================
# ✅ DB 연결 함수
# ============================================
def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=int(os.getenv("DB_PORT", 3306)),
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

# ============================================
# ✅ S3 클라이언트 설정
# ============================================
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION", "ap-northeast-2"),
    config=Config(signature_version="s3v4"),
    endpoint_url="https://s3.ap-northeast-2.amazonaws.com"  # 🔹 명시적으로 서울 리전 지정!
)
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cookus Upload API")

# ✅ CORS 설정 (React 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 나중에 React 주소로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],  # ← 여기 덕분에 OPTIONS 허용됨
    allow_headers=["*"],
)
# ============================================
# ✅ 1️⃣ Presigned URL 생성 API
# ============================================
@app.post("/generate-presigned-urls")
async def generate_presigned_urls(
    file_exts: List[str] = Query([], description="파일 확장자 리스트 (예: jpg, png, 최대 7개)"),
    event_id: int = Query(..., description="이벤트 ID"),
    user_id: str = Query(..., description="사용자 ID")
):
    """
    여러 장 이미지에 대한 presigned URL을 생성해서 반환합니다.
    아직 DB에는 아무 것도 저장하지 않습니다.
    """
    try:
        if len(file_exts) > 7:
            raise ValueError("최대 7장까지만 업로드 가능합니다.")

        urls = []
        for file_ext in file_exts:
            file_ext = file_ext.strip(".").lower()
            if file_ext not in ["jpg", "jpeg", "png"]:
                raise ValueError(f"지원하지 않는 확장자: {file_ext}")

            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4()
            file_name = f"{user_id}_{event_id}_{now}_{unique_id}.{file_ext}"
            key = f"uploads/{event_id}/{file_name}"

            presigned_url = s3.generate_presigned_url(
                ClientMethod="put_object",
                Params={"Bucket": BUCKET_NAME, "Key": key, "ContentType": f"image/{file_ext}"},
                ExpiresIn=300
            )

            file_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
            urls.append({"upload_url": presigned_url, "file_url": file_url, "file_name": file_name})

        return {
            "status": "ready",
            "event_id": event_id,
            "user_id": user_id,
            "upload_list": urls,
            "expires_in": 300
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL 생성 실패: {str(e)}")

# ============================================
# ✅ 2️⃣ 업로드 완료 후 게시글 저장 API
# ============================================
@app.post("/save-board")
async def save_board(
    event_id: int = Body(..., embed=True),
    user_id: str = Body(..., embed=True),
    content_title: str = Body(..., embed=True),
    content_text: str = Body(..., embed=True),
    img_urls: List[str] = Body([], embed=True)
):
    """
    사용자가 S3 업로드를 마친 뒤 게시글을 DB에 저장합니다.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO board (event_id, user_id, content_title, content_text, img_url, like_count, created_at)
                VALUES (%s, %s, %s, %s, %s, 0, NOW())
            """
            cur.execute(sql, (
                event_id,
                user_id,
                content_title,
                content_text,
                json.dumps(img_urls) if img_urls else None
            ))
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": "게시글이 성공적으로 저장되었습니다.",
            "event_id": event_id,
            "user_id": user_id,
            "image_count": len(img_urls)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 저장 실패: {str(e)}")
