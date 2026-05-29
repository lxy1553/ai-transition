"""Week 6 NL2SQL 服务配置。

配置层把路径、环境、返回行数等变量从业务代码里拆出来。
生产环境里这些值通常来自环境变量、配置中心或密钥系统；本地学习阶段先用
`.env.example` 说明可配置项，并提供稳定默认值。
"""

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    """服务运行配置。

    这里保留 `demo_result_path` 和 `audit_db_path`，是为了让服务层不写死文件位置。
    后续替换成真实数据库或对象存储时，只需要改配置和存储适配层。
    """

    app_name: str = "Week 6 NL2SQL Service"
    app_env: str = "dev"
    version: str = "0.1.0"
    demo_result_path: Path = (
        ROOT_DIR
        / "projects/day35_nl2sql_assistant/output/nl2sql_assistant_demo_results.json"
    )
    audit_db_path: Path = PROJECT_DIR / "output/audit.sqlite"
    max_question_length: int = 300
    expose_sql: bool = True


def load_settings() -> Settings:
    """从环境变量加载配置，并提供本地默认值。

    不直接在模块顶层读取环境变量，是为了测试时能替换配置。
    """

    return Settings(
        app_name=os.getenv("APP_NAME", "Week 6 NL2SQL Service"),
        app_env=os.getenv("APP_ENV", "dev"),
        version=os.getenv("APP_VERSION", "0.1.0"),
        demo_result_path=Path(
            os.getenv(
                "NL2SQL_DEMO_RESULT_PATH",
                str(Settings.demo_result_path),
            )
        ),
        audit_db_path=Path(os.getenv("NL2SQL_AUDIT_DB_PATH", str(Settings.audit_db_path))),
        max_question_length=int(os.getenv("MAX_QUESTION_LENGTH", "300")),
        expose_sql=os.getenv("EXPOSE_SQL", "true").lower() == "true",
    )

