"""Репозиторий для работы с ежедневынми заметками в БД."""

from sqlmodel import Session, delete, select

from src.common.base import BaseRepository

from .models import DailyNote, TimeLog


class DailyRepository(BaseRepository[DailyNote]):
    """Репозиторий для управления данными ежедневных заметок."""
    def __init__(self, session: Session) -> None:
        """Инициализирует репозиторий ежедневных заметок."""
        super().__init__(session, DailyNote)

    def get_by_date(self, date_str: str) -> DailyNote | None:
        """Возвращение ежедневной заметки по определенной даты."""
        return self.session.exec(select(DailyNote).where(DailyNote.date == date_str)).first()

    def upsert_daily(self, note: DailyNote, logs: list[TimeLog]) -> None:
        """
            Обновляет день и связанные логи времени.
            
            Args:
                note: Данные ежедневной заметки.
                logs: Список данных временных логов из ежедневной заметки.
            
            Returns:
                None
        """
        
        existing = self.get_by_path(note.file_path)
        if existing:
            # Удаляем старые логи перед обновлением, чтобы не дублировать
            self.session.exec(delete(TimeLog).where(TimeLog.daily_id == existing.date))
            
            data = note.model_dump(exclude={"date"})
            for key, value in data.items():
                setattr(existing, key, value)
            self.session.add(existing)
        else:
            self.session.add(note)
        
        for log in logs:
            self.session.add(log)
            
        self.session.commit()