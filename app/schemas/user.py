# 定義使用者資料更新的驗證模型。
from pydantic import BaseModel, Field


class UserUpdateRequest(BaseModel):
    account: str | None = Field(default=None, min_length=3, max_length=50)
    name: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=200)
    imageUrl: str | None = Field(default=None, max_length=500)
