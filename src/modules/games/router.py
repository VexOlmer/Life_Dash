"""Роутер для управления разделом игр."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, and_, func, or_, select

from src.common.utils import translate
from src.core.database import get_session
from src.parser.sync import sync_games

from .models import Game
from .service import GameService

router = APIRouter(prefix="/games", tags=["Games"])
templates = Jinja2Templates(directory="src/web/templates")
SessionDep = Annotated[Session, Depends(get_session)]

@router.get("/", response_class=HTMLResponse)
async def list_games(
    request: Request, 
    session: SessionDep, 
    sort: str = "total_rating",
    order: str = "desc",
    page: int = 1,
    size: int = 20,
    q: str | None = None,
    status: str | None = None,
    genre: str | None = None,
    platform: str | None = None,
    country: str | None = None,
    developer: str | None = None,
    perfect: str | None = None,
) -> HTMLResponse:
    """
        Список игр с пагинацией, фильтрацией и расширенной сортировкой.
    
        Args:
            request: Объект HTTP-запроса для шаблонизатора.
            session: Сессия базы данных (Dependency Injection).
            sort: Поле для сортировки (рейтинги, цена, часы и т.д.).
            order: Направление сортировки (asc/desc).
            page: Текущая страница пагинации.
            size: Количество игр на одну страницу.
            q: Поисковый запрос (по названию, разработчику, серии).
            status: Фильтр по состоянию (план, играю, пройдено).
            genre: Фильтр по основному жанру.
            platform: Фильтр по платформе (из логов игры).
            country: Страна компании разработки.
            developer: Разработчик.
            perfect: Диапазон процента выполнения достижений.
                    
        Returns:
            HTMLResponse: Рендер страницы со списком игр.
    """
    
    # --- 1. Условия фильтрации ---
    conditions = []
    if q:
        conditions.append(or_(Game.title.icontains(q), Game.developer.icontains(q), Game.series.icontains(q))) # type: ignore
    if status:
        conditions.append(Game.status == status) # type: ignore
    if genre:
        conditions.append(Game.genres.icontains(genre)) # type: ignore
    if platform:
        conditions.append(Game.play_log.icontains(platform)) # type: ignore
    if country:
        conditions.append(Game.country_dev == country) # type: ignore
    if developer:
        conditions.append(Game.developer == developer) # type: ignore
    if perfect:
        if perfect == "100":
            conditions.append(Game.percent_achievements == 100) # type: ignore
        elif perfect == "75":
            conditions.append(Game.percent_achievements >= 75) # type: ignore
            conditions.append(Game.percent_achievements < 100) # type: ignore
        elif perfect == "50":
            conditions.append(Game.percent_achievements >= 50) # type: ignore
            conditions.append(Game.percent_achievements < 75) # type: ignore
        elif perfect == "25":
            conditions.append(Game.percent_achievements >= 25) # type: ignore
            conditions.append(Game.percent_achievements < 50) # type: ignore
        elif perfect == "0":
            conditions.append(Game.percent_achievements < 25) # type: ignore

    # --- 2. Базовый запрос ---
    filtered_stmt = select(Game)
    if conditions:
        filtered_stmt = filtered_stmt.where(and_(*conditions))

    # --- 3. Динамические фильтры (Актуальные значения) ---
    # Статусы завершения игр
    avail_statuses = session.exec(select(Game.status).where(and_(*conditions)).distinct() if conditions else select(Game.status).distinct()).all()
    
    # Страны разработчиков
    avail_countries = session.exec(select(Game.country_dev).where(and_(*conditions)).distinct() if conditions else select(Game.country_dev).distinct()).all()
    
    # Жанры
    genres_raw = session.exec(select(Game.genres).where(and_(*conditions)).distinct() if conditions else select(Game.genres).distinct()).all()
    unique_genres = set()
    for entry in genres_raw:
        if entry:
            for g in entry.split(","):
                unique_genres.add(g.strip())

    # Платформы (из логов)
    logs_raw = session.exec(select(Game.play_log).where(Game.play_log is not None).where(and_(*conditions)) if conditions else select(Game.play_log).where(Game.play_log is not None)).all()
    unique_platforms = set()
    for log in logs_raw:
        if not log:
            continue
        
        for entry in log.split(" || "):
            parts = entry.split("|")
            if len(parts) >= 3:
                unique_platforms.add(parts[2].strip())
    
    # Разработчики
    avail_developers = session.exec(
        select(Game.developer).where(and_(*conditions)).distinct() if conditions 
        else select(Game.developer).distinct()
    ).all()

    # --- 4. Пагинация ---
    count_statement = select(func.count()).select_from(filtered_stmt.subquery())
    total_count = session.exec(count_statement).one()
    total_pages = (total_count + size - 1) // size
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    offset = (page - 1) * size

    # Диапазон страниц
    start_range = max(1, page - 2)
    end_range = min(total_pages, page + 2)
    page_numbers = list(range(start_range, end_range + 1))

    # --- 5. Сортировка и выдача ---
    column = getattr(Game, sort, Game.total_rating)
    expression = column.desc() if order == "desc" else column.asc()
    games = session.exec(filtered_stmt.order_by(expression).offset(offset).limit(size)).all()

    showing_from = offset + 1 if total_count > 0 else 0
    showing_to = min(offset + size, total_count)
    
    # --- 6. Словарь меток для интерфейса сортировки ---
    labels = {
        # Основные метрики
        "total_rating": "Общий рейтинг",
        "hours_played": "Наиграно часов",
        "year": "Год выхода",
        "price": "Цена (руб)",
        "purchase_date": "Дата покупки",
        "percent_achievements": "Процент достижений",
        "metacritic": "Metacritic",
        "steam": "Steam",
        
        # 10 параметров рейтинга
        "rating_optimization": "Оптимизация",
        "rating_graphics": "Графика",
        "rating_audio": "Звук",
        "rating_gameplay": "Геймплей",
        "rating_price_quality": "Цена/Качество",
        "rating_story_lore": "Сюжет и Лор",
        "rating_immersion": "Погружение",
        "rating_replayability": "Реиграбельность",
        "rating_expected_real": "Ожидание/Реальность",
        "rating_cult_status": "Культовость",
    }

    return templates.TemplateResponse(
        "pages/games/list.html", 
        {
            "request": request,
            "games": games,
            
            # Параметры текущего состояния
            "current_sort": sort,
            "current_order": order,
            "current_page": page,
            "current_search": q or "",
            "current_status": status or "",
            "current_genre": genre or "",
            "current_platform": platform or "",
            "current_country": country or "",
            "current_developer": developer or "",
            "current_perfect": perfect or "",
            
            # Данные для пагинации
            "total_pages": total_pages,
            "total_count": total_count,
            "page_numbers": page_numbers,
            "showing_from": showing_from,
            "showing_to": showing_to,
            
            # Данные для фильтров и меток
            "sort_label": labels.get(sort, "Сортировка"),
            "labels": labels,
            "all_statuses": [{"id": s, "label": translate(s)} for s in avail_statuses if s],
            "all_genres": [{"id": g, "label": translate(g)} for g in sorted(list(unique_genres))],
            "all_platforms": sorted(list(unique_platforms)),
            "all_countries": sorted([c for c in avail_countries if c and c != "Unknown"]),
            "all_developers": sorted([d for d in avail_developers if d and d != "Unknown"]),
        }
    )

@router.post("/sync")
async def sync_games_endpoint(
    request: Request, 
    session: SessionDep, 
    force: bool = False
) -> HTMLResponse:
    """Запускает синхронизацию игр."""
    print("--- DEBUG: Кнопка синхронизации ИГР нажата ---")
    stats = sync_games(session, force=force)
    return templates.TemplateResponse(
        "components/sync_report.html", 
        {"request": request, "stats": stats}
    )

@router.get("/{game_id}")
async def game_detail(request: Request, game_id: int, session: SessionDep) -> HTMLResponse:
    """Детальная страница игры с полной аналитикой."""
    game = session.get(Game, game_id)
    if not game: 
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    # Получаем дополнительный текстовый контент (Герои, Впечатления)
    extra_content = GameService.get_game_content(game.file_path)

    return templates.TemplateResponse(
        "pages/games/detail.html",
        {
            "request": request, 
            "game": game, 
            "content": extra_content
        }
    )