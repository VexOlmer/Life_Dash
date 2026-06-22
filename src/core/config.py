"""Модуль конфигурации приложения."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

Path("data").mkdir(exist_ok=True)

class Settings(BaseSettings):
    """
        Настройки приложения, загружаемые из .env файла.

        Attributes:
            OBSIDIAN_VAULT_PATH: Абсолютный путь к базе знаний Obsidian.
            BOOKS_PATH: Путь к книгам относительно корня Vault.
            GAMES_PATH: Путь к играм относительно корня Vault.
            MOVIES_PATH: Путь к фильмам относительно корня Vault.
            SERIES_PATH: Путь к сериалам относительно корня Vault.
            DAILY_PATH: Путь к дневным заметкам относительно корня Vault.
            WEEKLY_PATH: Путь к недельным заметкам относительно корня Vault.
            DATABASE_URL: URL подключения к базе данных SQLite.
            DEBUG: Режим отладки.
            HOST: Хост для запуска сервера.
            PORT: Порт для запуска сервера.
    """

    OBSIDIAN_VAULT_PATH: Path

    BOOKS_PATH: str = "notes/books"
    GAMES_PATH: str = "notes/games"
    MOVIES_PATH: str = "notes/movies_series/movies"
    SERIES_PATH: str = "notes/movies_series/series"
    DAILY_PATH: str = "periodic/daily"
    
    COVERS_BOOKS_PATH: str = "files/covers/books"
    COVERS_GAMES_PATH: str = "files/covers/games"

    DATABASE_URL: str = "sqlite:///./data/db.sqlite"

    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Настройка поиска .env файла внутри папки src/core
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Группировка тегов временных логов
    TIME_CATEGORIES: dict[str, list[str]] = {
        "Развитие": ["study", "programming", "science", "language", "reading"],
        "Досуг": ["gaming", "movie", "series", "channel", "social"],
        "Работа": ["work", "project"],
        "Жизнь": ["sport", "routine", "hobby", "health"]
    }

    # Недельние бюджеты времени
    TIME_BUDGETS: dict[str, int] = {
        "Развитие": 15,    # ~2 часа в день
        "Досуг": 10,       # лимит
        "Работа": 40,      # стандарт
        "Жизнь": 12        # спорт, быт
    }


settings = Settings()