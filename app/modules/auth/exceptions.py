from app.core.exceptions import AppError


class AuthenticationError(AppError):
    status_code = 401
    code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidRefreshTokenError(AuthenticationError):
    code = "INVALID_REFRESH_TOKEN"
    message = "The refresh token is invalid or expired"


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class RefreshTokenReuseError(AuthenticationError):
    code = "REFRESH_TOKEN_REUSE"
    message = "Refresh token has already been used"


class UserInactiveError(AuthenticationError):
    code = "USER_INACTIVE"
    message = "User account is inactive"


class EmailAlreadyRegisteredError(AppError):
    status_code = 409
    code = "EMAIL_ALREADY_REGISTERED"
    message = "An account with this email address already exists"


class AuthorizationError(AppError):
    status_code = 403
    code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action"


class SamePasswordError(AppError):
    status_code = 400
    code = "SAME_PASSWORD"
    message = "The new password must be different from the current password"
