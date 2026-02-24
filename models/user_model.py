from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from modules.utils import get_timestamp


class CreateUserInput(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)

class CreateUser(CreateUserInput):
    is_active: bool = True
    created_at:float = Field(default_factory=lambda: get_timestamp())
    updated_at: float = Field(default_factory=lambda: get_timestamp())


class ReadUser(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(..., min_length=3, max_length=50)
    is_active: bool = Field(...)
    created_at: float = Field(...)
    updated_at: float = Field(...)
    id: str = Field(...)


class UpdateUser(BaseModel):
    updated_at: float = Field(default_factory=lambda: get_timestamp())
    password: Optional[str] = Field(None, min_length=4, max_length=100)


class DeleteUser(BaseModel):
    id: str


class LoginUser(BaseModel):
    email: EmailStr = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)


class ChangePassword(BaseModel):
    email: EmailStr = Field(..., min_length=3, max_length=50)
    current_password: str = Field(..., min_length=4, max_length=100)
    new_password: str = Field(..., min_length=4, max_length=100)