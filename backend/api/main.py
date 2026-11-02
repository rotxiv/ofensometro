"""
Punto de entrada: ``uvicorn api.main:app``. Documentación interactiva en /api/docs.
"""

from api.app import create_app

app = create_app()
