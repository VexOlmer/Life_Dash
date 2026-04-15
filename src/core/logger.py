"""Модуль настройки логирования."""

import sys
from pathlib import Path

from loguru import logger


def setup_logger() -> None:
    """
        Конфигурирует Loguru для вывода в консоль и файл.

        Создает директорию logs, если она отсутствует. Настраивает ротацию
            и уровень фильтрации логов.
    """
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.remove()

    # Красивый цветной вывод в консоль
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{message}</cyan>",
        level="INFO",
    )

    # Запись критических ошибок в файл (с ротацией каждые 10МБ)
    logger.add(
        log_dir / "app.log",
        rotation="10 MB",
        retention="10 days",
        level="ERROR",
        encoding="utf-8",
        compression="zip",
    )


setup_logger()