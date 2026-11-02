# Imagen en tres capas. El entrenamiento y la API usan la MISMA imagen de ejecución: así el
# preprocesamiento y las versiones de las librerías coinciden con las del modelo guardado.
#
#   builder   instala las dependencias en un entorno virtual (aquí se compila lo que haga falta)
#   runtime   copia solo ese entorno y el código; es lo que se ejecuta
#   dev       runtime + pytest, para correr las pruebas dentro del contenedor

FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY params.yaml ./
COPY src ./src
COPY api ./api
COPY data ./data
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM runtime AS dev
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
CMD ["pytest", "-q", "-p", "no:cacheprovider"]
