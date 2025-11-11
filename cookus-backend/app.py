"""CookUS FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from notifications.poller import start_poller, stop_poller
from badges.automation import start_badge_automation, stop_badge_automation

from auth import router as auth_router
from core import settings
from faq import router as faq_router
from fridge import router as fridge_router
from health import router as health_router
from ingredients import router as ingredient_router
from recipes import router as recipe_router
from nutrition import router as nutrition_router
from recommendations import router as recommendation_router
from users import router as user_router
from users.public_router import router as public_user_router
from stats import router as stats_router
from shorts import router as shorts_router
from badges.router import router as badges_router
from cooktest import router as cooktest_router
from notifications.router import router as notifications_router
from badge_title import router as badge_title_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_badge_automation()
    await start_poller()
    try:
        yield
    finally:
        await stop_poller()
        stop_badge_automation()

def create_app() -> FastAPI:
    app = FastAPI(title="CookUS API", version="1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "Authorization"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(fridge_router)
    app.include_router(ingredient_router)
    app.include_router(faq_router)
    app.include_router(recommendation_router)
    app.include_router(recipe_router)
    app.include_router(stats_router)
    app.include_router(nutrition_router)
    app.include_router(shorts_router)
    app.include_router(badges_router)
    app.include_router(badge_title_router)
    app.include_router(cooktest_router)
    app.include_router(notifications_router)
    app.include_router(public_user_router)

    return app


app = create_app()
