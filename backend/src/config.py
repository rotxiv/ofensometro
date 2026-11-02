"""Archivo de configuración para la aplicación."""

from pathlib import Path
from functools import cache
from dataclasses import dataclass

import os
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

@dataclass(frozen=True)
class Locations:
    """Rutas de entrada y salida. Se pueden redirigir con variables de entorno"""
    params: Path
    artifacts: Path

    @classmethod
    def from_environment(cls) -> "Locations":
        """
        Crea un objeto Locations usando las variables de entorno:
            - PARAMS_PATH: ruta al archivo params.yaml
            - ARTIFACTS_DIR: ruta al directorio de artefactos
        """
        return cls(params=Path(os.getenv("PARAMS_PATH", ROOT / "params.yaml")),
                   artifacts=Path(os.getenv("ARTIFACTS_DIR", ROOT / "artifacts")))

    @property
    def model(self) -> Path:
        """Ruta al archivo del modelo entrenado."""
        return self.artifacts / "model.joblib"

    @property
    def metrics(self) -> Path:
        """Ruta al archivo de métricas del último entrenamiento."""
        return self.artifacts / "metrics.json"

    @property
    def experiments(self) -> Path:
        """Ruta al archivo de experimentos (historial de entrenamientos)."""
        return self.artifacts / "experiments.csv"

    @property
    def errors(self) -> Path:
        """Ruta al archivo de errores de predicción."""
        return self.artifacts / "errors.csv"

LOCATIONS = Locations.from_environment()

# Nombres cortos que usan el resto de módulos.
PARAMS_PATH = LOCATIONS.params
ARTIFACTS_DIR = LOCATIONS.artifacts
MODEL_PATH = LOCATIONS.model
METRICS_PATH = LOCATIONS.metrics
EXPERIMENTS_PATH = LOCATIONS.experiments
ERRORS_PATH = LOCATIONS.errors

@cache
def load_params() -> dict:
    """Carga los parámetros de params.yaml y los devuelve como un diccionario."""
    return yaml.safe_load(PARAMS_PATH.read_text(encoding="utf-8"))

def label_info() -> dict:
    """Devuelve la información de las clases, tal como está en params.yaml."""
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
