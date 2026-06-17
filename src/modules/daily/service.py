"""Сервис для извлечения контента из ежедневных заметок."""

from datetime import datetime, timedelta

from sqlmodel import Session, select

from .models import DailyNote


class DailyService:
    """Класс обработки ежедневных заметок для информативного показа на дашборде сайта."""
    @staticmethod
    def get_week_data(session: Session, week_number: int, year: int) -> dict[str: str | datetime]:
        """Получает все записи за конкретную ISO-неделю."""
        import datetime as dt_lib
        start_date = dt_lib.date.fromisocalendar(year, week_number, 1)
        
        dates = [(start_date + timedelta(days=i)).isoformat() for i in range(7)]
        
        statement = select(DailyNote).where(DailyNote.date.in_(dates))
        notes = session.exec(statement).all()
        
        notes_map = {n.date: n for n in notes}
        week_days = []
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        
        for i, date_str in enumerate(dates):
            week_days.append({
                "date": date_str,
                "display_date": datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m"),
                "day_name": day_names[i],
                "note": notes_map.get(date_str)
            })
        return week_days

    @staticmethod
    def get_aggregated_stats(session: Session, weeks_data: list) -> dict[str: int]:
        """Считает средние и суммарные показатели за 14 дней."""
        all_notes = [d["note"] for d in weeks_data if d["note"]]
        if not all_notes:
            return None

        # Списки минут для расчетов
        night_sleep_list = [n.night_sleep_minutes for n in all_notes if n.night_sleep_minutes > 0]
        naps_list = [n.nap_mins for n in all_notes if n.nap_mins > 0]
        weights = [n.weight for n in all_notes if n.weight]
        
        # Суммарное время (Работа, Игры, Видео)
        totals = {"work": 0, "fun": 0}
        for note in all_notes:
            for log in note.time_logs:
                if log.service == "Работа":
                    totals["work"] += log.duration_minutes
                elif log.category_tag in ["g", "f", "s", "ch"]:
                    totals["fun"] += log.duration_minutes

        def avg_fmt(mins_list: list[int]) -> int:
            """Рассчет среднего значения из списка."""
            if not mins_list:
                return "-"
            avg = sum(mins_list) / len(mins_list)
            return f"{int(avg // 60)}ч {int(avg % 60)}м"

        return {
            "avg_night_sleep": avg_fmt(night_sleep_list),
            "avg_nap": avg_fmt(naps_list),
            "avg_weight": round(sum(weights) / len(weights), 1) if weights else 0,
            "total_work": f"{totals['work'] // 60}ч",
            "total_fun": f"{totals['fun'] // 60}ч"
        }

    @staticmethod
    def get_calendar_structure(session: Session) -> dict:
        """Подготовка данных для мини-календаря (список всех дат, где есть заметки)."""
        dates = session.exec(select(DailyNote.date)).all()
        # Группируем по годам и месяцам для UI
        structure = {}
        for d in sorted(dates, reverse=True):
            dt = datetime.strptime(d, "%Y-%m-%d")
            y, m = dt.year, dt.month
            if y not in structure: structure[y] = {}
            if m not in structure[y]: structure[y][m] = []
            structure[y][m].append(d)
        return structure