"""
配置模块：应用配置

使用Pydantic Settings管理配置
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""

    # 应用配置
    app_name: str = "用户管理API"
    app_version: str = "1.0.0"
    debug: bool = False

    # 服务器配置
    host: str = "127.0.0.1"
    port: int = 8000

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

    # 数据库配置
    data_file: str = "data/users.json"

    # API配置
    api_prefix: str = "/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()
