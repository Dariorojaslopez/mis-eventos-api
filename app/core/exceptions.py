from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.utils.sensitive_data import redact_mapping
from app.utils.validation_errors import sanitize_validation_errors

logger = get_logger(__name__)


class AppException(Exception):
    """Excepción de dominio base para errores de negocio."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, code="not_found", **kwargs)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict", **kwargs: Any) -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, code="conflict", **kwargs)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", **kwargs: Any) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            **kwargs,
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden", **kwargs: Any) -> None:
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, code="forbidden", **kwargs)


class AIRateLimitError(AppException):
    def __init__(self, message: str = "AI rate limit exceeded", **kwargs: Any) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="ai_rate_limit_exceeded",
            **kwargs,
        )


class AIGenerationError(AppException):
    def __init__(
        self,
        message: str = "Unable to generate AI content at this time",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="ai_generation_failed",
            **kwargs,
        )


def _error_payload(
    *,
    code: str,
    message: str,
    request_id: str | None,
    details: dict[str, Any] | list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        },
        "request_id": request_id,
    }
    if details:
        body["error"]["details"] = details
    return body


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "application_error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        details=redact_mapping(exc.details) if exc.details else None,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=redact_mapping(exc.details) if exc.details else None,
        ),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            code="http_error",
            message=str(exc.detail),
            request_id=request_id,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_payload(
            code="validation_error",
            message="Request validation failed",
            request_id=request_id,
            details=sanitize_validation_errors(exc.errors()),
        ),
    )


async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("unhandled_exception", request_id=request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_payload(
            code="internal_error",
            message="An unexpected error occurred",
            request_id=request_id,
        ),
    )
