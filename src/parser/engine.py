"""Модуль сканирования файлов Obsidian."""

import os
from pathlib import Path

from src.core.logger import logger


class ScannerEngine:
    """Инструмент для поиска файлов в базе знаний."""

    @staticmethod
    def scan_folder(folder_path: Path, extension: str = ".md") -> list[tuple[Path, float]]:
        """
            Сканирует директорию и возвращает пути к файлам и дату изменения.

            Args:
                folder_path: Абсолютный путь к папке.
                extension: Расширение файлов (по умолчанию .md).

            Returns:
                list[tuple[Path, float]]: Список (Путь, Timestamp).
        """
        
        files_data: list[tuple[Path, float]] = []

        if not folder_path.exists():
            logger.error(f"Папка не найдена: {folder_path}")
            return files_data

        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith(extension):
                    path = Path(root) / file
                    try:
                        mtime = os.path.getmtime(path)
                        files_data.append((path, mtime))
                    except OSError as e:
                        logger.warning(f"Не удалось прочитать mtime файла {path}: {e}")
        
        return files_data