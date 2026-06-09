"""Оркестратор синхронизации книг."""

import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from src.core.config import settings
from src.core.logger import logger
from src.modules.books.repository import BookRepository
from src.modules.books.transformer import BookTransformer

from .engine import ScannerEngine


def sync_books(session: Session) -> dict[str, Any]:
    """
        Синхронизация заметок из базы знаний с БД.
    
        Если файл не менялся, пропускается, иначе файл парсится и обновляется информация в БД.
        Если обработка заметки завершилась ошибкой, она не будет добавлена в БД.
        
        Args:
            session: Текущая сессия
            
        Returns:
            dict[str, Any] - Словарь статистики статусов синхронизации файлов
    """
    
    start_time = time.time()
    vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
    books_folder = vault_path / settings.BOOKS_PATH
    
    logger.info(f"Начало синхронизации. Папка: {books_folder}")
    
    scanner = ScannerEngine()
    repo = BookRepository(session)
    files = scanner.scan_folder(books_folder)
    
    logger.info(f"Сканирование завершено. Найдено файлов: {len(files)}")
    
    stats: dict[str, Any] = {"total": len(files), "updated": 0, "errors": 0, "error_details": []}
    
    for f_path, mtime in files:
        rel_path = str(f_path.relative_to(vault_path))
    
        # 1. Попытка поиска (может упасть, если прошлая итерация не сделала rollback)
        try:
            db_item = repo.get_by_path(rel_path)
            if db_item and db_item.last_modified >= mtime:
                logger.debug(f"Пропуск (не менялся): {rel_path}")
                continue
        except Exception as e:
            logger.error(f"Ошибка доступа к БД при поиске {rel_path}: {e}")
            session.rollback() # Чиним сессию
            continue
            
        try:
            logger.info(f"Обработка файла: {rel_path}")
            book_obj = BookTransformer.transform(f_path, vault_path, mtime)
            
            repo.upsert(book_obj)
            logger.debug(book_obj.to_pretty_str)
            
            stats["updated"] += 1
            logger.success(f"Обновлено: {book_obj.title}")
            
        except PydanticValidationError as e:
            # Ошибки структуры (пропущенные поля, типы данных)
            error_msg = " | ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            logger.warning(f"Ошибка валидации в {rel_path}: {error_msg}")
            stats["errors"] += 1
            stats["error_details"].append({"file": rel_path, "error": error_msg})
            
        except IntegrityError as e:
            # Ошибки базы данных (NOT NULL, Unique и т.д.)
            session.rollback()
            error_msg = f"Ошибка базы данных (проверьте обязательные поля): {e.orig}"
            logger.error(f"Ошибка записи в БД {rel_path}: {error_msg}")
            stats["errors"] += 1
            stats["error_details"].append({"file": rel_path, "error": "Ошибка структуры БД (пропущены поля?)"}) 
            
        except Exception as e:
            session.rollback()
            logger.error(f"Непредвиденная ошибка в {rel_path}: {e}")
            stats["errors"] += 1

    duration = round(time.time() - start_time, 2)
    logger.info(f"Синхронизация окончена за {duration}с. Обновлено: {stats['updated']}, Ошибок: {stats['errors']}")
    return stats
