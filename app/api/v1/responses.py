from fastapi import status

from app.shared.schemas.common import (
    ErrorResponse,
)

BAD_REQUEST_RESPONSE = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorResponse,
        "description": "The request could not be processed because the provided data is invalid",
    },
}

UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication credentials are missing or invalid",
    },
}

FORBIDDEN_RESPONSE = {
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponse,
        "description": "The authenticated user does not have permission to perform this operation",
    },
}

NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "The requested resource was not found",
    },
}

CONFLICT_RESPONSE = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "The request conflicts with the current state of the resource",
    },
}

VALIDATION_RESPONSE = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorResponse,
        "description": "The request contains invalid or malformed data",
    },
}

INTERNAL_SERVER_ERROR_RESPONSE = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorResponse,
        "description": "An unexpected server error occurred",
    },
}

LOGOUT_UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "The provided access token is invalid or expired, or the access and refresh tokens do not belong to the same session",
    },
}


TOO_MANY_REQUESTS_RESPONSE = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorResponse,
        "description": (
            "The request was rejected because the rate limit was exceeded. "
            "Retry after the period specified by the Retry-After header."
        ),
    },
}
