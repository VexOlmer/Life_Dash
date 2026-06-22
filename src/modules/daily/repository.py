"""Репозиторий для работы с ежедневынми заметками в БД."""

from sqlmodel import Session, select

from src.common.base import BaseRepository

from .models import DailyNote


class DailyRepository(BaseRepository[DailyNote]):
    """Репозиторий для управления данными ежедневных заметок."""
    def __init__(self, session: Session) -> None:
        """Инициализирует репозиторий ежедневных заметок."""
        super().__init__(session, DailyNote)

    def get_by_date(self, date_str: str) -> DailyNote | None:
        """Возвращение ежедневной заметки по определенной даты."""
        return self.session.exec(select(DailyNote).where(DailyNote.date == date_str)).first()