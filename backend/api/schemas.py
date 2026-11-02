"""
Contratos de entrada y salida; FastAPI los usa para validar y para documentar /api/docs.
"""

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from src.config import load_params

MAX_CHARS = load_params()["data"]["max_chars"]
_HAS_LETTER = re.compile(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]")

def check_comment(value: str) -> str:
    """Regla única para un comentario, la usan la predicción individual y la de lote."""
    value = value.strip()
    if not value:
        raise ValueError("El texto está vacío.")
    if len(value) > MAX_CHARS:
        raise ValueError(f"El texto tiene {len(value)} caracteres; el máximo es {MAX_CHARS}.")
    if not _HAS_LETTER.search(value):
        raise ValueError("El texto no contiene palabras.")
    return value

Comment = Annotated[str, AfterValidator(check_comment)]

class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "examples": [{"texto": "Eres un inútil, nadie te soporta 🤡"}]})

    texto: Comment = Field(description=f"Comentario en español, de 1 a {MAX_CHARS} caracteres.")

# -- piezas de la respuesta --------------------------------------------------------------

class Obfuscation(BaseModel):
    original: str
    normal: str

class Signals(BaseModel):
    mayusculas: bool = Field(description="Mayúsculas sostenidas (gritos).")
    ofuscadas: list[Obfuscation] = Field(description='Palabras disfrazadas, p. ej. "p3ndejo".')
    emojis: list[str]
    risas: bool

class PreprocessingSteps(BaseModel):
    original: str
    normalizado: str = Field(description="Minúsculas, sin URLs ni números; ofuscación revertida; "
                                         "emojis, risas y gritos convertidos en tokens.")
    tokens: list[str]
    stopwords_eliminadas: list[str]
    sin_stopwords: list[str]
    raices: list[str] = Field(description="Raíces (stemming) o lemas, según el modelo.")
    final: list[str] = Field(description="Lo que recibe TF-IDF: raíces sin tildes.")
    metodo: str = Field(description="stem o lemma")
    senales: Signals

class Term(BaseModel):
    termino: str = Field(description="Término tal como lo ve el modelo (raíz, o par de raíces).")
    palabra: str = Field(description="Cómo aparece en el texto del usuario, para resaltarlo.")
    peso: float = Field(description="Cuánto empujó el resultado: mayor = más influencia.")

class Explanation(BaseModel):
    clase: list[Term] = Field(description="Términos que empujaron hacia la clase predicha.")
    ofensivo: list[Term] = Field(description="Términos que empujaron hacia «ofensivo».")

class ModelInfo(BaseModel):
    nombre: str
    version: str

class Verdict(BaseModel):
    """Lo que toda predicción trae, venga de /predict o de /predict/batch."""
    clase: str = Field(description="NO, NOE, OFP u OFG: la más probable.")
    ofensivo: bool = Field(description="P(OFP) + P(OFG) supera el umbral.")
    probabilidad: float = Field(description="Probabilidad de la clase predicha.")
    probabilidad_ofensivo: float
    probabilidades: dict[str, float]

# -- respuestas por endpoint -------------------------------------------------------------

class PredictResponse(Verdict):
    nombre_clase: str
    descripcion: str
    umbral: float
    explicacion: Explanation
    preprocesamiento: PreprocessingSteps
    modelo: ModelInfo
    modo_demo: bool = Field(description="True si el modelo se entrenó con datos sintéticos.")
    tiempo_ms: float

class BatchItem(Verdict):
    fila: int
    texto: str

class SkippedRow(BaseModel):
    fila: int
    motivo: str

class BatchResponse(BaseModel):
    total: int
    ofensivos: int
    resumen: dict[str, int] = Field(description="Cantidad de comentarios por clase.")
    resultados: list[BatchItem]
    omitidas: list[SkippedRow]
    modo_demo: bool

class LabelInfo(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    ofensivo: bool

class HealthResponse(BaseModel):
    estado: str = Field(description="ok si el modelo está cargado; degradado si no.")
    modelo_cargado: bool
    modelo: str | None
    version: str | None
    datos: str | None = Field(description="Origen de los datos de entrenamiento: offendes o sintetico.")
    modo_demo: bool
    base_de_datos: str = Field(description="conectada, sin conexión o no configurada")

class ErrorResponse(BaseModel):
    error: str
    detalles: list[dict] = []
