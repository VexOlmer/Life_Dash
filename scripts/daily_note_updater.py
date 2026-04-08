"""
    Модуль для массового обновления ежедневных заметок Obsidian.

    Удаляет строки с пустыми aliases, также удаляет строку с указанием тега (tags)
"""


import re
from pathlib import Path
from typing import Dict, List, Tuple


class DailyNoteUpdater:
    """
        Класс для очистки метаданных и добавления анкеров в заметки Obsidian.

        Attributes:
            notes_dir: Путь к директории с заметками.
            backup: Флаг создания резервных копий.
            stats: Статистика обработки.
    """

    def __init__(self, notes_dir: str, backup: bool = True):
        self.notes_dir = Path(notes_dir)
        if not self.notes_dir.exists():
            raise FileNotFoundError(f"Путь не найден: {notes_dir}")

        self.backup = backup
        self.stats = {'processed': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

    def _clean_frontmatter(self, content: str) -> str:
        """
            Удаляет специфические теги и пустые алиасы из YAML блока.

            Если в блоке 'tags' указано только '- daily', удаляется весь блок тегов.
            Если 'aliases' пуст ([]), строка удаляется.

            Args:
                content: Полный текст заметки.

            Returns:
                Текст с обновленным (очищенным) YAML блоком.
        """
        
        # Находим Frontmatter (между первыми двумя ---)
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            return content

        original_fm = frontmatter_match.group(0)
        inner_fm = frontmatter_match.group(1)

        # 1. Удаляем блок tags, если там только daily
        # Ищем 'tags:' за которым следует новая строка, пробелы и '- daily'
        tags_pattern = r'tags:\n\s+-\s+daily\s*\n?'
        inner_fm = re.sub(tags_pattern, '', inner_fm)

        # 2. Удаляем пустые алиасы
        # Ищем 'aliases: []' с возможными пробелами
        aliases_pattern = r'aliases:\s*\[\]\s*\n?'
        inner_fm = re.sub(aliases_pattern, '', inner_fm)

        # Подчищаем возможные лишние пустые строки в конце после удаления
        inner_fm = inner_fm.strip()

        new_fm = f"---\n{inner_fm}\n---"
        return content.replace(original_fm, new_fm)

    def _update_file(self, filepath: Path) -> bool:
        """
            Обновляет содержимое одного файла.

            Args:
                filepath: Путь к файлу.

            Returns:
                True, если файл был изменен.
        """
        try:
            content = filepath.read_text(encoding='utf-8')
            original_content = content

            # Выполняем очистку метаданных
            content = self._clean_frontmatter(content)
            
            if content != original_content:
                if self.backup:
                    backup_path = filepath.with_suffix(filepath.suffix + '.backup')
                    filepath.replace(backup_path) # или запись нового
                
                filepath.write_text(content, encoding='utf-8')
                return True

            return False

        except Exception as e:
            print(f"  ❌ Ошибка в {filepath.name}: {e}")
            self.stats['errors'] += 1
            return False

    def run(self):
        md_files = list(self.notes_dir.glob('**/*.md'))
        for filepath in md_files:
            if filepath.suffix == '.backup':
                continue
                
            self.stats['processed'] += 1
            if self._update_file(filepath):
                self.stats['updated'] += 1
                print(f"✅ {filepath.name}: Обновлен (YAML очищен)")
            else:
                self.stats['skipped'] += 1

        print(f"\nИтог: {self.stats}")


def main():
    path = r"C:\Knowledge_Base\Knowledge_Base\periodic\daily\2026"
    updater = DailyNoteUpdater(path, backup=False)
    updater.run()


if __name__ == "__main__":
    pass
    #main()