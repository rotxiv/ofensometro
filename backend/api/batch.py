"""Lectura y validación de los archivos de la predicción por lote."""

import csv
import io

from api.errors import ApiError
from api.schemas import check_comment

MAX_ROWS = 500
MAX_BYTES = 1_000_000

def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ApiError(422, "El archivo debe estar codificado en UTF-8.") from None

def _from_txt(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]

def _from_csv(text: str) -> list[str]:
    reader = csv.DictReader(io.StringIO(text))
    if "texto" not in (reader.fieldnames or []):
        raise ApiError(422, "El CSV debe tener una columna llamada 'texto'.")
    return [row["texto"] or "" for row in reader]

READERS = {".txt": _from_txt, ".csv": _from_csv}

def read_comments(filename: str | None, raw: bytes) -> list[str]:
    """Extrae los comentarios del archivo, o explica por qué no se puede."""
    name = (filename or "").lower()
    extension = next((ext for ext in READERS if name.endswith(ext)), None)
    if extension is None:
        raise ApiError(422, "Formato no soportado: sube un .txt (un comentario por línea) "
                            "o un .csv con una columna 'texto'.")
    if len(raw) > MAX_BYTES:
        raise ApiError(413, "El archivo supera el máximo de 1 MB.")
    comments = READERS[extension](_decode(raw))
    if len(comments) > MAX_ROWS:
        raise ApiError(413, f"El archivo tiene {len(comments)} comentarios; "
                            f"el máximo es {MAX_ROWS}.")
    return comments

def split_valid(comments: list[str]) -> tuple[list[tuple[int, str]], list[dict]]:
    """Separa los comentarios válidos (con su número de fila) de los que se omiten."""
    valid, skipped = [], []
    for row, comment in enumerate(comments, start=1):
        try:
            valid.append((row, check_comment(comment)))
        except ValueError as problem:
            skipped.append({"fila": row, "motivo": str(problem)})
    if not valid:
        raise ApiError(422, "El archivo no contiene ningún comentario válido.")
    return valid, skipped
