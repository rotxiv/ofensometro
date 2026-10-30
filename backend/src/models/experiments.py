"""
Modelos, pipeline de producción y búsqueda de la mejor configuración.

La búsqueda se hace en DOS etapas en lugar de probar todas las combinaciones a la vez:

  1. Cribado del preprocesamiento. Cada variante de (normalizador, stop words, n-gramas) se
     mide con cada modelo usando sus hiperparámetros por defecto. Como todos juegan en
     igualdad de condiciones, la tabla permite comparar una decisión contra otra
     («¿lema o raíz?») sin que el ajuste fino distorsione la comparación.
  2. Ajuste de hiperparámetros. Cada modelo se afina SOLO sobre su mejor variante de
     preprocesamiento.

Es una búsqueda voraz: no explora interacciones entre el preprocesamiento y los hiperparámetros,
a cambio de evaluar mucho menos (30 validaciones cruzadas).
Todo se evalúa con validación cruzada sobre el conjunto de entrenamiento.
"""

from dataclasses import dataclass
from itertools import product

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import ParameterGrid, StratifiedKFold, cross_validate
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import Pipeline

from src.nlp.preprocessing import TextPreprocessor

MODEL_LABELS = {
    "baseline": "Línea base (siempre la clase más frecuente)",
    "complement_nb": "Naive Bayes complementario",
    "logistic_regression": "Regresión logística",
}

STAGE_SCREENING = "cribado"
STAGE_TUNING = "ajuste"
STAGE_BASELINE = "línea base"

def make_model(name: str, seed: int):
    """ComplementNB y no el multinomial: estima cada clase con los textos de las DEMÁS, así que
    no se hunde cuando una clase tiene ~1 % de los datos (OFG)."""
    factories = {
        "complement_nb": lambda: ComplementNB(),
        "logistic_regression": lambda: LogisticRegression(max_iter=2000, random_state=seed),
        "baseline": lambda: DummyClassifier(strategy="most_frequent"),
    }
    if name not in factories:
        raise ValueError(f"Modelo desconocido: {name}")
    return factories[name]()

def make_vectorizer(ngram_range, tfidf: dict) -> TfidfVectorizer:
    # El preprocesador ya bajó a minúsculas y separó las palabras: solo se divide por espacios.
    return TfidfVectorizer(token_pattern=r"\S+", lowercase=False,
                           ngram_range=tuple(ngram_range), **tfidf)

def make_preprocessor(normalizer: str, stopword_list: str, nlp: dict) -> TextPreprocessor:
    """
    Crea un transformador de scikit-learn que aplica el preprocesamiento a los textos crudos.
    """
    return TextPreprocessor(normalizer=normalizer, stopword_list=stopword_list,
                            keep_words=tuple(nlp["keep_words"]),
                            extra_stopwords=tuple(nlp["extra_stopwords"]))

def build_pipeline(config: dict, params: dict) -> Pipeline:
    """El objeto que se guarda y se sirve: texto crudo entra, clase sale."""
    model = make_model(config["model"], params["seed"])
    model.set_params(**config.get("hyperparameters", {}))
    return Pipeline([
        ("preprocess", make_preprocessor(config["normalizer"], config["stopword_list"],
                                         params["nlp"])),
        ("tfidf", make_vectorizer(config["ngram_range"], params["tfidf"])),
        ("model", model),
    ])

@dataclass(frozen=True)
class Variant:
    """Una forma concreta de preprocesar: se calcula una vez y se reutiliza."""
    normalizer: str
    stopword_list: str
    ngram_range: tuple

