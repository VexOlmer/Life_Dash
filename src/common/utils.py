"""Утилиты для преобразования данных (перевод, форматирование)."""

import re

from src.core.logger import logger

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
    "co-op": "Кооператив",

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

def parse_duration_to_minutes(dur_str: str | None) -> int:
    """
        Универсальный парсер строки времени в минуты.
        
        Поддерживает форматы: '1h 20m', '2h', '45m', '01:30'.
        
        Args:
            dur_str: Строка с указанием потраченного времени.
            
        Returns:
            int: Кол-во минут.
    """
    
    if not dur_str:
        return 0
    
    total = 0
    dur_str = str(dur_str).lower().strip()

    # --- 1. Проверка формата ЧЧ:ММ ---
    if ":" in dur_str:
        try:
            parts = dur_str.split(":")
            if len(parts) >= 2:
                return int(parts[0]) * 60 + int(parts[1])
        except ValueError as e:
            raise ValueError(f"Ошибка обработки строки временной затраты. Ошибка - {e}") from e

    # --- 2. Определение части с часами и минутами (1h 20m) ---
    h_match = re.search(r'(\d+)\s*h', dur_str)
    m_match = re.search(r'(\d+)\s*m', dur_str)
    
    if h_match:
        total += int(h_match.group(1)) * 60
    if m_match:
        total += int(m_match.group(1))

    # --- 3. Если просто число ("45"), считаем за минуты ---
    if not h_match and not m_match and dur_str.isdigit():
        total = int(dur_str)

    return total

def format_minutes_to_pretty(total_minutes: int) -> str:
    """Конвертирует минуты в строку вида '2ч 15м' или '45м'."""
    if total_minutes <= 0:
        return "-"
    
    h = total_minutes // 60
    m = total_minutes % 60
    
    if h > 0 and m > 0:
        return f"{h}ч {m}м"
    if h > 0:
        return f"{h}ч"
    return f"{m}м"

def format_date_ru(date_iso: str) -> str:
    """Превращает YYYY-MM-DD в DD.MM.YYYY для отображения."""
    if not date_iso or len(date_iso) < 10:
        return "-"
    y, m, d = date_iso.split("-")
    return f"{d}.{m}.{y}"

def extract_section(content: str, keyword: str) -> str:
    """
        Вырезает текст секции Markdown, ограниченный заголовками ##.
        
        Args:
            content: Весь текст заметки.
            keyword: Ключевое слово для поиска в заголовке (напр. 'Мысли').
            
        Returns:
            str: Очищенный текст секции или пустая строка.
    """
    
    # Паттерн: 
    # (?m)^## - начало строки с ##
    # [^\n]*?{re.escape(keyword)}[^\n]* - заголовок, содержащий ключевое слово
    # \n(.*? ) - захват контента до...
    # (?=\n##(?![#])|\n---|\Z) - ...следующего заголовка ##, разделителя --- или конца файла
    pattern = rf"(?m)^##\s+[^\n]*?{re.escape(keyword)}[^\n]*\n(.*?)(?=\n##(?![#])|\n---|\Z)"
    
    match = re.search(pattern, content, flags=re.DOTALL)
    if match:
        text = match.group(1).strip()
        logger.debug(f"Секция '{keyword}' извлечена ({len(text)} симв.)")
        return text
    
    return ""