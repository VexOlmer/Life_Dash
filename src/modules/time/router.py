"""Роутер для управления разделом времени в ежедневных заметках."""

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from src.core.database import get_session

from .service import TimeService

router = APIRouter(prefix="/time", tags=["Time"])
templates = Jinja2Templates(directory="src/web/templates")

@router.get("/")
async def time_index(request: Request, session: Session = Depends(get_session)):
    stats = TimeService.get_stats_for_period(session, days=30)
    return templates.TemplateResponse("pages/time/index.html", {"request": request, "stats": stats})