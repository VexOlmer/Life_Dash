"""
    Модуль для массового обновления ежедневных заметок Obsidian.

    Добавляет анкерные комментарии (HTML-теги) в разделы активности и тренировок
        для последующего автоматизированного парсинга.
    Удаляет строки с пустыми aliases, также удаляет строку с указанием тега (tags).
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path


class UpdateStrategy(ABC):
    """Базовый абстрактный класс для стратегий обновления заметок."""
    
    @abstractmethod
    def apply(self, content: str) -> str:
        """
            Применяет изменения к содержимому заметки.
            
            Args:
                content: Исходное содержимое заметки.
                
            Returns:
                Измененное содержимое заметки.
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Возвращает название стратегии для логирования."""
        pass


# class AddAnchorsStrategy(UpdateStrategy):
#     """
#         Стратегия добавления комментариев-анкеров в ежедневные заметки.
        
#         Добавляет анкерные комментарии в разделы активности и тренировок.
#     """
    
#     def __init__(self) -> None:
#         """Инициализирует паттерны для поиска секций."""
        
#         # Паттерн для поиска секции общей активности
#         self._general_activity_pattern = re.compile(
#             r'(### Общая активность\n)(.*?)(?=\n### Тренировки|\n## |$)',
#             re.DOTALL
#         )
        
#         # Паттерны для поиска блоков тренировок
#         self._training_patterns = {
#             r'#### 🏋️ Силовая': 'STRENGTH',
#             r'#### ❤️ Кардио': 'CARDIO',
#             r'#### 🚴 Велосипед': 'BIKE',
#             r'#### 🏊 Бассейн': 'SWIM',
#             r'#### ⛷️ Лыжи': 'SKI',
#         }
    
#     def get_name(self) -> str:  # noqa: D102
#         return "Добавление анкеров"
    
#     def apply(self, content: str) -> str:
#         """
#             Применяет добавление анкеров к содержимому.
            
#             Args:
#                 content: Исходное содержимое заметки.
                
#             Returns:
#                 Содержимое с добавленными анкерами.
#         """
        
#         content = self._add_anchors_to_general_activity(content)
#         content = self._add_anchors_to_trainings(content)
        
#         return content
    
#     def _add_anchors_to_general_activity(self, content: str) -> str:
#         """
#             Добавляет анкеры в секцию общей активности и вечерней прогулки.

#             Args:
#                 content: Исходное содержимое заметки.

#             Returns:
#                 Содержимое с добавленными анкерами.
#         """
        
#         match = self._general_activity_pattern.search(content)
#         if not match:
#             return content

#         header = match.group(1)
#         body = match.group(2)

#         # Удаление дублирующихся переносов строк
#         body = re.sub(r'\n\s*\n+', '\n', body)

#         if '<!-- GENERAL_ACTIVITY_START -->' in body:
#             return content

#         # Начинаем с открывающего анкера
#         new_body = '<!-- GENERAL_ACTIVITY_START -->\n' + body

#         # Добавляем анкер для прогулки
#         walk_token = '- 🌙 Вечерняя прогулка:'
#         if walk_token in body:
#             walk_re = re.compile(rf'({walk_token}\n(?:  - .*\n)*)', re.DOTALL)
#             walk_match = walk_re.search(new_body)
#             if walk_match and '<!-- WALK_START -->' not in walk_match.group(1):
#                 walk_block = walk_match.group(1)
#                 replacement = f'\n<!-- WALK_START -->\n{walk_block}<!-- WALK_END -->\n\n'  # noqa: E501
#                 new_body = new_body.replace(walk_block, replacement)

#         # Обработка разделителя в конце
#         if new_body.endswith('---'):
#             new_body = new_body[:-3].rstrip() + '\n<!-- GENERAL_ACTIVITY_END -->\n\n---'
#         else:
#             new_body = new_body.rstrip() + '\n<!-- GENERAL_ACTIVITY_END -->\n\n---'

#         return content.replace(match.group(0), header + new_body)

#     def _add_anchors_to_trainings(self, content: str) -> str:
#         """
#             Добавляет анкеры для каждого типа тренировок.

#             Args:
#                 content: Исходное содержимое заметки.

#             Returns:
#                 Обновленное содержимое.
#         """
        
#         for pattern, anchor_name in self._training_patterns.items():
#             training_regex = re.compile(
#                 rf'({pattern}.*?)(?=\n#### |\n## |$)',
#                 re.DOTALL
#             )

#             matches = list(training_regex.finditer(content))

#             # Обратный порядок, чтобы сохранять корректность индексов при замене
#             for match in reversed(matches):
#                 block = match.group(1)
#                 if f'<!-- {anchor_name}_START -->' in content:
#                     continue

