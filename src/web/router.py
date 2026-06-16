"""Роутер для основных страниц сайта."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from src.core.cache import stats_cache
from src.core.database import get_session
from src.core.logger import logger
from src.modules.books.models import Book
from src.modules.games.models import Game

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

    # --- Статистика блока книг ---
    total_books = session.exec(select(func.count()).select_from(Book)).one()
    total_pages = session.exec(select(func.sum(Book.total))).one() or 0
    avg_rating = session.exec(select(func.avg(Book.total_rating))).one() or 0
    finished_books = session.exec(select(func.count()).where(Book.status == "finished")).one()
    reading_books = session.exec(select(func.count()).where(Book.status == "reading")).one()
    
    # --- Статистика блока игр ---
    total_games = session.exec(select(func.count()).select_from(Game)).one()
    total_hours = session.exec(select(func.sum(Game.hours_played))).one() or 0
    perfect_games = session.exec(select(func.count()).where(Game.percent_achievements == 100)).one()
    avg_game_rating = session.exec(select(func.avg(Game.total_rating))).one() or 0

    new_stats = {
        "books": {
            "total": total_books,
            "pages": total_pages,
            "avg": round(avg_rating, 1),
            "finished": finished_books,
            "reading": reading_books
        },
        "games": {
            "total": total_games,
            "hours": round(total_hours, 1),
            "perfect": perfect_games,
            "avg": round(avg_game_rating, 1)
        }
    }
    logger.debug(f"Обновленная статистика - {new_stats}")
    
    # Обновляем кеш
    stats_cache.set(new_stats)

    return templates.TemplateResponse(
        "pages/index.html", {"request": request, "stats": new_stats}
    )