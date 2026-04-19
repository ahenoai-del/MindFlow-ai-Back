import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from config.settings import settings
from db.database import init_db, close_db
from bot.handlers import (
    start_router, tasks_router, planning_router, webapp_router,
    admin_router, payments_router, reminders_router,
)
from middlewares.error_handler import ErrorHandlerMiddleware
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.admin import AdminMiddleware
from scheduler.jobs import setup_scheduler
from utils.logging import setup_logging

logger = logging.getLogger(__name__)


# FIXED: убран хрупкий ProxySession который переопределял приватный метод _make_request.
# Теперь прокси передаётся через стандартный параметр aiohttp.
# Добавь в .env: HTTPS_PROXY=http://user:pass@host:port
# aiogram/aiohttp подхватят его автоматически через переменную окружения,
# либо можно передать явно через connector_owner и proxy в ClientSession.

def _make_session() -> AiohttpSession:
    """Создаёт aiohttp-сессию с поддержкой прокси если задан PROXY_URL."""
    if settings.PROXY_URL:
        # Стандартный способ через переменную окружения — aiogram сам прочитает
        os.environ.setdefault("HTTPS_PROXY", settings.PROXY_URL)
    return AiohttpSession()


async def run_bot() -> None:
    session = _make_session()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    dp = Dispatcher()

    dp.message.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    dp.message.middleware(RateLimitMiddleware(limit_seconds=settings.RATE_LIMIT_SECONDS))

    # FIXED: порядок роутеров важен — payments должен быть первым
    # чтобы successful_payment обрабатывался раньше общих хэндлеров
    dp.include_router(payments_router)
    dp.include_router(start_router)
    dp.include_router(tasks_router)
    dp.include_router(planning_router)
    dp.include_router(webapp_router)
    dp.include_router(admin_router)
    dp.include_router(reminders_router)

    setup_scheduler(bot)

    logger.info("Bot started")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await close_db()


async def run_api() -> None:
    import uvicorn
    from api import app

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    setup_logging(log_level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)
    await init_db()

    if os.environ.get("RUN_API") == "true":
        # FIXED: если один из процессов упадёт — gather не отменит второй молча.
        # return_exceptions=False (дефолт) выбросит исключение наверх и main упадёт целиком.
        # Это правильное поведение — краш виден сразу.
        await asyncio.gather(run_bot(), run_api())
    else:
        await run_bot()


if __name__ == "__main__":
    asyncio.run(main())
