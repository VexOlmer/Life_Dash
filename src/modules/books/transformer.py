"""Модуль обработки заметок о книгах."""

from pathlib import Path

import frontmatter

from src.core.exceptions import ValidationError
from src.core.logger import logger

from .models import Book


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
            started=str(meta.get("started", "")) if meta.get("started") else None,
            finished=str(meta.get("finished", "")) if meta.get("finished") else None,
            bg_color=str(meta.get("bg_color", "#ffffff")),
            text_color=str(meta.get("text_color", "#000000")),
            
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