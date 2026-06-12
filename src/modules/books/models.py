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
    good_reads: int | None = Field(default=None)
    
    # Формат в БД: "Дата-Дата | Стр | Формат книги | Язык книги | Коммент || Дата-Дата | Стр | Формат книги | Язык книги | Коммент"
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


    # --- Валидаторы ---
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
        """
            Валидация жанров и поджанров.
            
            Обязательно наличие 1-3 основных жанров, внутри каждого неболее 2-х поджанров.
        """
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


    # --- Доп функции ---
    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        """
            Конвертирует '12:30' или '45' в минуты (целое число).
            
            Args:
                time_str: Общее время в часах или минутах.
                
            Returns:
                int: Общее время в минутах
        """
        
        time_str = str(time_str).strip()
        if ":" in time_str:
            try:
                parts = time_str.split(":")
                # Если формат ЧЧ:ММ (например, 12:30)
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                # Если формат ЧЧ:ММ:СС (на всякий случай)
                elif len(parts) == 3:
                    return int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                return 0
        # Если введено просто число (например, "45"), считаем это минутами
        return int(time_str) if time_str.isdigit() else 0

    @staticmethod
    def _minutes_to_pretty(minutes: int) -> str:
        """
            Конвертирует минуты в часых с минутами/только минуты.

            Args:
                minutes: Общее кол-во минут.
            
            Returns:
                str: Минуты или Часы с минутами.
        """
        
        if minutes <= 0:
            return "0м"
        if minutes < 60:
            return f"{minutes}м"
        
        h = minutes // 60 # Целое количество часов
        m = minutes % 60  # Остаток минут
        
        if m == 0:
            return f"{h}ч"
        return f"{h}ч {m}м"


    # --- Свойства жанров ---
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
    
    # --- Языки книг ---
    @property
    def all_languages_list(self) -> list[str]:
        """Возвращает список уникальных языков из сессий чтения."""
        if not self.read_log:
            return []
        
        languages = []
        raw_entries = self.read_log.split(" || ")
        for entry in raw_entries:
            parts = [p.strip() for p in entry.split("|")]
            if len(parts) >= 4:
                lang = parts[3]
                if lang and lang not in languages:
                    languages.append(lang)
        return sorted(languages)
    
    @property
    def all_languages_list_ru(self) -> list[str]:
        """Возвращает список уникальных переведенных языков."""
        return [translate(lang) for lang in self.all_languages_list]
    
    # --- Форматы книг ---
    @property
    def format_ru(self) -> str:
        """Локализация формата книги."""
        return translate(self.format)
    
    @property
    def all_formats_list(self) -> list[str]:
        """Возвращает список уникальных форматов из read_log."""
        if not self.read_log:
            return []
        
        formats = []
        raw_entries = self.read_log.split(" || ")
        for entry in raw_entries:
            parts = [p.strip() for p in entry.split("|")]
            if len(parts) >= 3:
                fmt = parts[2]
                if fmt and fmt not in formats:
                    formats.append(fmt)
        return formats
    
    @property
    def all_formats_list_ru(self) -> list[str]:
        """Возвращает список уникальных переведенных форматов."""
        return [translate(f) for f in self.all_formats_list]
    
    # --- Статус книги ---
    @property
    def status_ru(self) -> str:
        """Локализация статуса прочтения книги."""
        return translate(self.status)

    # --- Рейтинговые параметры книг ---
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
        
    # --- Обработка read_log ---
    @property
    def reading_sessions(self) -> list[dict[str, Any]]:
        """
            Парсит сессии чтения из строки read_log и рассчитывает аналитику темпа.
            
            Ожидаемый формат одной записи в Obsidian (минимум 4 части):
            Даты | Объём (стр или ЧЧ:ММ) | Формат (paper/electronic/audio) | Язык | [Комментарий]
            
            Returns:
                list[dict[str, Any]]: Список словарей с данными каждой сессии:
                    - number: порядковый номер
                    - start/finish: даты начала и конца
                    - volume_val: числовое значение объема (стр или минуты)
                    - display_volume: отформатированная строка объема
                    - comment: описание сессии
                    - format/language: технические характеристики
                    - type: тип контента (audio/book)
                    - days: длительность в днях
                    - pace: рассчитанный темп (стр/дн или время/дн)
        """
        
        if not self.read_log:
            return []

        sessions = []
        # Разделитель сессий, склеенный трансформером
        raw_entries = self.read_log.split(" || ")

        for i, entry in enumerate(raw_entries, 1):
            try:
                # Ожидаем минимум 4 обязательных поля (Даты, Объем, Формат, Язык)
                parts = [p.strip() for p in entry.split("|")]
                if len(parts) < 4:
                    logger.warning(f"Пропуск сессии {i} в {self.title}: недостаточно полей (нужно 4, найдено {len(parts)})")
                    continue

                # 1. Даты (обязательно)
                date_part = parts[0]
                dates = date_part.split("-")
                start_str = dates[0].strip()
                finish_str = dates[1].strip() if len(dates) > 1 and dates[1].strip() else "..."
                
                # 2. Объем (обязательно)
                raw_vol = parts[1]
                
                # 3. Формат (обязательно)
                s_format = parts[2]
                
                # 4. Язык (обязательно)
                s_lang = parts[3]
                
                # 5. Комментарий (опционально)
                comment = parts[4] if len(parts) > 4 and parts[4] else f"Сессия {i}"

                # --- Определение типа контента и обработка объема ---
                if s_format == "audio" or ":" in raw_vol:
                    vol_val = self._time_to_minutes(raw_vol)
                    disp_vol = self._minutes_to_pretty(vol_val)
                    s_type = "audio"
                else:
                    vol_val = int(raw_vol) if str(raw_vol).isdigit() else 0
                    disp_vol = f"{vol_val} стр"
                    s_type = "book"

                session = {
                    "number": i,
                    "start": start_str,
                    "finish": "в процессе" if finish_str in ["...", ""] else finish_str,
                    "volume_val": vol_val,
                    "display_volume": disp_vol,
                    "comment": comment,
                    "format": s_format,
                    "language": s_lang,
                    "type": s_type,
                    "days": None,
                    "pace": None
                }

                # --- Расчет аналитики (только при наличии полных дат) ---
                f_val = "" if session["finish"] == "в процессе" else session["finish"]
                if len(start_str) == 10 and len(f_val) == 10:
                    try:
                        d1 = datetime.strptime(start_str, "%d.%m.%Y")
                        d2 = datetime.strptime(f_val, "%d.%m.%Y")
                        delta = (d2 - d1).days + 1
                        
                        if delta > 0:
                            session["days"] = delta
                            pace_val = round(vol_val / delta, 1)
                            # Форматируем темп в зависимости от типа
                            if s_type == "audio":
                                session["pace"] = f"{self._minutes_to_pretty(int(pace_val))}/дн"
                            else:
                                session["pace"] = f"{pace_val} стр/дн"
                    except ValueError as e:
                        logger.debug(f"Некорректный формат дат в сессии {i} фильма {self.title}: {e}")
                
                sessions.append(session)

            except (ValueError, IndexError) as e:
                logger.error(f"Критическая ошибка парсинга сессии {i} в файле {self.file_path}: {e}")
                continue
                
        return sessions
    
    @property
    def read_stats_summary(self) -> dict[str, Any]:
        """
            Считает агрегированную статистику только для бумажных/электронных сессий.
            
            Высчитывает общее кол-во страниц, дней чтения, среднее кол-во страниц в день и процент прочтения книги.
            
            Returns:
                dict[str, Any] - {total_pages, total_days, avg_pace, percent}
        """
        
        sessions = self.reading_sessions
        if not sessions:
            return {"total_pages": None, "total_days": None, "avg_pace": None, "percent": 0}
        
        # 1. Фильтруем сессии, которые относятся к книгам (paper/electronic)
        page_sessions = [s for s in sessions if s["type"] == "book"]
        
        # 2. Считаем страницы (только если есть хотя бы одна такая сессия)
        total_pages = sum(s["volume_val"] for s in page_sessions) if page_sessions else None
        
        # 3. Дни считаем по ВСЕМ сессиям (и аудио, и бумаге), так как это общее время с книгой
        total_days = sum(s["days"] for s in sessions if s["days"])
        
        # 4. Средний темп считаем только для страниц
        pages_for_pace = sum(s["volume_val"] for s in page_sessions if s["days"])
        days_with_pages = sum(s["days"] for s in page_sessions if s["days"])
        avg_pace = round(pages_for_pace / days_with_pages, 1) if days_with_pages else None
        
        # 5. Прогресс (проценты)
        percent = 0
        if self.total and total_pages:
            percent = round((total_pages / self.total) * 100)
        
        return {
            "total_pages": total_pages,
            "total_days": total_days or None,
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