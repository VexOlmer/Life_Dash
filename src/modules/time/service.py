"""Сервис для извлечения контента времени из ежедневных заметок."""

from datetime import datetime, timedelta

from sqlmodel import Session, select

from .models import TimeLog


class TimeService:
    """Сервис для обработки данных в таблице временных логов."""
    @staticmethod
    def get_stats_for_period(session: Session, days: int = 30) -> dict[str: int]:
        """Получение информации по затраченному времени втечении 30 суток."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        statement = select(TimeLog).where(TimeLog.daily_id >= start_date)
        logs = session.exec(statement).all()

        # Агрегация по категориям
        by_category = {}
        # Агрегация по сервисам
        by_service = {}
        
        for log in logs:
            by_category[log.category_tag] = by_category.get(log.category_tag, 0) + log.duration_minutes
            by_service[log.service] = by_service.get(log.service, 0) + log.duration_minutes

        return {
            "categories": by_category,
            "services": by_service,
            "total_hours": round(sum(by_category.values()) / 60, 1)
        }