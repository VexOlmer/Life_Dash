"""Роутер для основных страниц сайта."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from src.core.database import get_session
from src.core.logger import logger
from src.modules.books.models import Book


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

router = APIRouter(tags=["Web"])
templates = Jinja2Templates(directory="src/web/templates")
SessionDep = Annotated[Session, Depends(get_session)]

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, session: SessionDep) -> HTMLResponse:
    """Подсчитывание общей статистики для главной страницы."""
    
    # Проверяем наличие данных в кэше
    cached_stats = stats_cache.get()
    if cached_stats:
        logger.debug("Статистика взята из кеша.")
        return templates.TemplateResponse(
            "pages/index.html", {"request": request, "stats": cached_stats}
        )

    # Если кэша нет — считаем
    total_books = session.exec(select(func.count()).select_from(Book)).one()
    total_pages = session.exec(select(func.sum(Book.total))).one() or 0
    avg_rating = session.exec(select(func.avg(Book.total_rating))).one() or 0
    finished_books = session.exec(select(func.count()).where(Book.status == "finished")).one()
    reading_books = session.exec(select(func.count()).where(Book.status == "reading")).one()

    new_stats = {
        "books": {
            "total": total_books,
            "pages": total_pages,
            "avg": round(avg_rating, 1),
            "finished": finished_books,
            "reading": reading_books
        }
    }
    logger.debug(f"Обновленная статистика - {new_stats}")
    
    # Обновляем кеш
    stats_cache.set(new_stats)

    return templates.TemplateResponse(
        "pages/index.html", {"request": request, "stats": new_stats}
    )