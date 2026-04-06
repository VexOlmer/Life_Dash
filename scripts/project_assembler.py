"""
    Сборка всех файлов в один общий .txt файл с созданием дерева архитектуры
"""

import os
from pathlib import Path


def assemble_project_code(output_filename="project_snapshot.txt"):
    """
        Сборка всех файлов в один общий .txt файл с созданием дерева архитектуры.
        
        Args:
            output_filename (str) - Наименование выходного файла.
        
        Returns:
            None
            
        Raises:
            Нет явных исключений.
    """
    
    # Определение корневой директории проекта (три уровня вверх от текущего файла)
    root_dir = Path(__file__).resolve().parent.parent
    output_path = root_dir / output_filename

    # Исключения папок
    excluded_dirs = {
        '.git', '__pycache__', '.venv', 'venv', 'env', 
        'data', 'logs', 'node_modules', '.idea', '.vscode', 'tests'
    }
    # Исключения расширения папок
    excluded_extensions = {
        '.sqlite', '.log', '.pyc', '.png', '.jpg', '.jpeg', 
        '.gif', '.svg', '.pdf', '.exe', '.bin', '.sqlite-journal', '.txt'
    }
    # Конкретные исключения файлов
    excluded_files = {
        output_filename, '.env', 'package-lock.json', 'poetry.lock', '.gitignore', 'LICENSE', 'README.md',
        'pyproject.toml', 'mass_update_daily_notes.py', 'project_assembler.py'
    }


    def generate_tree(current_dir, prefix=""):
        """
            Рекурсивно создает древовидную структуру проекта.
            
            Args:
                current_dir (str)   - Текущая директория для анализа;
                prefix (str)        - Префикс для форматирования дерева (отступы).
            
            Returns:
                (list) - Список строк с древовидной структурой.
                
            Raises:
                Нет явных исключений.
        """
        
        tree = []
        # Получаем список элементов, фильтруя исключения
        items = [i for i in os.listdir(current_dir) 
                 if i not in excluded_dirs and i not in excluded_files]
        
        # Сортируем: сначала папки, потом файлы
        items.sort(key=lambda x: (not os.path.isdir(os.path.join(current_dir, x)), x.lower()))

        for i, item in enumerate(items):
            path = os.path.join(current_dir, item)
            is_last = (i == len(items) - 1)  # Проверка, последний ли элемент в списке
            connector = "└── " if is_last else "├── "  # Выбор символа ветвления
            
            tree.append(f"{prefix}{connector}{item}")
            
            if os.path.isdir(path):
                # Формируем новый префикс для вложенных элементов
                new_prefix = prefix + ("    " if is_last else "│   ")
                tree.extend(generate_tree(path, new_prefix))
        return tree


    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write(f"# Project Snapshot: Obsidian Analytics\n\n")
        
        # 1. Генерируем и записываем архитектуру проекта
        outfile.write("## Project Architecture\n")
        outfile.write("```text\n")
        outfile.write(f"{root_dir.name}/\n")
        tree_lines = generate_tree(root_dir)
        outfile.write("\n".join(tree_lines))
        outfile.write("\n```\n\n---\n\n")

        # 2. Обходим файлы и записываем их содержимое
        outfile.write("## File Contents\n\n")
        for root, dirs, files in os.walk(root_dir):
            # Фильтрация исключенных директорий прямо во время обхода
            dirs[:] = [d for d in dirs if d not in excluded_dirs]

            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(root_dir)

                # Пропускаем файлы с исключенными расширениями или именами
                if file_path.suffix.lower() in excluded_extensions or file in excluded_files:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                    
                    outfile.write(f"### FILE: `{relative_path}`\n")
                    
                    # Определение языка для подсветки синтаксиса
                    lang = file_path.suffix.lstrip('.')
                    if lang == 'py':
                        lang = 'python'
                    
                    outfile.write(f"```{lang}\n")
                    outfile.write(content)
                    outfile.write(f"\n```\n\n---\n\n")
                    
                except Exception as e:
                    outfile.write(f"### FILE: `{relative_path}`\n")
                    outfile.write(f"Error reading file: {e}\n\n---\n\n")

    print(f"Сборка завершена! Архитектура и код сохранены в: {output_path}")


if __name__ == "__main__":
    assemble_project_code()