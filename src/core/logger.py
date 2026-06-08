"""Модуль настройки логирования."""

import sys
from pathlib import Path

from loguru import logger as logger


def setup_logger() -> None:
    """
        Конфигурирует Loguru для вывода в консоль и файл.

        Создает директорию logs, если она отсутствует. Настраивает ротацию
            и уровень фильтрации логов.
    """
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.remove()

    # 1. Вывод в консоль (красивый и лаконичный)
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO",
    )

    # 2. Общий лог (INFO и выше) — здесь будет вся история действий
    logger.add(
        log_dir / "app.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}",
        level="DEBUG",
        encoding="utf-8",
    )

    # 3. Лог ошибок (только ERROR и CRITICAL) — чтобы быстро найти проблемы
    logger.add(
        log_dir / "errors.log",
        rotation="5 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message} {exception}",
        level="ERROR",
        encoding="utf-8",
    )

setup_logger()