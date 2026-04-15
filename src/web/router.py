"""Роутер для основных страниц сайта."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Web"])
templates = Jinja2Templates(directory="src/web/templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Главная страница приложения."""
    return templates.TemplateResponse("pages/index.html", {"request": request})