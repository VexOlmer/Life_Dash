"""Модуль обработки логов времени из ежедневных заметок."""

import re

from src.common.utils import parse_duration_to_minutes
from src.core.exceptions import ValidationError
from src.core.logger import logger

from .models import TimeLog

# Регулярка для строки: - Сервис (Предмет | Тэг) - Время
# Группы: service, subject, tag, duration
TIME_LINE_PATTERN = re.compile(
    r"^-\s+(?P<service>[^(]+)\((?P<subject>[^|]+)\|\s*(?P<tag>[^)]+)\)\s*-\s*(?P<duration>.*)$",
    re.M
)

class TimeTransformer:
    """Трансформер для извлечения временных логов из текста заметки."""

    @staticmethod
    def extract_logs(content: str, daily_id: str) -> list[TimeLog]:
        """Находит секцию 'Время' и парсит все подходящие строки."""
        
        # 1. Вырезаем блок "## ⏳ Время" до следующего заголовка ## или разделителя ---
        block_match = re.search(
            r"(?m)^##\s+.*?Время.*?\n([\s\S]+?)(?=\n##|---|\Z)", 
            content
        )
        
        if not block_match:
            logger.warning("Блок Время не найден в заметке.")
            return []

        block_text = block_match.group(1).strip()
        logs = []

        # 2. Итерируемся по каждой строке блока
        for line in block_text.split('\n'):
            line = line.strip()
            if not line.startswith('-'):
                logger.debug("Строка начата не с символа -")
                continue

            match = TIME_LINE_PATTERN.match(line)
            if match:
                data = match.groupdict()
                #logger.debug(f"Данные времени: {data["service"]}, {data["subject"]}, {data["tag"]}, {data["duration"]}")
                
                duration_mins = parse_duration_to_minutes(data["duration"])
                if duration_mins == 0:
                    raise ValidationError("Не задано время в строке временных логов.")

                logs.append(TimeLog(
                    service=data['service'].strip(),
                    subject=data['subject'].strip(),
                    category_tag=data['tag'].strip(),
                    duration_minutes=duration_mins,
                    raw_duration=data['duration'].strip(),
                    daily_id=daily_id
                ))
            else:
                if line.strip() != "-": # Игнорируем пустые маркеры списка
                    logger.warning(f"[{daily_id}] Неверный формат строки времени: {line}")

        return logs