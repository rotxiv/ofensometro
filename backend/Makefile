# Atajos para macOS y Linux (en Windows, ejecuta los comandos docker compose directamente).
# `make` sin argumentos lista lo disponible.

COMPOSE  := docker compose
TRAINER  := $(COMPOSE) run --rm trainer
API_URL  := http://localhost:$${API_PORT:-8000}/api/docs

.DEFAULT_GOAL := help

help:                ## muestra esta ayuda
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

up:                  ## construye y levanta todo (la primera vez entrena)
	$(COMPOSE) up --build -d
	@echo "Documentación de la API: $(API_URL)"

ingest:              ## OffendES (data/external/offendes) -> data/raw/comentarios.csv
	$(TRAINER) python -m src.data.ingest

train:               ## reentrena con datos reales y reinicia la API
	$(TRAINER) python -m src.pipeline --reload-data
	$(COMPOSE) restart api

test:                ## pruebas automáticas dentro del contenedor
	$(COMPOSE) --profile dev run --rm --build tests

logs:                ## sigue los registros de la API y del entrenamiento
	$(COMPOSE) logs -f api trainer

down:                ## detiene los contenedores (conserva la base)
	$(COMPOSE) down

clean:               ## detiene todo y borra la base y los artefactos
	$(COMPOSE) down -v
	find artifacts -type f ! -name .gitkeep -delete

.PHONY: help up ingest train test logs down clean
