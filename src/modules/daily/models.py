"""Модель данных для ежедневных заметок."""

from datetime import datetime, timedelta

from sqlmodel import Field, Relationship, SQLModel

from src.common.utils import format_minutes_to_pretty
from src.modules.time.models import TimeLog


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
    
    # Активность
    steps: int | None = Field(default=None)
    calories: int | None = Field(default=None)
    
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
    def night_sleep_minutes(self) -> int:
        """
            Расчет только ночного сна (без учета дневного).
            
            Для обработки перехода между сутками к результату добавляется 24 часа.
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

    @property
    def night_sleep_pretty(self) -> str:
        """Преобразование времени основного сна."""
        return format_minutes_to_pretty(self.night_sleep_minutes)

    @property
    def nap_pretty(self) -> str:
        """Преобразование времени дневного сна."""
        return format_minutes_to_pretty(self.nap_mins)
    
    @property
    def time_stats_by_category(self) -> dict:
        """Группирует время по тэгам для краткого вывода."""
        stats = {}
        for log in self.time_logs:
            tag = log.category_tag.lower()
            stats[tag] = stats.get(tag, 0) + log.duration_minutes
        return stats

    @property
    def work_time_total(self) -> str:
        """Общее время на работе."""
        mins = self.time_stats_by_category.get("work", 0)
        return format_minutes_to_pretty(mins)