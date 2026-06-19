"""Утилиты для преобразования данных (перевод, форматирование)."""

TRANSLATIONS: dict[str, str] = {
    
    # Статусы
    "plan": "В планах",
    "reading": "Читаю",
    "finished": "Завершено",
    "dropped": "Брошено",
    "playing": "Играю",
    "watched": "Просмотрено",

    # Форматы
    "paper": "Бумажная книга",
    "electronic": "Электронная книга",
    "audio": "Аудиокнига",

    # Основные жанры
    "fantasy": "Фэнтези",
    "sci-fi": "Научная фантастика",
    "thriller": "Триллер",
    "drama": "Драма",
    "horror": "Ужасы",
    "adventure": "Приключения",
    "romance": "Романтика",
    "detective": "Детектив",
    "mystery": "Мистика",
    "crime": "Криминал",
    "spy-fiction": "Шпионский",
    "non-fiction": "Документальный",
    "historical": "Исторический",
    "gothic": "Готика",
    "self-help": "Саморазвитие",
    "biography": "Биография",
    "travel": "Путешествия",
    "science": "Наука",
    "philosophy": "Философия",
    "business": "Бизнес",
    "poetry": "Поэзия",
    "classic": "Классика",
    "comedy": "Комедия",
    "animation": "Анимация",
    "sitcom": "Ситком",

    # --- Поджанры (универсально для всех категорий) ---
    
    # Fantasy
    "high": "высокое",
    "epic": "эпическое",
    "dark": "тёмное",
    "neutral": "нейтральное",
    "light": "светлое",
    "heroic": "героическое",
    "urban": "городское",
    "mythic": "мифологическое",
    
    # Sci-fi
    "hard": "сложная",
    "space-opera": "космическая опера",
    "cyberpunk": "киберпанк",
    "dystopian": "антиутопия",
    "post-apocalyptic": "постапокалиптика",
    "time-travel": "путешествие во времени",
    "alien-invasion": "инопланетное вторжение",
    "military": "военная",
    
    # Thriller
    "psychological": "психологическая",
    "action": "Экшен",
    "conspiracy": "заговор",
    "legal": "юридическая",
    
    # Drama
    "social": "социальная",
    "family": "семейная",
    "war": "военная",
    
    # Horror
    "supernatural": "сверхъестественное",
    "body": "боди-хоррор",
    "cosmic": "лавкрафтовский ужас",
    "slasher": "слэшер",
    
    "rating_characters": "Герои",
    "rating_plot": "Сюжет",
    "rating_size": "Объем",
    "rating_prose": "Слог",
    "rating_ending": "Финал",
    "rating_depth": "Глубина",
    "rating_atmosphere": "Атмосфера",
    "rating_rereadability": "Перечитывание",
    "rating_expected_real": "Ожидание / Реальность",
    "rating_recommend": "Рекомендация",
    
    # Языки
    "russian": "Русский",
    "english": "Английский",
    "ru": "Русский",
    "en": "Английский",
       
    # Доп жанры из игр
    "shooter": "Шутер",
    "rpg": "RPG",
    "strategy": "Стратегия",
    "simulation": "Симулятор",
    "sports": "Спортивная",
    "racing": "Гонки",
    "sandbox": "Песочница",
    "survival": "Выживание",
    "puzzle": "Головоломка",
    "platformer": "Платформер",
    "fighting": "Файтинг",
    "zombie": "Зомби",
    "graphic adventure": "Квест",
    "interactive drama": "Интерактивное кино",
    "soulslike": "Soulslike",
    "vr": "VR",
    "indie": "Инди",
    "pixel-art": "Пиксель-арт",

    # Доп рейтинги из игр
    "rating_optimization": "Оптимизация",
    "rating_graphics": "Графика",
    "rating_audio": "Аудио",
    "rating_gameplay": "Геймплей",
    "rating_price_quality": "Цена/Качество",
    "rating_story_lore": "Сюжет и Лор",
    "rating_immersion": "Погружение",
    "rating_replayability": "Реиграбельность",
    "rating_cult_status": "Культовость",
    
    # Платформы
    "youtube": "YouTube",
    "twitch": "Twitch",
}

def translate(key: str | None) -> str:
    """Переводит технический термин на русский. Если перевода нет, возвращает оригинал."""
    if not key:
        return "-"
    
    # Пытаемся найти ключ в словаре (приводим к нижнему регистру на случай опечаток)
    low_key = key.lower().strip()
    return TRANSLATIONS.get(low_key, key.capitalize())