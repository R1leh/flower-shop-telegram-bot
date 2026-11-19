"""Скоринг и подбор букетов под критерии клиента.

Веса критериев (см. ТЗ):
  повод 25%, бюджет 20%, получатель 15%, цвет 10%, настроение 10%,
  история заказов 10%, сезон 5%, популярность 3%, рейтинг 2%.
"""

import re
from dataclasses import dataclass
from typing import Optional

from app.models.bouquet import Bouquet
from app.repositories import bouquet_repo, client_repo, favorite_repo, history_repo

WEIGHT_OCCASION = 0.25
WEIGHT_BUDGET = 0.20
WEIGHT_RECIPIENT = 0.15
WEIGHT_COLOR = 0.10
WEIGHT_MOOD = 0.10
WEIGHT_HISTORY = 0.10
WEIGHT_SEASON = 0.05
WEIGHT_POPULARITY = 0.03
WEIGHT_RATING = 0.02

PURCHASED_PENALTY = 0.5
FAVORITE_OCCASION_BONUS = 0.05
VIP_PRICE_BONUS = 0.10
FLOWER_MATCH_BONUS = 0.05
MIN_RATING_THRESHOLD = 3.0
POPULARITY_NORMALIZER = 50


@dataclass
class ScoredBouquet:
    bouquet: Bouquet
    score: float
    is_exact: bool


def _budget_score(price: float, budget_from: float, budget_to: Optional[float]) -> float:
    if budget_to is None:
        return 1.0
    if budget_from <= price <= budget_to:
        return 1.0
    if price < budget_from:
        diff = budget_from - price
        ref = budget_from or budget_to
    else:
        diff = price - budget_to
        ref = budget_to
    return max(0.0, 1 - diff / ref) if ref else 0.0


def _color_score(preference: Optional[str], bouquet_colors: list[str]) -> float:
    if not preference or preference == "Неважно":
        return 1.0
    if preference in bouquet_colors:
        return 1.0
    if "Микс" in bouquet_colors:
        return 0.5
    return 0.0


def _season_score(preference: Optional[str], bouquet_season: Optional[str]) -> float:
    if not preference or preference == "Неважно":
        return 1.0
    if bouquet_season == "Всесезонный":
        return 1.0
    if bouquet_season == preference:
        return 1.0
    return 0.3


def _flower_bonus(preferences: Optional[str], bouquet: Bouquet) -> float:
    """Небольшой бонус, если любимые цветы клиента упомянуты в названии/описании."""
    if not preferences:
        return 0.0
    haystack = f"{bouquet.name} {bouquet.description or ''}".lower()
    for flower in re.split(r"[,;]", preferences):
        flower = flower.strip().lower()
        if flower and flower in haystack:
            return FLOWER_MATCH_BONUS
    return 0.0


async def get_recommendations(
    telegram_id: int, session: dict
) -> tuple[list[Bouquet], bool]:
    """Вернуть букеты, отсортированные по релевантности, и флаг точного совпадения."""
    bouquets = await bouquet_repo.get_active()

    # Букеты с реальным низким рейтингом (а не просто без отзывов, rating == 0)
    # исключаются из рекомендаций согласно ТЗ.
    bouquets = [b for b in bouquets if not (0 < b.rating < MIN_RATING_THRESHOLD)]
    if not bouquets:
        return [], False

    client = await client_repo.get(telegram_id)
    purchased_ids = await history_repo.get_purchased_bouquet_ids(telegram_id)
    occasion_counts = await history_repo.get_occasion_counts(telegram_id)
    favorite_occasions = await favorite_repo.get_favorite_occasions(telegram_id)
    max_price = max((b.price for b in bouquets), default=1) or 1
    history_total = sum(occasion_counts.values()) or 1

    occasion = session.get("occasion")
    budget_from = session.get("budget_from") or 0
    budget_to = session.get("budget_to")
    season = session.get("season")
    recipient = session.get("recipient")
    color_preference = session.get("color_preference")
    mood = session.get("mood")
    flower_preferences = session.get("flower_preferences")

    scored: list[ScoredBouquet] = []
    for bouquet in bouquets:
        occasion_score = 1.0 if occasion and bouquet.occasion == occasion else 0.0
        budget_score = _budget_score(bouquet.price, budget_from, budget_to)
        recipient_score = 1.0 if recipient and bouquet.recipient == recipient else 0.0
        color_score = _color_score(color_preference, bouquet.color_list)
        mood_score = 1.0 if mood and bouquet.mood == mood else 0.0
        history_score = (
            min(occasion_counts.get(bouquet.occasion, 0) / history_total, 1.0)
            if bouquet.occasion
            else 0.0
        )
        season_score = _season_score(season, bouquet.season)
        popularity_score = min(bouquet.orders_count / POPULARITY_NORMALIZER, 1.0)
        rating_score = (bouquet.rating or 0) / 5.0

        total = (
            occasion_score * WEIGHT_OCCASION
            + budget_score * WEIGHT_BUDGET
            + recipient_score * WEIGHT_RECIPIENT
            + color_score * WEIGHT_COLOR
            + mood_score * WEIGHT_MOOD
            + history_score * WEIGHT_HISTORY
            + season_score * WEIGHT_SEASON
            + popularity_score * WEIGHT_POPULARITY
            + rating_score * WEIGHT_RATING
        )

        total += _flower_bonus(flower_preferences, bouquet)

        if bouquet.occasion and bouquet.occasion in favorite_occasions:
            total += FAVORITE_OCCASION_BONUS

        if client and client.is_vip:
            total += (bouquet.price / max_price) * VIP_PRICE_BONUS

        if bouquet.id in purchased_ids:
            total *= PURCHASED_PENALTY

        is_exact = occasion_score == 1.0 and budget_score == 1.0
        scored.append(ScoredBouquet(bouquet=bouquet, score=total, is_exact=is_exact))

    scored.sort(key=lambda item: item.score, reverse=True)

    has_exact_match = bool(scored) and scored[0].is_exact
    ordered_bouquets = [item.bouquet for item in scored]
    return ordered_bouquets, has_exact_match
