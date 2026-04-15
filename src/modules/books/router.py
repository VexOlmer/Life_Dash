"""Роутер для управления разделом книг."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from src.core.database import get_session
from src.parser.sync import sync_books

from .models import Book
from .service import BookService

router = APIRouter(prefix="/books", tags=["Books"])
templates = Jinja2Templates(directory="src/web/templates")
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
async def list_books(request: Request, session: SessionDep): # noqa: ANN201
    """Отображает страницу со списком книг."""
    statement = select(Book).order_by(Book.total_rating.desc())
    books = session.exec(statement).all()
    
    return templates.TemplateResponse(
        "pages/books.html", 
        {"request": request, "books": books}
    )

@router.post("/sync")
async def sync_books_endpoint(request: Request, session: SessionDep): # noqa: ANN201
    """Запускает синхронизацию книг."""
    stats = sync_books(session)
    return templates.TemplateResponse(
        "components/sync_report.html", 
        {"request": request, "stats": stats}
    )

@router.get("/{book_id}")
async def book_detail(request: Request, book_id: int, session: SessionDep): # noqa: ANN201
    """Детальная страница книги."""
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    # Получаем динамический контент из файла
    extra_content = BookService.get_book_content(book.file_path)

    return templates.TemplateResponse(
        "pages/book_detail.html", 
        {
            "request": request, 
            "book": book, 
            "content": extra_content
        }
    )