"""
核心模块：日志配置

配置应用日志系统
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
    """
    配置日志系统

    Args:
        name: 日志器名称
        log_file: 日志文件路径
        log_level: 日志级别
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量

    Returns:
        配置好的日志器
    """
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 如果已经有处理器，说明已经配置过，直接返回
    if logger.handlers:
        return logger

    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（带轮转）
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


# 创建默认日志器
logger = setup_logger()
