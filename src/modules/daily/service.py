"""Сервис для извлечения контента из ежедневных заметок."""

import re
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from src.core.config import settings
from src.core.logger import logger

from .models import DailyNote


class DailyService:
    """Класс обработки ежедневных заметок для информативного показа на дашборде сайта."""
    
    @staticmethod
    def get_week_data(session: Session, week_number: int, year: int) -> dict[str: str | datetime]:
        """
            Получает все записи за конкретную ISO-неделю.
            
            Args:
                session: текущая сессия БД.
                week_number: номер недели.
                year: номер года.
            
            Returns:
                dict[str: str | datetime]: данные недели в формате для отображения в html.
        """
        
        # Список дат в ISO-формате
        start_date = date.fromisocalendar(year, week_number, 1)
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
        """
            Считает средние и суммарные показатели за 14 дней.
            
            Args:
                session: текущая сессия БД.
                weeks_data: список данных за 2 недели.
            
            Returns:
                dict[str: int]: рассчитанные значения показателей за 2 недели.
        """
        
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
        # Группируем по годам -> месяцам -> дням для UI
        structure = {}
        for d in sorted(dates, reverse=True):
            dt = datetime.strptime(d, "%Y-%m-%d")
            y, m = dt.year, dt.month
            if y not in structure:
                structure[y] = {}
            if m not in structure[y]:
                structure[y][m] = []
            structure[y][m].append(d)
        return structure

    @staticmethod
    def prepare_charts_json(weeks_data: list) -> dict:
        """Подготавливает чистые списки данных для отрисовки в Chart.js."""
        labels = [d["display_date"] for d in weeks_data]
        
        # Показатели Сна
        sleep_night = []
        sleep_nap = []
        
        # Дневник самоконтроля (Да = 1, Нет = 0, Нет данных = null)
        workout = []
        sugar = []
        
        # Показатели Веса
        weight = []
        bmi = []
        fat = []
        muscle = []
        visceral = []

        for d in weeks_data:
            note = d["note"]
            if note:
                sleep_night.append(round(note.night_sleep_minutes / 60, 1))
                sleep_nap.append(round(note.nap_mins / 60, 1))
                workout.append(1 if note.morning_workout == "Да" else 0)
                sugar.append(1 if note.added_sugar == "Да" else 0)
                weight.append(note.weight)
                bmi.append(note.bmi)
                fat.append(note.fat_pct)
                muscle.append(note.muscle_pct)
                visceral.append(note.visceral_fat)
            else:
                # Если дня нет в БД, вставляем None для разрыва в графике
                for lst in [sleep_night, sleep_nap, workout, sugar, weight, bmi, fat, muscle, visceral]:
                    lst.append(None)
        
        workout_list = [1 if d["note"] and d["note"].morning_workout == "Да" else 0 for d in weeks_data]
        # Сахар инвертируем: 1 если сахара НЕ БЫЛО (успех)
        sugar_list = [1 if d["note"] and d["note"].added_sugar == "Нет" else 0 for d in weeks_data]

        return {
            "labels": labels,
            "sleep": {"night": sleep_night, "nap": sleep_nap},
            "control": {"workout": workout, "sugar": sugar},
            "metrics": {
                "weight": weight, "bmi": bmi, "fat": fat, 
                "muscle": muscle, "visceral": visceral
            },
            "discipline": {
                "workout": workout_list,
                "sugar": sugar_list,
                "workout_pct": int(sum(workout_list) / len(weeks_data) * 100),
                "sugar_pct": int(sum(sugar_list) / len(weeks_data) * 100)
            }
        }
        
    @staticmethod
    def get_daily_content(relative_path: str) -> dict[str, str]:
        """Парсит файл дня и извлекает мысли."""

        full_path = settings.OBSIDIAN_VAULT_PATH / relative_path
        if not full_path.exists():
            return {}

        content = full_path.read_text(encoding="utf-8")

        def extract_section(keyword: str) -> str:
            pattern = rf"(?m)^##\s+[^#\n]*?{re.escape(keyword)}[^\n]*\n(.*?)(?=\n##(?![#])|\n---|\Z)"
            match = re.search(pattern, content, flags=re.DOTALL)
            
            if match:
                text = match.group(1).strip()
                logger.debug(f"Секция '{keyword}' успешно захвачена. Символов: {len(text)}")
                return text
            
            logger.warning(f"Секция '{keyword}' не найдена в {relative_path}")
            return ""

        return {
            "mind": extract_section("Мысли"),
        }