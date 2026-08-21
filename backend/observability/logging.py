"""结构化应用日志模块
提供JSON格式的日志格式化器、日志配置工具和便捷的日志事件函数。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """JSON格式的日志格式化器。
    将日志记录格式化为JSON字符串，包含时间戳、级别、日志器名称、消息。
    如果日志记录包含task_id、trace_id等上下文字段，也会被包含在输出中。
    """

    def format(self, record: logging.LogRecord) -> str:
        """将日志记录格式化为JSON字符串。
        参数:
            record: Python日志记录对象
        返回:
            str: JSON格式的日志字符串
        """
        # 构建基础字段
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 提取可能的上下文字段（task_id、trace_id等）
        for key in ("task_id", "trace_id", "attack_case_id", "event_type", "agent", "tool_name"):
            value = getattr(record, key, None)
            # 只有非None的值才加入输出
            if value is not None:
                payload[key] = value
        # 如果存在异常信息，则序列化异常栈
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int | str = logging.INFO) -> None:
    """配置全局日志系统。
    如果根日志器已有处理器，则更新其格式化器；否则创建新的StreamHandler。
    参数:
        level: 日志级别，默认INFO
    """
    root = logging.getLogger()
    # 如果根日志器已有处理器，更新现有处理器
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(JsonLogFormatter())
        root.setLevel(level)
        return

    # 创建新的控制台输出处理器
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器，同时确保日志系统已配置。
    参数:
        name: 日志器名称（通常使用__name__）
    返回:
        logging.Logger: 配置好的日志器实例
    """
    configure_logging()
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    """记录一条结构化日志事件。
    参数:
        logger: 日志器实例
        level: 日志级别
        message: 日志消息
        **fields: 额外的上下文字段（如task_id、trace_id等），None值会被过滤
    """
    # 过滤掉None值的字段，通过extra字典传递给日志格式化器
    logger.log(level, message, extra={key: value for key, value in fields.items() if value is not None})