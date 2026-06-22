"""Сервис для извлечения контента из заметок об играх."""

from src.common.utils import extract_section
from src.core.config import settings


class GameService:
    """Сервис для работы с содержимым файлов игр."""

    @staticmethod
    def get_game_content(relative_path: str) -> dict[str, str]:
        """Парсит заметку и извлекает доп разделы для детальной карточки."""
        
        full_path = settings.OBSIDIAN_VAULT_PATH / relative_path
        if not full_path.exists():
            return {}

        content = full_path.read_text(encoding="utf-8")
        
        return {
            "impression": extract_section(content=content, keyword="Моё впечатление"),
        }