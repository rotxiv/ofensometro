"""Limpieza, resumen exploratorio y división entrenamiento / prueba."""

from collections import Counter

import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import labels
from src.nlp.preprocessing import normalize, stopwords, strip_accents, tokenize

def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Quita textos vacíos, etiquetas desconocidas y duplicados exactos.
    Devuelve los datos limpios y un reporte de lo eliminado, para el panel de EDA."""
    missing = {col: int(n) for col, n in raw.isna().sum().items() if n}
    df = raw.copy()
    df["texto"] = df["texto"].fillna("").astype(str).str.strip()
    empty = df["texto"].eq("")
    df = df[~empty]
    bad_label = ~df["etiqueta"].isin(labels())
    df = df[~bad_label]
    conflicts = int((df.groupby("texto")["etiqueta"].nunique() > 1).sum())
    duplicated = df.duplicated(subset="texto", keep="first")
    df = df[~duplicated].reset_index(drop=True)
    report = {
        "raw_rows": len(raw),
        "missing_values": missing,
        "empty_texts_removed": int(empty.sum()),
        "unknown_labels_removed": int(bad_label.sum()),
        "duplicates_removed": int(duplicated.sum()),
        "duplicates_with_conflicting_label": conflicts,
        "clean_rows": len(df),
    }
    return df, report

def _frequent_words(frame: pd.DataFrame, stop: frozenset, top_n: int) -> dict:
    """Palabras más usadas en cada clase, sin stop words ni tokens inventados."""
    found = {}
    for code in labels():
        counter = Counter()
        for text in frame.loc[frame["etiqueta"] == code, "texto"]:
            counter.update(t for t in tokenize(normalize(text))
                           if strip_accents(t) not in stop and not t.startswith("xx"))
        found[code] = counter.most_common(top_n)
    return found

def _length_profile(frame: pd.DataFrame, words: pd.Series) -> dict:
    profile = {}
    for code in labels():
        mask = frame["etiqueta"] == code
        if mask.any():
            profile[code] = {"mean": round(float(words[mask].mean()), 1),
                             "median": float(words[mask].median()),
                             "max": int(words[mask].max())}
    return profile

def _histogram(values: pd.Series, width: int = 5) -> list[dict]:
    counts = ((values // width) * width).value_counts().sort_index()
    return [{"from": int(low), "to": int(low + width - 1), "count": int(n)}
            for low, n in counts.items()]

def describe(df: pd.DataFrame, keep_words: tuple, extra_stopwords: tuple, top_n: int = 12) -> dict:
    """
    Resumen exploratorio: clases, longitudes y palabras frecuentes. 
    No influye en el modelo.
    """
    counts = df["etiqueta"].value_counts().reindex(labels()).fillna(0).astype(int)
    words = df["texto"].str.split().str.len()
    summary = {
        "class_counts": counts.to_dict(),
        "class_share": (counts / counts.sum()).round(4).to_dict(),
        "imbalance_ratio": round(float(counts.max() / max(counts.min(), 1)), 1),
        "length_words": _length_profile(df, words),
        "length_histogram": _histogram(words),
        "top_words": _frequent_words(df, stopwords("adjusted", keep_words, extra_stopwords), top_n),
    }
    if "plataforma" in df:
        table = pd.crosstab(df["plataforma"], df["etiqueta"])
        summary["by_platform"] = table.reindex(columns=labels(), fill_value=0).to_dict("index")
    return summary

def split(df: pd.DataFrame, params: dict):
    """
    División entrenamiento / prueba.

    stratified: mismas proporciones de cada clase en ambos conjuntos y misma división siempre
                (semilla fija).
    official:   train + validation oficiales para entrenar y test oficial para probar. Permite
                comparar con la literatura, pero la distribución del test oficial es distinta.
    """
    mode, seed = params["data"]["split"], params["seed"]
    if mode == "stratified":
        return train_test_split(df, test_size=params["data"]["test_size"],
                                stratify=df["etiqueta"], random_state=seed)
    if mode == "official":
        test = df[df["particion"] == "test"]
        train = df[df["particion"].isin(["train", "validation"])]
        if test.empty or train.empty:
            raise ValueError("split=official necesita filas con particion train/validation y test.")
        return train, test
    raise ValueError(f"data.split debe ser 'stratified' u 'official', no '{mode}'.")
