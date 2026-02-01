from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    gender: str = Field(..., min_length=1, max_length=10, description="性别")
    age: int = Field(..., ge=1, le=120, description="年龄")
    city: str = Field(..., min_length=1, max_length=50, description="城市")

    model_config = ConfigDict(populate_by_name=True)


class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")

    model_config = ConfigDict(populate_by_name=True)


class UserInfo(BaseModel):
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    gender: str = Field(..., description="性别")
    age: int = Field(..., description="年龄")
    city: str = Field(..., description="城市")
    signup_ts: datetime = Field(..., description="注册时间")
    role: str = Field(..., description="角色")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间(秒)")
    user: UserInfo

    model_config = ConfigDict(from_attributes=True)
