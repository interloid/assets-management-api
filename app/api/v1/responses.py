from fastapi import status

from app.shared.schemas.common import (
    ErrorResponse,
    ValidationErrorResponse,
)

UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication credentials are invalid or missing",
    },
}

FORBIDDEN_RESPONSE = {
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponse,
        "description": "Admin access is required",
    },
}

NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "Resource not found",
    },
}

CONFLICT_RESPONSE = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "Resource conflicts with the current state",
    },
}

VALIDATION_RESPONSE = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ValidationErrorResponse,
        "description": "Request validation failed",
    },
}

INTERNAL_SERVER_ERROR_RESPONSE = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorResponse,
        "description": "Internal server error",
    },
}
