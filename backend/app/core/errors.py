# ==========================================================================
# VeriQuest Backend — Structured Error Handling
# ==========================================================================

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Create a structured JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=message)
        ).model_dump(),
    )


class AppError(HTTPException):
    """Application-level error with structured response."""

    def __init__(self, status_code: int, code: str, message: str):
        self.error_code = code
        self.error_message = message
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


# Common error factories
def unauthorized(message: str = "Authentication required") -> AppError:
    return AppError(401, "UNAUTHORIZED", message)


def forbidden(message: str = "Access denied") -> AppError:
    return AppError(403, "FORBIDDEN", message)


def not_found(resource: str = "Resource") -> AppError:
    return AppError(404, "NOT_FOUND", f"{resource} not found")


def validation_error(message: str) -> AppError:
    return AppError(422, "VALIDATION_ERROR", message)


def rate_limited(message: str = "Too many requests") -> AppError:
    return AppError(429, "RATE_LIMITED", message)


def system_error(message: str = "Internal server error") -> AppError:
    return AppError(500, "SYSTEM_ERROR", message)
