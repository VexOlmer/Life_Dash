"""Сервис для динамического извлечения контента из заметок книг в Obsidian."""

from src.common.utils import extract_section
from src.core.config import settings


class BookService:
    """Сервис для работы с содержимым файлов книг."""

    @staticmethod
    def get_book_content(relative_path: str) -> dict[str, str]:
        """Парсит файл и извлекает специфические разделы по заголовкам."""
        
        full_path = settings.OBSIDIAN_VAULT_PATH / relative_path
        if not full_path.exists():
            return {}

        content = full_path.read_text(encoding="utf-8")

        return {
            "impression": extract_section(content=content, keyword="Моё впечатление"),
            "quotes": extract_section(content=content, keyword="Цитаты"),
        }