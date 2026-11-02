"""Métricas del modelo y registro histórico (entrenamientos y predicciones)."""

from typing import Any, cast

from fastapi import APIRouter, Query

from api.deps import LoadedService, Repository
from api.errors import ERROR_RESPONSES, ApiError

router = APIRouter(tags=["historial"])

@router.get(
    "/metrics",
    responses=cast(dict[int | str, dict[str, Any]], ERROR_RESPONSES),
    tags=["modelo"],
)
def metrics(service: LoadedService):
    """
    Todo lo que produjo el último entrenamiento: comparación de modelos, experimentos
    y análisis de errores.
    Incluye lenguaje ofensivo real: ocúltalo tras un aviso en los frontends.
    """
    return service.metrics

@router.get("/history", responses=ERROR_RESPONSES)
def history(repository: Repository,
            limit: int = Query(20, ge=1, le=200, description="Cantidad de predicciones")):
    """Últimas predicciones guardadas en PostgreSQL."""
    try:
        return repository.latest_predictions(limit)
    except Exception:
        raise ApiError(503, "No se pudo leer la base de datos.") from None

@router.get("/trainings", responses=ERROR_RESPONSES)
def trainings(repository: Repository):
    """Entrenamientos registrados: versión, modelo y métricas de cada uno."""
    try:
        return repository.trainings()
    except Exception:
        raise ApiError(503, "No se pudo leer la base de datos.") from None
