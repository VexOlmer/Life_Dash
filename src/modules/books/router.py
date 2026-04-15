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
async def list_books(
    request: Request, 
    session: SessionDep, 
    sort: str = "total_rating",
    order: str = "desc"
):
    """Список книг с универсальной сортировкой."""
    
    # Получаем атрибут модели динамически
    column = getattr(Book, sort, Book.total_rating)
    
    # Применяем направление
    expression = column.desc() if order == "desc" else column.asc()
    
    statement = select(Book).order_by(expression)
    books = session.exec(statement).all()
    
    # Словарь понятных названий для кнопки
    labels = {
        "total_rating": "Общий рейтинг",
        "total": "Количество страниц",
        "rating_characters": "Герои",
        "rating_plot": "Сюжет",
        "rating_size": "Объем",
        "rating_prose": "Слог",
        "rating_ending": "Финал",
        "rating_depth": "Глубина",
        "rating_atmosphere": "Атмосфера",
        "rating_rereadability": "Перечитывание",
        "rating_expected_real": "Ожидание/Реальность",
        "rating_recommend": "Рекомендация"
    }
    
    return templates.TemplateResponse(
        "pages/books.html", 
        {
            "request": request, 
            "books": books, 
            "current_sort": sort,
            "current_order": order,
            "sort_label": labels.get(sort, "Сортировка"),
            "labels": labels
        }
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