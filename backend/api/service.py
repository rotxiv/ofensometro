"""Módulo para el servicio de clasificación y explicación de comentarios ofensivos."""

import json
import logging
from dataclasses import asdict, dataclass

import joblib

from api.explanations import surface_forms, with_words
from src import db
from src.config import METRICS_PATH, MODEL_PATH, label_info, labels, offensive_labels
from src.models.evaluate import p_offensive, probabilities_by_label
from src.models.explain import explain_terms

log = logging.getLogger("ofensometro")


@dataclass(frozen=True)
class Prediction:
    """Resultado de la clasificación de un comentario ofensivo."""
    clase: str
    ofensivo: bool
    probabilidad: float
    probabilidad_ofensivo: float
    probabilidades: dict

    def as_dict(self) -> dict:
        return asdict(self)


class ModelService:
    """Servicio que carga el modelo de clasificación y explica sus decisiones."""
    def __init__(self):
        self.bundle: dict | None = None
        self.metrics: dict | None = None

    def load(self) -> None:
        if not MODEL_PATH.exists():
            log.warning("No existe %s: ejecuta el entrenamiento", MODEL_PATH)
            return
        self.bundle = joblib.load(MODEL_PATH)
        self.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        self.pipeline.predict(["calentamiento"])   # la primera llamada carga spaCy (~0,5 s)
        log.info("Modelo %s cargado (versión %s%s)", self.bundle["model"], self.version,
                 ", DEMO" if self.demo_mode else "")

    # -- datos del modelo cargado ------------------------------------------------------

    @property
    def loaded(self) -> bool:
        return self.bundle is not None

    @property
    def pipeline(self):
        return self.bundle["pipeline"]

    @property
    def threshold(self) -> float:
        return self.bundle["threshold"]

    @property
    def version(self) -> str:
        return self.bundle["version"]

    @property
    def label(self) -> str:
        return self.bundle["label"]

    @property
    def demo_mode(self) -> bool:
        return bool(self.bundle and self.bundle.get("demo_mode"))

    # -- clasificación -----------------------------------------------------------------

    def classify(self, texts: list[str]) -> list[Prediction]:
        proba = probabilities_by_label(self.pipeline, texts)
        offensive = p_offensive(proba)
        codes = labels()
        return [
            Prediction(
                clase=codes[int(row.argmax())],
                ofensivo=bool(p_off >= self.threshold),
                probabilidad=round(float(row.max()), 4),
                probabilidad_ofensivo=round(float(p_off), 4),
                probabilidades={c: round(float(p), 4) for c, p in zip(codes, row)},
            )
            for row, p_off in zip(proba, offensive)
        ]

    @staticmethod
    def describe_class(code: str) -> tuple[str, str]:
        info = label_info()[code]
        return info["nombre"], info["descripcion"]

    def inspect(self, text: str, prediction: Prediction) -> tuple[dict, dict]:
        """Pasos del preprocesamiento y términos que más pesaron en la decisión."""
        preprocessor = self.pipeline.named_steps["preprocess"]
        steps = preprocessor.explain(text)
        shown_steps = {
            "original": steps["original"],
            "normalizado": steps["normalized"],
            "tokens": steps["tokens"],
            "stopwords_eliminadas": steps["removed_stopwords"],
            "sin_stopwords": steps["without_stopwords"],
            "raices": steps["roots"],
            "final": steps["final"],
            "metodo": preprocessor.normalizer,
            "senales": steps["signals"],
        }
        terms = explain_terms(self.pipeline, text, prediction.clase, offensive_labels())
        return shown_steps, with_words(terms, surface_forms(steps))

    # -- historial ---------------------------------------------------------------------

    def remember(self, texts: list[str], predictions: list[Prediction], origin: str) -> None:
        """Guarda las predicciones; si la base falla, la respuesta al usuario no se ve afectada."""
        repository = db.get_repository()
        if repository is None:
            return
        try:
            repository.add_predictions([
                {"texto": text, **p.as_dict(), "version_modelo": self.version, "origen": origin}
                for text, p in zip(texts, predictions)
            ])
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo guardar la predicción: %s", exc)
