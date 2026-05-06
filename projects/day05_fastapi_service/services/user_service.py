"""
业务逻辑：用户服务

处理用户相关的业务逻辑
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict


class UserService:
    """用户服务类"""

    def __init__(self, data_file: Path):
        """
        初始化用户服务

        Args:
            data_file: 数据文件路径
        """
        self.data_file = data_file
        self.data_file.parent.mkdir(exist_ok=True)
        self._init_data()

    def _init_data(self):
        """初始化数据文件"""
        if not self.data_file.exists():
            self._save_data({"users": [], "next_id": 1})

    def _load_data(self) -> Dict:
        """加载数据"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_data(self, data: Dict):
        """保存数据"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_user(self, username: str, email: str, age: Optional[int] = None, city: Optional[str] = None) -> Dict:
        """
        创建用户

        Args:
            username: 用户名
            email: 邮箱
            age: 年龄
            city: 城市

        Returns:
            创建的用户信息
        """
        data = self._load_data()

        # 检查用户名是否已存在
        for user in data['users']:
            if user['username'] == username:
                raise ValueError(f"用户名 '{username}' 已存在")

        # 创建新用户
        user = {
            'user_id': data['next_id'],
            'username': username,
            'email': email,
            'age': age,
            'city': city,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        data['users'].append(user)
        data['next_id'] += 1
        self._save_data(data)

        return user

    def get_user(self, user_id: int) -> Optional[Dict]:
        """
        获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            用户信息，不存在返回None
        """
        data = self._load_data()
        for user in data['users']:
            if user['user_id'] == user_id:
                return user
        return None

    def get_all_users(self, skip: int = 0, limit: int = 10) -> List[Dict]:
        """
        获取所有用户

        Args:
            skip: 跳过数量
            limit: 返回数量

        Returns:
            用户列表
        """
        data = self._load_data()
        return data['users'][skip:skip + limit]

    def update_user(self, user_id: int, email: Optional[str] = None, age: Optional[int] = None, city: Optional[str] = None) -> Optional[Dict]:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            email: 邮箱
            age: 年龄
            city: 城市

        Returns:
            更新后的用户信息，不存在返回None
        """
        data = self._load_data()

        for user in data['users']:
            if user['user_id'] == user_id:
                if email is not None:
                    user['email'] = email
                if age is not None:
                    user['age'] = age
                if city is not None:
                    user['city'] = city

                self._save_data(data)
                return user

        return None

    def delete_user(self, user_id: int) -> bool:
        """
        删除用户

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        data = self._load_data()
        original_count = len(data['users'])

        data['users'] = [user for user in data['users'] if user['user_id'] != user_id]

        if len(data['users']) < original_count:
            self._save_data(data)
            return True

        return False
