"""Оркестратор синхронизации книг."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlmodel import Session

from src.core.config import settings
from src.core.logger import logger
from src.modules.books.repository import BookRepository
from src.modules.books.transformer import BookTransformer
from src.modules.daily.repository import DailyRepository
from src.modules.daily.transformer import DailyTransformer
from src.modules.games.repository import GameRepository
from src.modules.games.transformer import GameTransformer
from src.web.router import stats_cache

from .engine import ScannerEngine


def _base_sync(
    session: Session, 
    folder_path: Path, 
    repository: BookRepository | DailyRepository | GameRepository, 
    transformer: BookTransformer | DailyTransformer | GameTransformer, 
    model_name_ru: str,
    force: bool = False,
    is_daily: bool = False
) -> dict[str, Any]:
    """
        Синхронизация модулей по данным из заметок базы знаний Obsidian.
    
        Если файл не менялся, пропускается, иначе файл парсится и обновляется информация в БД.
        Если обработка заметки завершилась ошибкой, она не будет добавлена в БД.
        
        Args:
            session: Текущая сессия.
            folder_path: Путь до папки с заметками.
            repository: Класс модуля для взаимодействия с БД.
            transformer: Класс модуля для обработки заметки.
            model_name_ru: Наименование модуля текущей обработки.
            force: Флаг принудительного обновления данных в БД.
            is_daily: Флаг обработки ежедневной заметки.
            
        Returns:
            dict[str, Any] - Словарь статистики статусов синхронизации файлов
    """
    
    start_time = time.time()
    vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
    
    logger.info(f"Начало синхронизации [{model_name_ru}]. Папка: {folder_path}")
    
    scanner = ScannerEngine()
    files = scanner.scan_folder(folder_path)
    
    # 1. Сверка путей и удаление лишних (то, что было в книгах/играх)
    db_paths = set(repository.get_all_paths())
    current_files_rel = {str(f[0].relative_to(vault_path)) for f in files}
    
    deleted_count = 0
    paths_to_delete = db_paths - current_files_rel
    for path in paths_to_delete:
        repository.delete_by_path(path)
        logger.info(f"Удалена запись из БД (файл удален в Obsidian): {path}")
        deleted_count += 1

    stats: dict[str, Any] = {
        "total": len(files),
        "updated": 0,
        "errors": 0,
        "deleted": deleted_count,
        "error_details": []
    }

    # 2. Основной цикл обработки
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    for f_path, mtime in files:
        rel_path = f_path.relative_to(vault_path).as_posix() 
        
        # Пропуск текущего дня для DailyNotes
        if is_daily and f_path.stem == today_str:
            continue

        try:
            # Проверка mtime
            db_item = repository.get_by_path(rel_path)
            if not force and db_item and db_item.last_modified >= mtime:
                continue

            logger.info(f"Обработка: {rel_path}")
            model_obj = transformer.transform(f_path, vault_path, mtime)
            repository.upsert(model_obj)
            
            stats["updated"] += 1

        except PydanticValidationError as e:
            error_msg = " | ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            stats["errors"] += 1
            stats["error_details"].append({"file": rel_path, "error": error_msg})
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка в {rel_path}: {e}")
            stats["errors"] += 1
            stats["error_details"].append({"file": rel_path, "error": str(e)})

    stats_cache.clear()
    logger.info(f"Синхронизация [{model_name_ru}] завершена за {round(time.time() - start_time, 2)}с.")
    return stats


def sync_books(session: Session, force: bool = False) -> dict[str, Any]:
    """Синхронизация заметок книг."""
    return _base_sync(
        session=session,
        folder_path=Path(settings.OBSIDIAN_VAULT_PATH) / settings.BOOKS_PATH,
        repository=BookRepository(session),
        transformer=BookTransformer,
        model_name_ru="Книги",
        force=force
    )

def sync_games(session: Session, force: bool = False) -> dict[str, Any]:
    """Синхронизация заметок игр."""
    return _base_sync(
        session=session,
        folder_path=Path(settings.OBSIDIAN_VAULT_PATH) / settings.GAMES_PATH,
        repository=GameRepository(session),
        transformer=GameTransformer,
        model_name_ru="Игры",
        force=force
    )

def sync_daily(session: Session, force: bool = False) -> dict[str, Any]:
    """Синхронизация ежедневных заметок."""
    return _base_sync(
        session=session,
        folder_path=Path(settings.OBSIDIAN_VAULT_PATH) / settings.DAILY_PATH,
        repository=DailyRepository(session),
        transformer=DailyTransformer,
        model_name_ru="Дневник",
        force=force,
        is_daily=True
    )