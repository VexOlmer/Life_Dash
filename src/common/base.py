"""Базовые классы для работы с данными."""

from typing import Generic, TypeVar

from sqlmodel import Session, SQLModel, select

# T — это тип нашей модели (Book, Game и т.д.)
T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """Базовый репозиторий для CRUD операций."""

    def __init__(self, session: Session, model_type: type[T]) -> None:
        """
            Инициализирует репозиторий.

            Args:
                session: Сессия базы данных.
                model_type: Класс модели (напр. Book).
        """
        
        self.session = session
        self.model_type = model_type

    def get_by_path(self, relative_path: str) -> T | None:
        """
            Находит запись по пути к файлу.

            Args:
                relative_path: Относительный путь от корня Vault.
            
            Returns:
                T | None
        """
        
        # Мы предполагаем, что у всех моделей будет поле file_path
        statement = select(self.model_type).where(
            self.model_type.file_path == relative_path # type: ignore
        )
        return self.session.exec(statement).first()        

    def upsert(self, instance: T) -> None:
        """Обновляет существующую запись или создает новую."""
        # Нормализуем путь перед поиском (на всякий случай)
        path = getattr(instance, "file_path", None)
        existing = self.get_by_path(path) if path else None

        if existing:
            # Обновляем все поля, кроме первичных ключей
            # У книг это 'id', у дневника это 'date'
            data = instance.model_dump(exclude={"id", "date"})
            for key, value in data.items():
                setattr(existing, key, value)
            
            # Явное обновление связей (для TimeLog)
            if hasattr(instance, "time_logs"):
                existing.time_logs = instance.time_logs # type: ignore
                
            self.session.add(existing)
        else:
            self.session.add(instance)
        
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e

    def delete_by_path(self, relative_path: str) -> None:
        """
            Удаляет запись из БД.

            Args:
                relative_path: Относительный путь к файлу.
            
            Returns:
                None
        """
        
        instance = self.get_by_path(relative_path)
        if instance:
            self.session.delete(instance)
            self.session.commit()
            
    def get_all_paths(self) -> list[str]:
        """
            Возвращает список всех путей файлов, зарегистрированных в БД.
            
            Returns:
                list[str] - Список всех путей файлов
        """
        statement = select(self.model_type.file_path) # type: ignore
        return self.session.exec(statement).all()