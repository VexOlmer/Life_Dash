"""Базовые классы для работы с данными."""

from typing import Generic, TypeVar

from sqlmodel import Session, SQLModel, select

# T — это тип нашей модели (Book, Game и т.д.)
T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """Базовый репозиторий для CRUD операций."""

    def __init__(self, session: Session, model_type: type[T]) -> None:
        """Инициализирует репозиторий определенной моделью данных."""
        
        self.session = session
        self.model_type = model_type

    def get_by_path(self, relative_path: str) -> T | None:
        """Находит запись по пути к файлу."""
        
        # Мы предполагаем, что у всех моделей будет поле file_path
        statement = select(self.model_type).where(
            self.model_type.file_path == relative_path # type: ignore
        )
        return self.session.exec(statement).first()        

    def upsert(self, instance: T) -> None:
        """
            Подготавливает обновление существующей записи или создание новой в сессии.
    
            ВНИМАНИЕ: Метод не вызывает commit(). Для сохранения изменений.
        """
        
        path = getattr(instance, "file_path", None)
        existing = self.get_by_path(path) if path else None

        if existing:
            data = instance.model_dump(exclude={"id", "date"})
            for key, value in data.items():
                setattr(existing, key, value)
            if hasattr(instance, "time_logs"):
                existing.time_logs = instance.time_logs # type: ignore
            self.session.add(existing)
        else:
            self.session.add(instance)

    def delete_by_path(self, relative_path: str) -> None:
        """Удаляет запись из БД."""
        
        instance = self.get_by_path(relative_path)
        if instance:
            self.session.delete(instance)
            self.session.commit()
            
    def get_all_paths(self) -> list[str]:
        """Возвращает список всех путей файлов, зарегистрированных в БД."""
        statement = select(self.model_type.file_path) # type: ignore
        return self.session.exec(statement).all()