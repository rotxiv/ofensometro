"""Estado del servicio y catálogo de clases."""

from fastapi import APIRouter

from api.deps import AnyService
from api.schemas import HealthResponse, LabelInfo
from src import db
from src.config import label_info

router = APIRouter(tags=["estado"])

def _database_state() -> str:
    repository = db.get_repository()
    if repository is None:
        return "no configurada"
    return "conectada" if repository.is_reachable() else "sin conexión"

@router.get("/health", response_model=HealthResponse)
def health(service: AnyService):
    """Modelo cargado, origen de los datos de entrenamiento y estado de la base."""
    loaded = service.loaded
    return HealthResponse(
        estado="ok" if loaded else "degradado",
        modelo_cargado=loaded,
        modelo=service.label if loaded else None,
        version=service.version if loaded else None,
        datos=service.metrics["data_source"] if loaded else None,
        modo_demo=service.demo_mode,
        base_de_datos=_database_state(),
    )

@router.get("/labels", response_model=list[LabelInfo], tags=["modelo"])
def labels():
    """Las cuatro clases con nombre y descripción, para armar leyendas en los frontends."""
    return [LabelInfo(codigo=code, **{k: info[k] for k in ("nombre", "descripcion", "ofensivo")})
            for code, info in label_info().items()]