#                 if block.endswith('---'):
#                     block = block[:-3]
                
#                 block = block.strip()

#                 new_block = (
#                     f'<!-- {anchor_name}_START -->\n'
#                     f'{block}\n'
#                     f'<!-- {anchor_name}_END -->\n\n---'
#                 )
#                 content = (
#                     content[:match.start(1)] + 
#                     new_block + 
#                     content[match.end(1):]
#                 )

#         return content


# class CleanMetadataStrategy(UpdateStrategy):
#     """
#         Стратегия очистки метаданных и добавления анкеров в заметки Obsidian.
        
#         Удаляет специфические теги и пустые алиасы из YAML блока.
#     """
    
#     def get_name(self) -> str:  # noqa: D102
#         return "Очистка метаданных"
    
#     def apply(self, content: str) -> str:
#         """
#             Применяет очистку метаданных к содержимому.
            
#             Args:
#                 content: Исходное содержимое заметки.
                
#             Returns:
#                 Содержимое с очищенными метаданными.
#         """
#         return self._clean_frontmatter(content)
    
#     def _clean_frontmatter(self, content: str) -> str:
#         """
#             Удаляет специфические теги и пустые алиасы из YAML блока.

#             Если в блоке 'tags' указано только '- daily', удаляется весь блок тегов.
#             Если 'aliases' пуст ([]), строка удаляется.

#             Args:
#                 content: Полный текст заметки.

#             Returns:
#                 Текст с обновленным (очищенным) YAML блоком.
#         """
        
#         # Находим Frontmatter (между первыми двумя ---)
#         frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
#         if not frontmatter_match:
#             return content

#         original_fm = frontmatter_match.group(0)
#         inner_fm = frontmatter_match.group(1)

#         # 1. Удаляем блок tags, если там только daily
#         # Ищем 'tags:' за которым следует новая строка, пробелы и '- daily'
#         tags_pattern = r'tags:\n\s+-\s+daily\s*\n?'
#         inner_fm = re.sub(tags_pattern, '', inner_fm)

#         # 2. Удаляем пустые алиасы
#         # Ищем 'aliases: []' с возможными пробелами
#         aliases_pattern = r'aliases:\s*\[\]\s*\n?'
#         inner_fm = re.sub(aliases_pattern, '', inner_fm)

#         # Подчищаем возможные лишние пустые строки в конце после удаления
#         inner_fm = inner_fm.strip()

#         new_fm = f"---\n{inner_fm}\n---"
#         return content.replace(original_fm, new_fm)


# class AddCityStrategy(UpdateStrategy):
#     """
#         Стратегия добавления поля city в метаданные заметки.
        
#         Добавляет поле city: Omsk в YAML блок, если оно отсутствует.
#     """
    
#     def get_name(self) -> str:
#         """Вывод типа операции."""
#         return "Добавление города"
    
#     def apply(self, content: str) -> str:
#         """
#             Добавляет поле city в frontmatter.
            
#             Args:
#                 content: Исходное содержимое заметки.
                
#             Returns:
#                 Содержимое с добавленным полем city.
#         """
#         return self._add_city_to_frontmatter(content)
    
#     def _add_city_to_frontmatter(self, content: str) -> str:
#         """
#             Добавляет поле city: Omsk в YAML блок.
            
#             Args:
#                 content: Полный текст заметки.
                
#             Returns:
#                 Текст с обновленным YAML блоком.
#         """
        
#         # Находим Frontmatter (между первыми двумя ---)
#         frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
#         if not frontmatter_match:
#             return content
        
#         original_fm = frontmatter_match.group(0)
#         inner_fm = frontmatter_match.group(1)
        
#         # Проверяем, есть ли уже поле city
#         if re.search(r'^city:\s*', inner_fm, re.MULTILINE):
#             return content
        
#         # Добавляем city после created или в конец блока
#         # Ищем created: и вставляем после него
#         created_match = re.search(r'^(created:\s*.*?)$', inner_fm, re.MULTILINE)
#         if created_match:
#             # Вставляем после created
#             new_inner = inner_fm.replace(
#                 created_match.group(0),
#                 created_match.group(0) + '\ncity: Omsk'
#             )
#         else:
#             # Если created нет, добавляем в начало блока
#             new_inner = 'city: Omsk\n' + inner_fm
        
#         new_fm = f"---\n{new_inner}\n---"
#         return content.replace(original_fm, new_fm)


