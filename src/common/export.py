"""Функционал сохранения основных данных из БД в файл Excel по модулями Игры, Книги, Фильмы/Сериалы."""

import os
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlmodel import Session, desc, select

from src.core.logger import logger
from src.modules.books.models import Book
from src.modules.games.models import Game


class ExportService:
    """Класс для формирования Ecxel документа с основынми информациями по заметкам из модулей."""
    @staticmethod
    def get_downloads_path() -> Path:
        """Определяет путь к папке Загрузки для Windows/Mac/Linux."""
        if os.name == 'nt':  # Windows
            import winreg
            sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                return Path(winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0])
        return Path.home() / "Downloads"

    @staticmethod
    def get_unique_filename(base_name: str) -> Path:
        """Генерирует уникальное имя файла в папке Загрузки, добавляя (1), (2) и т.д."""
        downloads = ExportService.get_downloads_path()
        filename = downloads / f"{base_name}.xlsx"
        
        if not filename.exists():
            return filename
        
        counter = 1
        while True:
            filename = downloads / f"{base_name} ({counter}).xlsx"
            if not filename.exists():
                return filename
            counter += 1

    @staticmethod
    def hex_to_openpyxl(hex_color: str) -> str:
        """Конвертирует #RRGGBB в RRGGBB (формат openpyxl)."""
        if not hex_color:
            return "FFFFFF"
        return hex_color.lstrip('#').upper()

    @staticmethod
    def export_all_data(session: Session) -> str:
        """Основная функция формирования Excel файла."""
        
        # --- 1. Получаем данные с сортировкой по рейтингу ---
        books = session.exec(select(Book).order_by(desc(Book.total_rating))).all()
        games = session.exec(select(Game).order_by(desc(Game.total_rating))).all()

        wb = Workbook()
        
        # --- 2. Лист Книги ---
        ws_books = wb.active
        ws_books.title = "Книги"
        
        book_headers = [
            "Рейтинг", "Название", "Автор", "Страна", 
            "Герои", "Сюжет", "Объем", "Слог", "Финал", "Глубина", "Атмосфера", "Перечитывание", "Ожидание", "Рекомендация",
            "Жанры", "GoodReads", "Год", "Страниц", "Статус"
        ]
        ws_books.append(book_headers)

        for b in books:
            # Собираем жанры как в детальной карточке (на русском)
            genres_str = "; ".join([f"{g['name']} ({g['sub']})" if g['sub'] else g['name'] 
                                   for g in b.detailed_genres_list_ru])
            
            row = [
                b.total_rating, b.title, b.author, b.country_author,
                b.rating_characters, b.rating_plot, b.rating_size, b.rating_prose, b.rating_ending,
                b.rating_depth, b.rating_atmosphere, b.rating_rereadability, b.rating_expected_real, b.rating_recommend,
                genres_str, b.good_reads, b.year, b.total, b.status_ru
            ]
            ws_books.append(row)
            
            # Красим строку
            ExportService.style_row(ws_books, ws_books.max_row, b.bg_color, b.text_color)

        # --- 3. Лист Игры ---
        ws_games = wb.create_sheet("Игры")
        game_headers = [
            "Рейтинг", "Название", "Разработчик", "Страна (Р)", "Издатель", "Страна (И)",
            "Оптимизация", "Графика", "Звук", "Геймплей", "Цена/Качество", "Сюжет", "Погружение", "Реиграбельность", "Ожидание", "Культовость",
            "Жанры", "Steam", "Metacritic", "Год", "Часы", "Достижения (%)", "Статус"
        ]
        ws_games.append(game_headers)

        for g in games:
            genres_str = ", ".join(g.genres_list_ru)
            row = [
                g.total_rating, g.title, g.developer, g.country_dev, g.publisher, g.country_pub,
                g.rating_optimization, g.rating_graphics, g.rating_audio, g.rating_gameplay, g.rating_price_quality,
                g.rating_story_lore, g.rating_immersion, g.rating_replayability, g.rating_expected_real, g.rating_cult_status,
                genres_str, g.steam, g.metacritic, g.release_date_ru, g.hours_played, g.percent_achievements, g.status_ru
            ]
            ws_games.append(row)
            
            # Красим строку
            ExportService.style_row(ws_games, ws_games.max_row, g.bg_color, g.text_color)

        # Авто-подбор ширины колонок и стилизация шапок
        for sheet in wb.worksheets:
            ExportService.format_sheet(sheet)

        # Сохранение
        file_path = ExportService.get_unique_filename("Knowledge base ratings")
        wb.save(file_path)
        return file_path

    @staticmethod
    def style_row(ws: Workbook, row_idx: str, bg_hex: str, text_hex: str) -> None:
        """Применяет цвета фона и текста к строке."""
        fill = PatternFill(start_color=ExportService.hex_to_openpyxl(bg_hex),
                           end_color=ExportService.hex_to_openpyxl(bg_hex),
                           fill_type="solid")
        font = Font(color=ExportService.hex_to_openpyxl(text_hex), bold=True)
        
        for cell in ws[row_idx]:
            cell.fill = fill
            cell.font = font
            cell.alignment = Alignment(horizontal="center", vertical="center")

    @staticmethod
    def format_sheet(ws: Workbook) -> None:
        """Красивое оформление: жирная шапка и авто-ширина."""
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception as e:
                    logger.warning(f"Ошибка оформления формирующегося Excel файла по модулям. Ошибка - {e}")
                    pass
            ws.column_dimensions[column].width = min(max_length + 2, 40)