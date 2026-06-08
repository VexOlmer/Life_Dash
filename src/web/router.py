"""Роутер для основных страниц сайта."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from src.core.database import get_session
from src.modules.books.models import Book

router = APIRouter(tags=["Web"])
templates = Jinja2Templates(directory="src/web/templates")
SessionDep = Annotated[Session, Depends(get_session)]

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, session: Session = SessionDep) -> HTMLResponse:
    """Подсчитывание статистики книг."""
    
    total_books = session.exec(select(func.count(Book.id))).one()
    total_pages = session.exec(select(func.sum(Book.total))).one() or 0
    avg_rating = session.exec(select(func.avg(Book.total_rating))).one() or 0

    finished_books = session.exec(select(func.count(Book.id)).where(Book.status == "finished")).one()
    reading_books = session.exec(select(func.count(Book.id)).where(Book.status == "reading")).one()

    return templates.TemplateResponse(
        "pages/index.html", 
        {
            "request": request, 
            "stats": {
                "books": {
                    "total": total_books,
                    "pages": total_pages,
                    "avg": round(avg_rating, 1),
                    "finished": finished_books,
                    "reading": reading_books
                }
            }
        }
    )