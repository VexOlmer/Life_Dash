"""Роутер для управления разделом времени в ежедневных заметках."""

import calendar
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from src.core.database import get_session

from .service import TimeService

router = APIRouter(prefix="/time", tags=["Time"])
templates = Jinja2Templates(directory="src/web/templates")

SessionDep = Annotated[Session, Depends(get_session)]

@router.get("/", response_class=HTMLResponse)
async def time_index(
    request: Request, 
    session: SessionDep,
    month: int | None = None,
    year: int | None = None
) -> HTMLResponse:
    """Вывод агрегированной статистики по времени за месяц."""
    now = datetime.now()
    m = month or now.month
    y = year or now.year
    
    # 1. Месячная аналитика (графики, список)
    monthly_stats = TimeService.get_monthly_stats(session, y, m)
    
    # 2. Недельный прогресс (бюджеты)
    # Примечание: бюджеты всегда показывают ТЕКУЩУЮ неделю для оперативного контроля
    weekly_budgets = TimeService.get_weekly_budget_stats(session)
    
    return templates.TemplateResponse("pages/time/index.html", {
        "request": request, 
        "stats": monthly_stats,
        "budgets": weekly_budgets,
        "curr_m": m,
        "curr_y": y,
        "month_name": calendar.month_name[m]
    })