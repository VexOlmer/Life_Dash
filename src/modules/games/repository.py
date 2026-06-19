"""Репозиторий для работы с играми в БД."""

from sqlmodel import Session

from src.common.base import BaseRepository

from .models import Game


class GameRepository(BaseRepository[Game]):
    """Репозиторий для управления данными игр."""

    def __init__(self, session: Session) -> None:
        """Инициализирует репозиторий игр."""
        super().__init__(session, Game)