"""Модели данных для модуля времени из ежедневных заметок."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.modules.daily.models import DailyNote

class TimeLog(SQLModel, table=True):
    """Модель отдельной записи о затратах времени."""
    id: int | None = Field(default=None, primary_key=True)
    
    service: str          
    subject: str          
    category_tag: str     
    
    duration_minutes: int 
    raw_duration: str     
    
    # Внешний ключ на дату из ежедневной заметки
    daily_id: str = Field(foreign_key="dailynote.date", index=True)
    
    # Связь с записью из таблицы DailyNote
    daily_note: "DailyNote" = Relationship(back_populates="time_logs")