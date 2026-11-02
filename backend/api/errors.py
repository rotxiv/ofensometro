"""Un solo formato de error para toda la API: {"error": "...", "detalles": [...]}."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.schemas import ErrorResponse

ERROR_RESPONSES = {
    422: {"model": ErrorResponse, "description": "Entrada inválida"},
    503: {"model": ErrorResponse, "description": "Modelo o base de datos no disponible"},
}

_JSON_BODY_HINT = 'El cuerpo debe ser un objeto JSON, por ejemplo {"texto": "..."}.'
_PYDANTIC_MESSAGES = {
    "missing": "Falta este campo obligatorio.",
    "string_type": "Debe ser un texto entre comillas.",
    "json_invalid": "El cuerpo de la petición no es un JSON válido.",
    "model_attributes_type": _JSON_BODY_HINT,
    "dict_type": _JSON_BODY_HINT,
    "extra_forbidden": "Campo no permitido; solo se acepta 'texto'.",
}

class ApiError(Exception):
    """Error previsto, con el código HTTP que corresponde y un mensaje para la persona."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

def _body(message: str, details: list | None = None) -> dict:
    return {"error": message, "detalles": details or []}

def install_error_handlers(app: FastAPI) -> None:
    """
    Instala manejadores de errores para que toda la API devuelva el mismo formato JSON.
    """
    @app.exception_handler(ApiError)
    async def on_api_error(_: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.message))

    @app.exception_handler(StarletteHTTPException)
    async def on_http_error(_: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=_body(str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(_: Request, exc: RequestValidationError):
        details = []
        for issue in exc.errors():
            text = (_PYDANTIC_MESSAGES.get(issue["type"], issue["msg"]) or "Entrada inválida").removeprefix("Value error, ")
            where = ".".join(str(part) for part in issue["loc"] if part != "body") or "cuerpo"
            details.append({"campo": where, "mensaje": text})
        return JSONResponse(status_code=422, content=_body(details[0]["mensaje"], details))
