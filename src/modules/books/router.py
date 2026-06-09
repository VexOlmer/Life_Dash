"""Роутер для управления разделом книг."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

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
    order: str = "desc",
    page: int = 1,
    size: int = 20
) -> HTMLResponse:
    """
        Список книг с пагинацией и сортировкой.
    
        Args:
            request: Объект HTTP-запроса.
            session: Текущая сессия.
            sort: Колонка для первоначальной сортировки.
            order: Тип сортировки (по возрастанию/убыванию).
            page: Первоначальная страница.
            size: Кол-во документов на странице.
        
        Returns:
            HTMLResponse: Обновленный шаблон страницы.
    """
    
    # 1. Считаем общее количество книг
    total_count = session.exec(select(func.count()).select_from(Book)).one()
    
    # 2. Рассчитываем общее количество страниц
    total_pages = (total_count + size - 1) // size
    
    # 3. Защита от выхода за границы
    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages
        
    # 4. Рассчет диапазона ближайщих страниц
    start_range = max(1, page - 2)
    end_range = min(total_pages, page + 2)
    page_numbers = list(range(start_range, end_range + 1))

    # 5. Получаем атрибут для сортировки
    column = getattr(Book, sort, Book.total_rating)
    expression = column.desc() if order == "desc" else column.asc()
    
    # 6. Запрос с лимитом и смещением (LIMIT / OFFSET)
    offset = (page - 1) * size
    statement = select(Book).order_by(expression).offset(offset).limit(size)
    books = session.exec(statement).all()
    
    # 7. Номера книг, показанных на текущей странице
    showing_from = offset + 1 if total_count > 0 else 0
    showing_to = min(offset + size, total_count)
    
    # Варинты сортировки списка книг
    labels = {
        "total_rating": "Общий рейтинг",
        "total": "Количество страниц",
        "year": "Год издания",
        "rating_characters": "Герои",
        "rating_plot": "Сюжет",
        "rating_size": "Объем",
        "rating_prose": "Слог",
        "rating_ending": "Финал",
        "rating_depth": "Глубина",
        "rating_atmosphere": "Атмосфера",
        "rating_rereadability": "Перечитывание",
        "rating_expected_real": "Ожидание / Реальность",
        "rating_recommend": "Рекомендация"
    }
    
    return templates.TemplateResponse(
        "pages/books.html", 
        {
            "request": request,
            "books": books, 
            "current_sort": sort,
            "current_order": order,
            "current_page": page,
            "total_pages": total_pages,
            "page_numbers": page_numbers,
            "showing_from": showing_from,
            "showing_to": showing_to,
            "total_count": total_count,
            "sort_label": labels.get(sort, "Сортировка"),
            "labels": labels
        }
    )

@router.post("/sync")
async def sync_books_endpoint(request: Request, session: SessionDep) -> HTMLResponse:
    """Запускает синхронизацию книг."""
    stats = sync_books(session)
    return templates.TemplateResponse(
        "components/sync_report.html", 
        {"request": request, "stats": stats}
    )

@router.get("/{book_id}")
async def book_detail(request: Request, book_id: int, session: SessionDep) -> HTMLResponse:
    """
        Детальная страница книги.

        Args:
            request: Объект HTTP-запроса
            book_id: Путь к файлу в Obsidian Vault
            session: Текущая сессия
        
        Returns:
            HTMLResponse: Обновленный шаблон страницы
    """
    
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