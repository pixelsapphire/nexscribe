import logging
from typing import Any


def debug(message: str, *args: Any) -> None: logging.debug(message, *args)

def info(message: str, *args: Any) -> None: logging.info(message, *args)

def warning(message: str, *args: Any) -> None: logging.warning(message, *args)

def error(message: str, *args: Any) -> None: logging.error(message, *args)

def critical(message: str, *args: Any) -> None: logging.critical(message, *args)

def exception(message: str, *args: Any) -> None: logging.exception(message, *args)

def log(level: int, message: str, *args: Any) -> None: logging.log(level, message, *args)
