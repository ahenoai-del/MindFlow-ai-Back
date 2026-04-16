import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from core.config import settings
from db.database import init_db
from bot.handlers import start, tasks, planning, webapp_handler, admin, payments
from scheduler.jobs import setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxySession(AiohttpSession):
    def __init__(self, proxy_url: str, **kwargs):
        super().__init__(**kwargs)
        self._proxy_url = proxy_url

    async def _make_request(self, *args, **kwargs):
        kwargs.setdefault("proxy", self._proxy_url)
        return await super()._make_request(*args, **kwargs)


async def run_bot():
    proxy_url = settings.PROXY_URL
    if proxy_url:
        session = ProxySession(proxy_url=proxy_url)
    else:
        session = AiohttpSession()
    
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session
    )
    dp = Dispatcher()
    
    dp.include_router(payments.router)
    dp.include_router(start.router)
    dp.include_router(tasks.router)
    dp.include_router(planning.router)
    dp.include_router(webapp_handler.router)
    dp.include_router(admin.router)
    
    setup_scheduler(bot)
    
    logger.info("Bot started")
    await dp.start_polling(bot)


async def run_api():
    import uvicorn
    from api import app
    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    await init_db()
    
    if os.environ.get("RUN_API") == "true":
        await asyncio.gather(run_bot(), run_api())
    else:
        await run_bot()


if __name__ == "__main__":
    asyncio.run(main())
