"""Синхронизация заметок из базы знаний с БД."""

from pathlib import Path

from sqlmodel import Session

from src.core.config import settings
from src.core.exceptions import ValidationError
from src.core.logger import logger
from src.modules.books.models import Book
from src.modules.books.repository import BookRepository
from src.modules.books.transformer import BookTransformer

from .engine import ScannerEngine


def sync_books(session: Session) -> dict:
    """
        Синхронизация заметок из базы знаний с БД.
    
        Если обработка заметки завершилась ошибкой, она не будет добавлена в БД.
    """
    
    vault_path = Path(settings.OBSIDIAN_VAULT_PATH)
    books_folder = vault_path / settings.BOOKS_PATH
    
    scanner = ScannerEngine()
    repo = BookRepository(session, Book)
    
    files = scanner.scan_folder(books_folder)
    
    stats = {"total": len(files), "updated": 0, "errors": 0, "error_details": []}
    
    for f_path, mtime in files:
        rel_path = str(f_path.relative_to(vault_path))
        
        # Проверка mtime
        db_item = repo.get_by_path(rel_path)
        if db_item and db_item.last_modified >= mtime:
            continue
            
        try:
            book_obj = BookTransformer.transform(f_path, vault_path, mtime)
            repo.upsert(book_obj)
            stats["updated"] += 1
        except ValidationError as e:
            logger.warning(f"Ошибка валидации в файле {rel_path}: {e}")
            stats["errors"] += 1
            stats["error_details"].append({"file": rel_path, "error": str(e)})
        except Exception as e:
            logger.error(f"Критическая ошибка при обработке {rel_path}: {e}")
            stats["errors"] += 1

    return stats