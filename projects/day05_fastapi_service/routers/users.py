"""路由模块：用户路由。

这个模块只负责 HTTP 路由、参数校验和错误码转换。
具体业务规则交给 `UserService`，这样接口层和业务层不会混在一起。
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
from pathlib import Path

from models.user import UserCreate, UserUpdate, UserResponse
from services.user_service import UserService

# 创建路由器。prefix 统一给所有用户接口加 `/users` 前缀，tags 用于自动文档分组。
router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# 初始化用户服务。学习阶段用 JSON 文件模拟数据库，后续可以替换成真正的数据存储。
user_service = UserService(Path("data/users.json"))


@router.post("", response_model=UserResponse, status_code=201, summary="创建用户")
def create_user(user: UserCreate):
    """创建新用户。

    请求体先经过 `UserCreate` 校验，再交给服务层处理业务规则。
    如果用户名重复，服务层抛出 ValueError，这里转换成 400。

    - **username**: 用户名（3-50字符）
    - **email**: 邮箱地址
    - **age**: 年龄（可选，0-150）
    - **city**: 城市（可选）
    """
    try:
        result = user_service.create_user(
            username=user.username,
            email=user.email,
            age=user.age,
            city=user.city
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户信息")
def get_user(user_id: int):
    """根据用户 ID 获取用户信息。

    找不到用户时返回 404，比返回空对象更清楚，调用方能明确知道资源不存在。

    - **user_id**: 用户ID
    """
    user = user_service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return user


@router.get("", response_model=List[UserResponse], summary="获取用户列表")
def get_users(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量")
):
    """获取用户列表，并通过 skip/limit 做分页。

    分页参数由 FastAPI 自动校验，避免调用方传负数或一次请求过多数据。

    - **skip**: 跳过数量（默认0）
    - **limit**: 返回数量（默认10，最大100）
    """
    users = user_service.get_all_users(skip=skip, limit=limit)
    return users


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户信息")
def update_user(user_id: int, user: UserUpdate):
    """更新用户信息。

    更新接口只改请求体里传入的字段，没传的字段保持原值。
    这样前端可以只提交用户想改的部分。

    - **user_id**: 用户ID
    - **email**: 邮箱地址（可选）
    - **age**: 年龄（可选）
    - **city**: 城市（可选）
    """
    result = user_service.update_user(
        user_id=user_id,
        email=user.email,
        age=user.age,
        city=user.city
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return result


@router.delete("/{user_id}", status_code=204, summary="删除用户")
def delete_user(user_id: int):
    """删除用户。

    删除成功返回 204，表示请求成功但不需要返回正文。
    如果用户不存在，返回 404，避免调用方误以为删除成功。

    - **user_id**: 用户ID
    """
    success = user_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return None
