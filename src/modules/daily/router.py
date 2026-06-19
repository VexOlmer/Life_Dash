"""Роутер для управления ежедневными заметками."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from src.core.database import get_session
from src.parser.sync import sync_daily

from .models import DailyNote
from .service import DailyService

router = APIRouter(prefix="/daily", tags=["Daily"])
templates = Jinja2Templates(directory="src/web/templates")
SessionDep = Annotated[Session, Depends(get_session)]

@router.get("/", response_class=HTMLResponse)
async def daily_hub(
    request: Request, 
    session: SessionDep, 
    week: int | None = None, 
    year: int | None = None
) -> HTMLResponse:
    """Рассчеты показателей ежедневных заметок для отображения на главной странице Дневника."""
    now = datetime.now()
    
    # Сдвигаемся на вчера, чтобы не видеть "сегодня"
    reference_day = now - timedelta(days=1)
    target_year = year or reference_day.isocalendar()[0]
    target_week = week or reference_day.isocalendar()[1]

    # 1. Получаем объект даты для понедельника целевой недели
    # Это "якорь", от которого мы будем считать всё остальное
    current_monday = datetime.fromisocalendar(target_year, target_week, 1)
    
    # 2. Получаем данные за целевую неделю
    current_week_data = DailyService.get_week_data(session, target_week, target_year)
    
    # 3. Рассчитываем прошлую неделю и получаем ее данные
    prev_monday = current_monday - timedelta(days=7)
    prev_week_year, prev_week_num, _ = prev_monday.isocalendar()
    prev_week_data = DailyService.get_week_data(session, prev_week_num, prev_week_year)

    # 4. Рассчитываем параметры для кнопок "Вперед" и "Назад" (для ссылок)
    next_monday = current_monday + timedelta(days=7)
    next_week_year, next_week_num, _ = next_monday.isocalendar()
    
    # 5. Агрегируем статистику за все 14 дней
    stats = DailyService.get_aggregated_stats(session, current_week_data + prev_week_data)
    calendar = DailyService.get_calendar_structure(session)

    return templates.TemplateResponse(
        "pages/daily_hub.html", 
        {
            "request": request,
            "current_week": current_week_data,
            "prev_week": prev_week_data,
            "stats": stats,
            "calendar": calendar,
            "target_week": target_week,
            "target_year": target_year,
            
            # Передаем готовые ссылки для кнопок, чтобы не считать их в HTML
            "prev_link": f"?week={prev_week_num}&year={prev_week_year}",
            "next_link": f"?week={next_week_num}&year={next_week_year}"
        }
    )
   
@router.post("/sync")
async def sync_daily_endpoint(
    request: Request, 
    session: SessionDep, 
    force: bool = False
) -> HTMLResponse:
    """Синхронизация ежедневных заметок."""
    stats = sync_daily(session, force=force)
    return templates.TemplateResponse(
        "components/sync_report.html", 
        {"request": request, "stats": stats}
    )

@router.get("/charts", response_class=HTMLResponse)
async def daily_charts(
    request: Request, 
    session: SessionDep,
    week: int | None = None, 
    year: int | None = None
) -> HTMLResponse:
    """Страница с графиками показателей за месяц."""
    now = datetime.now()
    reference_day = now - timedelta(days=1)
    
    # Если параметры не переданы, берем 30 дней от вчера
    # Если переданы (через ISO неделю), вычисляем воскресенье этой недели
    if week and year:
        end_date = datetime.fromisocalendar(year, week, 7)
    else:
        end_date = reference_day

    # Берем 30 дней назад
    all_days_data = []
    for i in range(29, -1, -1):
        d = end_date - timedelta(days=i)
        all_days_data.append(d.strftime("%Y-%m-%d"))

    # Запрос к БД
    statement = select(DailyNote).where(DailyNote.date.in_(all_days_data))
    notes = session.exec(statement).all()
    notes_map = {n.date: n for n in notes}

    # Формируем структуру для сервиса
    prepared_days = []
    day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for d_str in all_days_data:
        dt = datetime.strptime(d_str, "%Y-%m-%d")
        prepared_days.append({
            "date": d_str,
            "display_date": dt.strftime("%d.%m"),
            "day_name": day_names[dt.weekday()],
            "note": notes_map.get(d_str)
        })
    
    charts_data = DailyService.prepare_charts_json(prepared_days)

    return templates.TemplateResponse(
        "pages/daily_charts.html", 
        {
            "request": request,
            "charts_data": charts_data,
            "target_date": end_date.strftime("%d.%m.%Y")
        }
    )

@router.get("/{date_str}", response_class=HTMLResponse)
async def daily_detail(request: Request, date_str: str, session: SessionDep) -> HTMLResponse:
    """Детальная страница дня."""
    note = session.get(DailyNote, date_str)
    if not note:
        # Если заметка не найдена в БД, перенаправляет назад
        return RedirectResponse(url="/daily/")

    # Получаем текстовый контент через сервис
    content = DailyService.get_daily_content(note.file_path)

    return templates.TemplateResponse(
        "pages/daily_detail.html", 
        {
            "request": request, 
            "note": note, 
            "content": content
        }
    )