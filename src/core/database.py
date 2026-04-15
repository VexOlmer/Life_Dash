"""Модуль управления базой данных."""

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from src.core.config import settings
from src.core.logger import logger

# Создаем движок (echo=True в режиме дебага выводит SQL-запросы в консоль)
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)


def init_db() -> None:
    """
        Инициализирует базу данных.

        Создает папку data и все таблицы, описанные в моделях SQLModel.
    """
    
    try:
        # Убеждаемся, что папка для БД существует
        db_path = Path("data")
        db_path.mkdir(exist_ok=True)

        SQLModel.metadata.create_all(engine)
        logger.info("База данных успешно инициализирована.")
    except Exception as e:
        logger.error(f"Критическая ошибка при инициализации БД: {e}")
        raise


def get_session() -> Generator[Session, None, None]:
    """
        Создает сессию базы данных.

        Yields:
            Session: Активная сессия SQLModel.
    """
    
    with Session(engine) as session:
        yield session