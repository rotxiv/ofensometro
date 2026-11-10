"""
Modelos, pipeline de producción y búsqueda de la mejor configuración.

Se evalúan todas las combinaciones de preprocesamiento e hiperparámetros con validación
cruzada sobre el conjunto de entrenamiento. El cribado registra las variantes con los
hiperparámetros por defecto; esas mismas combinaciones se omiten en la etapa de ajuste
para no evaluarlas dos veces.
"""

from dataclasses import dataclass
from itertools import product

import numpy as np
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
    """
    ComplementNB y no el multinomial: estima cada clase con los textos de las DEMÁS, 
    así que no se hunde cuando una clase tiene ~1 % de los datos (OFG).
    """
    factories = {
        "complement_nb": ComplementNB,
        "logistic_regression": lambda: LogisticRegression(max_iter=2000, random_state=seed),
        "baseline": lambda: DummyClassifier(strategy="most_frequent"),
    }
    if name not in factories:
        raise ValueError(f"Modelo desconocido: {name}")
    return factories[name]()

def make_vectorizer(ngram_range, tfidf: dict) -> TfidfVectorizer:
    """
    Crea un vectorizador de scikit-learn que aplica TF-IDF a los textos preprocesados.
    """
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
        """
        Devuelve las métricas de validación cruzada para un modelo y una variante 
        de preprocesamiento.
        """
        prepared_array = np.asarray(prepared, dtype=object)
        pipeline = Pipeline([
            ("tfidf", make_vectorizer(ngram_range, self.params["tfidf"])),
            ("model", make_model(model, self.params["seed"]).set_params(**hyperparameters)),
        ])
        result = cross_validate(pipeline, prepared_array, self.y, cv=self.folds, n_jobs=-1,
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
    """
    Ejecuta la busqueda de la mejor configuración y devuelve una tabla con los resultados
    de cada variante.
    """
    exp = params["experiments"]
    evaluator = Evaluator(y, params)
    families = list(exp["models"])

    # Cada preprocesamiento se calcula una sola vez y se reutiliza en todas las combinaciones.
    prepared_by_pair = {}
    for normalizer, stopword_list in product(exp["normalizers"], exp["stopword_lists"]):
        print(f"  preprocesamiento {normalizer} + {stopword_list}")
        prepared_by_pair[(normalizer, stopword_list)] = \
            make_preprocessor(normalizer, stopword_list, params["nlp"]).transform(texts)

    rows = []
    for (normalizer, stopword_list), prepared in prepared_by_pair.items():
        for ngram_range in exp["ngram_ranges"]:
            variant = Variant(normalizer, stopword_list, tuple(ngram_range))
            for model in families:
                # El cribado es la combinación por defecto de cada variante y modelo.
                scores = evaluator.score(prepared, variant.ngram_range, model, {})
                rows.append(_row(STAGE_SCREENING, model, variant, {}, scores))
                defaults = make_model(model, params["seed"]).get_params()
                for hyperparameters in ParameterGrid(exp["models"][model]):
                    if all(defaults.get(name) == value
                           for name, value in hyperparameters.items()):
                        continue
                    scores = evaluator.score(prepared, variant.ngram_range, model, hyperparameters)
                    rows.append(_row(STAGE_TUNING, model, variant, hyperparameters, scores))

    baseline = cross_validate(make_model("baseline", params["seed"]),
                              texts.astype(str).to_numpy(), y, cv=evaluator.folds,
                              scoring=["f1_macro", "accuracy"])
    rows.append(_row(STAGE_BASELINE, "baseline", None, {"strategy": "most_frequent"}, {
        "cv_f1_macro": round(float(baseline["test_f1_macro"].mean()), 4),
        "cv_f1_macro_std": round(float(baseline["test_f1_macro"].std()), 4),
        "cv_accuracy": round(float(baseline["test_accuracy"].mean()), 4),
    }))

    return (pd.DataFrame(rows)
            .sort_values(["cv_f1_macro", "stage"], ascending=[False, True], kind="stable")
            .reset_index(drop=True))

def row_to_config(row: pd.Series) -> dict:
    """"
    Convierte una fila de la tabla de resultados en un diccionario que se puede pasar 
    a build_pipeline().
    """
    return {
        "model": row["model"],
        "normalizer": row["normalizer"],
        "stopword_list": row["stopword_list"],
        "ngram_range": [int(n) for n in row["ngram_range"].split("-")],
        "hyperparameters": row["hyperparameters"],
    }
