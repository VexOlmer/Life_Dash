"""Модели данных для модуля игр."""

import re
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel

from src.common.utils import translate
from src.core.logger import logger


class Game(SQLModel, table=True):
    """Модель игры на основе шаблона Obsidian."""
    
    id: int | None = Field(default=None, primary_key=True)

    # Основная информация (YAML)
    title: str
    title_orig: str | None = None
    year: int
    status: str = "plan"
    genres: str
    series: str | None = None
    price: int = 0
    purchase_date: str | None = None  # dd.mm.yyyy
    digital_dist: str = "Steam"
    
    developer: str = "Unknown"
    publisher: str = "Unknown"
    country: str = "Unknown"
    
    hours_played: float = 0.0
    hours_to_beat: float | None = None
    percent_achievements: int = 0
    
    # Формат в БД: "Даты | Часы | Платформа | Коммент || ..."
    play_log: str | None = Field(default=None)
    
    # Рейтинги (10 параметров)
    rating_optimization: float
    rating_graphics: float
    rating_audio: float
    rating_gameplay: float
    rating_price_quality: float
    rating_story_lore: float
    rating_immersion: float
    rating_replayability: float
    rating_expected_real: float
    rating_cult_status: float
    
    total_rating: float = Field(default=0.0)
    
    bg_color: str = Field(default="#ffffff")
    text_color: str = Field(default="#000000")
    
    # Внешние рейтинги и ID игры с сайта igdb
    metacritic: float | None = None
    steam: float | None = None
    igdb: str | None = None
    
    # Путь к файлу обложки
    cover: str | None = Field(default=None)

    # Служебные поля
    file_path: str = Field(unique=True, index=True)
    last_modified: float
    created_at: str
    
    model_config = ConfigDict(validate_assignment=True)

    # --- Валидаторы ---
    @field_validator("bg_color", "text_color", mode="before")
    @classmethod
    def validate_colors(cls, v: str) -> str:
        """Валидация корректности цветов."""   
        if not v.startswith("#") or len(v) not in [4, 7]:
            raise ValueError("Цвет должен быть HEX-формата (#fff или #ffffff)")
        return v

    @field_validator(
        "rating_optimization", "rating_graphics", "rating_audio", "rating_gameplay",
        "rating_price_quality", "rating_story_lore", "rating_immersion", 
        "rating_replayability", "rating_expected_real", "rating_cult_status",
        mode="before"
    )
    @classmethod
    def validate_ratings(cls, v: float) -> float:
        """Валидация рейтинговых параметров."""       
        if not (0 <= v <= 10):
            raise ValueError("Рейтинг должен быть в диапазоне от 0 до 10")
        return v
    
    @field_validator("purchase_date", mode="before")
    @classmethod
    def validate_purchase_date(cls, v: Any) -> str | None:
        """Переворачиваем дату покупки в ISO формат для сохранения в БД."""
        if not v or v == "None" or v == "":
            return None
        v_str = str(v).strip()
        # Если дата уже в формате ГГГГ-ММ-ДД (например, после обновления), оставляем
        if re.match(r"\d{4}-\d{2}-\d{2}", v_str):
            return v_str
        # Если дата в формате ДД.ММ.ГГГГ, переворачиваем для базы
        match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", v_str)
        if match:
            d, m, y = match.groups()
            return f"{y}-{m}-{d}"
        return v_str


    def __init__(self, **data: Any) -> None: # noqa: ANN401
        """Рассчитываем общий рейтинг по 10 параметрам."""
        
        rating_keys = [
            "rating_optimization", "rating_graphics", "rating_audio", "rating_gameplay",
            "rating_price_quality", "rating_story_lore", "rating_immersion", 
            "rating_replayability", "rating_expected_real", "rating_cult_status"
        ]
        total = sum(float(data.get(k, 0.0) or 0.0) for k in rating_keys)
        data["total_rating"] = total
        super().__init__(**data)
        
        self.total_rating = total


    # --- Свойства ---
    @property
    def is_perfect(self) -> bool:
        """Игра пройдена на 100% достижений."""
        return self.percent_achievements == 100

    @property
    def genres_list_ru(self) -> list[str]:
        """Возвращает локализованные жанры игры."""
        if not self.genres:
            return []
        return [translate(g.strip()) for g in self.genres.split(",") if g.strip()]

    @property
    def status_ru(self) -> str:
        """Возвращает локализованный статус игры."""
        return translate(self.status)
    
    @property
    def purchase_date_ru(self) -> str:
        """Вывод даты на сайте в привычном формате."""
        if not self.purchase_date or self.purchase_date == "None":
            return "—"
        # Конвертируем обратно из ГГГГ-ММ-ДД в ДД.ММ.ГГГГ
        parts = self.purchase_date.split("-")
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return self.purchase_date

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
    def progress_percent(self) -> int:
        """
            Рассчитывает процент прохождения.
            
            Приоритет:
            1. Если игра завершена (finished), всегда 100%.
            2. Если игра в процессе и есть эталон (hours_to_beat), считаем долю.
            3. Если эталона нет, но статус finished - 100%, иначе 0%.
        """
        
        # Если игра завершена ИЛИ просмотрена — это 100%
        if self.status in ["finished", "watched"]:
            return 100
        
        # Если игра брошена, мы всё равно хотим видеть, как далеко ты зашел
        # Или если она в процессе (playing)
        if self.hours_to_beat and self.hours_to_beat > 0:
            percent = round((self.hours_played / self.hours_to_beat) * 100)
            return min(percent, 100)
        
        # Во всех остальных случаях (план или нет данных)
        return 0

    # --- Обработка read_log ---
    @property
    def playing_sessions(self) -> list[dict[str, Any]]:
        """
            Парсит игровые сессии из строки play_log и рассчитывает аналитику темпа.
            
            Ожидаемый формат одной записи в Obsidian (минимум 4 части):
            Даты | Часы (ЧЧ) | Платформа | | ! [Комментарий (! показывает первое завершения сюжета)]
            
            Returns:
                list[dict[str, Any]]: Список словарей с данными каждой сессии:
                    - number: порядковый номер
                    - start/finish: даты начала и конца
                    - hours: кол-во наигранных часов
                    - platform: платформа где играл
                    - comment: описание сессии
                    - is_completion: флаг завершения сюжета
        """
        
        if not self.play_log:
            return []
        
        sessions = []
        raw_entries = self.play_log.split(" || ")
        total_entries = len(raw_entries)
        
        for i, entry in enumerate(raw_entries, 1):
            try:
                parts = [p.strip() for p in entry.split("|")]
                if len(parts) < 3:
                    logger.warning(f"Пропуск сессии {i} в {self.title}: недостаточно полей (нужно 3, найдено {len(parts)})")
                    continue
                
                # 1. Даты (обязательно)
                date_part = parts[0].split("-")
                start_str = date_part[0].strip()
                finish_str = date_part[1].strip() if len(date_part) > 1 and date_part[1].strip() else "..."
                
                # 2. Часы (обязательно)
                hours = float(parts[1]) if parts[1].replace('.','',1).isdigit() else 0.0
                
                # 3. Платформа (обязательно)
                platform = parts[2]
                
                # 4. Комментарий (опционально)
                comment = parts[3] if len(parts) > 3 and parts[3] else f"Сессия {i}"
                
                # Поиск знака завершения сюжета
                is_completion = "!" in comment
                
                # --- Определение статуса сессии ---
                is_last = (i == total_entries)
                has_no_finish = (finish_str in ["...", ""])
                session_status = None # По умолчанию завершенная сессия
                
                if has_no_finish:
                    if not is_last:
                        # Если дата не закрыта и это НЕ последняя сессия -> брошена
                        session_status = "dropped"
                    else:
                        # Если это последняя сессия, смотрим на общий статус книги
                        if self.status == "dropped":
                            session_status = "dropped"
                        else:
                            session_status = "playing"
                elif is_last and self.status == "dropped":
                    # Крайний случай: дата завершения стоит, но игру в итоге дропнули на этом моменте
                    session_status = "dropped"
                
                session = {
                    "number": i,
                    "start": start_str,
                    "finish": "в процессе" if finish_str in ["...", ""] else finish_str,
                    "hours": hours,
                    "platform": platform,
                    "comment": comment.replace("!", "").strip() or f"Сессия {i}",
                    "is_completion": is_completion,
                    "session_status": session_status, # "dropped", "playing" или None
                    "days": None,
                    "pace": None
                }
                
                # Расчет темпа (часов в день), только для наличия полных обоих дат
                f_val = "" if session["finish"] == "в процессе" else session["finish"]
                if len(start_str) == 10 and len(f_val) == 10:
                    try:
                        d1 = datetime.strptime(start_str, "%d.%m.%Y")
                        d2 = datetime.strptime(f_val, "%d.%m.%Y")
                        delta = (d2 - d1).days + 1
                        if delta > 0:
                            session["days"] = delta
                            session["pace"] = f"{round(hours / delta, 1)} ч/дн"
                    except ValueError:
                        pass
                    
                sessions.append(session)
                
            except (ValueError, IndexError) as e:
                logger.error(f"Критическая ошибка парсинга сессии {i} в файле {self.file_path}: {e}")
                continue
        return sessions

    # --- Аналитика Дат (Бэклог и Финал) ---
    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str or len(date_str) < 10 or date_str == "None":
            logger.warning(f"Ошибка парсинга даты - {date_str}. Дата пустая или меньше 10 символов.")
            return None
        
        try:
            # Пытаемся распарсить ГГГГ-ММ-ДД
            if "-" in date_str:
                return datetime.strptime(date_str[:10], "%Y-%m-%d")
            # Пытаемся распарсить ДД.ММ.ГГГГ (на случай старых данных)
            return datetime.strptime(date_str[:10], "%d.%m.%Y")
        except Exception as e:
            logger.warning(f"Ошибка парсинга даты - {date_str}. Ошибка - {e}")
            return None

    @property
    def days_in_backlog(self) -> int | None:
        """
            Кол-во дней между покупкой и первой сессией.
            
            Returns:
                int | None: кол-во дней между покупкой и первой сессией или None.
        """
        p_date = self._parse_date(self.purchase_date)
        s = self.playing_sessions
        if not p_date or not s:
            logger.warning(f"Невозможно определить кол-во дней с моментам покупки до первого запуска. \
                           Либо не указана дата покупки, либо не указаны игровые сессии. Заметка - {self.file_path}")
            return None
        
        first_session_date = self._parse_date(s[0]["start"])
        if not first_session_date:
            return None
        
        delta = (first_session_date - p_date).days
        return max(0, delta)

    @property
    def days_to_completion(self) -> int | None:
        """
            Кол-во дней от покупки до завершения сюжета.
            
            Завершения сюжета определяется наличием в комментарии сессии знака !.
            
            Returns:
                int | None: кол-во дней между покупкой и завершением сюжета или None.
        """
        
        p_date = self._parse_date(self.purchase_date)
        if not p_date:
            return None
        
        completion_session = next((s for s in self.playing_sessions if s["is_completion"]), None)
        if not completion_session:
            return None
        
        # Берем дату финиша сессии с "!", если её нет - дату начала
        comp_date_str = completion_session["finish"] if completion_session["finish"] != "..." else None
        comp_date = self._parse_date(comp_date_str)
        
        if not comp_date:
            return None
        return max(0, (comp_date - p_date).days)

    @property
    def ratings_map(self) -> list[dict[str, Any]]:
        """Возвращает список словарей с переведенным именем и значением рейтинга."""
        
        keys = [
            "rating_optimization", "rating_graphics", "rating_audio", "rating_gameplay",
            "rating_price_quality", "rating_story_lore", "rating_immersion", 
            "rating_replayability", "rating_expected_real", "rating_cult_status"
        ]
        return [
            {"label": translate(k), "value": getattr(self, k), "percent": getattr(self, k) * 10}
            for k in keys
        ]
        
    @property
    def to_pretty_str(self) -> str:
        """Возвращает идеально выровненную таблицу данных игры для логов."""
            
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
        title_line = f"GAMES DATA: {self.title}"
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