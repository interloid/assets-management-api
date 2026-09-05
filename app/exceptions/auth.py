from app.exceptions.base import AppError


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class InvalidTokenError(AuthenticationError):
    code = "INVALID_TOKEN"
    message = "Invalid or expired token"


class RefreshTokenReuseError(AuthenticationError):
    code = "REFRESH_TOKEN_REUSE"
    message = "Refresh token has already been used"


class UserInactiveError(AuthenticationError):
    code = "USER_INACTIVE"
    message = "User account is inactive"


class EmailAlreadyRegisteredError(AppError):
    status_code = 409
    code = "EMAIL_ALREADY_REGISTERED"
    message = "Email is already registered"


class AuthorizationError(AppError):
    status_code = 403
    code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action"


class SamePasswordError(AppError):
    status_code = 400
    code = "SAME_PASSWORD"
    message = "New Password and current password cannot be same"
