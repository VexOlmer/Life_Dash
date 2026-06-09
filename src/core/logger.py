"""Модуль настройки логирования."""

import sys
from datetime import datetime
from pathlib import Path

from loguru import logger as logger


def setup_logger() -> None:
    """
        Конфигурирует Loguru для вывода в консоль и уникальную папку запуска.

        Создает директорию logs/run_YYYY-MM-DD_HH-MM-SS/ для каждого нового запуска.
    """
    
    # 1. Генерируем уникальный ID запуска на основе текущего времени
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # 2. Формируем путь к папке этого конкретного запуска
    base_log_dir = Path("logs")
    current_run_dir = base_log_dir / f"run_{run_id}"
    
    current_run_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()

    # 3. Вывод в консоль (остается общим)
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO",
    )

    # 4. Лог текущего запуска (INFO и выше)
    logger.add(
        current_run_dir / "main.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message}",
        level="DEBUG",
        encoding="utf-8",
    )

    # 5. Лог ошибок текущего запуска (только ERROR и выше)
    logger.add(
        current_run_dir / "errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} - {message} {exception}",
        level="ERROR",
        encoding="utf-8",
    )

    logger.info(f"Сессия логирования инициализирована: {current_run_dir}")

setup_logger()