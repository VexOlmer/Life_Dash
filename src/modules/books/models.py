"""Модели данных для модуля книг."""

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
    genres: str = ""
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