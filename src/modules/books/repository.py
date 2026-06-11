"""Репозиторий для работы с книгами в БД."""

from sqlmodel import Session

from src.common.base import BaseRepository

from .models import Book


class BookRepository(BaseRepository[Book]):
    """Репозиторий для управления данными книг."""

    def __init__(self, session: Session) -> None:
        """Инициализирует репозиторий книг."""
        super().__init__(session, Book)