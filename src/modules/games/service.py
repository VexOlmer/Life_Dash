"""Сервис для извлечения контента из заметок об играх."""

import re

from src.core.config import settings
from src.core.logger import logger


class GameService:
    """Сервис для работы с содержимым файлов игр."""

    @staticmethod
    def get_game_content(relative_path: str) -> dict[str, str]:
        """
            Парсит файл и извлекает персонажей и впечатления.
        
            Args:
                relative_path: путь до заметки в базе знаний Obsidian.
            
            Returns:
                dict[str, str]: Словарь с содержимым доп секций (герои и мое впечатление)
        """
        
        full_path = settings.OBSIDIAN_VAULT_PATH / relative_path
        if not full_path.exists():
            return {}

        content = full_path.read_text(encoding="utf-8")

        def extract_section(keyword: str) -> str:
            """Находит секцию по ключевому слову в заголовке ##."""
            # Паттерн учитывает, что в заголовке могут быть эмодзи (👤, ❤️)
            pattern = rf"(?m)^##\s+.*{re.escape(keyword)}.*\n(.*?)(?=\n##(?![#])|\n---|\Z)"
            match = re.search(pattern, content, flags=re.DOTALL)
            
            if match:
                text = match.group(1).strip()
                logger.debug(f"Секция '{keyword}' успешно захвачена. Символов: {text}")
                return text
            
            logger.warning(f"Секция '{keyword}' не найдена в {relative_path}")
            return ""

        return {
            "impression": extract_section("Моё впечатление"),
        }