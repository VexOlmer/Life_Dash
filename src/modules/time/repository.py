"""Репозиторий для работы с временем из ежедневных заметок в БД."""

from sqlmodel import Session

from src.common.base import BaseRepository

from .models import TimeLog


class TimeRepository(BaseRepository[TimeLog]):
    """Репозиторий для работы с таблице временных логов в БД."""
    def __init__(self, session: Session) -> None:
        """Базовая инициализация через наследуемый класс."""
        super().__init__(session, TimeLog)