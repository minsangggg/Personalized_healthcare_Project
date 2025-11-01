"""CookUS FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import router as auth_router
from core import settings
from faq import router as faq_router
from fridge import router as fridge_router
from health import router as health_router
from ingredients import router as ingredient_router
from recipes import router as recipe_router
from recommendations import router as recommendation_router
from users import router as user_router


def create_app() -> FastAPI:
    app = FastAPI(title="CookUS API", version="1.0")

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

    return app


app = create_app()
