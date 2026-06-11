"""Модели данных для модуля книг."""

import re
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel

from src.common.utils import translate
from src.core.logger import logger


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
    good_reads: int | None = Field(default=None)
    
    # Формат в БД: "Дата-Дата | Стр | Коммент || Дата-Дата | Стр | Коммент"
    read_log: str | None = Field(default=None)
    
    # Рейтинги (10 параметров)
    rating_characters: float
    rating_plot: float
    rating_size: float
    rating_prose: float
    rating_ending: float
    rating_depth: float
    rating_atmosphere: float
    rating_rereadability: float
    rating_expected_real: float
    rating_recommend: float
    
    # Итоговый рейтинг (сумма 10 параметров)
    total_rating: float = Field(default=0.0)
    
    # Цвета фона и текста
    bg_color: str = Field(default="#ffffff")
    text_color: str = Field(default="#000000")
    
    # Путь к файлу обложки
    cover: str | None = Field(default=None)

    # Служебные поля
    file_path: str = Field(unique=True, index=True)
    last_modified: float
    created_at: str
    
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True
    )  # type: ignore
    
    # --- ВАЛИДАТОРЫ ---

    @field_validator("bg_color", "text_color", mode="before")
    @classmethod
    def validate_colors(cls, v: str) -> str:
        """Валидация корректности цветов."""
        if not v.startswith("#") or len(v) not in [4, 7]:
            raise ValueError("Цвет должен быть HEX-формата (#fff или #ffffff)")
        return v

    @field_validator(
        "rating_characters", "rating_plot", "rating_size", "rating_prose",
        "rating_ending", "rating_depth", "rating_atmosphere", 
        "rating_rereadability", "rating_expected_real", "rating_recommend",
        mode="before"
    )
    @classmethod
    def validate_ratings(cls, v: float) -> float:
        """Валидация рейтинговых параметров."""
        if not (0 <= v <= 10):
            raise ValueError("Рейтинг должен быть в диапазоне от 0 до 10")
        return v

    @field_validator("genres", mode="before")
    @classmethod
    def validate_genres(cls, v: str) -> str:
        """Валидация жанров и поджанров."""
        if not v.strip():
            raise ValueError("Список жанров не может быть пустым")
        
        # Получение основных жанров минуя поджанры
        genre_blocks = re.split(r',\s*(?![^()]*\))', v)
        genre_blocks = [g.strip() for g in genre_blocks if g.strip()]

        if not (1 <= len(genre_blocks) <= 3):
            raise ValueError(f"Должно быть от 1 до 3 основных жанров (найдено: {len(genre_blocks)})")

        for block in genre_blocks:
            # Получение поджанров, находящихся в скобках
            subgenres_match = re.search(r'\((.*?)\)', block)
            if subgenres_match:
                sub_list = [s.strip() for s in subgenres_match.group(1).split(',') if s.strip()]
                if len(sub_list) > 2:
                    raise ValueError(f"В жанре '{block}' не может быть более 2-х поджанров")
        return v

    # --- СВОЙСТВА ДЛЯ ЛОГОВ И ВЕБА ---

    @property
    def primary_genres_list(self) -> list[str]:
        """Получение основных жанров."""
        if not self.genres:
            return []
        
        clean = re.sub(r'\s*\([^)]*\)', '', self.genres)
        return [g.strip() for g in clean.split(',') if g.strip()]

    @property
    def detailed_genres_list(self) -> list[dict[str, str]]:
        """Получение словаря жанров и его поджанров."""
        if not self.genres:
            return []
        
        results = []
        blocks = re.split(r',\s*(?![^()]*\))', self.genres)
        for block in blocks:
            name = re.sub(r'\s*\([^)]*\)', '', block).strip()
            sub = ""
            match = re.search(r'\((.*?)\)', block)
            
            if match:
                sub = match.group(1).strip()
            results.append({"name": name, "sub": sub})
        return results
    
    @property
    def to_pretty_str(self) -> str:
        """Возвращает идеально выровненную таблицу данных книги для логов."""
            
        # 1. Получаем данные через __dict__, чтобы SQLModel ничего не скрыл
        # Исключаем служебные и внутренние поля SQLAlchemy
        exclude = {"id", "last_modified", "metadata", "registry"}
        
        display_rows = []
        max_key_width = 0
        max_val_width = 0

        # Проходимся по всем полям модели
        for key in self.model_fields.keys():
            if key in exclude:
                continue
            
            val = getattr(self, key)
            display_key = key.replace("_", " ").capitalize()
            display_val = str(val) if val is not None else "-"
            
            display_rows.append((display_key, display_val))
            max_key_width = max(max_key_width, len(display_key))
            max_val_width = max(max_val_width, len(display_val))

        # 2. Расчет ширины
        title_line = f"BOOK DATA: {self.title}"
        # Даем запас под длинные пути
        content_width = max(max_key_width + max_val_width + 5, len(title_line), 60)
        
        # 3. Сборка рамки
        top    = f"┏{'━' * (content_width + 2)}┓"
        header = f"┃ {title_line:<{content_width}} ┃"
        sep    = f"┣{'━' * (content_width + 2)}┫"
        bottom = f"┗{'━' * (content_width + 2)}┛"

        lines = [f"\n{top}", header, sep]

        for k, v in display_rows:
            # Математически точное выравнивание
            spacing = content_width - len(k) - len(v) - 3
            lines.append(f"┃ {k} : {v}{' ' * spacing} ┃")

        lines.append(bottom)
        return "\n".join(lines)
        
    def __init__(self, **data: Any) -> None:  # noqa: ANN401
        """Рассчитываем общий рейтинг по 10 параметрам."""
        
        # 1. Список полей для расчета
        rating_keys = [
            "rating_characters", "rating_plot", "rating_size", 
            "rating_prose", "rating_ending", "rating_depth", 
            "rating_atmosphere", "rating_rereadability", 
            "rating_expected_real", "rating_recommend"
        ]
        
        # 2. Считаем сумму из входящего словаря данных
        # Если каких-то данных нет, берем 0.0
        total = sum(float(data.get(k, 0.0) or 0.0) for k in rating_keys)
        
        # 3. Записываем результат в словарь данных, который пойдет в базу
        data["total_rating"] = total
        
        # 4. Вызываем инициализацию родительского класса (SQLModel)
        super().__init__(**data)
        
        # 5. Принудительно обновляем атрибут после создания (для надежности)
        self.total_rating = total
        
    
    @property
    def status_ru(self) -> str:
        """Локализация статуса прочтения книги."""
        return translate(self.status)

    @property
    def format_ru(self) -> str:
        """Локализация формата книги."""
        return translate(self.format)

    @property
    def primary_genres_list_ru(self) -> list[str]:
        """Локализация списка основных жанров."""
        return [translate(g) for g in self.primary_genres_list]

    @property
    def detailed_genres_list_ru(self) -> list[dict[str, str]]:
        """Локализация список жанров и поджанров."""
        
        results = []
        for g in self.detailed_genres_list:
            name_ru = translate(g["name"])
            
            subs = g["sub"].split(",")
            subs_ru = ", ".join([translate(s.strip()) for s in subs if s.strip()])
            
            results.append({"name": name_ru, "sub": subs_ru})
        return results
    
    @property
    def ratings_map(self) -> list[dict[str, Any]]:
        """Возвращает список словарей с переведенным именем и значением рейтинга."""
        
        keys = [
            "rating_characters", "rating_plot", "rating_size", "rating_prose",
            "rating_ending", "rating_depth", "rating_atmosphere", 
            "rating_rereadability", "rating_expected_real", "rating_recommend"
        ]
        return [
            {"label": translate(k), "value": getattr(self, k), "percent": getattr(self, k) * 10}
            for k in keys
        ]
        
    @property
    def reading_sessions(self) -> list[dict[str, Any]]:
        """Парсит унифицированный лог чтений."""
        if not self.read_log:
            return []

        sessions = []
        # Записи разделены через || (это делает трансформер)
        raw_entries = self.read_log.split(" || ")

        for i, entry in enumerate(raw_entries, 1):
            try:
                # Разбиваем строку: "Даты | Стр | Коммент"
                parts = [p.strip() for p in entry.split("|")]
                
                # 1. Обработка Дат
                date_part = parts[0]
                dates = date_part.split("-")
                start_str = dates[0].strip()
                # Если после дефиса пусто или его нет - ставим точки
                finish_str = dates[1].strip() if len(dates) > 1 and dates[1].strip() else "..."
                
                # 2. Обработка Страниц
                pages = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                
                # 3. Обработка Комментария (Ситуация когда его нет или пусто)
                comment = parts[2] if len(parts) > 2 and parts[2] else f"Сессия {i}"

                session = {
                    "number": i,
                    "start": start_str,
                    "finish": "в процессе" if finish_str in ["...", ""] else finish_str,
                    "pages": pages,
                    "comment": comment,
                    "days": None,
                    "pages_per_day": None
                }

                # Расчет темпа (только для полных дат DD.MM.YYYY)
                f_val = "" if session["finish"] == "в процессе" else session["finish"]
                if len(start_str) == 10 and len(f_val) == 10:
                    try:
                        d1 = datetime.strptime(start_str, "%d.%m.%Y")
                        d2 = datetime.strptime(f_val, "%d.%m.%Y")
                        delta = (d2 - d1).days + 1
                        if delta > 0:
                            session["days"] = delta
                            if pages > 0:
                                session["pages_per_day"] = round(pages / delta, 1)
                    except ValueError:
                        pass
                
                sessions.append(session)
            except Exception:
                continue
        return sessions
    
    @property
    def read_stats_summary(self) -> dict[str, Any]:
        """
            Считает агрегированную статистику по всем сессиям.
            
            В рассчете среднего кол-во страниц учитываются только сессии с полными датами.
        """
        sessions = self.reading_sessions
        if not sessions:
            return {"total_pages": 0, "total_days": None, "avg_pace": None, "percent": 0}
        
        total_pages_all = sum(s["pages"] for s in sessions)
        
        # Считаем дни только там, где они есть
        pages_for_pace = sum(s["pages"] for s in sessions if s["days"])
        total_days = sum(s["days"] for s in sessions if s["days"])
        
        # Если дней 0, ставим None для темпа и дней
        avg_pace = round(pages_for_pace / total_days, 1) if total_days and total_days > 0 else None
        display_days = total_days if total_days and total_days > 0 else None
        
        percent = round((total_pages_all / self.total) * 100) if self.total else 0
        
        return {
            "total_pages": total_pages_all,
            "total_days": display_days,
            "avg_pace": avg_pace,
            "percent": min(percent, 100)
        }
    
    @property
    def cover_url(self) -> str:
        """Возвращает путь к обложке для тега img."""
        if not self.cover:
            # Заглушка, если обложка не найдена
            return "https://via.placeholder.com/400x600?text=No+Cover"
        
        # Если в базе лежит URL
        if self.cover.startswith("http"):
            return self.cover
            
        # Если это локальный файл из Vault
        return f"/vault/{self.cover}"