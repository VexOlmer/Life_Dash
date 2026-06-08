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
    country_author: str | None = None
    year: int | None = None
    total: int = 0
    isbn: str | None = None
    status: str = "finished"
    genres: str = ""        # Здесь храним полную строку: "fantasy (dark, epic), drama"
    series: str | None = None
    format: str | None = None
    language: str | None = None
    
    # Даты (храним как строки, так как формат в шаблоне специфичный)
    started: str | None = None
    finished: str | None = None

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
    def primary_genres_list(self) -> list:
        """Возвращает список только основных жанров: ['fantasy', 'drama']."""
        
        if not self.genres:
            return []
        
        # 1. Убираем всё в скобках
        clean = re.sub(r'\s*\([^)]*\)', '', self.genres)
        # 2. Разбиваем по запятой и чистим пробелы
        return [g.strip() for g in clean.split(',') if g.strip()]

    @property
    def detailed_genres_list(self) -> list:
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