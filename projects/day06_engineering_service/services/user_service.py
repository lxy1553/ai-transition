"""业务逻辑：用户服务。

这个模块在 Day 5 的用户服务基础上加入日志和自定义异常。
它负责用户数据读写和业务规则，路由层只负责 HTTP 参数和响应。
这种拆分让业务逻辑更容易测试，也方便以后把 JSON 文件换成数据库。
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from core.logger import logger
from core.exceptions import NotFoundException, ConflictException, InternalServerException


class UserService:
    """用 JSON 文件模拟用户数据存储，并提供业务级增删改查。"""

    def __init__(self, data_file: Path):
        """初始化用户服务。

        服务启动时确保数据目录和基础文件存在。
        初始化日志能帮助确认服务实际使用的是哪个数据文件。

        Args:
            data_file: 数据文件路径
        """
        self.data_file = data_file
        self.data_file.parent.mkdir(exist_ok=True)
        self._init_data()
        logger.info(f"用户服务初始化完成，数据文件: {data_file}")

    def _init_data(self):
        """初始化数据文件。

        第一次运行没有数据文件时，创建空用户列表和自增 ID。
        这样后续代码不用每次都判断基础结构是否存在。
        """
        if not self.data_file.exists():
            self._save_data({"users": [], "next_id": 1})
            logger.info("创建新的数据文件")

    def _load_data(self) -> Dict:
        """加载用户数据。

        读文件失败属于服务端问题，不应该让底层异常直接暴露给接口调用方，
        所以这里记录日志后抛出统一的 InternalServerException。
        """
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            raise InternalServerException("数据加载失败")

    def _save_data(self, data: Dict):
        """保存用户数据。

        写文件失败会影响所有增删改操作，所以这里统一记录错误并抛业务异常。
        """
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            raise InternalServerException("数据保存失败")

    def create_user(self, username: str, email: str, age: Optional[int] = None, city: Optional[str] = None) -> Dict:
        """创建用户，并处理用户名冲突。

        用户名重复是业务冲突，不是系统崩溃。
        因此这里抛 ConflictException，入口层会返回稳定的 409 响应。

        Args:
            username: 用户名
            email: 邮箱
            age: 年龄
            city: 城市

        Returns:
            创建的用户信息
        """
        logger.info(f"创建用户: username={username}, email={email}")

        data = self._load_data()

        # 用户名重复会导致后续身份识别混乱，所以创建前必须先检查。
        for user in data['users']:
            if user['username'] == username:
                logger.warning(f"用户名已存在: {username}")
                raise ConflictException(f"用户名 '{username}' 已存在")

        # 关键字段由服务端生成，避免客户端伪造 ID 或创建时间。
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

        logger.info(f"用户创建成功: user_id={user['user_id']}, username={username}")
        return user

    def get_user(self, user_id: int) -> Dict:
        """按 ID 获取用户。

        找不到用户时抛 NotFoundException，由全局异常处理器转换成 404。

        Args:
            user_id: 用户ID

        Returns:
            用户信息
        """
        logger.debug(f"查询用户: user_id={user_id}")

        data = self._load_data()
        for user in data['users']:
            if user['user_id'] == user_id:
                logger.debug(f"用户查询成功: user_id={user_id}")
                return user

        logger.warning(f"用户不存在: user_id={user_id}")
        raise NotFoundException(f"用户 {user_id} 不存在")

    def get_all_users(self, skip: int = 0, limit: int = 10) -> List[Dict]:
        """分页获取用户列表。

        分页是接口工程里的基本保护，避免一次返回过多数据拖慢服务。

        Args:
            skip: 跳过数量
            limit: 返回数量

        Returns:
            用户列表
        """
        logger.debug(f"查询用户列表: skip={skip}, limit={limit}")

        data = self._load_data()
        users = data['users'][skip:skip + limit]

        logger.debug(f"用户列表查询成功: 返回{len(users)}条记录")
        return users

    def update_user(self, user_id: int, email: Optional[str] = None, age: Optional[int] = None, city: Optional[str] = None) -> Dict:
        """更新用户信息。

        只更新非 None 字段，避免没传的字段被误清空。
        更新失败时抛 404，让调用方明确知道用户不存在。

        Args:
            user_id: 用户ID
            email: 邮箱
            age: 年龄
            city: 城市

        Returns:
            更新后的用户信息
        """
        logger.info(f"更新用户: user_id={user_id}")

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
                logger.info(f"用户更新成功: user_id={user_id}")
                return user

        logger.warning(f"用户不存在: user_id={user_id}")
        raise NotFoundException(f"用户 {user_id} 不存在")

    def delete_user(self, user_id: int) -> bool:
        """删除用户。

        删除前后对比数量，用来判断是否真的删掉了目标用户。
        如果数量没变，说明用户不存在，应该返回 404。

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        logger.info(f"删除用户: user_id={user_id}")

        data = self._load_data()
        original_count = len(data['users'])

        data['users'] = [user for user in data['users'] if user['user_id'] != user_id]

        if len(data['users']) < original_count:
            self._save_data(data)
            logger.info(f"用户删除成功: user_id={user_id}")
            return True

        logger.warning(f"用户不存在: user_id={user_id}")
        raise NotFoundException(f"用户 {user_id} 不存在")
