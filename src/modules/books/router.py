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
    size: int = 20,
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
    
    # --- 1. Собираем все активные фильтры ---
    conditions = []
    if q:
        conditions.append(or_(Book.title.icontains(q), Book.author.icontains(q), Book.series.icontains(q)))
    if status:
        conditions.append(Book.status == status)
    if country:
        conditions.append(Book.country_author == country)
    if genre:
        conditions.append(Book.genres.icontains(genre))
    if book_format:
        conditions.append(Book.read_log.icontains(book_format))

    # --- 2. Создаем базовый запрос для ТЕКУЩИХ отфильтрованных книг ---
    # Мы будем использовать этот запрос как основу для всех выпадающих списков
    filtered_stmt = select(Book)
    if conditions:
        filtered_stmt = filtered_stmt.where(and_(*conditions))
    
    # --- 3. Получаем АКТУАЛЬНЫЕ значения для фильтров ---

    # Статусы
    avail_statuses = session.exec(
        select(Book.status).where(and_(*conditions)).distinct() if conditions 
        else select(Book.status).distinct()
    ).all()
    
    # Страны
    avail_countries = session.exec(
        select(Book.country_author).where(and_(*conditions)).distinct() if conditions 
        else select(Book.country_author).distinct()
    ).all()

    # Основные жанры
    genres_raw = session.exec(
        select(Book.genres).where(and_(*conditions)).distinct() if conditions 
        else select(Book.genres).distinct()
    ).all()
    
    unique_genres = set()
    for entry in genres_raw:
        if not entry:
            continue
        for p in re.split(r',\s*(?![^()]*\))', entry):
            clean = re.sub(r'\s*\([^)]*\)', '', p).strip()
            if clean:
                unique_genres.add(clean)

    # Форматы (Парсим только из отфильтрованных книг)
    logs_raw = session.exec(
        select(Book.read_log).where(Book.read_log is not None).where(and_(*conditions)) if conditions 
        else select(Book.read_log).where(Book.read_log is not None)
    ).all()
    
    unique_formats = set()
    for log in logs_raw:
        for entry in log.split(" || "):
            parts = entry.split("|")
            if len(parts) >= 3:
                fmt = parts[2].strip()
                if fmt:
                    unique_formats.add(fmt)
    avail_formats = sorted(list(unique_formats))
    
    # --- 4. Рассчеты пагинации ---
    count_statement = select(func.count()).select_from(filtered_stmt.subquery())
    
    total_count = session.exec(count_statement).one()
    total_pages = (total_count + size - 1) // size

    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages
    offset = (page - 1) * size
        
    # --- 5. Рассчет диапазона ближайщих страниц ---
    start_range = max(1, page - 2)
    end_range = min(total_pages, page + 2)
    page_numbers = list(range(start_range, end_range + 1))

    # --- 6. Получаем атрибут для сортировки ---
    column = getattr(Book, sort, Book.total_rating)
    expression = column.desc() if order == "desc" else column.asc()
    
    # --- 7. Запрос с лимитом и смещением (LIMIT / OFFSET) ---
    statement = filtered_stmt.order_by(expression).offset(offset).limit(size)
    books = session.exec(statement).all()
    
    # --- 8. Номера книг, показанных на текущей странице ---
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
    print("--- DEBUG: Кнопка синхронизации КНИГ нажата ---")
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

    # Просто получаем словарь строк из сервиса
    extra_content = BookService.get_book_content(book.file_path)

    return templates.TemplateResponse(
        "pages/book_detail.html", 
        {
            "request": request, 
            "book": book, 
            "content": extra_content
        }
    )