import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from bot.handlers.common import router as common_router
from bot.handlers.superadmin import router as superadmin_router
from bot.handlers.admin import router as admin_router
from bot.handlers.owner import router as owner_router
from bot.middlewares.auth import AuthMiddleware
from models.db import init_db
from scheduler import start_scheduler
from api_server import create_app
from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

API_PORT = int(os.environ.get("PORT", 8080))


async def main() -> None:
    await init_db()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    dp.include_router(common_router)
    dp.include_router(superadmin_router)
    dp.include_router(admin_router)
    dp.include_router(owner_router)

    start_scheduler(bot)

    # Start HTTP API for Mini App
    api_app = create_app()
    runner = web.AppRunner(api_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    logger.info("HTTP API started on port %d", API_PORT)

    logger.info("Bot started")
    await dp.start_polling(bot)

    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
