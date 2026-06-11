"""Сервис для динамического извлечения контента из заметок Obsidian."""

import re

from src.core.config import settings
from src.core.logger import logger


class BookService:
    """Сервис для работы с содержимым файлов книг."""

    @staticmethod
    def get_book_content(relative_path: str) -> dict[str, str]:
        """
            Парсит файл и извлекает специфические разделы по заголовкам.
            
            Args:
                relative_path: Путь к файлу в Obsidian Vault.
        """
        
        full_path = settings.OBSIDIAN_VAULT_PATH / relative_path
        if not full_path.exists():
            return {}

        content = full_path.read_text(encoding="utf-8")

        def extract_section(keyword: str) -> str:
            """Находит секцию по ключевому слову в заголовке ##, игнорируя подзаголовки ###."""
            # ГЛАВНОЕ ИЗМЕНЕНИЕ В ПОСЛЕДНЕЙ ГРУППЕ (Lookahead):
            # (?=\n##(?![#]) | \n--- | \Z)
            # Это означает: 
            # 1. Остановись, если видишь \n##, но ПРИ УСЛОВИИ, что дальше НЕ идет еще одна #
            # 2. Или если видишь разделитель \n---
            # 3. Или если это конец файла \Z
            
            pattern = rf"(?m)^##\s+[^#\n]*?{re.escape(keyword)}[^\n]*\n(.*?)(?=\n##(?![#])|\n---|\Z)"
            
            match = re.search(pattern, content, flags=re.DOTALL)
            
            if match:
                text = match.group(1).strip()
                logger.debug(f"Секция '{keyword}' успешно захвачена. Символов: {len(text)}")
                return text
            
            logger.warning(f"Секция '{keyword}' не найдена в {relative_path}")
            return ""

        return {
            "impression": extract_section("Моё впечатление"),
            "quotes": extract_section("Цитаты"),
        }