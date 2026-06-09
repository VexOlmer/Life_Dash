"""Модуль обработки заметок о книгах."""

import re
from pathlib import Path

import frontmatter

from src.core.exceptions import ValidationError
from src.core.logger import logger

from .models import Book


class BookTransformer:
    """Трансформер для обработки расширенного YAML книг."""
    
    @staticmethod
    def transform(file_path: Path, vault_path: Path, mtime: float) -> Book:
        """Превращает Markdown файл в объект Book с расчетом суммы рейтинга."""
        
        logger.debug(f"Начало обработки: {file_path.name}")
        
        # Считывание верхней части файла в YAML формате
        try:
            post = frontmatter.load(file_path)
        except Exception as e:
            logger.error(f"Не удалось прочитать YAML в {file_path.name}")
            raise ValidationError(f"Ошибка структуры YAML: {e}") from e
        
        meta = post.metadata
        rel_path = str(file_path.relative_to(vault_path))

        # 1. Проверка 10 параметров рейтинга
        rating_keys = [
            "rating_characters", "rating_plot", "rating_size",
            "rating_prose", "rating_ending", "rating_depth",
            "rating_atmosphere", "rating_rereadability",
            "rating_expected_real", "rating_recommend"
        ]
        
        total_score = 0.0
        ratings_data = {}
        for key in rating_keys:
            val = meta.get(key)
            # Проверяем, что значение есть и оно числовое (не None и не пустая строка)
            if val is None or val == "":
                logger.warning(f"Пропущен обязательный рейтинг: {key}")
                raise ValidationError(f"Пропущен обязательный рейтинг: {key}")
            try:
                numeric_val = float(val)
                ratings_data[key] = numeric_val
                total_score += numeric_val
            except ValueError as e:
                logger.warning(f"Рейтинг {key} должен быть числом")
                raise ValidationError(f"Рейтинг {key} должен быть числом") from e

        # 2. Проверка обязательных метаданных
        required_meta = {
            "author": "Автор",
            "country_author": "Страна автора",
            "total": "Количество страниц (total)",
            "year": "Год",
            "status": "Статус",
            "genres": "Жанры",
            "format": "Формат",
            "language": "Язык",
            "bg_color": "Цвет фона",
            "text_color": "Цвет текста"
        }

        for key, label in required_meta.items():
            if not meta.get(key):
                logger.warning(f"Поле '{label}' ({key}) не заполнено")
                raise ValidationError(f"Поле '{label}' ({key}) не заполнено")

        # 3. Валидация жанров и поджанров (от 1 до 3)
        raw_genres = str(meta.get("genres", ""))
        logger.debug(f"Полученная строка жанров - {raw_genres}")
        
        # 1. Регулярка для разделения по запятым, которые НЕ в скобках
        # Разделяет "fantasy (dark, epic), drama" на ["fantasy (dark, epic)", "drama"] игнорируя запятую внутри скобок поджанров
        genre_blocks = re.split(r',\s*(?![^()]*\))', raw_genres)
        genre_blocks = [g.strip() for g in genre_blocks if g.strip()]
        logger.debug(f"Разделенные жанры - {genre_blocks}")

        if not (1 <= len(genre_blocks) <= 3):
            logger.warning(f"Должно быть от 1 до 3 основных жанров (найдено: {len(genre_blocks)})")
            raise ValidationError(f"Должно быть от 1 до 3 основных жанров (найдено: {len(genre_blocks)})")

        for block in genre_blocks:
            # Ищем поджанры внутри скобок
            subgenres_match = re.search(r'\((.*?)\)', block)
            logger.debug(f"Поджанры - {subgenres_match}")
            if subgenres_match:
                subgenres_str = subgenres_match.group(1)
                sub_list = [s.strip() for s in subgenres_str.split(',') if s.strip()]
                if len(sub_list) > 2:
                    logger.warning(f"В жанре '{block}' более 2-х поджанров")
                    raise ValidationError(f"В жанре '{block}' более 2-х поджанров")

        # 4. Валидация HEX-цветов (должны начинаться с #)
        for color_key in ["bg_color", "text_color"]:
            color = str(meta.get(color_key, ""))
            if not color.startswith("#") or len(color) not in [4, 7]:
                logger.warning(f"Поле {color_key} должно быть в формате HEX (#ffffff)")
                raise ValidationError(f"Поле {color_key} должно быть в формате HEX (#ffffff)")

        logger.debug(f"Конец обработки: {file_path.name}")
        return Book(
            title=meta.get("title", file_path.stem),
            title_orig=meta.get("title_orig"),
            author=meta.get("author"),
            country_author=meta.get("country_author"),
            year=int(meta.get("year", 0)),
            total=int(meta.get("total", 0)),
            isbn=meta.get("isbn"),
            status=meta.get("status"),
            genres=", ".join(genre_blocks),
            series=meta.get("series"),
            format=meta.get("format"),
            language=meta.get("language"),
            started=meta.get("started"),
            finished=meta.get("finished"),
            bg_color=str(meta.get("bg_color")),
            text_color=str(meta.get("text_color")),
            total_rating=total_score,
            file_path=rel_path,
            last_modified=mtime,
            created_at=str(meta.get("created", "")),
            **ratings_data
        )