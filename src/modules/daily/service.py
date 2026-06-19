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
    def _format_date_ru(date_iso: str) -> str:
        """Превращает YYYY-MM-DD в DD.MM.YYYY для отображения."""
        if not date_iso or len(date_iso) < 10:
            return "-"
        y, m, d = date_iso.split("-")
        return f"{d}.{m}.{y}"
    
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
    def get_current_streaks(session: Session) -> dict:
        """Рассчитывает текущие непрерывные периоды от вчерашнего дня назад."""
        yesterday = date.today() - timedelta(days=1)
        
        def count_streak(attr_name: str, pos_val: str) -> int:
            """
                Рассчет длительности положительной серии параметра.
            
                Args:
                    attr_name: Наименование атрибута из DailyNote.
                    pos_val: Положительный флаг.
                
                Returns:
                    int: Длина текущей положительной серии.
            """
            
            count = 0
            check_date = yesterday
            while True:
                note = session.get(DailyNote, check_date.isoformat())
                if note and getattr(note, attr_name) == pos_val:
                    count += 1
                    check_date -= timedelta(days=1)
                else:
                    # Если заметки нет или там "Нет" (или сахар "Да") — серия прервана
                    break
            return count

        # Для разминки успех - "Да", для сахара успех - "Нет"
        workout_current = count_streak("morning_workout", "Да")
        sugar_current = count_streak("added_sugar", "Нет")
        
        # Получаем также исторические рекорды для сравнения
        all_records = DailyService.get_records(session)
        workout_max = all_records.get("streaks", {}).get("workout", {}).get("max_pos", 0)
        sugar_max = all_records.get("streaks", {}).get("sugar", {}).get("max_pos", 0)

        return {
            "workout": {"current": workout_current, "max": workout_max},
            "sugar": {"current": sugar_current, "max": sugar_max}
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
        """
            Парсит файл дня и извлекает мысли.
            
            Args:
                relative_path: Относительный путь до файла ежедневной заметки.
            
            Returns:
                dict[str, str]: Доп разделы для вывода на странице ежедневной заметки.
        """

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
    
    @staticmethod
    def get_records(session: Session) -> dict:
        """
            Рассчет различных рекордов и средних показателей по всем ежедневным заметкам.
            
            Args:
                session: Текущая сессия БД.
            
            Returns:
                session: Текущая сессия БД.
        """
        
        notes = session.exec(select(DailyNote).order_by(DailyNote.date)).all()
        if not notes:
            return {}

        # --- 1. РАСЧЕТ СРЕДНЕГО ВРЕМЕНИ (Сон) ---
        def time_to_min(t_str: str) -> int:
            """Корректный перевод времени в минуты."""
            if not t_str or ":" not in t_str:
                return None
            h, m = map(int, t_str.split(":"))
            # Если засыпаем после полуночи (00:00 - 04:00), добавляем 24 часа для корректного среднего
            if h < 12:
                h += 24
            return h * 60 + m

        def min_to_time(total_min: int) -> str:
            """Корректный перевод минут в h m."""
            if not total_min:
                return "--:--"
            h = int(total_min // 60) % 24
            m = int(total_min % 60)
            return f"{h:02d}:{m:02d}"

        sleep_from_mins = [time_to_min(n.sleep_from) for n in notes if n.sleep_from]
        sleep_to_mins = [time_to_min(n.sleep_to) for n in notes if n.sleep_to]
        
        avg_bedtime = min_to_time(sum(sleep_from_mins)/len(sleep_from_mins)) if sleep_from_mins else "--:--"
        avg_wakeuptime = min_to_time(sum(sleep_to_mins)/len(sleep_to_mins)) if sleep_to_mins else "--:--"
        logger.info(f"Среднее время засыпания - {avg_bedtime}.\nСреднее время подъема - {avg_wakeuptime}")

        # --- 2. РЕКОРДЫ СНА ---
        sleep_notes = [n for n in notes if n.night_sleep_minutes > 0]
        
        # Классы DailyNote с определенным значением после фильтрации
        max_sn = max(sleep_notes, key=lambda n: n.night_sleep_minutes) if sleep_notes else None
        min_sn = min(sleep_notes, key=lambda n: n.night_sleep_minutes) if sleep_notes else None
        max_nn = max([n for n in notes if n.nap_mins > 0], key=lambda n: n.nap_mins, default=None)
        
        def build_sleep_record(note: DailyNote, attr_pretty: str) -> dict[str: str]:
            """Вспомогательная функция для сборки словаря рекорда сна."""
            if not note:
                return {"val": "-", "display_date": "-", "iso_date": None}
            return {
                "val": getattr(note, attr_pretty),
                "display_date": DailyService._format_date_ru(note.date),
                "iso_date": note.date # Для ссылки
            }

        # --- 3. СЕРИИ И ИХ СРЕДНИЕ ЗНАЧЕНИЯ ---
        def calc_detailed_streaks(attr_name: str, positive_val: str) -> dict[str: int]:
            """
                Рассчет положительных и отрицительных серий из Дневника самоконтроля.
                
                Args:
                    attr_name: наименование атрибута класса DailyNote.
                    positive_val: флаг положительной записи.
                
                Returns:
                    dict[str: int]: максимальный/минимальный период + и - записи и значения их средней продолжительности.
            """
            
            # Списки с длинами своих периодов
            pos_periods, neg_periods = [], []
            current_count, current_state, period_start_date = 0, None, None

            for i, n in enumerate(notes):
                val = getattr(n, attr_name)
                if val is None:
                    continue # Пропускаем дни без данных
                
                is_pos = (val == positive_val)

                if current_state is None:
                    current_state, current_count, period_start_date = is_pos, 1, n.date
                elif current_state == is_pos:
                    current_count += 1
                else:
                    # Состояние изменилось -> формируем красивый диапазон
                    d1 = DailyService._format_date_ru(period_start_date)
                    d2 = DailyService._format_date_ru(notes[i-1].date)
                    p_str = f"{d1} — {d2}"
                    if current_state:
                        pos_periods.append((current_count, p_str))
                    else:
                        neg_periods.append((current_count, p_str))
                    current_state, current_count, period_start_date = is_pos, 1, n.date
                    
            # Добавляем последний период
            if current_count > 0:
                d1 = DailyService._format_date_ru(period_start_date)
                d2 = DailyService._format_date_ru(notes[-1].date)
                p_str = f"{d1} — {d2}"
                if current_state:
                    pos_periods.append((current_count, p_str))
                else:
                    neg_periods.append((current_count, p_str))

            def get_max_info(periods: list[list]) -> dict[str: str]:
                """Получение максимально длительного периода из списка."""
                if not periods:
                    return {"val": 0, "range": "-"}
                best = max(periods, key=lambda x: x[0])
                return {"val": best[0], "range": best[1]}

            # Расчет средних значений
            avg_pos = round(sum(p[0] for p in pos_periods) / len(pos_periods), 1) if pos_periods else 0
            avg_neg = round(sum(p[0] for p in neg_periods) / len(neg_periods), 1) if neg_periods else 0
            logger.info(f"Средний положительный период - {avg_pos}.\nСредний отрицательный период - {avg_neg}")

            max_pos_info = get_max_info(pos_periods)
            max_neg_info = get_max_info(neg_periods)
            logger.info(f"Максимальный положительный период - {max_pos_info["range"]}, длительность - {max_pos_info["val"]}")
            logger.info(f"Максимальный отрицательрный период - {max_neg_info["range"]}, длительность - {max_neg_info["val"]}")

            return {
                "max_pos": max_pos_info["val"],
                "range_max_pos": max_pos_info["range"],
                "max_neg": max_neg_info["val"],
                "range_max_neg": max_neg_info["range"],
                "avg_pos": round(sum(p[0] for p in pos_periods)/len(pos_periods), 1) if pos_periods else 0,
                "avg_neg": round(sum(p[0] for p in neg_periods)/len(neg_periods), 1) if neg_periods else 0
            }

        return {
            "sleep": {
                "max": build_sleep_record(max_sn, "night_sleep_pretty"),
                "min": build_sleep_record(min_sn, "night_sleep_pretty"),
                "nap": build_sleep_record(max_nn, "nap_pretty"),
                "avg_bedtime": avg_bedtime,
                "avg_wakeuptime": avg_wakeuptime
            },
            "streaks": {
                "workout": calc_detailed_streaks("morning_workout", "Да"),
                "sugar": calc_detailed_streaks("added_sugar", "Нет")
            }
        }