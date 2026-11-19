import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.database.connection import init_db
from app.handlers.admin import catalog as admin_catalog
from app.handlers.admin import menu as admin_menu
from app.handlers.admin import orders as admin_orders
from app.handlers.admin import stats as admin_stats
from app.handlers.client import favorites as client_favorites
from app.handlers.client import loyalty as client_loyalty
from app.handlers.client import orders as client_orders
from app.handlers.client import profile as client_profile
from app.handlers.client import reminders as client_reminders
from app.handlers.client import selection as client_selection
from app.handlers.client import start as client_start
from app.middlewares.auth import AdminMiddleware
from app.middlewares.privacy import PrivacyMiddleware
from app.schedulers import setup_scheduler
from app.utils.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    admin_routers = [
        admin_menu.router,
        admin_orders.router,
        admin_catalog.router,
        admin_stats.router,
    ]
    for router in admin_routers:
        router.message.middleware(AdminMiddleware())
        router.callback_query.middleware(AdminMiddleware())
        dp.include_router(router)

    client_routers = [
        client_start.router,
        client_selection.router,
        client_orders.router,
        client_profile.router,
        client_favorites.router,
        client_reminders.router,
        client_loyalty.router,
    ]
    for router in client_routers:
        router.message.middleware(PrivacyMiddleware())
        router.callback_query.middleware(PrivacyMiddleware())
        dp.include_router(router)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    logger.info("Бот «Бутон» запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот «Бутон» остановлен")
