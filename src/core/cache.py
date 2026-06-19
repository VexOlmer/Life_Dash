"""Формирование кеша статистики главной страницы."""

from typing import Any


class StatsCache:
    """Кеш статистики с главной страницы. Обновляется каждый раз после синхронизации."""
    def __init__(self) -> None:
        """Создаем пустой кеш статистики главной страницы."""
        self._data: dict[str, Any] | None = None

    def get(self) -> dict[str, Any] | None:
        """Возвращаем текущий кеш статистики."""
        return self._data

    def set(self, data: dict[str, Any]) -> None:
        """Обновление текущего кеша."""
        self._data = data

    def clear(self) -> None:
        """Очистка текущего кеша."""
        self._data = None

stats_cache = StatsCache()