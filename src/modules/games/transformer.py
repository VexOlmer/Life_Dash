"""Модуль обработки заметок об играх."""

from pathlib import Path

import frontmatter

from src.core.config import settings
from src.core.exceptions import ValidationError
from src.core.logger import logger

from .models import Game

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

class GameTransformer:
    """Трансформер для обработки YAML игр."""
    
    @staticmethod
    def transform(file_path: Path, vault_path: Path, mtime: float) -> Game:
        """
            Превращает Markdown файл в объект Game.
            
            Args:
                file_path: Полный путь к Mardown файлу
                vault_path: Полный путь к базе знаний Obsidian
                mtime: Время последнего обновления
            
            Returns:
                Game: Готовая модель класса Game
        """
        
        logger.debug(f"Начало обработки игры: {file_path.name}")
        
        try:
            post = frontmatter.load(file_path)
        except Exception as e:
            raise ValidationError(f"Ошибка структуры YAML: {e}") from e
        
        meta = post.metadata
        
        # --- 1. Проверка обязательных полей для шаблона заметки игры ---
        required_fields = [
            "title_orig", "year", "status", "genres",
            "developer", "country_dev", "publisher", "country_pub",
            "hours_played", "hours_to_beat",
            "play_log", "bg_color", "text_color",
            "metacritic", "steam", "igdb",
            "rating_optimization", "rating_graphics", "rating_audio", "rating_gameplay",
            "rating_price_quality", "rating_story_lore", "rating_immersion", 
            "rating_replayability", "rating_expected_real", "rating_cult_status"
        ]
        missing = [f for f in required_fields if f not in meta or meta.get(f) is None]
        if missing:
            raise ValidationError(f"В заметке отсутствуют обязательные поля: {', '.join(missing)}")
        
        # --- 2. Поиск обложки (files/covers/games/Название_файла.ext) ---
        game_filename = file_path.stem
        covers_dir = vault_path / settings.COVERS_GAMES_PATH
        detected_cover = None
        
        if covers_dir.exists():
            for ext in IMAGE_EXTENSIONS:
                potential_file = covers_dir / f"{game_filename}{ext}"
                if potential_file.exists():
                    detected_cover = str(potential_file.relative_to(vault_path))
                    break

        # --- 3. Обработка play_log (превращаем список из YAML в строку "||") ---
        raw_log = meta.get("play_log", [])
        if isinstance(raw_log, list):
            # Фильтруем пустые записи и склеиваем
            play_log_str = " || ".join([str(e).strip() for e in raw_log if e])
        else:
            play_log_str = str(raw_log) if raw_log else None
            
        # --- 4. Обработка достижений ---
        raw_achievements = meta.get("achievements") 
        achievements_str = str(raw_achievements).strip() if raw_achievements is not None else None
        percent_achievements = Game.calculate_percentage(achievements_str)

        # --- 5. Сборка модели ---
        return Game(
            title=meta.get("title", file_path.stem),
            title_orig=meta.get("title_orig"),
            
            year=int(meta.get("year", 0)),
            status=meta.get("status", "plan"),
            genres=str(meta.get("genres", "")),
            series=meta.get("series"),
            
            # Информация о покупке игры
            price=int(meta.get("price", 0)) if meta.get("price") else None,
            purchase_date=str(meta.get("purchase_date", None)),
            digital_dist=meta.get("digital_dist", None),
            
            # Компания Разработчика и Издателя
            developer = meta.get("developer"),
            country_dev = meta.get("country_dev"),
            publisher = meta.get("publisher"),
            country_pub = meta.get("country_pub"),
            
            # Кол-во часов и Процент достижений
            hours_played=float(meta.get("hours_played", 0.0)),
            hours_to_beat=float(meta.get("hours_to_beat", 0.0)) if meta.get("hours_to_beat") else None,
            achievements=achievements_str,
            percent_achievements=percent_achievements,
            
            # Логи игровых сессий
            play_log=play_log_str,

            # Цвета и Обложка
            bg_color=str(meta.get("bg_color", "#ffffff")),
            text_color=str(meta.get("text_color", "#000000")),
            cover=detected_cover,
            
            # Внешние Рейтинги и ID с сайта IGDB
            metacritic=meta.get("metacritic"),
            steam=meta.get("steam"),
            igdb=str(meta.get("igdb", "")) if meta.get("igdb") else None,
            
            # Рейтинги (10 параметров)
            rating_optimization=meta.get("rating_optimization", 0),
            rating_graphics=meta.get("rating_graphics", 0),
            rating_audio=meta.get("rating_audio", 0),
            rating_gameplay=meta.get("rating_gameplay", 0),
            rating_price_quality=meta.get("rating_price_quality", 0),
            rating_story_lore=meta.get("rating_story_lore", 0),
            rating_immersion=meta.get("rating_immersion", 0),
            rating_replayability=meta.get("rating_replayability", 0),
            rating_expected_real=meta.get("rating_expected_real", 0),
            rating_cult_status=meta.get("rating_cult_status", 0),
            
            file_path=file_path.relative_to(vault_path).as_posix(),
            last_modified=mtime,
            created_at=str(meta.get("created", "")),
        )