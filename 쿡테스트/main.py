from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from cooktest import router

app = FastAPI(title="CookUs API")

# ✅ 에러 내용을 Swagger에서도 바로 보이게 하는 미들웨어
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Welcome to CookUs API 🚀"}
