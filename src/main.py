"""Главный модуль приложения Obsidian Analytics."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.core.config import settings
from src.core.database import init_db
from src.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
        Управляет жизненным циклом приложения.

        Выполняет инициализацию базы данных при запуске и логирует
        события старта и остановки.

        Args:
            app: Экземпляр приложения FastAPI.
    """
    
    # --- Действия при запуске (Startup) ---
    logger.info("Запуск приложения Obsidian Analytics...")
    init_db()
    
    yield  # Здесь приложение начинает принимать запросы
    
    # --- Действия при остановке (Shutdown) ---
    logger.info("Остановка приложения...")


app = FastAPI(
    title="Obsidian Analytics",
    description="Аналитический дашборд для базы знаний Obsidian",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str | bool]:
    """
        Проверка доступности API и базы знаний.

        Returns:
            dict: Статус приложения и доступность Vault.
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