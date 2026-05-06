"""
数据模型：用户模型

使用Pydantic定义数据模型
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """用户创建模型"""
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
    """用户更新模型"""
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
    """用户响应模型"""
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
