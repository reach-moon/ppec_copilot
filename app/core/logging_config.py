# app/core/logging_config.py
import logging
from logging.config import dictConfig
import sys
import json
from datetime import datetime
import os

from config.settings import settings

# 确保日志目录存在
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)


class JsonFormatter(logging.Formatter):
    """
    自定义JSON格式化器，用于生产环境日志
    """
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage()
        }
        
        # 添加异常信息（如果有的话）
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


def setup_logging():
    """
    配置应用的日志记录器
    根据环境自动选择合适的日志格式
    """
    # 确保日志目录存在
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    if settings.APP_ENV.lower() == "production":
        # 生产环境使用JSON格式日志
        log_format = "json"
        formatter_config = {
            "()": JsonFormatter,
        }
        default_level = "INFO"  # 生产环境默认使用INFO级别
    else:
        # 开发环境使用人类可读格式
        log_format = "default"
        formatter_config = {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
        }
        default_level = "DEBUG"  # 开发环境使用DEBUG级别

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": formatter_config,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": log_format,
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": log_format,
                "filename": os.path.join(log_dir, "app.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            # 配置根 logger
            "": {
                "handlers": ["console", "file"],
                "level": settings.LOG_LEVEL.upper() if settings.LOG_LEVEL else default_level,
                "propagate": True,
            },
            # 为特定库设置不同的日志级别，减少噪音
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "httpx": {
                "handlers": ["console", "file"],
                "level": "WARNING",  # 避免记录所有 HTTP 请求的 DEBUG 日志
                "propagate": False,
            },
            "openai": {
                "handlers": ["console", "file"],
                "level": "WARNING",  # 减少第三方库的日志噪音
                "propagate": False,
            },
            "urllib3": {
                "handlers": ["console", "file"],
                "level": "WARNING",  # 减少第三方库的日志噪音
                "propagate": False,
            }
        },
    }
    dictConfig(logging_config)


# 在模块加载时获取一个 logger 实例，方便在任何地方使用
# from app.core.logging_config import logger
logger = logging.getLogger(settings.PROJECT_NAME)