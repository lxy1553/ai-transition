"""数据模型：用户模型。

这个模块用 Pydantic 定义请求和响应结构。
它的用途是把“接口能接收什么、返回什么”写成明确协议，
让 FastAPI 自动完成字段校验和文档生成。
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """创建用户时允许前端提交的字段。

    创建接口不让用户自己传 `user_id` 和 `created_at`，
    因为这些字段应该由服务端生成，避免客户端伪造。
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
    """更新用户时允许修改的字段。

    所有字段都是可选的，因为用户可能只改邮箱、年龄或城市中的一个。
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
    """接口返回给调用方的用户结构。

    响应模型固定后，前端或其他系统就能稳定消费这些字段，
    不需要猜服务端每次会返回什么。
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
                "created_at": "2026-05-06 10:00:00"
            }
        }
