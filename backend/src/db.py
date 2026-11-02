"""
Módulo para la configuración de la base de datos y del motor SQLAlchemy Core.
"""

from functools import cache

import pandas as pd

from sqlalchemy import (Boolean, Column, DateTime, Float, Integer, MetaData, Table, Text,
                        create_engine, func, insert, select, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from src.config import database_url

metadata = MetaData()

COMMENTS = Table(
    "comentarios", metadata,
    Column("id", Text, primary_key=True),
    Column("texto", Text),
    Column("etiqueta", Text, nullable=False),
    Column("plataforma", Text),
    Column("influencer", Text),
    Column("particion", Text),
    Column("fuente", Text, nullable=False),
)

TRAININGS = Table(
    "entrenamientos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("version", Text, nullable=False, unique=True),
    Column("fecha", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("modelo", Text, nullable=False),
    Column("configuracion", JSONB, nullable=False),
    Column("fuente_datos", Text, nullable=False),
    Column("cv_f1_macro", Float, nullable=False),
    Column("test_f1_macro", Float, nullable=False),
    Column("test_accuracy", Float, nullable=False),
    Column("test_f1_ofensivo", Float, nullable=False),
    Column("n_entrenamiento", Integer, nullable=False),
    Column("n_prueba", Integer, nullable=False),
)

PREDICTIONS = Table(
    "predicciones", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fecha", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("texto", Text, nullable=False),
    Column("clase", Text, nullable=False),
    Column("ofensivo", Boolean, nullable=False),
    Column("probabilidad", Float, nullable=False),
    Column("probabilidad_ofensivo", Float, nullable=False),
    Column("probabilidades", JSONB, nullable=False),
    Column("version_modelo", Text, nullable=False),
    Column("origen", Text, nullable=False),
)

INSERT_BATCH = 5000

class Repository:
    """Operaciones de lectura y escritura sobre las tres tablas."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def is_reachable(self) -> bool:
        """Devuelve True si la base de datos responde, False si no hay conexión."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            return False

    # -- comentarios -------------------------------------------------------------------

    def comment_count(self) -> int:
        """Devuelve la cantidad de comentarios guardados en la base de datos."""
        with self.engine.connect() as conn:
            return conn.execute(select(func.count()).select_from(COMMENTS)).scalar_one()

    def comment_sources(self) -> set[str]:
        """Orígenes de los datos guardados: 'offendes' y/o 'sintetico'."""
        with self.engine.connect() as conn:
            return set(conn.execute(select(COMMENTS.c.fuente).distinct()).scalars())

    def replace_comments(self, frame: pd.DataFrame) -> None:
        """
        Reemplaza todos los comentarios guardados en la base de datos por los del DataFrame.
        """
        columns = [column.name for column in COMMENTS.columns]
        records = (frame[columns].astype(object).where(frame[columns].notna(), None)
                   .to_dict("records"))
        with self.engine.begin() as conn:
            conn.execute(text("TRUNCATE comentarios"))
            for start in range(0, len(records), INSERT_BATCH):
                conn.execute(insert(COMMENTS), records[start:start + INSERT_BATCH])

    def load_comments(self) -> pd.DataFrame:
        """Carga todos los comentarios de la base de datos en un DataFrame."""
        with self.engine.connect() as conn:
            return pd.read_sql(select(COMMENTS).order_by(COMMENTS.c.id), conn)

    # -- entrenamientos ----------------------------------------------------------------

    def add_training(self, run: dict) -> None:
        """Agrega un entrenamiento a la base de datos."""
        with self.engine.begin() as conn:
            conn.execute(insert(TRAININGS), [run])

    def trainings(self) -> list[dict]:
        """Devuelve los entrenamientos guardados, ordenados por fecha descendente."""
        wanted = [TRAININGS.c[name] for name in
                  ("version", "fecha", "modelo", "fuente_datos", "cv_f1_macro",
                   "test_f1_macro", "test_accuracy", "test_f1_ofensivo")]
        with self.engine.connect() as conn:
            rows = conn.execute(select(*wanted).order_by(TRAININGS.c.fecha.desc()))
            return [dict(row) for row in rows.mappings()]

    # -- predicciones ------------------------------------------------------------------

    def add_predictions(self, rows: list[dict]) -> None:
        """Agrega predicciones a la base de datos."""
        with self.engine.begin() as conn:
            conn.execute(insert(PREDICTIONS), rows)

    def latest_predictions(self, limit: int) -> list[dict]:
        """Devuelve las últimas predicciones guardadas, ordenadas por fecha descendente."""
        wanted = [column for column in PREDICTIONS.columns if column.name != "probabilidades"]
        query = (select(*wanted)
                 .order_by(PREDICTIONS.c.fecha.desc(), PREDICTIONS.c.id.desc())
                 .limit(limit))
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(query).mappings()]

@cache
def get_repository() -> Repository | None:
    """
    Devuelve un repositorio conectado a la base de datos, o None si no hay URL.
    """
    url = database_url()
    if url is None:
        return None
    return Repository(create_engine(url, pool_pre_ping=True))
