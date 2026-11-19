"""Заполнение БД демонстрационными данными: клиенты, заказы, отзывы,
избранное, напоминания и сессии подбора — для демонстрации работы бота
и админ-панели (/orders, /stats, /profile, /loyalty, /history, /favorites, /remind).

Запуск: python -m scripts.seed_demo_data

Скрипт идемпотентен: если демонстрационные клиенты уже есть в БД, повторный
запуск ничего не делает.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from app.database.connection import get_connection, init_db
from app.models.bouquet import Bouquet
from app.repositories import bouquet_repo, client_repo, favorite_repo, history_repo, loyalty_repo, reminder_repo, review_repo
from app.utils.constants import DEFAULT_LOYALTY_LEVEL, LOYALTY_THRESHOLDS, POINTS_PER_RUBLE_DIVISOR
from app.utils.dt import now
from app.utils.validators import normalize_phone
from scripts.seed_bouquets import seed as seed_bouquets

CLIENTS: list[dict] = [
    dict(
        telegram_id=900000001,
        full_name="Анна Кузнецова",
        phone="89261234501",
        birth_date="15.03.1990",
        delivery_address="г. Екатеринбург, ул. Ленина, д. 10, кв. 25",
        is_vip=1,
        registered_days_ago=60,
    ),
    dict(
        telegram_id=900000002,
        full_name="Дмитрий Соколов",
        phone="89031234502",
        birth_date="22.07.1985",
        delivery_address="г. Екатеринбург, ул. Малышева, д. 5",
        is_vip=0,
        registered_days_ago=45,
    ),
    dict(
        telegram_id=900000003,
        full_name="Елена Морозова",
        phone="89221234503",
        birth_date="03.11.1995",
        delivery_address="г. Екатеринбург, пр. Космонавтов, д. 14, кв. 7",
        is_vip=0,
        registered_days_ago=30,
    ),
    dict(
        telegram_id=900000004,
        full_name="Игорь Васильев",
        phone="89121234504",
        birth_date="30.01.1988",
        delivery_address="г. Екатеринбург, ул. Восточная, д. 22",
        is_vip=0,
        registered_days_ago=20,
    ),
    dict(
        telegram_id=900000005,
        full_name="Мария Новикова",
        phone="89501234505",
        birth_date="18.06.1999",
        delivery_address="г. Екатеринбург, ул. Сакко и Ванцетти, д. 3, кв. 41",
        is_vip=0,
        registered_days_ago=10,
    ),
]

# Клиент, который согласился на обработку ПДн, но не завершил регистрацию
INCOMPLETE_CLIENT = dict(telegram_id=900000006, registered_days_ago=1)

# (старый_статус, новый_статус, часов_после_создания)
_STATUS_HISTORY: dict[str, list[tuple[Optional[str], str, float]]] = {
    "new": [(None, "new", 0)],
    "accepted": [(None, "new", 0), ("new", "accepted", 1)],
    "assembling": [(None, "new", 0), ("new", "accepted", 1), ("accepted", "assembling", 3)],
    "ready": [
        (None, "new", 0),
        ("new", "accepted", 1),
        ("accepted", "assembling", 3),
        ("assembling", "ready", 5),
    ],
    "delivery": [
        (None, "new", 0),
        ("new", "accepted", 1),
        ("accepted", "assembling", 3),
        ("assembling", "ready", 5),
        ("ready", "delivery", 7),
    ],
    "completed": [
        (None, "new", 0),
        ("new", "accepted", 1),
        ("accepted", "assembling", 3),
        ("assembling", "ready", 5),
        ("ready", "delivery", 7),
        ("delivery", "completed", 9),
    ],
    "cancelled": [(None, "new", 0), ("new", "accepted", 1), ("accepted", "cancelled", 2)],
    "rejected": [(None, "new", 0), ("new", "rejected", 1)],
}

# Заказы: client — индекс в CLIENTS, bouquet_name — название из seed_bouquets.BOUQUETS
ORDERS: list[dict] = [
    dict(client=0, bouquet_name="Нежность пиона", status="completed", days_ago=40,
         recipient_name="Светлана Кузнецова", recipient_phone="89261234511",
         delivery_address="г. Екатеринбург, ул. Восстания, д. 8, кв. 12",
         comment="Поздравляем с днём рождения!"),
    dict(client=0, bouquet_name="Алая страсть", status="completed", days_ago=25,
         recipient_name="Анна Кузнецова", recipient_phone="89261234501",
         delivery_address="г. Екатеринбург, ул. Ленина, д. 10, кв. 25",
         comment=None),
    dict(client=0, bouquet_name="Юбилейный фейерверк", status="completed", days_ago=15,
         recipient_name="Ольга Кузнецова", recipient_phone="89261234512",
         delivery_address="г. Екатеринбург, ул. 8 Марта, д. 40, кв. 3",
         comment="Юбилей мамы, очень ждём!"),
    dict(client=0, bouquet_name="Романтический вечер", status="completed", days_ago=8,
         recipient_name="Анна Кузнецова", recipient_phone="89261234501",
         delivery_address="г. Екатеринбург, ул. Ленина, д. 10, кв. 25",
         comment=None),
    dict(client=0, bouquet_name="Премиум розы", status="completed", days_ago=3,
         recipient_name="Анна Кузнецова", recipient_phone="89261234501",
         delivery_address="г. Екатеринбург, ул. Ленина, д. 10, кв. 25",
         comment="Самовывоз вечером"),
    dict(client=0, bouquet_name="Свадебный вальс", status="new", days_ago=0, hours_ago=3,
         recipient_name="Мария и Алексей", recipient_phone="89261234513",
         delivery_address="г. Екатеринбург, ул. Сурикова, д. 31",
         comment="Доставить к загсу за час до церемонии"),
    dict(client=1, bouquet_name="Летнее настроение", status="completed", days_ago=20,
         recipient_name="Дмитрий Соколов", recipient_phone="89031234502",
         delivery_address="г. Екатеринбург, ул. Малышева, д. 5",
         comment=None),
    dict(client=1, bouquet_name="Мужской стиль", status="completed", days_ago=10,
         recipient_name="Павел Соколов", recipient_phone="89031234521",
         delivery_address="г. Екатеринбург, ул. Куйбышева, д. 17",
         comment="С днём рождения, брат!"),
    dict(client=1, bouquet_name="Корпоративный шик", status="delivery", days_ago=1,
         recipient_name="Отдел продаж ООО «Альфа»", recipient_phone="89031234502",
         delivery_address="г. Екатеринбург, ул. Машиностроителей, д. 4, офис 210",
         comment="Привезти к 10:00, на ресепшн"),
    dict(client=2, bouquet_name="Светлая память", status="completed", days_ago=12,
         recipient_name="Елена Морозова", recipient_phone="89221234503",
         delivery_address="г. Екатеринбург, пр. Космонавтов, д. 14, кв. 7",
         comment=None),
    dict(client=2, bouquet_name="Выпускной бал", status="assembling", days_ago=2,
         recipient_name="Виктория Морозова", recipient_phone="89221234531",
         delivery_address="г. Екатеринбург, ул. Технической, д. 9",
         comment="Выпускной в школе №25"),
    dict(client=2, bouquet_name="Просто хорошего дня", status="cancelled", days_ago=5,
         recipient_name="Елена Морозова", recipient_phone="89221234503",
         delivery_address="г. Екатеринбург, пр. Космонавтов, д. 14, кв. 7",
         comment=None),
    dict(client=3, bouquet_name="Зимняя сказка", status="completed", days_ago=18,
         recipient_name="Игорь Васильев", recipient_phone="89121234504",
         delivery_address="г. Екатеринбург, ул. Восточная, д. 22",
         comment=None),
    dict(client=3, bouquet_name="Бюджетный букетик", status="accepted", days_ago=0, hours_ago=4,
         recipient_name="Игорь Васильев", recipient_phone="89121234504",
         delivery_address="г. Екатеринбург, ул. Восточная, д. 22",
         comment="Курьеру позвонить за 15 минут"),
    dict(client=4, bouquet_name="Весеннее пробуждение", status="new", days_ago=4,
         recipient_name="Мария Новикова", recipient_phone="89501234505",
         delivery_address="г. Екатеринбург, ул. Сакко и Ванцетти, д. 3, кв. 41",
         comment=None),
    dict(client=4, bouquet_name="Алая страсть", status="rejected", days_ago=6,
         recipient_name="Татьяна Новикова", recipient_phone="89501234551",
         delivery_address="г. Екатеринбург, ул. Шейнкмана, д. 90",
         comment="Адрес уточняется"),
]

# Отзывы для завершённых заказов: индекс заказа в ORDERS -> (оценка, текст)
REVIEWS: dict[int, tuple[int, str]] = {
    0: (5, "Очень понравился букет, спасибо за оперативную доставку!"),
    1: (4, "Красивые розы, но привезли немного позже обещанного времени."),
    2: (5, "Шикарная композиция на юбилей, все гости были в восторге!"),
    6: (5, "Яркий и свежий букет, поднял настроение всей семье."),
    9: (5, "Очень деликатно и достойно, спасибо за поддержку в трудный момент."),
}

# Избранное: (индекс клиента, название букета)
FAVORITES: list[tuple[int, str]] = [
    (0, "Премиум розы"),
    (0, "Свадебный вальс"),
    (2, "Выпускной бал"),
    (4, "Весеннее пробуждение"),
    (4, "Нежность пиона"),
]

_MONTHS_GENITIVE = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def _format_delivery_time(dt: datetime) -> str:
    return f"{dt.day} {_MONTHS_GENITIVE[dt.month - 1]}, {dt.strftime('%H:%M')}"


def _level_for(completed_orders: int) -> str:
    for level, threshold in LOYALTY_THRESHOLDS:
        if completed_orders >= threshold:
            return level
    return DEFAULT_LOYALTY_LEVEL


async def _seed_clients() -> None:
    for data in CLIENTS:
        registered_at = (now() - timedelta(days=data["registered_days_ago"])).isoformat(
            timespec="seconds"
        )
        await client_repo.accept_privacy(data["telegram_id"], registered_at)
        await client_repo.complete_registration(
            data["telegram_id"], data["full_name"], normalize_phone(data["phone"])
        )
        await client_repo.update_profile(
            data["telegram_id"],
            birth_date=data["birth_date"],
            delivery_address=data["delivery_address"],
            is_vip=data["is_vip"],
        )

    registered_at = (
        now() - timedelta(days=INCOMPLETE_CLIENT["registered_days_ago"])
    ).isoformat(timespec="seconds")
    await client_repo.accept_privacy(INCOMPLETE_CLIENT["telegram_id"], registered_at)


async def _seed_orders(bouquets_by_name: dict[str, Bouquet]) -> None:
    completed_counts = [0] * len(CLIENTS)

    async with get_connection() as conn:
        for index, item in enumerate(ORDERS):
            bouquet = bouquets_by_name[item["bouquet_name"]]
            client = CLIENTS[item["client"]]
            created_dt = now() - timedelta(
                days=item["days_ago"], hours=item.get("hours_ago", 0)
            )
            created_at = created_dt.isoformat(timespec="seconds")
            delivery_time = _format_delivery_time(
                created_dt + timedelta(days=1, hours=14 - created_dt.hour)
            )

            cursor = await conn.execute(
                """
                INSERT INTO orders (
                    telegram_id, bouquet_id, bouquet_name, recipient_name, recipient_phone,
                    delivery_address, delivery_time, comment, total_price, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client["telegram_id"],
                    bouquet.id,
                    bouquet.name,
                    item["recipient_name"],
                    normalize_phone(item["recipient_phone"]),
                    item["delivery_address"],
                    delivery_time,
                    item["comment"],
                    bouquet.price,
                    item["status"],
                    created_at,
                ),
            )
            order_id = cursor.lastrowid

            completed_at = None
            for old_status, new_status, offset_hours in _STATUS_HISTORY[item["status"]]:
                changed_at = (created_dt + timedelta(hours=offset_hours)).isoformat(
                    timespec="seconds"
                )
                changed_by = "client" if new_status in ("new", "cancelled") else "admin"
                await conn.execute(
                    """
                    INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, changed_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (order_id, old_status, new_status, changed_by, changed_at),
                )
                if new_status == "completed":
                    completed_at = changed_at

            await conn.commit()
            await bouquet_repo.increment_orders_count(bouquet.id)

            if completed_at:
                history_id = await history_repo.add(
                    telegram_id=client["telegram_id"],
                    bouquet_id=bouquet.id,
                    bouquet_name=bouquet.name,
                    occasion=bouquet.occasion,
                    season=bouquet.season,
                    price=bouquet.price,
                    ordered_at=completed_at,
                )
                points = int(bouquet.price // POINTS_PER_RUBLE_DIVISOR)
                await loyalty_repo.add_points_and_spent(client["telegram_id"], points, bouquet.price)
                completed_counts[item["client"]] += 1

                review = REVIEWS.get(index)
                if review:
                    rating, text = review
                    await review_repo.create(bouquet.id, client["telegram_id"], rating, text)
                    await history_repo.set_rating(history_id, rating)
                    await bouquet_repo.recalculate_rating(bouquet.id)

    for client, completed in zip(CLIENTS, completed_counts):
        level = _level_for(completed)
        if level != DEFAULT_LOYALTY_LEVEL:
            await loyalty_repo.set_level(client["telegram_id"], level)


async def _seed_favorites(bouquets_by_name: dict[str, Bouquet]) -> None:
    for client_index, bouquet_name in FAVORITES:
        client = CLIENTS[client_index]
        bouquet = bouquets_by_name[bouquet_name]
        await favorite_repo.add(client["telegram_id"], bouquet.id)


async def _seed_reminders() -> None:
    today = now().date()
    reminders = [
        (0, "Мама", (today + timedelta(days=3)).strftime("%d.%m"), "🎂 День рождения"),
        (1, "Жена", (today + timedelta(days=7)).strftime("%d.%m"), "💍 Годовщина"),
        (2, "Дочь", (today + timedelta(days=1)).strftime("%d.%m.%Y"), "🎂 День рождения"),
        (4, "Коллега", (today + timedelta(days=20)).strftime("%d.%m"), "🎉 Праздник"),
    ]
    for client_index, person_name, remind_date, occasion in reminders:
        client = CLIENTS[client_index]
        await reminder_repo.create(client["telegram_id"], person_name, remind_date, occasion)


async def _seed_sessions(bouquets_by_name: dict[str, Bouquet]) -> None:
    sessions = [
        (0, 35, "День рождения", "Маме", 1000, 3000, "Весна", "Пастельные", "Нежность", "Нежность пиона", True),
        (0, 9, "Юбилей", "Маме", 5000, 10000, "Осень", "Тёплые", "Роскошь", "Юбилейный фейерверк", True),
        (1, 21, "Просто так", "Себе", 0, 1000, "Неважно", "Микс", "Радость", "Просто хорошего дня", True),
        (1, 11, "День рождения", "Мужчине", 3000, 5000, "Неважно", "Тёплые", "Сдержанность", "Мужской стиль", True),
        (2, 13, "Траур", "Коллеге", 1000, 3000, "Неважно", "Холодные", "Сдержанность", "Светлая память", True),
        (2, 3, "Выпускной", "Девушке", 3000, 5000, "Лето", "Пастельные", "Радость", "Выпускной бал", True),
        (3, 19, "День рождения", "Девушке", 3000, 5000, "Зима", "Холодные", "Роскошь", "Зимняя сказка", True),
        (4, 5, "День рождения", "Маме", 1000, 3000, "Весна", "Пастельные", "Нежность", "Весеннее пробуждение", True),
        (4, 1, "Свадьба", "Девушке", 5000, 10000, "Лето", "Пастельные", "Роскошь", None, False),
        (1, 17, "Корпоратив", "Коллеге", 3000, 5000, "Неважно", "Холодные", "Сдержанность", None, False),
        (2, 7, "День влюблённых", "Девушке", 3000, 5000, "Неважно", "Тёплые", "Романтика", None, False),
        (3, 2, "Юбилей", "Девушке", 10000, None, "Неважно", "Тёплые", "Роскошь", None, False),
    ]

    async with get_connection() as conn:
        for client_index, days_ago, occasion, recipient, budget_from, budget_to, season, color, mood, bouquet_name, completed in sessions:
            client = CLIENTS[client_index]
            started_at = (now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
            result_bouquet_id = bouquets_by_name[bouquet_name].id if bouquet_name else None
            await conn.execute(
                """
                INSERT INTO selection_sessions (
                    telegram_id, occasion, budget_from, budget_to, season, recipient,
                    color_preference, flower_preferences, mood, result_bouquet_id, completed, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                """,
                (
                    client["telegram_id"], occasion, budget_from, budget_to, season, recipient,
                    color, mood, result_bouquet_id, int(completed), started_at,
                ),
            )
        await conn.commit()


async def seed() -> None:
    await init_db()

    if await client_repo.get(CLIENTS[0]["telegram_id"]) is not None:
        print("Демонстрационные данные уже загружены, заполнение пропущено.")
        return

    await seed_bouquets()
    bouquets_by_name = {b.name: b for b in await bouquet_repo.get_all()}

    await _seed_clients()
    await _seed_orders(bouquets_by_name)
    await _seed_favorites(bouquets_by_name)
    await _seed_reminders()
    await _seed_sessions(bouquets_by_name)

    print(
        f"Добавлено: {len(CLIENTS) + 1} клиентов, {len(ORDERS)} заказов, "
        f"{len(REVIEWS)} отзывов, {len(FAVORITES)} записей избранного, "
        f"{4} напоминания, {12} сессий подбора."
    )


if __name__ == "__main__":
    asyncio.run(seed())
