"""Модуль обработки ежедневных заметок."""

import re
from datetime import datetime
from pathlib import Path

import frontmatter

from src.core.exceptions import ValidationError
from src.core.logger import logger

from .models import DailyNote, TimeLog


class DailyTransformer:
    """Трансформер для обработки расширенного YAML ежедневных заметок."""
    
    @staticmethod
    def _parse_duration(dur_str: str) -> int:
        """Конвертирует '1h 20m', '2h' или '45m' в минуты."""
        total = 0
        h_match = re.search(r'(\d+)h', dur_str)
        m_match = re.search(r'(\d+)m', dur_str)
        if h_match:
            total += int(h_match.group(1)) * 60
        if m_match:
            total += int(m_match.group(1))
        return total

    @staticmethod
    def transform(file_path: Path, vault_path: Path, mtime: float) -> tuple[DailyNote, list[TimeLog]]:
        """
            Превращает Markdown файл в объект DailyNote и список временных логов.
            
            Основные блоки:
                Сон: Время сна и Дневной сон.
                Дневник самоконтроля: флаги Утренней разминки и Дополнительного сахара.
                Личнные показатели: Вес.
                Болезнь: Состояние и Температура.
                
            Если один из основных блоков присутствуте в файле, проверяется наличие всех обязательных строк внутри него.
                Исключение строка Дневного сна в блоке Сна.
            
            Временной блок:
                Строки формата `- Сервис (Уточнение | Тип) - Время`

            Args:
                file_path: Полный путь к Mardown файлу.
                vault_path: Полный путь к базе знаний Obsidian.
                mtime: Время последнего обновления.
            
            Returns:
                tuple[DailyNote, list[TimeLog]]: Связка объекта ежедневной заметки с временными логами.
        """
        
        content = file_path.read_text(encoding="utf-8")
        post = frontmatter.loads(content)
        meta = post.metadata
        filename = file_path.name
        
        # 1. Дата (Имя файла)
        # Конвертация даты: 17-06-2026 -> 2026-06-17
        try:
            date_obj = datetime.strptime(file_path.stem, "%d-%m-%Y")
            db_date_str = date_obj.strftime("%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Имя файла должно быть в формате DD-MM-YYYY: {filename}. Ошибка - {e}.")
            raise ValidationError(f"Имя файла должно быть в формате DD-MM-YYYY: {filename}.") from e
        
        # 2. Город
        city = meta.get("city")
        if not city or city == "Unknown":
            logger.error(f"[{filename}] Поле 'city' в YAML не заполнено")
            raise ValidationError(f"[{filename}] Поле 'city' в YAML не заполнено")

        # 3. Сон
        # Обязательное наличие Лег и Встал, опциональное Дневной сон
        sleep_from, sleep_to, nap_mins = None, None, 0
        if re.search(r"(?m)^##.*Сон", content):
            f = re.search(r"-.*Лег:\s*(\d{2}:\d{2})\s*$", content, re.M)
            t = re.search(r"-.*Встал:\s*(\d{2}:\d{2})\s*$", content, re.M)
            
            if not (f and t):
                logger.error(f"[{file_path.name}] Поля 'Лег' и 'Встал' обязательны в блоке Сна.")
                raise ValidationError(f"[{file_path.name}] Поля 'Лег' и 'Встал' обязательны в блоке Сна.")
            
            sleep_from, sleep_to = f.group(1).strip(), t.group(1).strip()
            
            if sleep_from in ["—", "-", ":"] or sleep_to in ["—", "-", ":"]:
                logger.error(f"[{filename}] Поля Сна не заполнены или имеют неверный формат")
                raise ValidationError(f"[{filename}] Поля Сна не заполнены или имеют неверный формат")
            
            # Ищем саму строку "Дневной сон"
            nap_line_match = re.search(r"- Дневной сон:\s*(.*)$", content, re.M)
            
            if nap_line_match:
                val = nap_line_match.group(1).strip()
                # Если строка есть, проверяем наличие хотя бы одной цифры
                if any(char.isdigit() for char in val):
                    nap_mins = DailyTransformer._parse_duration(val)
                else:
                    # Строка есть, но цифр нет (например, "- Дневной сон: h m" или "- Дневной сон: ")
                    logger.error(f"[{file_path.name}] Поле 'Дневной сон' присутствует, но не заполнено значениями. Строка - {val}.")
                    raise ValidationError(f"[{file_path.name}] Поле 'Дневной сон' присутствует, но не заполнено значениями. Строка - {val}.")
            else:
                # Самой строки нет — это нормально, пишем 0
                nap_mins = 0
        
        # 3. Дневник самоконтроля
        morning_workout, added_sugar = None, None
        if re.search(r"(?m)^##.*Дневник самоконтроля", content):
            m_w = re.search(r"^-\s*.*Утренняя разминка:\s*(.+)$", content, re.M)
            a_s = re.search(r"^-\s*.*Дополнительный сахар:\s*(.+)$", content, re.M)
            
            if not m_w or not a_s:
                logger.error(f"[{file_path.name}] Отсутствуют поля в Дневнике самоконтроля")
                raise ValidationError(f"[{file_path.name}] Отсутствуют поля в Дневнике самоконтроля")
            
            morning_workout = m_w.group(1).strip()
            added_sugar = a_s.group(1).strip()
            
            valid_values = {"Да", "Нет"}
            if morning_workout not in valid_values or added_sugar not in valid_values:
                logger.error(
                    f"[{file_path.name}] Поля в Дневнике самоконтроля содержат "
                    f"недопустимые значения: Утренняя разминка='{morning_workout}', "
                    f"Дополнительный сахар='{added_sugar}'. Допустимы только 'Да' или 'Нет'."
                )
                raise ValidationError(
                    f"[{file_path.name}] Поля в Дневнике самоконтроля содержат "
                    f"недопустимые значения: Утренняя разминка='{morning_workout}', "
                    f"Дополнительный сахар='{added_sugar}'. Допустимы только 'Да' или 'Нет'."
                )

        # 4. Личные показатели
        metrics = {"w": None, "bmi": None, "fat": None, "mus": None, "vis": None}
        if re.search(r"(?m)^##.*Личные показатели", content):
            w = re.search(r"- Вес:\s*([\d.]+)\s*кг$", content, re.M)
            bmi = re.search(r"- ИМТ:\s*([\d.]+)\s*$", content, re.M)
            fat = re.search(r"- Жира:\s*([\d.]+)\s*%$", content, re.M)
            mus = re.search(r"- Мышц:\s*([\d.]+)\s*%$", content, re.M)
            vis = re.search(r"- Уровень висцерального жира:\s*([\d.]+)\s*$", content, re.M)
            
            if not (w and bmi and fat and mus and vis):
                logger.error(f"[{file_path.name}] Все 5 личных показателей должны быть заполнены.")
                raise ValidationError(f"[{file_path.name}] Все 5 личных показателей должны быть заполнены.")
            
            metrics = {
                "w": float(w.group(1)), "bmi": float(bmi.group(1)),
                "fat": float(fat.group(1)), "mus": float(mus.group(1)), "vis": float(vis.group(1))
            }
            
        # 5. Общая активность
        steps_val, calories_val = None, None
        
        # Ищем блок между комментариями START и END
        activity_block_match = re.search(
            r"<!-- GENERAL_ACTIVITY_START -->([\s\S]+?)<!-- GENERAL_ACTIVITY_END -->", 
            content
        )
        
        if activity_block_match:
            block_text = activity_block_match.group(1)
            
            # Поиск значений по тексту (без учета иконок в начале строки)
            s_match = re.search(r"Шаги:\s*(.*)$", block_text, re.M)
            c_match = re.search(r"Сожжённые калории:\s*(.*)$", block_text, re.M)
            
            if not s_match or not c_match:
                raise ValidationError(f"[{file_path.name}] В блоке активности должны быть и Шаги, и Калории.")
            
            s_raw = s_match.group(1).strip()
            c_raw = c_match.group(1).strip()
            
            # Если строки найдены, они обязаны быть числами
            if not s_raw or not c_raw:
                logger.error(f"[{file_path.name}] Поля активности не могут быть пустыми, если блок присутствует.")
                raise ValidationError(f"[{file_path.name}] Поля активности не могут быть пустыми, если блок присутствует.")
            
            try:
                steps_val = int(s_raw)
                calories_val = int(c_raw)
            except ValueError as e:
                raise ValidationError(f"[{file_path.name}] Шаги и Калории должны быть целыми числами без лишних символов.") from e

        # 6. Болезнь
        ill_state_val, temp_val = None, None
        
        # Ищем блок болезни. Паттерн теперь учитывает:
        # 1. Возможный дефис перед ### (- ###)
        # 2. Любые иконки в заголовке (.*Болезнь)
        # 3. Захватывает контент до следующего заголовка или разделителя
        ill_block_match = re.search(r"(?m)^-?\s*###\s*.*Болезнь\s*\n([\s\S]+?)(?=\n-?\s*#|---|$)", content)
        
        if ill_block_match:                        
            state_m = re.search(r"Состояние:\s*(.+)", content)
            temp_m = re.search(r"Температура:\s*([\d.]+)", content)
            
            logger.debug(f"Найден блок Болезни. Найденный блок состояния - {state_m}, температуры - {temp_m}")
            
            if state_m:
                # Если в поле написано что-то вроде "—" или оно пустое, игнорируем
                val = state_m.group(1).strip()
                if val and val not in ["—", "", "-"]:
                    ill_state_val = val
            
            if temp_m:
                try:
                    temp_val = float(temp_m.group(1))
                except ValueError:
                    temp_val = None
                
            if not (ill_state_val and temp_val):
                raise ValidationError(f"[{file_path.name}] Оба показетеля блока болезни должны быть заполнены.")
        
        # 6. Мысли
        has_content = False
        content_match = re.search(r"##\s*.*Мысли.*\n([\s\S]+?)(?=\n##|---|$)", content)

        if content_match:
            text_inside = content_match.group(1).strip()
            
            # Дополнительная проверка: не является ли текст просто пустым списком "- "
            clean_text = text_inside.replace("-", "").strip()
            
            if len(clean_text) > 5:
                has_content = True

        note = DailyNote(
            date=db_date_str,
            city=meta.get("city", "Unknown"),
            
            sleep_from=sleep_from,
            sleep_to=sleep_to,
            nap_mins=nap_mins,
            
            morning_workout=morning_workout,
            added_sugar=added_sugar,
            
            weight=metrics["w"],
            bmi=metrics["bmi"],
            fat_pct=metrics["fat"],
            muscle_pct=metrics["mus"],
            visceral_fat=metrics["vis"],
            
            steps=steps_val,
            calories=calories_val,
            
            illness_state=ill_state_val,
            temperature=temp_val,
            
            has_content=has_content,
            
            file_path=str(file_path.relative_to(vault_path)),
            last_modified=mtime
        )

        # 5. Парсинг Времени
        logs = []
        # time_section = re.search(r"(?m)^##.*Время\n(.*?)(?=\n---|##|$)", content, re.DOTALL)
        # if time_section:
        #     lines = time_section.group(1).strip().split("\n")
        #     for line in lines:
        #         # Regex под формат: - Сервис (Уточнение | Тип) - Время
        #         match = re.match(r"-\s*(.*?)\s*\((.*?)(?:\s*\|\s*(.*?))?\)\s*-\s*(.*)", line.strip())
        #         if match:
        #             srv, sub, tag, dur = match.groups()
        #             logs.append(TimeLog(
        #                 service=srv.strip(),
        #                 subject=sub.strip(),
        #                 category_tag=tag.strip() if tag else None,
        #                 raw_duration=dur.strip(),
        #                 duration_minutes=DailyTransformer._parse_duration(dur),
        #                 daily_id=db_date_str
        #             ))
        #         else:
        #             # Упрощенный вариант без тега: - Работа (Ростелеком) - 5h
        #             match_simple = re.match(r"-\s*(.*?)\s*\((.*?)\)\s*-\s*(.*)", line.strip())
        #             if match_simple:
        #                 srv, sub, dur = match_simple.groups()
        #                 logs.append(TimeLog(
        #                     service=srv.strip(),
        #                     subject=sub.strip(),
        #                     raw_duration=dur.strip(),
        #                     duration_minutes=DailyTransformer._parse_duration(dur),
        #                     daily_id=db_date_str
        #                 ))
        
        return note, logs