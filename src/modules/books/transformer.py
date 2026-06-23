"""Модуль обработки заметок об книгах."""

from pathlib import Path

import frontmatter

from src.core.config import settings
from src.core.exceptions import ValidationError
from src.core.logger import logger

from .models import Book

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


class BookTransformer:
    """Трансформер для обработки расширенного YAML книг."""
    
    @staticmethod
    def transform(file_path: Path, vault_path: Path, mtime: float) -> Book:
        """
            Превращает Markdown файл в объект Book с расчетом суммы рейтинга.

            Args:
                file_path: Полный путь к Mardown файлу.
                vault_path: Полный путь к базе знаний Obsidian.
                mtime: Время последнего обновления.
            
            Returns:
                Book: Готовая модель класса Book.
        """
        
        logger.debug(f"Начало обработки: {file_path.name}")
        
        try:
            post = frontmatter.load(file_path)
        except Exception as e:
            raise ValidationError(f"Ошибка структуры YAML: {e}") from e
        
        meta = post.metadata
        
        # --- 1. Проверка обязательных полей в шаблоне книги ---
        required_fields = [
            "title_orig", "author", "country_author", "year", "total",
            "status", "genres", "good_reads", "read_log", "bg_color", "text_color",
            "rating_characters", "rating_plot", "rating_size", "rating_prose",
            "rating_ending", "rating_depth", "rating_atmosphere", 
            "rating_rereadability", "rating_expected_real", "rating_recommend"
        ]
        missing = [f for f in required_fields if f not in meta or meta.get(f) is None]
        if missing:
            raise ValidationError(f"В заметке отсутствуют обязательные поля: {', '.join(missing)}")
        
        # --- 2. Поиск обложки (files/covers/books/Название_файла.ext) ---
        book_filename = file_path.stem
        covers_dir = vault_path / settings.COVERS_BOOKS_PATH
        detected_cover = None
        
        if covers_dir.exists():
            for ext in IMAGE_EXTENSIONS:
                potential_file = covers_dir / f"{book_filename}{ext}"
                if potential_file.exists():
                    detected_cover = str(potential_file.relative_to(vault_path))
                    break

        # --- 3. Обработка read_log (превращаем список из YAML в строку "||") ---
        log_entries = meta.get("read_log", [])
        if isinstance(log_entries, list):
            # Склеиваем записи через специальный разделитель ||
            read_log_str = " || ".join([str(e) for e in log_entries])
        else:
            read_log_str = str(log_entries) if log_entries else None

        # --- 4. Сборка модели ---
        return Book(
            title=meta.get("title", file_path.stem),
            title_orig=meta.get("title_orig"),
            
            author=meta.get("author"),
            country_author=meta.get("country_author"),
            year=meta.get("year"),
            total=meta.get("total"),
            
            status=meta.get("status", "finished"),
            genres=str(meta.get("genres")),
            series=meta.get("series"),
            
            # Рейтинг с сайта GoodReads
            good_reads=meta.get("good_reads"),
            
            # Логи сессий чтения
            read_log=read_log_str, 

            # Цвета и Обложка
            bg_color=str(meta.get("bg_color", "#ffffff")),
            text_color=str(meta.get("text_color", "#000000")),
            cover=detected_cover,
            
            # Рейтинги (10 параметров)
            rating_characters=meta.get("rating_characters"),
            rating_plot=meta.get("rating_plot"),
            rating_size=meta.get("rating_size"),
            rating_prose=meta.get("rating_prose"),
            rating_ending=meta.get("rating_ending"),
            rating_depth=meta.get("rating_depth"),
            rating_atmosphere=meta.get("rating_atmosphere"),
            rating_rereadability=meta.get("rating_rereadability"),
            rating_expected_real=meta.get("rating_expected_real"),
            rating_recommend=meta.get("rating_recommend"),
            
            # Находим относительный путь к файлу относительно всей базы
            file_path=file_path.relative_to(vault_path).as_posix(),
            last_modified=mtime,
            created_at=str(meta.get("created", ""))
        )