"""核心模块：日志配置。

这个模块统一配置控制台日志和文件日志。
日志是生产排查的基础：没有日志，就很难知道请求进没进来、哪里失败、耗时多少。
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path


def setup_logger(
    name: str = "app",
    log_file: str = "logs/app.log",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> logging.Logger:
    """配置日志系统。

    同时输出到控制台和文件：控制台方便本地开发看，文件方便长期留存和问题追踪。
    文件处理器使用轮转，避免日志无限增长把磁盘写满。

    Args:
        name: 日志器名称
        log_file: 日志文件路径
        log_level: 日志级别
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量

    Returns:
        配置好的日志器
    """
    # 创建日志器并设置级别。级别越低记录越详细，但生产里日志太多也会增加成本。
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 避免重复配置导致同一条日志被打印多次。
    if logger.handlers:
        return logger

    # 日志格式里放文件名和行号，是为了出问题时能快速定位到代码位置。
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台日志用于开发和容器标准输出。
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件日志用于留存历史；轮转能防止单个日志文件无限变大。
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# 默认日志器供业务模块直接导入使用，避免每个模块重复配置。
logger = setup_logger()
