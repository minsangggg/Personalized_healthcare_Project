# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, ingredients, recommendations, users, youtube, recipes, faq, receipts

app = FastAPI(title="CookUS API")

# ✅ 프론트 EC2 공인 IP를 여기에 넣으세요 
FRONTEND_IP = "54.180.2.153"

origins = [
    # 로컬 개발
    "http://localhost:3000", "http://localhost:3001",
    "http://127.0.0.1:3000", "http://127.0.0.1:3001",

    # ✅ 운영 프론트 (IP로 접근 시)
    f"http://{FRONTEND_IP}",
    f"http://{FRONTEND_IP}:80",
    # 도메인을 쓰면 여기에 "https://your-domain.com" 형태로 추가
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

print("✅ FastAPI CORS Middleware Loaded")

app.include_router(ingredients.router)
app.include_router(auth.router)
app.include_router(recommendations.router)
app.include_router(users.router)
app.include_router(youtube.router)
app.include_router(recipes.router)
app.include_router(faq.router)
app.include_router(receipts.router)
