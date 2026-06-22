"""Модуль управления базой данных."""

import logging
from collections.abc import Generator

from sqlmodel import Session, create_engine

from src.core.config import settings

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)


def get_session() -> Generator[Session, None, None]:
    """Создает сессию базы данных."""
    
    with Session(engine) as session:
        yield session