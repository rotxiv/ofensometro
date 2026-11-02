"""Dependencias de FastAPI: lo que cada endpoint necesita, ya validado."""

from typing import Annotated

from fastapi import Depends

from api.errors import ApiError
from api.service import ModelService
from src import db

_service = ModelService()

def get_service() -> ModelService:
    return _service

def loaded_service(service: Annotated[ModelService, Depends(get_service)]) -> ModelService:
    if not service.loaded:
        raise ApiError(503, "El modelo no está entrenado. Ejecuta: python -m src.pipeline")
    return service

def configured_repository() -> db.Repository:
    repository = db.get_repository()
    if repository is None:
        raise ApiError(503, "La base de datos no está configurada (DATABASE_URL).")
    return repository

AnyService = Annotated[ModelService, Depends(get_service)]
LoadedService = Annotated[ModelService, Depends(loaded_service)]
Repository = Annotated[db.Repository, Depends(configured_repository)]
