"""业务逻辑：用户服务。

这个模块负责用户增删改查的核心规则。
路由层只处理 HTTP 请求和响应，真正的数据读写、用户名重复检查等业务逻辑放在这里。
这种拆分能让以后把 JSON 文件换成数据库时，路由层尽量少改。
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict


class UserService:
    """用本地 JSON 文件模拟一个最小用户数据服务。"""

    def __init__(self, data_file: Path):
        """初始化用户服务，并确保数据文件所在目录存在。

        学习阶段先用 JSON 文件存数据，不需要额外启动数据库。
        这样能把注意力放在 API 分层、校验和业务流程上。

        Args:
            data_file: 数据文件路径
        """
        self.data_file = data_file
        self.data_file.parent.mkdir(exist_ok=True)
        self._init_data()

    def _init_data(self):
        """初始化数据文件。

        如果第一次运行没有数据文件，就创建一个空用户列表和自增 ID。
        这样后续增删改查可以假设基础结构存在。
        """
        if not self.data_file.exists():
            self._save_data({"users": [], "next_id": 1})

    def _load_data(self) -> Dict:
        """从 JSON 文件加载当前用户数据。

        每次操作前重新读取文件，保证拿到的是最新数据。
        学习项目数据量小，这种方式简单直观。
        """
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_data(self, data: Dict):
        """把用户数据保存回 JSON 文件。

        `ensure_ascii=False` 保证中文城市名可读，方便直接打开文件检查。
        """
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_user(self, username: str, email: str, age: Optional[int] = None, city: Optional[str] = None) -> Dict:
        """创建用户，并保证用户名不重复。

        用户名重复会让后续查询和识别变得混乱，所以这里在服务层拦截。
        路由层会把这个业务错误转换成 HTTP 400。

        Args:
            username: 用户名
            email: 邮箱
            age: 年龄
            city: 城市

        Returns:
            创建的用户信息
        """
        data = self._load_data()

        # 用户名是这个 Demo 里的业务唯一标识，创建前必须先检查冲突。
        for user in data['users']:
            if user['username'] == username:
                raise ValueError(f"用户名 '{username}' 已存在")

        # user_id 和创建时间由服务端生成，避免客户端伪造关键字段。
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
        """按用户 ID 查找单个用户。

        找不到时返回 None，让路由层统一转换成 404。

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
        """分页获取用户列表。

        即使是学习项目也要练习分页意识。
        真实接口不能一次返回无限数据，否则容易拖慢接口或压垮前端。

        Args:
            skip: 跳过数量
            limit: 返回数量

        Returns:
            用户列表
        """
        data = self._load_data()
        return data['users'][skip:skip + limit]

    def update_user(self, user_id: int, email: Optional[str] = None, age: Optional[int] = None, city: Optional[str] = None) -> Optional[Dict]:
        """更新用户信息，只修改调用方明确传入的字段。

        `None` 表示这个字段不更新，避免没有传的字段把原值覆盖掉。

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
        """删除用户，并返回是否真的删除成功。

        返回布尔值可以让路由层区分“删除成功”和“用户不存在”，从而返回正确 HTTP 状态码。

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
