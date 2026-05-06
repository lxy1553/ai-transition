"""
路由模块：用户路由

定义用户相关的API路由
"""

from fastapi import APIRouter, Query
from typing import List
from pathlib import Path

from models.user import UserCreate, UserUpdate, UserResponse
from services.user_service import UserService
from config.settings import settings
from core.logger import logger

# 创建路由器
router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# 初始化用户服务
user_service = UserService(Path(settings.data_file))


@router.post("", response_model=UserResponse, status_code=201, summary="创建用户")
def create_user(user: UserCreate):
    """
    创建新用户

    - **username**: 用户名（3-50字符）
    - **email**: 邮箱地址
    - **age**: 年龄（可选，0-150）
    - **city**: 城市（可选）
    """
    logger.info(f"API请求: 创建用户 - {user.username}")
    result = user_service.create_user(
        username=user.username,
        email=user.email,
        age=user.age,
        city=user.city
    )
    return result


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户信息")
def get_user(user_id: int):
    """
    根据用户ID获取用户信息

    - **user_id**: 用户ID
    """
    logger.info(f"API请求: 获取用户 - user_id={user_id}")
    user = user_service.get_user(user_id)
    return user


@router.get("", response_model=List[UserResponse], summary="获取用户列表")
def get_users(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量")
):
    """
    获取用户列表（分页）

    - **skip**: 跳过数量（默认0）
    - **limit**: 返回数量（默认10，最大100）
    """
    logger.info(f"API请求: 获取用户列表 - skip={skip}, limit={limit}")
    users = user_service.get_all_users(skip=skip, limit=limit)
    return users


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户信息")
def update_user(user_id: int, user: UserUpdate):
    """
    更新用户信息

    - **user_id**: 用户ID
    - **email**: 邮箱地址（可选）
    - **age**: 年龄（可选）
    - **city**: 城市（可选）
    """
    logger.info(f"API请求: 更新用户 - user_id={user_id}")
    result = user_service.update_user(
        user_id=user_id,
        email=user.email,
        age=user.age,
        city=user.city
    )
    return result


@router.delete("/{user_id}", status_code=204, summary="删除用户")
def delete_user(user_id: int):
    """
    删除用户

    - **user_id**: 用户ID
    """
    logger.info(f"API请求: 删除用户 - user_id={user_id}")
    user_service.delete_user(user_id)
    return None
