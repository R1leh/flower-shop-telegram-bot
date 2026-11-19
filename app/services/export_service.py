from io import BytesIO

from openpyxl import Workbook

from app.models.order import Order
from app.utils.constants import ORDER_STATUS_LABELS

ORDERS_SHEET_HEADERS = [
    "ID",
    "Дата создания",
    "Статус",
    "Букет",
    "Сумма, ₽",
    "Получатель",
    "Телефон получателя",
    "Адрес доставки",
    "Время доставки",
    "Комментарий",
]


def build_orders_workbook(orders: list[Order]) -> BytesIO:
    """Сформировать Excel-отчёт по заказам за период."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Заказы"
    ws.append(ORDERS_SHEET_HEADERS)

    for order in orders:
        ws.append(
            [
                order.id,
                order.created_at,
                ORDER_STATUS_LABELS.get(order.status, order.status),
                order.bouquet_name,
                order.total_price,
                order.recipient_name,
                order.recipient_phone,
                order.delivery_address,
                order.delivery_time,
                order.comment or "",
            ]
        )

    for column_cells in ws.columns:
        max_length = max(
            (len(str(cell.value)) for cell in column_cells if cell.value is not None),
            default=0,
        )
        ws.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 40)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
