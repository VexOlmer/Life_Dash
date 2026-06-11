"""Модуль обработки заметок о книгах."""

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
                file_path: Полный путь к Mardown файлу
                vault_path: Полный путь к базе знаний Obsidian
                mtime: Время последнего обновления
            
            Returns:
                Book: Готовая модель класса Book
        """
        
        logger.debug(f"Начало обработки: {file_path.name}")
        
        # Считывание верхней части файла в YAML формате
        try:
            post = frontmatter.load(file_path)
        except Exception as e:
            logger.error(f"Не удалось прочитать YAML в {file_path.name}")
            raise ValidationError(f"Ошибка структуры YAML: {e}") from e
        
        meta = post.metadata
        
        # Поиск обложки в файлах Obsidian
        book_filename = file_path.stem  # Название заметки без .md
        covers_dir = vault_path / settings.COVERS_BOOKS_PATH
        detected_cover = None
        
        if covers_dir.exists():
            for ext in IMAGE_EXTENSIONS:
                # Ищем файл типа: files/covers/books/Название_книги.jpg
                potential_file = covers_dir / f"{book_filename}{ext}"
                if potential_file.exists():
                    # Сохраняем относительный путь для БД
                    detected_cover = str(potential_file.relative_to(vault_path))
                    break

        log_entries = meta.get("read_log", [])
        if isinstance(log_entries, list):
            # Склеиваем записи через специальный разделитель ||
            read_log_str = " || ".join([str(e) for e in log_entries])
        else:
            read_log_str = str(log_entries) if log_entries else None

        # Извлекаем все данные из метадаты, валидация автоматическая
        return Book(
            title=meta.get("title", file_path.stem),
            title_orig=meta.get("title_orig"),
            author=meta.get("author"),
            country_author=meta.get("country_author"),
            year=meta.get("year"),
            total=meta.get("total"),
            isbn=meta.get("isbn"),
            status=meta.get("status", "finished"),
            genres=str(meta.get("genres")),
            series=meta.get("series"),
            format=meta.get("format"),
            language=meta.get("language"),
            good_reads=meta.get("good_reads"),
            
            read_log=read_log_str, 

            bg_color=str(meta.get("bg_color", "#ffffff")),
            text_color=str(meta.get("text_color", "#000000")),
            cover=detected_cover,
            
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
            file_path=str(file_path.relative_to(vault_path)),
            last_modified=mtime,
            created_at=str(meta.get("created", ""))
        )