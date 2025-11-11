from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, ingredients, recommendations, users, youtube, recipes, faq, receipts

app = FastAPI(title="CookUS API")

origins = [
    "http://localhost:3000", "http://localhost:3001",
    "http://127.0.0.1:3000", "http://127.0.0.1:3001",
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
