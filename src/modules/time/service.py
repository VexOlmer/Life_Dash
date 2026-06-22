"""Сервис для извлечения контента времени из ежедневных заметок."""

import calendar
from datetime import date, timedelta

from sqlmodel import Session, select

from src.core.config import settings
from src.modules.books.models import Book
from src.modules.games.models import Game
from src.modules.time.models import TimeLog


class TimeService:
    """Сервис обработки данных временных логов из БД."""
    
    @staticmethod
    def get_weekly_budget_stats(session: Session) -> dict[str: str, int]:
        """Расчет прогресса по бюджетам за ТЕКУЩУЮ неделю."""
        today = date.today()
        # Находим понедельник текущей недели
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        statement = select(TimeLog).where(
            TimeLog.daily_id >= start_of_week.isoformat(),
            TimeLog.daily_id <= end_of_week.isoformat()
        )
        logs = session.exec(statement).all()
        
        # Группировка по категориям
        tag_to_cat = {tag: cat for cat, tags in settings.TIME_CATEGORIES.items() for tag in tags}
        cat_stats = {cat: 0 for cat in settings.TIME_CATEGORIES}
        
        for log in logs:
            cat = tag_to_cat.get(log.category_tag, "Другое")
            if cat in cat_stats:
                cat_stats[cat] += log.duration_minutes

        budgets = []
        for cat, goal_hours in settings.TIME_BUDGETS.items():
            actual_hours = cat_stats.get(cat, 0) / 60
            percent = (actual_hours / goal_hours * 100) if goal_hours > 0 else 0
            budgets.append({
                "category": cat,
                "goal": goal_hours,
                "actual": round(actual_hours, 1),
                "percent": int(percent),
                "is_over": percent > 100 and cat == "Досуг"
            })
        return budgets
    
    @staticmethod
    def get_monthly_stats(session: Session, year: int, month: int) -> dict[dict | int]:
        """
            Формирование статистики потраченного времени за месяц.
        
            Args:
                session: Текущая сессия БД.
                year: Номер года.
                month: Номер месяца.
            
            Returns:
                dict[dict | int]: Словарь с данными по месяцу.
        """
        
        # 1. Определяем диапазон дат
        start_date = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day}"

        # 2. Получаем все логи за месяц
        statement = select(TimeLog).where(
            TimeLog.daily_id >= start_date,
            TimeLog.daily_id <= end_date
        )
        logs = session.exec(statement).all()

        # Теги, для которых мы ищем связи в БД
        LINKABLE_TAGS = ["reading", "gaming", "movie", "series"]

        stats = {
            "total_minutes": 0,
            "by_tag": {},       
            "by_category": {cat: 0 for cat in settings.TIME_CATEGORIES},
            "by_service": {},
            "daily_totals": {i: 0 for i in range(1, last_day + 1)}, 
            "logs": [] 
        }

        # Предзагрузка маппингов (только для игр и книг)
        books_map = {b.title.lower(): b.id for b in session.exec(select(Book)).all()}
        games_map = {g.title.lower(): g.id for g in session.exec(select(Game)).all()}

        tag_to_cat = {tag: cat for cat, tags in settings.TIME_CATEGORIES.items() for tag in tags}

        for log in logs:
            mins = log.duration_minutes
            tag = log.category_tag
            stats["total_minutes"] += mins
            
            # Агрегация для графиков
            stats["by_tag"][tag] = stats["by_tag"].get(tag, 0) + mins
            stats["by_service"][log.service] = stats["by_service"].get(log.service, 0) + mins
            cat = tag_to_cat.get(tag, "Другое")
            stats["by_category"][cat] += mins
            
            day = int(log.daily_id.split("-")[2])
            stats["daily_totals"][day] += mins

            # --- ЛОГИКА СВЯЗЕЙ (пункт 2) ---
            link = None
            if tag in LINKABLE_TAGS:
                subject_l = log.subject.lower()
                if tag == "reading" and subject_l in books_map:
                    link = f"/books/{books_map[subject_l]}"
                elif tag == "gaming" and subject_l in games_map:
                    link = f"/games/{games_map[subject_l]}"
                # Для movie/series логика будет аналогичной, когда появятся модули

            stats["logs"].append({
                "date": log.daily_id,
                "service": log.service,
                "subject": log.subject,
                "tag": tag,
                "duration": log.raw_duration,
                "link": link
            })

        return {
            "summary": stats,
            "budgets": TimeService.get_weekly_budget_stats(session), # Передаем сюда же
            "total_hours": round(stats["total_minutes"] / 60, 1),
            "charts": {
                "days": list(stats["daily_totals"].keys()),
                "day_values": [round(m/60, 1) for m in stats["daily_totals"].values()],
                "categories": list(stats["by_category"].keys()),
                "category_values": [round(m/60, 1) for m in stats["by_category"].values()],
                "services": list(dict(sorted(stats["by_service"].items(), key=lambda x: x[1], reverse=True)[:10]).keys()),
                "service_values": [round(m/60, 1) for m in sorted(stats["by_service"].values(), reverse=True)[:10]]
            },
            "all_tags": sorted(list(stats["by_tag"].keys()))
        }