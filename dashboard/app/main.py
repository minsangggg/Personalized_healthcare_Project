from fastapi import FastAPI
from .routers import (
    health,
    stats_process,
    stats_recipe_logs_category,
    stats_recipe_logs_level,
)

app = FastAPI(title="Recipe Dashboard API", version="1.0.0")

# 라우터 등록
app.include_router(health.router)
app.include_router(stats_process.router)
app.include_router(stats_recipe_logs_category.router)
app.include_router(stats_recipe_logs_level.router)