class DiaryFormatStrategy(UpdateStrategy):
    """
        Стратегия замены тире на двоеточие в блоке дневника самоконтроля.
        
        Преобразует формат:
            - ☀️Утренняя разминка - Нет
            в:
            - ☀️Утренняя разминка: Нет
    """
    
    def get_name(self) -> str:
        """Возвращение наименования применяемой стратегии."""
        return "Форматирование дневника"
    
    def apply(self, content: str) -> str:
        """
            Применяет замену тире на двоеточие в секции дневника.
            
            Args:
                content: Исходное содержимое заметки.
                
            Returns:
                Содержимое с отформатированным дневником.
        """
        return self._format_diary_section(content)
    
    def _format_diary_section(self, content: str) -> str:
        """
            Находит блок дневника самоконтроля и заменяет тире на двоеточие.
            
            Args:
                content: Полный текст заметки.
                
            Returns:
                Текст с отформатированным блоком дневника.
        """
        
        # Паттерн для поиска секции дневника
        diary_pattern = re.compile(
            r'(## 📒Дневник самоконтроля\n)(.*?)(?=\n## |\n---|$)',
            re.DOTALL
        )
        
        match = diary_pattern.search(content)
        if not match:
            return content
        
        header = match.group(1)
        body = match.group(2)
        
        # Проверяем, есть ли что менять
        if not re.search(r'-\s*[^:]+-\s*', body):
            return content
        
        # Заменяем тире на двоеточие в строках вида "- текст - значение"
        # Паттерн ищет: дефис, пробел, текст без двоеточия, пробел, дефис, пробел, значение
        def replace_tire(match: re.Match) -> str:
            # match.group(1) - текст до дефиса, match.group(2) - значение после дефиса
            return f"- {match.group(1)}: {match.group(2)}"
        
        # Ищем строки вида "- Текст - Значение" 
        # (не захватываем строки, где уже есть двоеточие)
        line_pattern = re.compile(r'^-\s+([^:]+?)\s+-\s+(.+)$', re.MULTILINE)
        new_body = line_pattern.sub(replace_tire, body)
        
        # Если ничего не изменилось, возвращаем исходный контент
        if new_body == body:
            return content
        
        # Заменяем старый блок новым
        new_section = header + new_body
        return content.replace(match.group(0), new_section)


class DailyNoteUpdater:
    """
        Класс для применения стратегий обновления к ежедневным заметкам.

        Attributes:
            notes_dir: Путь к директории с заметками.
            backup: Флаг создания резервных копий перед изменением.
            strategies: Список стратегий для применения к файлам.
            stats: Словарь со статистикой обработки.
    """

    def __init__(self, notes_dir: str, strategies: list[UpdateStrategy],
                 backup: bool = True) -> None:
        """
            Инициализирует экземпляр DailyNoteUpdater.

            Args:
                notes_dir: Путь к директории с файлами заметок.
                strategies: Список стратегий для применения к файлам.
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
        self.strategies = strategies
        self.stats = {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
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
            raise OSError(f"Ошибка создания бэкапа {filepath.name}: {e}") from e

    def _update_file(self, filepath: Path) -> bool:
        """
            Обновляет один файл заметки, применяя все стратегии.

            Args:
                filepath: Путь к файлу.

            Returns:
                True, если файл был изменен.
        """
        
        try:
            content = filepath.read_text(encoding='utf-8')
            original_content = content

            # Применяем все стратегии последовательно
            for strategy in self.strategies:
                content = strategy.apply(content)

            if content != original_content:
                if self.backup:
                    self._backup_file(filepath)
                filepath.write_text(content, encoding='utf-8')
                return True

            return False

        except (OSError, PermissionError) as e:
            print(f"  ❌ Ошибка доступа/записи: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            print(f"  ❌ Неожиданная ошибка в {filepath.name}: {e}")
            self.stats['errors'] += 1
            return False

    def _get_sort_key(self, filepath: Path) -> tuple[int, int, int]:
        """Извлекает дату из имени файла dd-mm-yyyy для сортировки."""
        
        date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', filepath.stem)
        if date_match:
            day, month, year = map(int, date_match.groups())
            return (year, month, day)
        return (9999, 99, 99)

    def run(self) -> dict[str, int]:
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
        print(f"Применяемые стратегии: {[s.get_name() for s in self.strategies]}")
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

    def _print_summary(self) -> None:
        """Выводит статистику обработки."""
        
        print(f"\n{'='*60}")
        print("СТАТИСТИКА ОБРАБОТКИ")
        print(f"{'='*60}")
        for key, value in self.stats.items():
            print(f"{key.capitalize():<15}: {value}")
        print(f"{'='*60}")


def main() -> None:
    """Запускает основной процесс обновления заметок."""
    
    notes_directory = r"C:\Knowledge_Base\Knowledge_Base\periodic\daily\2026"

    try:
        strategies = [
            DiaryFormatStrategy(),
        ]
        
        updater = DailyNoteUpdater(notes_directory, strategies=strategies, backup=True)
        updater.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    #main()
    pass