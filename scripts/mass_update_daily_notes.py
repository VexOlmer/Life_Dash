"""
    Модуль для массового обновления ежедневных заметок Obsidian.

    Добавляет анкерные комментарии (HTML-теги) в разделы активности и тренировок
        для последующего автоматизированного парсинга.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


class DailyNoteUpdater:
    """
        Класс для добавления комментариев-анкеров в ежедневные заметки.

        Attributes:
            notes_dir: Путь к директории с заметками.
            backup: Флаг создания резервных копий перед изменением.
            stats: Словарь со статистикой обработки.
    """

    def __init__(self, notes_dir: str, backup: bool = True):
        """
            Инициализирует экземпляр DailyNoteUpdater.

            Args:
                notes_dir: Путь к директории с файлами заметок.
                backup: Создавать ли .backup копию файла.

            Raises:
                FileNotFoundError: Если указанная директория не существует.
                NotADirectoryError: Если указанный путь не является директорией.
        """
        
        self.notes_dir = Path(notes_dir)

        if not self.notes_dir.exists():
            raise FileNotFoundError(f"Директория не найдена: {notes_dir}")

        if not self.notes_dir.is_dir():
            raise NotADirectoryError(f"Путь не является директорией: {notes_dir}")

        self.backup = backup
        self.stats = {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

        # Паттерн для поиска секции общей активности
        self._general_activity_pattern = re.compile(
            r'(### Общая активность\n)(.*?)(?=\n### Тренировки|\n## |$)',
            re.DOTALL
        )

        # Паттерны для поиска блоков тренировок
        self._training_patterns = {
            r'#### 🏋️ Силовая': 'STRENGTH',
            r'#### ❤️ Кардио': 'CARDIO',
            r'#### 🚴 Велосипед': 'BIKE',
            r'#### 🏊 Бассейн': 'SWIM',
            r'#### ⛷️ Лыжи': 'SKI',
        }

    def _backup_file(self, filepath: Path) -> Path:
        """
            Создает резервную копию файла.

            Args:
                filepath: Путь к исходному файлу.

            Returns:
                Путь к созданной резервной копии.

            Raises:
                IOError: Если не удалось записать файл.
        """
        
        try:
            backup_path = filepath.with_suffix(filepath.suffix + '.backup')
            content = filepath.read_text(encoding='utf-8')
            backup_path.write_text(content, encoding='utf-8')
            return backup_path
        except Exception as e:
            raise IOError(f"Ошибка создания бэкапа {filepath.name}: {e}") from e

    def _add_anchors_to_general_activity(self, content: str) -> str:
        """
            Добавляет анкеры в секцию общей активности и вечерней прогулки.

            Args:
                content: Исходное содержимое заметки.

            Returns:
                Содержимое с добавленными анкерами.
        """
        
        match = self._general_activity_pattern.search(content)
        if not match:
            return content

        header = match.group(1)
        body = match.group(2)

        # Удаление дублирующихся переносов строк
        body = re.sub(r'\n\s*\n+', '\n', body)

        if '<!-- GENERAL_ACTIVITY_START -->' in body:
            return content

        # Начинаем с открывающего анкера
        new_body = '<!-- GENERAL_ACTIVITY_START -->\n' + body

        # Добавляем анкер для прогулки
        walk_token = '- 🌙 Вечерняя прогулка:'
        if walk_token in body:
            walk_re = re.compile(rf'({walk_token}\n(?:  - .*\n)*)', re.DOTALL)
            walk_match = walk_re.search(new_body)
            if walk_match and '<!-- WALK_START -->' not in walk_match.group(1):
                walk_block = walk_match.group(1)
                replacement = f'\n<!-- WALK_START -->\n{walk_block}<!-- WALK_END -->\n\n'
                new_body = new_body.replace(walk_block, replacement)

        # Обработка разделителя в конце
        if new_body.endswith('---'):
            new_body = new_body[:-3].rstrip() + '\n<!-- GENERAL_ACTIVITY_END -->\n\n---'
        else:
            new_body = new_body.rstrip() + '\n<!-- GENERAL_ACTIVITY_END -->\n\n---'

        return content.replace(match.group(0), header + new_body)

    def _add_anchors_to_trainings(self, content: str) -> str:
        """
            Добавляет анкеры для каждого типа тренировок.

            Args:
                content: Исходное содержимое заметки.

            Returns:
                Обновленное содержимое.
        """
        
        for pattern, anchor_name in self._training_patterns.items():
            training_regex = re.compile(
                rf'({pattern}.*?)(?=\n#### |\n## |$)',
                re.DOTALL
            )

            matches = list(training_regex.finditer(content))

            # Обратный порядок, чтобы сохранять корректность индексов при замене
            for match in reversed(matches):
                block = match.group(1)
                if f'<!-- {anchor_name}_START -->' in content:
                    continue

                if block.endswith('---'):
                    block = block[:-3]
                
                block = block.strip()

                new_block = (
                    f'<!-- {anchor_name}_START -->\n'
                    f'{block}\n'
                    f'<!-- {anchor_name}_END -->\n\n---'
                )
                content = (
                    content[:match.start(1)] + 
                    new_block + 
                    content[match.end(1):]
                )

        return content

    def _update_file(self, filepath: Path) -> bool:
        """
            Обновляет один файл заметки.

            Args:
                filepath: Путь к файлу.

            Returns:
                True, если файл был изменен.
        """
        
        try:
            content = filepath.read_text(encoding='utf-8')
            original_content = content

            content = self._add_anchors_to_general_activity(content)
            content = self._add_anchors_to_trainings(content)

            if content != original_content:
                if self.backup:
                    self._backup_file(filepath)
                filepath.write_text(content, encoding='utf-8')
                return True

            return False

        except (IOError, PermissionError) as e:
            print(f"  ❌ Ошибка доступа/записи: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            print(f"  ❌ Неожиданная ошибка в {filepath.name}: {e}")
            self.stats['errors'] += 1
            return False

    def _get_sort_key(self, filepath: Path) -> Tuple[int, int, int]:
        """
            Извлекает дату из имени файла dd-mm-yyyy для сортировки.
        """
        
        date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', filepath.stem)
        if date_match:
            day, month, year = map(int, date_match.groups())
            return (year, month, day)
        return (9999, 99, 99)

    def run(self) -> Dict[str, int]:
        """
            Запускает процесс обновления всех заметок.

            Returns:
                Словарь со статистикой (processed, updated, skipped, errors).
        """
        
        all_files = list(self.notes_dir.glob('**/*.md'))
        md_files = [f for f in all_files if f.suffix != '.backup']
        md_files.sort(key=self._get_sort_key)

        print(f"\n{'='*60}")
        print(f"Директория: {self.notes_dir}")
        print(f"Найдено файлов: {len(md_files)}")
        print(f"{'='*60}\n")

        for filepath in md_files:
            self.stats['processed'] += 1
            print(f"[{self.stats['processed']}/{len(md_files)}] {filepath.name}")

            if self._update_file(filepath):
                self.stats['updated'] += 1
                print("  ✅ Обновлен")
            else:
                self.stats['skipped'] += 1
                print("  ⏭️ Пропущен")

        self._print_summary()
        return self.stats

    def _print_summary(self):
        print(f"\n{'='*60}")
        print("СТАТИСТИКА ОБРАБОТКИ")
        print(f"{'='*60}")
        for key, value in self.stats.items():
            print(f"{key.capitalize():<15}: {value}")
        print(f"{'='*60}")


def main():
    notes_directory = r"C:\Knowledge_Base\Knowledge_Base\periodic\daily\2025"

    try:
        updater = DailyNoteUpdater(notes_directory, backup=False)
        updater.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main()