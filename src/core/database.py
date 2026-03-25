"""

"""


from sqlmodel import create_engine, Session, SQLModel

from .config import settings


# connect_args нужны только для SQLite, чтобы избежать проблем с потоками
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG  # Вывод всех SQL-запросы в консоль
)


def init_db():
    """
        Создает все таблицы, описанные в моделях
    """
    
    SQLModel.metadata.create_all(engine)


def get_session():
    """
        Генератор сессии для FastAPI
    """
    
    with Session(engine) as session:
        yield session
        