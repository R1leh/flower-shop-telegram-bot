from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.keyboards.admin_kb import STATS_PERIODS, stats_period_kb, stats_result_kb
from app.repositories import bouquet_repo, client_repo, order_repo, session_repo
from app.services.export_service import build_orders_workbook
from app.utils.constants import label_by_code
from app.utils.dt import TZ, now

router = Router(name="admin_stats")


def _period_bounds(code: str) -> tuple[str, str]:
    end = now()
    if code == "today":
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    elif code == "week":
        start = end - timedelta(days=7)
    elif code == "month":
        start = end - timedelta(days=30)
    else:
        start = datetime(2000, 1, 1, tzinfo=TZ)
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


async def _build_stats_text(period_code: str, period_label: str) -> str:
    start_iso, end_iso = _period_bounds(period_code)

    orders_count = await order_repo.count_in_period(start_iso, end_iso)
    revenue = await order_repo.revenue_in_period(start_iso, end_iso)
    avg_check = await order_repo.average_check_in_period(start_iso, end_iso)
    repeat_ratio = await order_repo.repeat_clients_ratio(start_iso, end_iso)
    new_clients = await client_repo.count_registered_since(start_iso)
    top_bouquets = await bouquet_repo.top_popular(5)

    sessions_total = await session_repo.count_total_in_period(start_iso, end_iso)
    sessions_completed = await session_repo.count_completed_in_period(start_iso, end_iso)
    conversion = (sessions_completed / sessions_total * 100) if sessions_total else 0.0

    lines = [
        f"📊 <b>Статистика — {period_label}</b>\n",
        f"🧾 Заказов оформлено: {orders_count}",
        f"👥 Новых клиентов: {new_clients}",
        f"💰 Выручка (завершённые заказы): {revenue:.0f} ₽",
        f"💳 Средний чек: {avg_check:.0f} ₽",
        f"🔁 Повторные клиенты: {repeat_ratio * 100:.0f}%",
        f"🎯 Конверсия подбора в заказ: {conversion:.0f}% ({sessions_completed}/{sessions_total})",
    ]

    if top_bouquets:
        lines.append("\n🏆 <b>Топ-5 букетов по заказам:</b>")
        for i, bouquet in enumerate(top_bouquets, start=1):
            lines.append(f"{i}. {bouquet.name} — {bouquet.orders_count} зак.")

    return "\n".join(lines)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    await message.answer("Выберите период для статистики:", reply_markup=stats_period_kb())


@router.callback_query(F.data == "adm_stats")
async def cb_stats(callback: CallbackQuery) -> None:
    await callback.message.answer("Выберите период для статистики:", reply_markup=stats_period_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("adm_stats_period:"))
async def cb_stats_period(callback: CallbackQuery) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(STATS_PERIODS, code) or code
    text = await _build_stats_text(code, label)
    await callback.message.answer(text, reply_markup=stats_result_kb(code))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_export:"))
async def cb_export_orders(callback: CallbackQuery) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(STATS_PERIODS, code) or code
    start_iso, end_iso = _period_bounds(code)

    orders = await order_repo.get_in_period(start_iso, end_iso)
    if not orders:
        await callback.answer("Нет заказов за выбранный период", show_alert=True)
        return

    buffer = build_orders_workbook(orders)
    filename = f"orders_{code}_{now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    await callback.message.answer_document(
        BufferedInputFile(buffer.read(), filename=filename),
        caption=f"📊 Заказы за период «{label}»: {len(orders)} шт.",
    )
    await callback.answer()
