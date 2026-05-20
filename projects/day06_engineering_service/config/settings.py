"""配置模块：应用配置。

这个模块把端口、日志、数据文件、API 前缀等配置从业务代码里拆出来。
真实服务需要开发、测试、生产多套环境，如果配置写死在代码里，每次部署都要改代码，风险很高。
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置类。

    Pydantic Settings 会从环境变量或 `.env` 文件读取配置。
    这样同一份代码可以在不同环境使用不同参数。
    """

    # 应用配置说明服务身份，日志和接口文档里都会用到这些信息。
    app_name: str = "用户管理API"
    app_version: str = "1.0.0"
    debug: bool = False

    # 服务器配置决定服务监听在哪个地址和端口。
    host: str = "127.0.0.1"
    port: int = 8000

    # 日志配置决定记录多少信息、写到哪里，以及单个日志文件多大后轮转。
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

    # 数据文件配置让存储位置可调整，避免路径写死在 service 代码里。
    data_file: str = "data/users.json"

    # API 前缀用于接口版本管理，后续升级接口时可以保留旧版本。
    api_prefix: str = "/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例。其他模块直接导入 settings，避免重复读取环境变量。
settings = Settings()
