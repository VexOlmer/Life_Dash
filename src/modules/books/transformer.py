"""Модуль трансформации заметок о книгах."""

from pathlib import Path

import frontmatter

from src.core.exceptions import ValidationError

from .models import Book


class BookTransformer:
    """Трансформер для обработки расширенного YAML книг."""
    
    @staticmethod
    def transform(file_path: Path, vault_path: Path, mtime: float) -> Book:
        """Превращает Markdown файл в объект Book с расчетом суммы рейтинга."""
        
        post = frontmatter.load(file_path)
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
                raise ValidationError(f"Пропущен обязательный рейтинг: {key}")
            try:
                numeric_val = float(val)
                ratings_data[key] = numeric_val
                total_score += numeric_val
            except ValueError as e:
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
                raise ValidationError(f"Поле '{label}' ({key}) не заполнено")

        # 3. Валидация жанров (от 1 до 3)
        genres_raw = meta.get("genres", "")
        if isinstance(genres_raw, list):
            genre_list = [str(g).strip() for g in genres_raw if g]
        else:
            genre_list = [g.strip() for g in str(genres_raw).split(",") if g.strip()]
        
        if not (1 <= len(genre_list) <= 3):
            raise ValidationError(f"Должно быть от 1 до 3 жанров (сейчас: {len(genre_list)})")

        # 4. Валидация HEX-цветов (должны начинаться с #)
        for color_key in ["bg_color", "text_color"]:
            color = str(meta.get(color_key, ""))
            if not color.startswith("#") or len(color) not in [4, 7]:
                raise ValidationError(f"Поле {color_key} должно быть в формате HEX (#ffffff)")

        # Если все проверки прошли, создаем объект
        return Book(
            title=meta.get("title", file_path.stem),
            title_orig=meta.get("title_orig"),
            author=meta.get("author"),
            country_author=meta.get("country_author"),
            year=int(meta.get("year", 0)),
            total=int(meta.get("total", 0)),
            isbn=meta.get("isbn"),
            status=meta.get("status"),
            genres=", ".join(genre_list),
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