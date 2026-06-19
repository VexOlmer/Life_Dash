"""Оркестратор синхронизации книг."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
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


def sync_books(session: Session, force: bool = False) -> dict[str, Any]:
    """
        Синхронизация книжных заметок из базы знаний с БД.
    
        Если файл не менялся, пропускается, иначе файл парсится и обновляется информация в БД.
        Если обработка заметки завершилась ошибкой, она не будет добавлена в БД.
        
        Args:
            session: Текущая сессия.
            force: Флаг принудительного обновления данных в БД.
            
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
    
    # --- Сверка путей к файлам в БД с реальными файлами в базе знаний ---
    db_paths = set(repo.get_all_paths())
    current_files_rel = {str(f[0].relative_to(vault_path)) for f in files}
    
    deleted_count = 0
    paths_to_delete = db_paths - current_files_rel
    logger.info(f"Кол-во файлов в БД, которых нет в системе - {len(paths_to_delete)}")
    for path in paths_to_delete:
        repo.delete_by_path(path)
        logger.info(f"Удалена запись (файл не найден): {path}")
        deleted_count += 1
    
    stats: dict[str, Any] = {
        "total": len(files),
        "updated": 0,
        "errors": 0,
        "deleted": deleted_count,
        "error_details": []
    }
    
    for f_path, mtime in files:
        rel_path = str(f_path.relative_to(vault_path))
    
        # 1. Попытка поиска (может упасть, если прошлая итерация не сделала rollback)
        try:
            db_item = repo.get_by_path(rel_path)
            if not force and db_item and db_item.last_modified >= mtime:
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

    # Сбрасываем кэш статистики после успешной синхронизации
    stats_cache.clear()
    
    logger.info(f"Синхронизация окончена за {round(time.time() - start_time, 2)}с. Обновлено: {stats['updated']}, Ошибок: {stats['errors']}")
    return stats


def sync_games(session: Session, force: bool = False) -> dict[str, Any]:
    """
        Синхронизация игровых заметок из базы знаний с БД.
    
        Если файл не менялся, пропускается, иначе файл парсится и обновляется информация в БД.
        Если обработка заметки завершилась ошибкой, она не будет добавлена в БД.
        
        Args:
            session: Текущая сессия.
            force: Флаг принудительного обновления данных в БД.
            
        Returns:
            dict[str, Any] - Словарь статистики статусов синхронизации файлов
    """
    
    start_time = time.time()
    vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
    games_folder = vault_path / settings.GAMES_PATH
    
    logger.info(f"Начало синхронизации игр. Папка: {games_folder}")
    
    scanner = ScannerEngine()
    repo = GameRepository(session)
    files = scanner.scan_folder(games_folder)
    
    logger.info(f"Сканирование завершено. Найдено файлов: {len(files)}")
    
    # --- Сверка путей к файлам в БД с реальными файлами в базе знаний ---
    db_paths = set(repo.get_all_paths())
    current_files_rel = {str(f[0].relative_to(vault_path)) for f in files}
    
    deleted_count = 0
    paths_to_delete = db_paths - current_files_rel
    logger.info(f"Кол-во файлов в БД, которых нет в системе - {len(paths_to_delete)}")
    for path in paths_to_delete:
        repo.delete_by_path(path)
        logger.info(f"Удалена запись (файл не найден): {path}")
        deleted_count += 1
    
    stats: dict[str, Any] = {
        "total": len(files),
        "updated": 0,
        "errors": 0,
        "deleted": deleted_count,
        "error_details": []
    }
    
    for f_path, mtime in files:
        rel_path = str(f_path.relative_to(vault_path))
        
        # 1. Попытка поиска (может упасть, если прошлая итерация не сделала rollback)
        try:
            db_item = repo.get_by_path(rel_path)
            if not force and db_item and db_item.last_modified >= mtime:
                logger.debug(f"Пропуск (не менялся): {rel_path}")
                continue
        except Exception as e:
            logger.error(f"Ошибка доступа к БД при поиске {rel_path}: {e}")
            session.rollback() # Чиним сессию
            continue
            
        try:
            logger.info(f"Обработка файла: {rel_path}")
            game_obj = GameTransformer.transform(f_path, vault_path, mtime)
            
            repo.upsert(game_obj)
            logger.debug(game_obj.to_pretty_str)
            
            stats["updated"] += 1
            logger.success(f"Обновлена игра: {game_obj.title}")
        
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
            stats["error_details"].append({"file": rel_path, "error": str(e)})

    # Сбрасываем кэш статистики после успешной синхронизации
    stats_cache.clear()
    
    logger.info(f"Синхронизация окончена за {round(time.time() - start_time, 2)}с. Обновлено: {stats['updated']}, Ошибок: {stats['errors']}")
    return stats

