# 定義登入與回傳資料的驗證模型。
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    account: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(default="", max_length=50)


class LoginRequest(BaseModel):
    account: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class GoogleLoginRequest(BaseModel):
    idToken: str = Field(min_length=10)


class UserResponse(BaseModel):
    id: str
    account: str
    provider: str
    name: str
    description: str
    imageUrl: str
    createdAt: str | None


class AuthResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    expiresIn: int
    user: UserResponse
