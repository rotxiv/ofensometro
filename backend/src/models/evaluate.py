"""
Métricas sobre el conjunto de prueba, análisis de errores y términos más influyentes.
"""

import re

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support, roc_auc_score)
from sklearn.pipeline import Pipeline

from src.config import labels, offensive_labels
from src.nlp.preprocessing import normalize_with_signals

NEGATION_RE = re.compile(r"\b(no|ni|nunca|nada|tampoco|nadie|sin)\b", re.IGNORECASE)


def probabilities_by_label(pipeline, texts) -> np.ndarray:
    """
    Probabilidades en el orden de params.yaml. scikit-learn ordena las clases
    alfabéticamente (NO, NOE, OFG, OFP)
    """
    proba = pipeline.predict_proba(texts)
    order = [list(pipeline.classes_).index(code) for code in labels()]
    return proba[:, order]

def p_offensive(proba: np.ndarray) -> np.ndarray:
    """P(ofensivo) = P(OFP) + P(OFG). ``proba`` va en el orden de params.yaml."""
    codes = labels()
    return proba[:, [codes.index(c) for c in offensive_labels()]].sum(axis=1)

def classification_metrics(y_true, y_pred) -> dict:
    codes = labels()
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=codes, zero_division=0)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro",
                                         labels=codes, zero_division=0)), 4),
        "per_class": {
            code: {"precision": round(float(p), 4), "recall": round(float(r), 4),
                   "f1": round(float(f), 4), "support": int(s)}
            for code, p, r, f, s in zip(codes, precision, recall, f1, support)
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=codes).tolist(),
    }

def binary_metrics(y_true, proba: np.ndarray, threshold: float) -> dict:
    """Vista binaria ofensivo / no ofensivo, derivada de las 4 clases con el umbral."""
    truth = pd.Series(y_true).isin(offensive_labels()).to_numpy()
    p_off = p_offensive(proba)
    pred = p_off >= threshold
    precision, recall, f1, _ = precision_recall_fscore_support(
        truth, pred, labels=[True], zero_division=0)
    both_classes = truth.any() and not truth.all()
    return {
        "threshold": threshold,
        "accuracy": round(float(accuracy_score(truth, pred)), 4),
        "f1_macro": round(float(f1_score(truth, pred, average="macro", zero_division=0)), 4),
        "offensive": {"precision": round(float(precision[0]), 4),
                      "recall": round(float(recall[0]), 4), "f1": round(float(f1[0]), 4)},
        "roc_auc": round(float(roc_auc_score(truth, p_off)), 4) if both_classes else None,
        "confusion_matrix": confusion_matrix(truth, pred, labels=[False, True]).tolist(),
    }

def phenomena(text: str) -> list[str]:
    """Rasgos del texto crudo que suelen explicar los errores."""
    _, signals = normalize_with_signals(text)
    found = []
    if signals["mayusculas"]:
        found.append("mayúsculas (gritos)")
    if signals["ofuscadas"]:
        found.append("ofuscación (p3ndejo)")
    if signals["emojis"]:
        found.append("emojis")
    if signals["risas"]:
        found.append("risas")
    if NEGATION_RE.search(text):
        found.append("negación")
    n_words = len(text.split())
    if n_words < 5:
        found.append("texto muy corto (<5 palabras)")
    elif n_words >= 30:
        found.append("texto largo (≥30 palabras)")
    return found or ["ninguno de los anteriores"]

def error_table(pipeline: Pipeline, test: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Todos los textos de prueba con su predicción y confianza; los errores quedan marcados."""
    proba = probabilities_by_label(pipeline, test["texto"])
    codes = labels()
    predicted = [codes[i] for i in proba.argmax(axis=1)]
    table = pd.DataFrame({
        "id": test["id"].to_numpy(),
        "texto": test["texto"].to_numpy(),
        "real": test["etiqueta"].to_numpy(),
        "predicho": predicted,
        "probabilidad": proba.max(axis=1).round(4),
        "prob_ofensivo": p_offensive(proba).round(4),
        "plataforma": test["plataforma"].to_numpy() if "plataforma" in test else "n/d",
    })
    table["correcto"] = table["real"] == table["predicho"]
    table["fenomenos"] = [phenomena(t) for t in table["texto"]]
    return table

def accuracy_by_phenomenon(table: pd.DataFrame) -> list[dict]:
    exploded = table.explode("fenomenos")
    grouped = exploded.groupby("fenomenos")["correcto"].agg(["count", "mean"])
    return [{"fenomeno": name, "n": int(row["count"]), "accuracy": round(float(row["mean"]), 4)}
            for name, row in grouped.sort_values("mean").iterrows()]

def accuracy_by_platform(table: pd.DataFrame) -> list[dict]:
    grouped = table.groupby("plataforma")["correcto"].agg(["count", "mean"])
    return [{"plataforma": name, "n": int(row["count"]), "accuracy": round(float(row["mean"]), 4)}
            for name, row in grouped.sort_values("mean").iterrows()]

def error_examples(table: pd.DataFrame, n: int = 12) -> list[dict]:
    """Los errores con más confianza, como máximo 3 por tipo de confusión (real → predicho)."""
    errors = (table[~table["correcto"]]
              .sort_values("probabilidad", ascending=False)
              .groupby(["real", "predicho"]).head(3)
              .head(n))
    errors = errors.drop(columns="correcto")
    return errors.to_dict(orient="records")

def top_terms(pipeline: Pipeline, n: int = 12) -> dict:
    """Términos que más empujan hacia cada clase.

    Regresión logística: los mayores coeficientes. Naive Bayes: mayor log-probabilidad
    respecto del promedio de las clases.
    """
    vocabulary = pipeline.named_steps["tfidf"].get_feature_names_out()
    model = pipeline.named_steps["model"]
    if hasattr(model, "coef_"):
        weights = model.coef_
    elif hasattr(model, "feature_log_prob_"):
        weights = model.feature_log_prob_ - model.feature_log_prob_.mean(axis=0)
    else:
        return {}
    return {
        code: [[vocabulary[i], round(float(weights[c, i]), 3)]
               for i in np.argsort(weights[c])[::-1][:n]]
        for c, code in enumerate(model.classes_)
    }
