"""
    Массовое обновление ежедневных заметок Obsidian для добавления анкерных комментариев.

    Основные функции:
        - Добавление анкеров в секцию общей активности
        - Добавление анкеров для вечерней прогулки (вложенный блок)
        - Добавление анкеров для каждого типа тренировок (силовая, кардио, велосипед, бассейн, лыжи)
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple


class DailyNoteUpdater:
    """
        Класс для массового добавления комментариев-анкеров в сущеставующие ежедневные заметки.
    """
    
    def __init__(self, notes_dir: str, backup: bool = True):
        """
            Инициализация обновлятора заметок.
            
            Args:
                notes_dir (str) - Путь к директории с файлами заметок.
                backup (bool)   - Флаг создания резервных копий.
            
            Returns:
                None
            
            Raises:
                FileNotFoundError   - Если указанная директория не существует.
                NotADirectoryError  - Если указанный путь не является директорией.
        """
        
        self.notes_dir = Path(notes_dir)
        
        if not self.notes_dir.exists():
            raise FileNotFoundError(f"Директория не найдена: {notes_dir}")
        
        if not self.notes_dir.is_dir():
            raise NotADirectoryError(f"Указанный путь не является директорией: {notes_dir}")
        
        self.backup = backup
        self.stats = {
            'processed': 0,      # Всего обработано файлов
            'updated': 0,        # Файлов, в которые внесены изменения
            'skipped': 0,        # Файлов, пропущенных (без изменений)
            'errors': 0          # Файлов, при обработке которых возникли ошибки
        }
        
        # Паттерн для поиска секции общей активности
        self.general_activity_pattern = re.compile(
            r'(### Общая активность\n)(.*?)(?=\n### Тренировки|\n## |$)',
            re.DOTALL
        )
        
        # Паттерны для поиска блоков тренировок
        self.training_patterns = {
            r'#### 🏋️ Силовая': 'STRENGTH',
            r'#### ❤️ Кардио': 'CARDIO',
            r'#### 🚴 Велосипед': 'BIKE',
            r'#### 🏊 Бассейн': 'SWIM',
            r'#### ⛷️ Лыжи': 'SKI',
        }
    
    
    def backup_file(self, filepath: Path) -> Path:
        """
            Создает резервную копию файла.
            
            Args:
                filepath (Path) - Путь к исходному файлу.
            
            Returns:
                Path - Путь к созданной резервной копии.
            
            Raises:
                IOError - Если не удалось создать резервную копию.
        """
        try:
            backup_path = filepath.with_suffix(filepath.suffix + '.backup')
            content = filepath.read_text(encoding='utf-8')
            backup_path.write_text(content, encoding='utf-8')
            
            return backup_path
            
        except Exception as e:
            raise IOError(f"Не удалось создать резервную копию {filepath.name}: {e}")
    
    
    def add_anchors_to_general_activity(self, content: str) -> str:
        """
            Добавляет анкеры в секцию общей активности и для вечерней прогулки.
            
            Функция ищет секцию "### Общая активность" и оборачивает её в анкеры
                <!-- GENERAL_ACTIVITY_START --> и <!-- GENERAL_ACTIVITY_END -->.
            Также внутри секции ищет блок вечерней прогулки и оборачивает его
                в анкеры <!-- WALK_START --> и <!-- WALK_END -->.
            
            Args:
                content (str) - Исходное содержимое заметки.
            
            Returns:
                str - Содержимое с добавленными анкерами.
                        Если анкеры уже присутствуют, возвращает исходное содержимое.
            
            Raises:
                Нет явных исключений. В случае ошибок регулярных выражений
                    возвращается исходное содержимое.
        """
        
        # Ищем секцию общей активности
        match = self.general_activity_pattern.search(content)
        if not match:
            return content
        
        header = match.group(1)
        body = match.group(2)
        body = re.sub(r'\n\s*\n+', '\n', body)      # Удаление дублирующихся переносов строк
        
        # Проверяем, есть ли уже анкер
        if '<!-- GENERAL_ACTIVITY_START -->' in body:
            return content
        #print(f"\nHeader:\n----------{header}\n----------nBody:\n----------{body}\n----------n")
        
        # Начинаем с открывающего анкера
        new_body = '<!-- GENERAL_ACTIVITY_START -->\n' + body
        
        # Добавляем анкер для прогулки, если секция прогулки существует
        if '- 🌙 Вечерняя прогулка:' in body:
            walk_match = re.search(r'(- 🌙 Вечерняя прогулка:\n(?:  - .*\n)*)', new_body, re.DOTALL)
            if walk_match and '<!-- WALK_START -->' not in walk_match.group(1):
                walk_block = walk_match.group(1)
                new_body = new_body.replace(
                    walk_block,
                    f'\n<!-- WALK_START -->\n{walk_block}<!-- WALK_END -->\n\n'
                )
        
        #print(f"New body:\n----------\n{new_body}\n----------")
        
        if (new_body.endswith('---')):
            # Убираем исходный ---
            new_body_correct = new_body[:-3]
            new_body_correct += '<!-- GENERAL_ACTIVITY_END -->\n\n---'
        else:
            new_body_correct = new_body
            new_body_correct += '<!-- GENERAL_ACTIVITY_END -->\n\n---'
        
        # Замена старого текста на новый
        full_match = match.group(0)
        new_section = header + new_body_correct
        #print(f"New_section:\n\n{new_section}\n")
            
        return content.replace(full_match, new_section)
        

    def add_anchors_to_trainings(self, content: str) -> str:
        """
            Добавляет анкеры для каждого типа тренировок.
            
            Функция ищет блоки тренировок (силовая, кардио, велосипед, бассейн, лыжи)
                и оборачивает каждый блок в соответствующие анкеры:
                    <!-- {TYPE}_START --> и <!-- {TYPE}_END -->.
            
            Args:
                content (str) - Исходное содержимое заметки.
            
            Returns:
                str - Содержимое с добавленными анкерами для тренировок.
                        Если анкеры уже присутствуют, возвращает исходное содержимое.
            
            Raises:
                Нет явных исключений.
        """
            
        for pattern, anchor_name in self.training_patterns.items():
            # Ищем все блоки тренировок
            training_regex = re.compile(
                rf'({pattern}.*?)(?=\n#### |\n## |$)',
                re.DOTALL
            )
            
            # Находим все совпадения
            matches = list(training_regex.finditer(content))
            
            # Идем в обратном порядке, чтобы не сломать индексы
            for match in reversed(matches):
                block = match.group(1)
                block_start = match.start(1)
                block_end = match.end(1)
                #print(f"Блок:\n----------\n{block}\n----------\n")
                
                # Если в заметке уже есть нужный анкер, пропускаем
                if f'<!-- {anchor_name}_START -->' in content:
                    continue
                
                if (block.endswith('---')):
                    # Убираем исходный ---
                    block = block[:-3]
                block = block.removesuffix('\n')
                block = block.removesuffix('\n')
                
                # Создаем новый блок с анкерами
                new_block = f'<!-- {anchor_name}_START -->\n{block}\n<!-- {anchor_name}_END -->\n\n---'
                #print(f"Блок:\n----------\n{new_block}\n----------\n")
                
                content = content[:block_start] + new_block + content[block_end:]
        
        return content
        
    
    def update_file(self, filepath: Path) -> bool:
        """
            Обновляет один файл заметки, добавляя анкеры.
            
            Процесс обновления:
                1. Чтение содержимого файла
                2. Добавление анкеров в секцию общей активности
                3. Добавление анкеров для тренировок
                4. Если были изменения, создание резервной копии (если включено)
                5. Запись обновленного содержимого
            
            Args:
                filepath (Path) - Путь к файлу заметки для обновления.
            
            Returns:
                bool - True если файл был обновлен, False если изменений не требовалось.
            
            Raises:
                IOError         - При ошибках чтения/записи файла.
                PermissionError - При отсутствии прав доступа.
        """
        
        try:
            content = filepath.read_text(encoding='utf-8')
            original_content = content
            
            # Проверяем/Добавляем анкеры
            content = self.add_anchors_to_general_activity(content)
            content = self.add_anchors_to_trainings(content)
            
            if content != original_content:
                if self.backup:
                    self.backup_file(filepath)
                
                filepath.write_text(content, encoding='utf-8')
                return True
            
            return False
            
        except (IOError, PermissionError) as e:
            print(f"  ❌ Ошибка: {e}")
            self.stats['errors'] += 1
            
            return False
        
        except Exception as e:
            print(f"  ❌ Неожиданная ошибка: {e}")
            self.stats['errors'] += 1
            
            return False
    
    
    def run(self) -> Dict[str, int]:
        """
            Запускает процесс обновления всех заметок в директории.
            
            Выполняет:
                1. Поиск всех .md файлов в указанной директории (рекурсивно)
                2. Обработку каждого файла с обновлением
                3. Сбор статистики по обработке
            
            Args:
                None
            
            Returns:
                Dict[str, int]: Словарь со статистикой обработки:
                    'processed' - количество обработанных файлов
                    'updated'   - количество обновленных файлов
                    'skipped'   - количество пропущенных файлов
                    'errors'    - количество файлов с ошибками
            
            Raises:
                Нет явных исключений. Ошибки отдельных файлов логируются,
                    но не прерывают выполнение.
        """
        
        # Ищем все .md файлы в директории и поддиректориях
        all_files = list(self.notes_dir.glob('**/*.md'))
        
        print(f"\n{'='*60}")
        print(f"Начало обработки файлов в директории: {self.notes_dir}")
        print(f"Найдено файлов: {len(all_files)}")
        print(f"Создание резервных копий: {'Да' if self.backup else 'Нет'}")
        print(f"{'='*60}\n")
        
            
        # Фильтруем файлы резервных копий
        md_files = [f for f in all_files if f.suffix != '.backup']
        
        # Сортируем файлы по дате из имени (формат: dd-mm-yyyy)
        def extract_date(filepath: Path) -> tuple:
            """
                Извлекает дату из имени файла для сортировки.
                Формат имени: dd-mm-yyyy.md или любой текст с датой в таком формате
            """
            
            name = filepath.stem
            
            date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', name)
            if date_match:
                day, month, year = date_match.groups()
                # Возвращаем кортеж для сортировки: год, месяц, день
                return (int(year), int(month), int(day))
            else:
                # Если дата не найдена, отправляем в конец с максимальной датой
                return (9999, 99, 99)
        
        # Сортируем файлы по дате
        md_files.sort(key=extract_date)
        
        
        for filepath in md_files:
            # Пропускаем файлы резервных копий
            if filepath.suffix == '.backup':
                continue
            
            self.stats['processed'] += 1
            
            print(f"[{self.stats['processed']}/{len(md_files)}] {filepath.name}")
            
            if self.update_file(filepath):
                self.stats['updated'] += 1
                print(f"  ✅ Обновлен")
            else:
                self.stats['skipped'] += 1
                print(f"  ⏭️ Пропущен (нет изменений или ошибка)")
        
        
        print(f"\n{'='*60}")
        print("СТАТИСТИКА ОБРАБОТКИ")
        print(f"{'='*60}")
        print(f"📁 Обработано файлов:  {self.stats['processed']}")
        print(f"✅ Обновлено:          {self.stats['updated']}")
        print(f"⏭️ Пропущено:          {self.stats['skipped']}")
        print(f"❌ Ошибок:             {self.stats['errors']}")
        print(f"{'='*60}")
        
        
        if self.backup:
            print("\n💾 Резервные копии созданы с расширением .backup")
            print("   Для восстановления удалите .backup из имени файлов")
        
        return self.stats


def main():
    """
        Главная функция для запуска обновления заметок.
        
        Выполняет:
            1. Получение пути к директории с заметками
            2. Создание экземпляра обновлятора
            3. Запуск процесса обновления
            4. Обработка возможных ошибок
        
        Args:
            None
        
        Returns:
            None
        
        Raises:
            KeyboardInterrupt   - При прерывании пользователем.
            Exception           - При критических ошибках выполнения.
    """
    
    NOTES_DIRECTORY = r"C:\Knowledge_Base\Knowledge_Base\periodic\daily\2025"
    
    try:
        updater = DailyNoteUpdater(NOTES_DIRECTORY, backup=False)
        
        # Запускаем обновление
        updater.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Обновление прервано пользователем")
        print("Файлы остались в текущем состоянии")
        
    except FileNotFoundError as e:
        print(f"\n❌ Ошибка: {e}")
        print("Проверьте правильность пути к директории с заметками")
        
    except PermissionError as e:
        print(f"\n❌ Ошибка доступа: {e}")
        print("Убедитесь, что у вас есть права на чтение/запись файлов")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        print("Обратитесь к разработчику или проверьте логи")
        
        raise


if __name__ == "__main__":
    #main()
    
    pass
    