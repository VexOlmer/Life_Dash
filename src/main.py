"""Главный модуль приложения Obsidian Analytics."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.core.logger import logger
from src.modules.books.router import router as books_router
from src.modules.daily.router import router as daily_router
from src.modules.games.router import router as games_router
from src.web.router import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
        Управляет жизненным циклом приложения.

        Выполняет инициализацию базы данных при запуске и логирует
            события старта и остановки.

        Args:
            app: Экземпляр приложения FastAPI.
        
        Returns:
            AsyncGenerator[None, None]: Жизненный цикл сайта.
    """
    
    # --- Действия при запуске (Startup) ---
    logger.info("Запуск приложения Obsidian Analytics...")
    
    yield  # Принятие запросов приложением
    
    # --- Действия при остановке (Shutdown) ---
    logger.info("Остановка приложения...")


app = FastAPI(
    title="Obsidian Analytics",
    description="Аналитический дашборд для базы знаний Obsidian",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
app.mount("/vault", StaticFiles(directory=str(settings.OBSIDIAN_VAULT_PATH)), name="vault")

app.include_router(web_router)      # Главная страница (/)
app.include_router(books_router)    # Модуль книг (/books)
app.include_router(games_router)    # Модуль игр (/games)
app.include_router(daily_router)    # Модуль ежедневных заметок (/daily)


@app.get("/health")
async def health_check() -> dict[str, str | bool]:
    """
        Проверка доступности API и базы знаний.

        Returns:
            dict[str, str | bool]: Статус приложения и доступность Vault.
    """
    
    return {
        "status": "online",
        "vault_ready": settings.OBSIDIAN_VAULT_PATH.exists(),
        "vault_path": str(settings.OBSIDIAN_VAULT_PATH),
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )