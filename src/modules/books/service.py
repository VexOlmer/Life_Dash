"""Сервис для динамического извлечения контента из заметок Obsidian."""

import re

from src.core.config import settings


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

        # Универсальная функция для поиска контента между заголовками
        def extract_section(header_name: str) -> str:
            # Ищем заголовок, затем забираем всё до следующего ## или --- или конца файла
            # Флаг re.DOTALL позволяет точке . захватывать переносы строк
            pattern = rf"{re.escape(header_name)}(.*?)(?=\n##|\n---|\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
            return ""

        return {
            "main_characters": extract_section("## 👤 Главные герои"),
            "side_characters": extract_section("## 👤 Второстепенные герои"),
            "impression": extract_section("## ❤️ Моё впечатление"),
            "quotes": extract_section("## 📝 Цитаты"),
        }