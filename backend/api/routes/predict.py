"""Clasificación de un comentario y de un archivo con varios."""

import time
from collections import Counter

from fastapi import APIRouter, File, UploadFile

from api import batch
from api.deps import LoadedService
from api.errors import ERROR_RESPONSES
from api.schemas import BatchItem, BatchResponse, PredictRequest, PredictResponse
from src.config import labels

router = APIRouter(prefix="/predict", tags=["predicción"])

@router.post("", response_model=PredictResponse, responses=ERROR_RESPONSES)
def predict(body: PredictRequest, service: LoadedService):
    """
    Clase, veredicto ofensivo/no ofensivo, probabilidades, palabras que pesaron 
    y los pasos del preprocesamiento.
    """
    started = time.perf_counter()
    prediction = service.classify([body.texto])[0]
    steps, explanation = service.inspect(body.texto, prediction)
    elapsed_ms = (time.perf_counter() - started) * 1000

    service.remember([body.texto], [prediction], origin="individual")
    class_name, description = service.describe_class(prediction.clase)
    return PredictResponse(
        **prediction.as_dict(),
        nombre_clase=class_name,
        descripcion=description,
        umbral=service.threshold,
        explicacion=explanation,
        preprocesamiento=steps,
        modelo={"nombre": service.label, "version": service.version},
        modo_demo=service.demo_mode,
        tiempo_ms=round(elapsed_ms, 1),
    )


@router.post("/batch", response_model=BatchResponse,
             responses={**ERROR_RESPONSES,
                        413: {"description": "Archivo demasiado grande"}})
async def predict_batch(service: LoadedService, archivo: UploadFile = File(
        description="Un .txt con un comentario por línea, o un .csv con una columna 'texto'.")):
    """Clasifica los comentarios de un archivo. Las filas inválidas se informan y se omiten."""
    raw = await archivo.read(batch.MAX_BYTES + 1)
    comments = batch.read_comments(archivo.filename, raw)
    valid, skipped = batch.split_valid(comments)

    texts = [text for _, text in valid]
    predictions = service.classify(texts)
    service.remember(texts, predictions, origin="lote")

    per_class = Counter(p.clase for p in predictions)
    return BatchResponse(
        total=len(predictions),
        ofensivos=sum(p.ofensivo for p in predictions),
        resumen={code: per_class.get(code, 0) for code in labels()},
        resultados=[BatchItem(fila=row, texto=text, **p.as_dict())
                for (row, text), p in zip(valid, predictions)],
        omitidas=skipped,
        modo_demo=service.demo_mode,
    )
