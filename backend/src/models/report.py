"""
Arma el informe de un entrenamiento (lo que se guarda en metrics.json y sirve /api/metrics).
"""

from dataclasses import dataclass

import pandas as pd

from src.config import label_info, labels, offensive_labels
from src.models.evaluate import (accuracy_by_phenomenon, accuracy_by_platform, error_examples,
                                 top_terms)
from src.models.experiments import STAGE_SCREENING

@dataclass
class ModelResult:
    """
    Un modelo ya entrenado con su mejor configuración y sus notas en el conjunto de prueba.
    """
    name: str
    label: str
    config: dict
    cv_f1_macro: float
    cv_f1_macro_std: float
    test: dict
    test_binary: dict
    pipeline: object

    def as_report(self) -> dict:
        return {
            "name": self.name, 
            "label": self.label, 
            "config": self.config,
            "cv_f1_macro": self.cv_f1_macro, 
            "cv_f1_macro_std": self.cv_f1_macro_std,
            "test": self.test, "test_binary": self.test_binary
        }

def factor_effects(experiments: pd.DataFrame) -> dict:
    """
    Mejor F1 de validación cruzada para cada valor de cada decisión (¿raíz o lema?, etc.).
    Usa solo la etapa de cribado: ahí todas las variantes se miden con los mismos
    hiperparámetros, así que la comparación es justa."""
    screening = experiments[experiments["stage"] == STAGE_SCREENING]
    return {
        factor: screening.groupby(factor)["cv_f1_macro"].max().round(4).to_dict()
            for factor in ("normalizer", "stopword_list", "ngram_range", "model")
    }

def _class_counts(frame: pd.DataFrame) -> dict:
    return frame["etiqueta"].value_counts().reindex(labels()).fillna(0).astype(int).to_dict()

def build_report(*, version: str, trained_at: str, params: dict, raw: pd.DataFrame,
                 cleaning: dict, eda: dict, train_df: pd.DataFrame, test_df: pd.DataFrame,
                 results: list[ModelResult], production: ModelResult,
                 experiments: pd.DataFrame, error_table: pd.DataFrame) -> dict:
    sources = sorted(raw["fuente"].dropna().unique()) if "fuente" in raw else ["desconocida"]
    return {
        "version": version,
        "trained_at": trained_at,
        "seed": params["seed"],
        "labels": {code: {"nombre": info["nombre"], "ofensivo": info["ofensivo"],
                          "descripcion": info["descripcion"]}
                   for code, info in label_info().items()},
        "offensive_labels": offensive_labels(),
        "threshold": params["decision"]["umbral_ofensivo"],
        "split": params["data"]["split"],
        "data_source": sources[0] if len(sources) == 1 else "mixta",
        "demo_mode": sources == ["sintetico"],
        "dataset": {
            "cleaning": cleaning,
            "eda": eda,
            "train_size": len(train_df),
            "test_size": len(test_df),
            "train_counts": _class_counts(train_df),
            "test_counts": _class_counts(test_df),
        },
        "production": {"name": production.name, "label": production.label,
                       "config": production.config, "cv_f1_macro": production.cv_f1_macro},
        "models": [result.as_report() for result in results],
        "experiments": experiments.to_dict(orient="records"),
        "factor_effects": factor_effects(experiments),
        "tfidf": params["tfidf"],
        "vocabulary_size": len(production.pipeline.named_steps["tfidf"].vocabulary_),
        "accuracy_by_phenomenon": accuracy_by_phenomenon(error_table),
        "accuracy_by_platform": accuracy_by_platform(error_table),
        "error_examples": error_examples(error_table),
        "top_terms": top_terms(production.pipeline),
    }
