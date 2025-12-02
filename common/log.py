import logging
import os
import sys


def _reset_logger(log: logging.Logger) -> None:
    # 清理旧 handler，避免重复输出
    for handler in log.handlers[:]:
        try:
            handler.close()
        finally:
            log.removeHandler(handler)
    log.handlers.clear()
    log.propagate = False

    formatter = logging.Formatter(
        "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 日志文件路径可通过 LOG_PATH 覆盖，默认 run.log
    log_path = os.environ.get("LOG_PATH", "run.log")
    file_handle = logging.FileHandler(log_path, encoding="utf-8", delay=True)
    file_handle.setFormatter(formatter)

    console_handle = logging.StreamHandler(sys.stdout)
    console_handle.setFormatter(formatter)

    log.addHandler(file_handle)
    log.addHandler(console_handle)


def _get_logger() -> logging.Logger:
    log = logging.getLogger("log")
    _reset_logger(log)
    log.setLevel(logging.INFO)
    return log


# 日志句柄
logger = _get_logger()
