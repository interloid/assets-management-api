from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.enums import UserRole
from app.validators.full_name import validate_full_name
from app.validators.password import validate_password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    _validate_password = field_validator("password")(validate_password)
    _validate_full_name = field_validator("full_name")(validate_full_name)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResult(BaseModel):
    access_token: str
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    _validate_new_password = field_validator("new_password")(validate_password)

class MessageResponse(BaseModel):
    message: str

