"""Application-wide error type + handler registration.

`AppError` is the domain exception every route raises. The FastAPI
handler in `register_error_handlers` shapes responses to CLAUDE.md's
`{error: {code, message}}` contract.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Domain error shaped to CLAUDE.md's {error: {code, message}} contract."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def _handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handler)  # type: ignore[arg-type]
