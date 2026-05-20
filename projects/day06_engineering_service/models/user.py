"""数据模型：用户模型。

这个模块定义用户接口的请求和响应结构。
Pydantic 会自动做字段校验，并把模型信息同步到 FastAPI 文档。
这样接口契约清楚，调用方也能知道哪些字段必填、哪些字段可选。
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    """创建用户的请求模型。

    服务端生成 `user_id` 和 `created_at`，所以创建请求里不允许客户端传这些字段。
    """
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
    city: Optional[str] = Field(None, max_length=50, description="城市")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "zhangsan",
                "email": "zhangsan@example.com",
                "age": 25,
                "city": "北京"
            }
        }


class UserUpdate(BaseModel):
    """更新用户的请求模型。

    字段全部可选，表示只更新调用方传入的部分。
    """
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    age: Optional[int] = Field(None, ge=0, le=150, description="年龄")
    city: Optional[str] = Field(None, max_length=50, description="城市")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newemail@example.com",
                "age": 26,
                "city": "上海"
            }
        }


class UserResponse(BaseModel):
    """返回给调用方的用户结构。

    响应模型固定后，前端和测试都能依赖稳定字段，不需要猜接口返回内容。
    """
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    age: Optional[int] = Field(None, description="年龄")
    city: Optional[str] = Field(None, description="城市")
    created_at: str = Field(..., description="创建时间")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "username": "zhangsan",
                "email": "zhangsan@example.com",
                "age": 25,
                "city": "北京",
                "created_at": "2026-05-07 10:00:00"
            }
        }