class Evaluator:
    """Mide una configuración con validación cruzada estratificada (mismos pliegues siempre)."""

    def __init__(self, y: pd.Series, params: dict):
        self.y = y
        self.params = params
        self.folds = StratifiedKFold(n_splits=params["experiments"]["cv_folds"],
                                     shuffle=True, random_state=params["seed"])

    def score(self, prepared: list[str], ngram_range, model: str, hyperparameters: dict) -> dict:
        pipeline = Pipeline([
            ("tfidf", make_vectorizer(ngram_range, self.params["tfidf"])),
            ("model", make_model(model, self.params["seed"]).set_params(**hyperparameters)),
        ])
        result = cross_validate(pipeline, prepared, self.y, cv=self.folds, n_jobs=-1,
                                scoring={"f1": "f1_macro", "acc": "accuracy"})
        return {
            "cv_f1_macro": round(float(result["test_f1"].mean()), 4),
            "cv_f1_macro_std": round(float(result["test_f1"].std()), 4),
            "cv_accuracy": round(float(result["test_acc"].mean()), 4),
        }

def _row(stage: str, model: str, variant: Variant | None, hyperparameters: dict,
         scores: dict) -> dict:
    return {
        "stage": stage,
        "model": model,
        "normalizer": variant.normalizer if variant else "-",
        "stopword_list": variant.stopword_list if variant else "-",
        "ngram_range": f"{variant.ngram_range[0]}-{variant.ngram_range[1]}" if variant else "-",
        "hyperparameters": hyperparameters,
        **scores,
    }

def run_experiments(texts: pd.Series, y: pd.Series, params: dict) -> pd.DataFrame:
    exp = params["experiments"]
    evaluator = Evaluator(y, params)
    families = list(exp["models"])

    # Etapa 1: cada preprocesamiento se calcula una sola vez y se prueba con cada modelo.
    prepared_by_pair = {}
    for normalizer, stopword_list in product(exp["normalizers"], exp["stopword_lists"]):
        print(f"  preprocesamiento {normalizer} + {stopword_list}")
        prepared_by_pair[(normalizer, stopword_list)] = \
            make_preprocessor(normalizer, stopword_list, params["nlp"]).transform(texts)

    rows = []
    variants_of = {}
    for (normalizer, stopword_list), prepared in prepared_by_pair.items():
        for ngram_range in exp["ngram_ranges"]:
            variant = Variant(normalizer, stopword_list, tuple(ngram_range))
            for model in families:
                scores = evaluator.score(prepared, variant.ngram_range, model, {})
                rows.append(_row(STAGE_SCREENING, model, variant, {}, scores))
                variants_of[(model, variant)] = scores["cv_f1_macro"]

    # Etapa 2: cada modelo se afina sobre SU mejor variante.
    for model in families:
        best = max((v for (m, v) in variants_of if m == model),
                   key=lambda v: variants_of[(model, v)])
        print(f"  ajuste de {model} sobre {best.normalizer}/{best.stopword_list}/{best.ngram_range}")
        prepared = prepared_by_pair[(best.normalizer, best.stopword_list)]
        for hyperparameters in ParameterGrid(exp["models"][model]):
            scores = evaluator.score(prepared, best.ngram_range, model, hyperparameters)
            rows.append(_row(STAGE_TUNING, model, best, hyperparameters, scores))

    baseline = cross_validate(make_model("baseline", params["seed"]), texts, y,
                              cv=evaluator.folds, scoring=["f1_macro", "accuracy"])
    rows.append(_row(STAGE_BASELINE, "baseline", None, {"strategy": "most_frequent"}, {
        "cv_f1_macro": round(float(baseline["test_f1_macro"].mean()), 4),
        "cv_f1_macro_std": round(float(baseline["test_f1_macro"].std()), 4),
        "cv_accuracy": round(float(baseline["test_accuracy"].mean()), 4),
    }))

    return (pd.DataFrame(rows)
            .sort_values(["cv_f1_macro", "stage"], ascending=[False, True], kind="stable")
            .reset_index(drop=True))

def row_to_config(row: pd.Series) -> dict:
    return {
        "model": row["model"],
        "normalizer": row["normalizer"],
        "stopword_list": row["stopword_list"],
        "ngram_range": [int(n) for n in row["ngram_range"].split("-")],
        "hyperparameters": row["hyperparameters"],
    }
