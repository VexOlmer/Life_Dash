"""Модель данных для ежедневных заметок."""

from datetime import datetime, timedelta

from sqlmodel import Field, Relationship, SQLModel


class TimeLog(SQLModel, table=True):
    """Строки активности из раздела Время."""    
    id: int | None = Field(default=None, primary_key=True)
    
    service: str  # Steam, Youtube, Работа, Разное
    subject: str  # Red Dead Redemption 2, Ростелеком, Властелин колец
    category_tag: str | None = None  # g, f, s, ch
    
    duration_minutes: int  # Общего кол-во минут
    raw_duration: str  # Сырая строка времени "1h 2m"
    
    daily_id: str = Field(foreign_key="dailynote.date")
    daily_note: "DailyNote" = Relationship(back_populates="time_logs")

class DailyNote(SQLModel, table=True):
    """Ежедневная заметка с показателями здоровья и сна."""
    date: str = Field(primary_key=True)  # Формат YYYY-MM-DD
    city: str = "Unknown"
    
    # Сон
    sleep_from: str | None = None
    sleep_to: str | None = None
    nap_mins: int = 0
    
    # Дневник самоконтроля
    morning_workout: str | None = None
    added_sugar: str | None = None
    
    # Здоровье
    weight: float | None = None
    bmi: float | None = None
    fat_pct: float | None = None
    muscle_pct: float | None = None
    visceral_fat: float | None = None
    
    # Болезнь
    illness_state: str | None = None
    temperature: float | None = None
    
    # Мысли
    has_content: bool = Field(default=False)
    
    # Служебные поля
    file_path: str = Field(unique=True, index=True)
    last_modified: float

    # Связи
    time_logs: list[TimeLog] = Relationship(
        back_populates="daily_note", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @property
    def total_work_minutes(self) -> int:
        """Общее время работы."""
        return sum(log.duration_minutes for log in self.time_logs if log.service == "Работа")
    
    @property
    def night_sleep_minutes(self) -> int:
        """
            Расчет только ночного сна (без учета дневного).
            
            Для обработки перехода между сутками к результату добавляется 24 часа.
            
            Args:
                None
            
            Returns:
                int: Кол-во минут ночного сна.
        """
        
        if not self.sleep_from or not self.sleep_to:
            return 0
        try:
            fmt = "%H:%M"
            start = datetime.strptime(self.sleep_from, fmt)
            end = datetime.strptime(self.sleep_to, fmt)
            if end < start:
                end += timedelta(days=1)
            return int((end - start).total_seconds() / 60)
        except ValueError:
            return 0

    def _format_mins(self, total_mins: int) -> str:
        """Вспомогательный метод для форматирования."""
        if total_mins <= 0:
            return "-"
        h = total_mins // 60
        m = total_mins % 60
        return f"{h}ч {m}м" if h > 0 else f"{m}м"

    @property
    def night_sleep_pretty(self) -> str:
        """Преобразование времени основного сна."""
        return self._format_mins(self.night_sleep_minutes)

    @property
    def nap_pretty(self) -> str:
        """Преобразование времени дневного сна."""
        return self._format_mins(self.nap_mins)