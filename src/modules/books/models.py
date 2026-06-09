"""Модели данных для модуля книг."""

import re

from sqlmodel import Field, SQLModel


class Book(SQLModel, table=True):
    """Модель книги на основе расширенного шаблона Obsidian."""

    id: int | None = Field(default=None, primary_key=True)

    # Основная информация (YAML)
    title: str
    title_orig: str | None = None
    author: str = "Unknown"
    country_author: str = "Unknown"
    year: int
    total: int
    isbn: str | None = None
    status: str = "finished"
    genres: str
    series: str | None = None
    format: str
    language: str
    
    # Даты начала и конца чтения
    started: str
    finished: str

    # Рейтинги (10 параметров)
    rating_characters: float = 0.0
    rating_plot: float = 0.0
    rating_size: float = 0.0
    rating_prose: float = 0.0
    rating_ending: float = 0.0
    rating_depth: float = 0.0
    rating_atmosphere: float = 0.0
    rating_rereadability: float = 0.0
    rating_expected_real: float = 0.0
    rating_recommend: float = 0.0
    
    # Итоговый рейтинг (сумма 10 параметров)
    total_rating: float = 0.0
    
    # Цвета фона и текста
    bg_color: str = Field(default="#ffffff")
    text_color: str = Field(default="#000000")

    # Служебные поля
    file_path: str = Field(unique=True, index=True)
    last_modified: float
    created_at: str | None = None  # Из поля created в YAML
    
    @property
    def primary_genres_list(self) -> list[str]:
        """Возвращает список только основных жанров: ['fantasy', 'drama']."""
        
        if not self.genres:
            return []
        
        # 1. Убираем всё в скобках
        clean = re.sub(r'\s*\([^)]*\)', '', self.genres)
        # 2. Разбиваем по запятой и чистим пробелы
        return [g.strip() for g in clean.split(',') if g.strip()]

    @property
    def detailed_genres_list(self) -> list[dict[str, str]]:
        """Возвращает список словарей: [{'name': 'fantasy', 'sub': 'dark, epic'}, ...]."""
        
        if not self.genres:
            return []
        
        results = []
        # Разделяем по запятым, которые НЕ находятся внутри скобок
        blocks = re.split(r',\s*(?![^()]*\))', self.genres)
        
        for block in blocks:
            # Извлекаем основной жанр
            name = re.sub(r'\s*\([^)]*\)', '', block).strip()
            # Извлекаем то, что в скобках
            sub = ""
            match = re.search(r'\((.*?)\)', block)
            if match:
                sub = match.group(1).strip()
            
            results.append({"name": name, "sub": sub})
        return results
    
    @property
    def to_pretty_str(self) -> str:
            """Возвращает идеально выровненную таблицу данных книги для логов."""
            
            # 1. Подготовка данных (исключаем лишние колонки)
            exclude_fields = {"id", "last_modified"}
            data = self.model_dump()
            
            display_rows = []
            max_key_width = 0
            max_val_width = 0

            for key, value in data.items():
                if key in exclude_fields:
                    continue
                
                display_key = key.replace("_", " ").capitalize()
                display_val = str(value) if value is not None else "-"
                
                display_rows.append((display_key, display_val))
                
                # Измеряем максимальную ширину для каждого столбца
                max_key_width = max(max_key_width, len(display_key))
                max_val_width = max(max_val_width, len(display_val))

            # 2. Определяем общую ширину контента
            # Заголовок тоже должен влезать
            title_line = f"BOOK DATA: {self.title}"
            content_width = max(max_key_width + max_val_width + 3, len(title_line))
            
            # 3. Собираем рамку
            # Используем f-строки ПРАВИЛЬНО (f"...")
            top =    f"┏{'━' * (content_width + 2)}┓"
            header = f"┃ {title_line:<{content_width}} ┃"
            sep =    f"┣{'━' * (content_width + 2)}┫"
            bottom = f"┗{'━' * (content_width + 2)}┛"

            lines = [f"\n{top}", header, sep]

            for k, v in display_rows:
                # Считаем сколько пробелов нужно добавить между ключом и значением
                # чтобы закрывающая черта ┃ всегда была на одном уровне
                spacing = content_width - len(k) - len(v) - 1
                lines.append(f"┃ {k} : {v}{' ' * spacing} ┃")

            lines.append(bottom)
            return "\n".join(lines)