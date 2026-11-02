"""
Explicación de UNA predicción: qué términos del texto empujaron el resultado.

Contribución de un término = valor TF-IDF del término en ese texto x su peso en el modelo.
El peso se mide respecto del promedio de las clases (así tiene sentido tanto en la regresión
logística, con coeficientes, como en Naive Bayes, con log-probabilidades).
"""

import numpy as np
from sklearn.pipeline import Pipeline

def _weights(model) -> np.ndarray | None:
    if hasattr(model, "coef_"):
        return model.coef_
    if hasattr(model, "feature_log_prob_"):
        return model.feature_log_prob_
    return None

def explain_terms(pipeline: Pipeline, text: str, predicted: str, offensive: list[str],
                  top_n: int = 5) -> dict:
    """Devuelve los términos que más empujaron hacia la clase predicha y hacia «ofensivo»."""
    empty = {"clase": [], "ofensivo": []}
    model = pipeline.named_steps["model"]
    weights = _weights(model)
    if weights is None:
        return empty
    tfidf = pipeline.named_steps["tfidf"]
    x = tfidf.transform(pipeline.named_steps["preprocess"].transform([text])).tocoo()
    if x.nnz == 0:
        return empty

    names = tfidf.get_feature_names_out()
    centered = weights - weights.mean(axis=0)
    classes = list(model.classes_)
    toward_class = centered[classes.index(predicted)]
    off = [i for i, c in enumerate(classes) if c in offensive]
    non = [i for i, c in enumerate(classes) if c not in offensive]
    toward_offensive = centered[off].mean(axis=0) - centered[non].mean(axis=0)

    def top(direction: np.ndarray) -> list[dict]:
        contribution = x.data * direction[x.col]
        order = np.argsort(contribution)[::-1][:top_n]
        return [{"termino": str(names[x.col[i]]), "peso": round(float(contribution[i]), 4)}
                for i in order if contribution[i] > 0]

    return {"clase": top(toward_class), "ofensivo": top(toward_offensive)}
