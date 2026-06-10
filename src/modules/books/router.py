"""Роутер для управления разделом книг."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, and_, func, or_, select

from src.common.utils import translate
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
    size: int = 2,
    q: str | None = None,
    status: str | None = None,
    genre: str | None = None,
    country: str | None = None,
    book_format: str | None = None
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
            q: Данные в поисковой строке.
            status: Статус прочитанности книги.
            genre: Основные жанры книги.
            country: Страна автора.
            book_format: Формат книги.
        
        Returns:
            HTMLResponse: Обновленный шаблон страницы.
    """
    
    # --- 1. Базовый запрос для данных ---
    
    # Собираем фильтры для основного списка
    conditions = []
    if q:
        conditions.append(or_(Book.title.icontains(q), Book.author.icontains(q), Book.series.icontains(q)))
    if status:
        conditions.append(Book.status == status)
    if country:
        conditions.append(Book.country_author == country)
    if book_format:
        conditions.append(Book.format == book_format)
    if genre:
        conditions.append(Book.genres.icontains(genre))

    # --- 2. Умная фильтрация для выпадающих списков ---
    def get_available_values(column, current_conditions):  # noqa: ANN001
        """
            Получение данных из колонки по текущей фильтрации.
            
            Args:
                column: Наименование столбца
                current_conditions: Текущий набор фильтров
        """
        stmt = select(column).distinct()
        if current_conditions:
            stmt = stmt.where(and_(*current_conditions))
        return session.exec(stmt).all()

    # Получаем доступные значения, исключая из условий сам этот фильтр (чтобы можно было переключить)
    filtered_subquery = select(Book)
    if conditions:
        filtered_subquery = filtered_subquery.where(and_(*conditions))
    
    # Выполняем запросы для получения актуальных списков
    actual_books_stmt = filtered_subquery
    avail_statuses = get_available_values(Book.status, conditions)
    avail_formats = get_available_values(Book.format, conditions)
    avail_countries = get_available_values(Book.country_author, conditions)
    
    # Жанры (чуть сложнее из-за строки)
    avail_genres_raw = get_available_values(Book.genres, conditions)
    unique_genres = set()
    for entry in avail_genres_raw:
        if not entry:
            continue
        parts = re.split(r',\s*(?![^()]*\))', entry)
        for p in parts:
            clean_g = re.sub(r'\s*\([^)]*\)', '', p).strip()
            if clean_g:
                unique_genres.add(clean_g)
    
    count_statement = select(func.count()).select_from(actual_books_stmt.subquery())
    
    # --- 3. Рассчеты пагинации ---
    total_count = session.exec(count_statement).one()
    total_pages = (total_count + size - 1) // size

    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages
    offset = (page - 1) * size
        
    # --- 4. Рассчет диапазона ближайщих страниц ---
    start_range = max(1, page - 2)
    end_range = min(total_pages, page + 2)
    page_numbers = list(range(start_range, end_range + 1))

    # --- 5. Получаем атрибут для сортировки ---
    column = getattr(Book, sort, Book.total_rating)
    expression = column.desc() if order == "desc" else column.asc()
    
    # --- 6. Запрос с лимитом и смещением (LIMIT / OFFSET) ---
    statement = actual_books_stmt.order_by(expression).offset(offset).limit(size)
    books = session.exec(statement).all()
    
    # --- 7. Номера книг, показанных на текущей странице ---
    showing_from = offset + 1 if total_count > 0 else 0
    showing_to = min(offset + size, total_count)
    
    # Варинты сортировки списка книг
    labels = {
        "total_rating": "Общий рейтинг",
        "total": "Количество страниц",
        "year": "Год издания",
        "good_reads": "GoodReads",
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
            "current_search": q or "",
            
            "total_pages": total_pages,
            "total_count": total_count,
            "page_numbers": page_numbers,
            
            "showing_from": showing_from,
            "showing_to": showing_to,
            
            "sort_label": labels.get(sort, "Сортировка"),
            "labels": labels,
            
            # Динамические списки для фильтрации
            "all_statuses": [{"id": s, "label": translate(s)} for s in avail_statuses if s],
            "all_genres": [{"id": g, "label": translate(g)} for g in sorted(list(unique_genres))],
            "all_countries": sorted([c for c in avail_countries if c and c != "Unknown"]),
            "all_formats": [{"id": f, "label": translate(f)} for f in avail_formats if f],
            
            # Текущие выбранные значения
            "current_status": status or "",
            "current_genre": genre or "",
            "current_country": country or "",
            "current_format": book_format or ""
        }
    )

@router.post("/sync")
async def sync_books_endpoint(
    request: Request, 
    session: SessionDep, 
    force: bool = False
) -> HTMLResponse:
    """Запускает синхронизацию книг."""
    stats = sync_books(session, force=force)
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