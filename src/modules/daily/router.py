"""Роутер для управления ежедневными заметками."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from src.core.database import get_session
from src.parser.sync import sync_daily

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
    
    # Текущие параметры из URL или по умолчанию
    target_year = year or reference_day.isocalendar()[0]
    target_week = week or reference_day.isocalendar()[1]

    # 1. Получаем объект даты для понедельника целевой недели
    # Это "якорь", от которого мы будем считать всё остальное
    current_monday = datetime.fromisocalendar(target_year, target_week, 1)
    
    # 2. Получаем данные за целевую неделю
    current_week_data = DailyService.get_week_data(session, target_week, target_year)
    
    # 3. Рассчитываем прошлую неделю (просто вычитаем 7 дней от нашего якоря)
    prev_monday = current_monday - timedelta(days=7)
    prev_week_year, prev_week_num, _ = prev_monday.isocalendar()
    prev_week_data = DailyService.get_week_data(session, prev_week_num, prev_week_year)

    # 4. Рассчитываем параметры для кнопок "Вперед" и "Назад" (для ссылок)
    next_monday = current_monday + timedelta(days=7)
    next_week_year, next_week_num, _ = next_monday.isocalendar()
    
    # Агрегируем статистику за все 14 дней
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
async def sync_daily_endpoint(request: Request, session: SessionDep) -> HTMLResponse:
    """Синхронизация ежедневных заметок."""
    stats = sync_daily(session)
    return templates.TemplateResponse(
        "components/sync_report.html", 
        {"request": request, "stats": stats}
    )