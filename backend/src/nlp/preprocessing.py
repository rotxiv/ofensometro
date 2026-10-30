"""Preprocesamiento completo de un comentario, listo para TF-IDF.

``TextPreprocessor`` es el primer paso del pipeline de scikit-learn. El mismo objeto que se usa
al entrenar se guarda en ``model.joblib`` y atiende cada petición de la API: nada más
reimplementa estos pasos.

Cadena de pasos (la limpieza inicial vive en ``normalizer.py``):
    normalizar -> separar en palabras -> quitar stop words -> raíz o lema -> quitar tildes

Se conserva a propósito lo que en otras tareas se borra: groserías, negaciones, pronombres de
segunda persona, plurales, emojis, gritos y risas. En detección de ofensas eso ES la señal.
"""

from functools import lru_cache
from dataclasses import dataclass, field

import spacy
from spacy.tokens import Doc
from spacy.lang.es.stop_words import STOP_WORDS

from nltk.stem import SnowballStemmer
from sklearn.base import BaseEstimator, TransformerMixin

from src.nlp.lexicon import SPECIAL_PREFIX
from src.nlp.normalizer import normalize, normalize_with_signals, strip_accents

__all__ = ["TextPreprocessor", "tokenize", "stopwords", "normalize", "normalize_with_signals",
           "strip_accents", "STOPWORD_LISTS", "NORMALIZERS"]

STOPWORD_LISTS = ("spacy_full", "adjusted")
NORMALIZERS = ("stem", "lemma")


def tokenize(normalized: str) -> list[str]:
    """Tras normalizar solo quedan letras, así que basta separar por espacios.
    Se descartan las letras sueltas («a», «y», «o»)."""
    return [token for token in normalized.split(" ") if len(token) > 1]

@lru_cache
def stopwords(list_name: str, keep_words: tuple = (), extra: tuple = ()) -> frozenset:
    """
    Stop words de spaCy en español, sin tildes (en redes sociales casi nunca se escriben).
    ``adjusted`` quita las palabras de ``keep_words`` (que aportan señal) y suma las de ``extra``.
    """
    if list_name not in STOPWORD_LISTS:
        raise ValueError(f"Lista de stop words desconocida: {list_name}")
    base = {strip_accents(word) for word in STOP_WORDS}
    if list_name == "spacy_full":
        return frozenset(base)
    return frozenset((base - {strip_accents(w) for w in keep_words})
                     | {strip_accents(w) for w in extra})

@lru_cache
def _snowball():
    return SnowballStemmer("spanish")

@lru_cache
def _spacy_model():
    return spacy.load("es_core_news_sm", disable=["parser", "ner"])

def _is_invented(token: str) -> bool:
    return token.startswith(SPECIAL_PREFIX)

@dataclass
class Analysis:
    """Cada etapa del preprocesamiento de UN texto; la API lo muestra tal cual."""
    original: str
    normalized: str
    tokens: list
    removed_stopwords: list
    without_stopwords: list
    roots: list
    final: list
    signals: dict = field(default_factory=dict)

class TextPreprocessor(BaseEstimator, TransformerMixin):
    """
    Transformador de scikit-learn: textos crudos entran, textos preprocesados salen.
    No aprende nada de los datos, así que aplicarlo antes de la validación cruzada no filtra
    información entre pliegues.
    """
    def __init__(self, normalizer: str = "lemma", stopword_list: str = "adjusted",
                 keep_words: tuple = (), extra_stopwords: tuple = ()):
        self.normalizer = normalizer
        self.stopword_list = stopword_list
        self.keep_words = keep_words
        self.extra_stopwords = extra_stopwords

    def fit(self, X, y=None):
        """Verifica que los parámetros sean válidos, pero no aprende nada de los datos."""
        _ = X  # Mantiene la firma estándar de scikit-learn.
        if self.normalizer not in NORMALIZERS:
            raise ValueError(f"normalizer debe ser uno de {NORMALIZERS}")
        if self.stopword_list not in STOPWORD_LISTS:
            raise ValueError(f"stopword_list debe ser uno de {STOPWORD_LISTS}")
        return self

    def transform(self, X) -> list[str]:
        return [" ".join(item.final) for item in self._analyze(list(X))]

    def explain(self, text: str) -> dict:
        """Todas las etapas de un texto, con los mismos nombres que usa la API."""
        item = self._analyze([text])[0]
        return {name: getattr(item, name) for name in item.__dataclass_fields__}

    # -- etapas internas --------------------------------------------------------------

    def _stop_set(self) -> frozenset:
        return stopwords(self.stopword_list, tuple(self.keep_words), tuple(self.extra_stopwords))

    @staticmethod
    def _stem_all(token_lists: list[list[str]]) -> list[list[str]]:
        stem = _snowball().stem
        return [[t if _is_invented(t) else stem(t) for t in tokens] for tokens in token_lists]

    @staticmethod
    def _lemmatize_all(token_lists: list[list[str]]) -> list[list[str]]:
        """
        spaCy lematiza con la frase completa a la vista (por eso va antes de quitar stop words).
        """
        model = _spacy_model()
        docs = (Doc(model.vocab, words=tokens) for tokens in token_lists)
        return [[t.text if _is_invented(t.text) else t.lemma_.lower() for t in doc]
                for doc in model.pipe(docs, batch_size=256)]

    def _analyze(self, texts: list[str]) -> list[Analysis]:
        cleaned = [normalize_with_signals(text or "") for text in texts]
        tokens_per_text = [tokenize(normalized) for normalized, _ in cleaned]
        reduce_to_root = {"stem": self._stem_all, "lemma": self._lemmatize_all}[self.normalizer]
        roots_per_text = reduce_to_root(tokens_per_text)
        stop = self._stop_set()

        analyses = []
        for text, (normalized, signals), tokens, roots in zip(
                texts, cleaned, tokens_per_text, roots_per_text):
            is_stop = [strip_accents(t) in stop for t in tokens]
            kept = [(t, r) for t, r, dropped in zip(tokens, roots, is_stop) if not dropped]
            analyses.append(Analysis(
                original=text,
                normalized=normalized,
                tokens=tokens,
                removed_stopwords=[t for t, dropped in zip(tokens, is_stop) if dropped],
                without_stopwords=[t for t, _ in kept],
                roots=[r for _, r in kept],
                final=[strip_accents(r) for _, r in kept],
                signals=signals,
            ))
        return analyses