def sync_daily(session: Session, force: bool = False) -> dict[str, Any]:
    """
        Синхронизация ежедневных заметок из базы знаний с БД.
    
        Если файл не менялся, пропускается, иначе файл парсится и обновляется информация в БД.
        Если обработка заметки завершилась ошибкой, она не будет добавлена в БД.
        
        Args:
            session: Текущая сессия.
            force: Флаг принудительного обновления данных в БД.
            
        Returns:
            dict[str, Any] - Словарь статистики статусов синхронизации файлов
    """
    
    start_time = time.time()
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
    daily_folder = vault_path / settings.DAILY_PATH
    
    logger.info(f"Начало синхронизации игр. Папка: {daily_folder}")
    
    scanner = ScannerEngine()
    repo = DailyRepository(session)
    files = scanner.scan_folder(daily_folder)
    
    logger.info(f"Сканирование завершено. Найдено файлов: {len(files)}")
    
    stats: dict[str, Any] = {
        "total": len(files),
        "updated": 0,
        "errors": 0,
        "deleted": 0,
        "error_details": []
    }

    for f_path, mtime in files:
        rel_path = str(f_path.relative_to(vault_path))
        
        if f_path.stem == today_str:
            logger.debug(f"Пропуск текущего дня: {f_path.stem}")
            continue
        
        # 1. Попытка поиска (может упасть, если прошлая итерация не сделала rollback)
        try:
            db_item = repo.get_by_path(rel_path)
            if not force and db_item and db_item.last_modified >= mtime:
                #logger.debug(f"Пропуск (не менялся): {rel_path}")
                continue
        except Exception as e:
            logger.error(f"Ошибка доступа к БД при поиске {rel_path}: {e}")
            session.rollback() # Чиним сессию
            continue
        
        try:
            logger.info(f"Обработка файла: {rel_path}")
            note_obj, logs_list = DailyTransformer.transform(f_path, vault_path, mtime)
            repo.upsert_daily(note_obj, logs_list)
            
            stats["updated"] += 1
            logger.success(f"Обновлена ежедневная заметка: {note_obj.date}")
            
        except PydanticValidationError as e:
            # Ошибки структуры (пропущенные поля, типы данных)
            error_msg = " | ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            logger.warning(f"Ошибка валидации ежедневной заметки - {rel_path}: {error_msg}")
            stats["errors"] += 1
            stats["error_details"].append({"file": rel_path, "error": error_msg})
            
        except IntegrityError as e:
            # Ошибки базы данных (NOT NULL, Unique и т.д.)
            session.rollback()
            error_msg = f"Ошибка базы данных (проверьте обязательные поля): {e.orig}"
            logger.error(f"Ошибка записи ежедневной заметки в БД {rel_path}: {error_msg}")
            stats["errors"] += 1
            stats["error_details"].append({"file": rel_path, "error": "Ошибка структуры БД (пропущены поля?)"})
            
        except Exception as e:
            session.rollback()
            logger.error(f"Непредвиденная ошибка обработки ежедневной заметки - {rel_path}: {e}")
            stats["errors"] += 1
            stats["error_details"].append({"file": rel_path, "error": str(e)})
    
    logger.info(f"Синхронизация окончена за {round(time.time() - start_time, 2)}с. Обновлено: {stats['updated']}, Ошибок: {stats['errors']}")
    return stats