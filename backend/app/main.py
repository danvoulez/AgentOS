# app/main.py

from fastapi import FastAPI
from app.core.config import settings
from app.api.api_v1.api import api_router  # Ajustar se necessário
from app.core.logging_config import setup_logging

def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
from core.config import settings

from fastapi.middleware.cors import CORSMiddleware

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )
    app.include_router(api_router, prefix=settings.API_V1_STR)
    return app

app = create_app()
