"""Заполнение каталога демонстрационным набором букетов.

Запуск: python -m scripts.seed_bouquets
"""

import asyncio

from app.database.connection import init_db
from app.repositories import bouquet_repo

BOUQUETS: list[dict] = [
    dict(
        name="Нежность пиона",
        description="Воздушный букет из розовых пионов и эустомы — тёплое поздравление маме.",
        price=2800,
        occasion="День рождения",
        season="Весна",
        mood="Нежность",
        colors="Пастельные",
        recipient="Маме",
        photo_path=None,
    ),
    dict(
        name="Алая страсть",
        description="Классические алые розы с зеленью — яркое признание в любви.",
        price=3500,
        occasion="День влюблённых",
        season="Всесезонный",
        mood="Романтика",
        colors="Тёплые",
        recipient="Девушке",
        photo_path=None,
    ),
    dict(
        name="Свадебный вальс",
        description="Изысканная композиция из белых роз, пионов и гипсофилы для особого дня.",
        price=8500,
        occasion="Свадьба",
        season="Лето",
        mood="Роскошь",
        colors="Пастельные,Холодные",
        recipient="Девушке",
        photo_path=None,
    ),
    dict(
        name="Корпоративный шик",
        description="Сдержанная и стильная композиция в деловых тонах для коллег.",
        price=4200,
        occasion="Корпоратив",
        season="Всесезонный",
        mood="Сдержанность",
        colors="Холодные",
        recipient="Коллеге",
        photo_path=None,
    ),
    dict(
        name="Юбилейный фейерверк",
        description="Пышный букет из гербер и хризантем ярких осенних оттенков.",
        price=6000,
        occasion="Юбилей",
        season="Осень",
        mood="Роскошь",
        colors="Тёплые,Микс",
        recipient="Маме",
        photo_path=None,
    ),
    dict(
        name="Выпускной бал",
        description="Лёгкий и радостный букет из тюльпанов и хризантем пастельных тонов.",
        price=3200,
        occasion="Выпускной",
        season="Лето",
        mood="Радость",
        colors="Пастельные",
        recipient="Девушке",
        photo_path=None,
    ),
    dict(
        name="Светлая память",
        description="Сдержанная композиция из белых хризантем.",
        price=2500,
        occasion="Траур",
        season="Всесезонный",
        mood="Сдержанность",
        colors="Холодные",
        recipient="Коллеге",
        photo_path=None,
    ),
    dict(
        name="Просто хорошего дня",
        description="Небольшой яркий букет-микс — отличный повод улыбнуться без повода.",
        price=900,
        occasion="Просто так",
        season="Всесезонный",
        mood="Радость",
        colors="Микс",
        recipient="Себе",
        photo_path=None,
    ),
    dict(
        name="Зимняя сказка",
        description="Белые и голубые тона, эвкалипт и зимняя зелень.",
        price=4700,
        occasion="День рождения",
        season="Зима",
        mood="Роскошь",
        colors="Холодные,Пастельные",
        recipient="Девушке",
        photo_path=None,
    ),
    dict(
        name="Летнее настроение",
        description="Яркий букет из подсолнухов и полевых цветов.",
        price=1800,
        occasion="Просто так",
        season="Лето",
        mood="Радость",
        colors="Тёплые",
        recipient="Ребёнку",
        photo_path=None,
    ),
    dict(
        name="Мужской стиль",
        description="Лаконичный букет из подсолнухов и зелени в крафтовой бумаге.",
        price=3100,
        occasion="День рождения",
        season="Всесезонный",
        mood="Сдержанность",
        colors="Тёплые",
        recipient="Мужчине",
        photo_path=None,
    ),
    dict(
        name="Романтический вечер",
        description="Букет из роз и пионовидных тюльпанов в тёплой пастельной гамме.",
        price=5200,
        occasion="Юбилей",
        season="Осень",
        mood="Романтика",
        colors="Тёплые,Пастельные",
        recipient="Девушке",
        photo_path=None,
    ),
    dict(
        name="Бюджетный букетик",
        description="Компактный букет из хризантем — приятный знак внимания.",
        price=700,
        occasion="Просто так",
        season="Всесезонный",
        mood="Радость",
        colors="Микс",
        recipient="Маме",
        photo_path=None,
    ),
    dict(
        name="Премиум розы",
        description="51 роза премиум-сорта — статусный подарок на юбилей.",
        price=12000,
        occasion="Юбилей",
        season="Всесезонный",
        mood="Роскошь",
        colors="Тёплые",
        recipient="Девушке",
        photo_path=None,
    ),
    dict(
        name="Весеннее пробуждение",
        description="Тюльпаны и нарциссы — нежный весенний привет маме.",
        price=2200,
        occasion="День рождения",
        season="Весна",
        mood="Нежность",
        colors="Пастельные,Тёплые",
        recipient="Маме",
        photo_path=None,
    ),
]


async def seed() -> None:
    await init_db()

    existing = await bouquet_repo.count_all()
    if existing:
        print(f"В каталоге уже есть {existing} букет(ов), заполнение пропущено.")
        return

    for data in BOUQUETS:
        await bouquet_repo.create(**data)

    print(f"Добавлено {len(BOUQUETS)} букетов в каталог.")


if __name__ == "__main__":
    asyncio.run(seed())
