"""Archivo de configuración para la aplicación."""

from pathlib import Path
from functools import lru_cache

import os
import yaml

ROOT = Path(os.getenv("ROOT", Path.home() / "ofensometro"))
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", ROOT / "artifacts"))
PARAMS_PATH = Path(os.getenv("PARAMS_PATH", ROOT / "params.yaml"))

MODEL_PATH = ARTIFACTS_DIR / "model.joblib"

@lru_cache
def load_params() -> dict:
    """Carga los parámetros de configuración desde params.yaml."""
    with open(PARAMS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

def label_info() -> dict:
    return load_params()["labels"]

def labels() -> list[str]:
    """Orden fijo de las clases: el de params.yaml."""
    return list(label_info())

def offensive_labels() -> list[str]:
    """Clases consideradas ofensivas, definidas en params.yaml."""
    return [code for code, info in label_info().items() if info["ofensivo"]]

def database_url() -> str | None:
    """Obtiene la URL de la base de datos desde la variable de entorno DATABASE_URL."""
    return os.getenv("DATABASE_URL") or None
