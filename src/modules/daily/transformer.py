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
        
        # 1. Конвертация даты: 17-06-2026 -> 2026-06-17
        try:
            date_obj = datetime.strptime(file_path.stem, "%d-%m-%Y")
            db_date_str = date_obj.strftime("%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Не удалось прочитать YAML в {file_path.name}. Ошибка - {e}")
            raise ValidationError(f"Имя файла должно быть в формате DD-MM-YYYY: {file_path.name}") from e

        # 2. Валидация блока Сон
        sleep_from, sleep_to, nap_mins = None, None, 0
        if re.search(r"(?m)^##.*Сон", content):
            f = re.search(r"- Лег:\s*(\d{2}:\d{2})\s*$", content, re.M)
            t = re.search(r"- Встал:\s*(\d{2}:\d{2})\s*$", content, re.M)
            
            if not (f and t):
                raise ValidationError(f"[{file_path.name}] Поля 'Лег' и 'Встал' обязательны в блоке Сна")
            
            sleep_from, sleep_to = f.group(1), t.group(1)
            
            # Ищем саму строку "Дневной сон"
            nap_line_match = re.search(r"- Дневной сон:\s*(.*)$", content, re.M)
            
            if nap_line_match:
                val = nap_line_match.group(1).strip()
                # Если строка есть, проверяем наличие хотя бы одной цифры
                if any(char.isdigit() for char in val):
                    nap_mins = DailyTransformer._parse_duration(val)
                else:
                    # Строка есть, но цифр нет (например, "- Дневной сон: h m" или "- Дневной сон: ")
                    raise ValidationError(f"[{file_path.name}] Поле 'Дневной сон' присутствует, но не заполнено значениями")
            else:
                # Самой строки нет — это нормально, пишем 0
                nap_mins = 0

        # 3. Валидация блока Личные показатели
        metrics = {"w": None, "bmi": None, "fat": None, "mus": None, "vis": None}
        if re.search(r"(?m)^##.*Личные показатели", content):
            w = re.search(r"- Вес:\s*([\d.]+)\s*кг$", content, re.M)
            bmi = re.search(r"- ИМТ:\s*([\d.]+)\s*$", content, re.M)
            fat = re.search(r"- Жира:\s*([\d.]+)\s*%$", content, re.M)
            mus = re.search(r"- Мышц:\s*([\d.]+)\s*%$", content, re.M)
            vis = re.search(r"- Уровень висцерального жира:\s*([\d.]+)\s*$", content, re.M)
            
            if not (w and bmi and fat and mus and vis):
                raise ValidationError(f"[{file_path.name}] Все 5 личных показателей должны быть заполнены")
            
            metrics = {
                "w": float(w.group(1)), "bmi": float(bmi.group(1)),
                "fat": float(fat.group(1)), "mus": float(mus.group(1)), "vis": float(vis.group(1))
            }

        # 4. Болезнь
        ill_state = re.search(r"-.*Состояние\s*-\s*(.+)$", content, re.M)
        temp = re.search(r"-.*Температура\s*-\s*([\d.]+)\s*$", content, re.M)

        note = DailyNote(
            date=db_date_str,
            city=meta.get("city", "Unknown"),
            sleep_from=sleep_from,
            sleep_to=sleep_to,
            nap_mins=nap_mins,
            weight=metrics["w"],
            bmi=metrics["bmi"],
            fat_pct=metrics["fat"],
            muscle_pct=metrics["mus"],
            visceral_fat=metrics["vis"],
            illness_state=ill_state.group(1).strip() if ill_state else None,
            temperature=float(temp.group(1)) if temp else None,
            file_path=str(file_path.relative_to(vault_path)),
            last_modified=mtime
        )

        # 5. Парсинг Времени
        logs = []
        time_section = re.search(r"(?m)^##.*Время\n(.*?)(?=\n---|##|$)", content, re.DOTALL)
        if time_section:
            lines = time_section.group(1).strip().split("\n")
            for line in lines:
                # Regex под формат: - Сервис (Уточнение | Тип) - Время
                match = re.match(r"-\s*(.*?)\s*\((.*?)(?:\s*\|\s*(.*?))?\)\s*-\s*(.*)", line.strip())
                if match:
                    srv, sub, tag, dur = match.groups()
                    logs.append(TimeLog(
                        service=srv.strip(),
                        subject=sub.strip(),
                        category_tag=tag.strip() if tag else None,
                        raw_duration=dur.strip(),
                        duration_minutes=DailyTransformer._parse_duration(dur),
                        daily_id=db_date_str
                    ))
                else:
                    # Упрощенный вариант без тега: - Работа (Ростелеком) - 5h
                    match_simple = re.match(r"-\s*(.*?)\s*\((.*?)\)\s*-\s*(.*)", line.strip())
                    if match_simple:
                        srv, sub, dur = match_simple.groups()
                        logs.append(TimeLog(
                            service=srv.strip(),
                            subject=sub.strip(),
                            raw_duration=dur.strip(),
                            duration_minutes=DailyTransformer._parse_duration(dur),
                            daily_id=db_date_str
                        ))
        
        return note, logs