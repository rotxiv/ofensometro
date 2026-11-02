"""Módulo para la construcción de la aplicación"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_service
from api.errors import install_error_handlers
from api.routes import insights, predict, status

DESCRIPTION = ("Detecta lenguaje ofensivo en comentarios en español: clasifica en cuatro clases "
               "(NO, NOE, OFP, OFG), indica si el comentario es ofensivo y explica qué palabras "
               "pesaron en la decisión.")

def allowed_origins() -> list[str]:
    """Orígenes de los frontends que llaman desde un navegador (web y Flutter web).
    En producción: CORS_ORIGINS="https://mi-sitio.com,https://otro.com"."""
    raw = os.getenv("CORS_ORIGINS", "*")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

def create_app() -> FastAPI:
    """Crea la aplicación FastAPI, con rutas, dependencias y manejadores de errores."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        get_service().load()    # una vez al arrancar, no en cada petición
        yield

    app = FastAPI(title="Ofensómetro API", version="1.0.0", description=DESCRIPTION,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None,
                  lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=allowed_origins(),
                       allow_methods=["GET", "POST"], allow_headers=["*"])
    install_error_handlers(app)
    for router in (status.router, predict.router, insights.router):
        app.include_router(router, prefix="/api")
    return app
