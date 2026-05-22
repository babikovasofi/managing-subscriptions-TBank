from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Persona:
    name: str
    # Категории подписок, характерные для этого архетипа (из subscriptions.json).
    # Генератор использует их как веса при случайном выборе подписок.
    typical_subscription_categories: List[str]
    # (min, max) числа подписок у клиента данного архетипа.
    n_subscriptions_range: Tuple[int, int]
    # (min, max) общего числа транзакций в месяц (подписки + шум).
    monthly_transactions_range: Tuple[int, int]
    # Относительные веса категорий из regular_merchants.json.
    # Нули означают «этот мерчант не характерен для персоны».
    regular_categories_weights: Dict[str, float]
    # Примерный диапазон суммарных трат/мес в рублях (ориентир для генератора шума).
    monthly_total_spending_range: Tuple[int, int]


PERSONAS: List[Persona] = [
    Persona(
        name="Студент",
        typical_subscription_categories=[
            "streaming_music",
            "streaming_video",
            "education",
        ],
        n_subscriptions_range=(1, 3),
        monthly_transactions_range=(30, 50),
        regular_categories_weights={
            "groceries": 1.5,
            "transport": 1.5,
            "food_delivery_oneoff": 0.5,
            "pharmacy": 0.3,
            "clothing": 0.3,
            "fuel": 0.0,
            "cafe": 0.8,
            "marketplace": 1.0,
            "utilities": 0.3,
            "fitness": 0.0,
            "atm": 0.5,
            "entertainment": 0.5,
        },
        monthly_total_spending_range=(15_000, 35_000),
    ),
    Persona(
        name="Фрилансер",
        typical_subscription_categories=[
            "productivity",
            "streaming_video",
            "streaming_music",
            "cloud_storage",
        ],
        n_subscriptions_range=(3, 6),
        monthly_transactions_range=(40, 70),
        regular_categories_weights={
            "groceries": 1.0,
            "transport": 0.5,
            "food_delivery_oneoff": 1.2,
            "pharmacy": 0.3,
            "clothing": 0.5,
            "fuel": 0.3,
            "cafe": 1.5,
            "marketplace": 1.0,
            "utilities": 0.5,
            "fitness": 0.5,
            "atm": 0.3,
            "entertainment": 0.5,
        },
        monthly_total_spending_range=(40_000, 90_000),
    ),
    Persona(
        name="Семейный",
        typical_subscription_categories=[
            "food_delivery",
            "streaming_video",
            "cloud_storage",
            "streaming_music",
        ],
        n_subscriptions_range=(2, 5),
        monthly_transactions_range=(50, 90),
        regular_categories_weights={
            "groceries": 2.0,
            "transport": 0.8,
            "food_delivery_oneoff": 0.8,
            "pharmacy": 0.8,
            "clothing": 1.0,
            "fuel": 1.2,
            "cafe": 0.5,
            "marketplace": 1.5,
            "utilities": 1.0,
            "fitness": 0.3,
            "atm": 0.5,
            "entertainment": 0.5,
        },
        monthly_total_spending_range=(70_000, 150_000),
    ),
    Persona(
        name="Геймер",
        typical_subscription_categories=[
            "gaming",
            "streaming_video",
            "streaming_music",
        ],
        n_subscriptions_range=(2, 5),
        monthly_transactions_range=(35, 65),
        regular_categories_weights={
            "groceries": 0.8,
            "transport": 0.8,
            "food_delivery_oneoff": 1.5,
            "pharmacy": 0.1,
            "clothing": 0.3,
            "fuel": 0.2,
            "cafe": 0.8,
            "marketplace": 1.5,
            "utilities": 0.3,
            "fitness": 0.0,
            "atm": 0.3,
            "entertainment": 0.8,
        },
        monthly_total_spending_range=(30_000, 70_000),
    ),
    Persona(
        name="Забывашка",
        # Подписывается на всё подряд и не отписывается — широкий охват категорий.
        typical_subscription_categories=[
            "streaming_video",
            "streaming_music",
            "cloud_storage",
            "education",
            "food_delivery",
            "reading",
            "other",
        ],
        n_subscriptions_range=(4, 8),
        monthly_transactions_range=(40, 70),
        regular_categories_weights={
            "groceries": 1.0,
            "transport": 1.0,
            "food_delivery_oneoff": 1.0,
            "pharmacy": 0.5,
            "clothing": 0.8,
            "fuel": 0.5,
            "cafe": 0.8,
            "marketplace": 1.0,
            "utilities": 0.5,
            "fitness": 0.3,
            "atm": 0.5,
            "entertainment": 0.5,
        },
        monthly_total_spending_range=(40_000, 80_000),
    ),
    Persona(
        name="IT-специалист",
        typical_subscription_categories=[
            "productivity",
            "cloud_storage",
            "streaming_video",
            "streaming_music",
        ],
        n_subscriptions_range=(4, 8),
        monthly_transactions_range=(50, 80),
        regular_categories_weights={
            "groceries": 0.8,
            "transport": 0.5,
            "food_delivery_oneoff": 1.5,
            "pharmacy": 0.2,
            "clothing": 0.5,
            "fuel": 0.3,
            "cafe": 1.5,
            "marketplace": 1.2,
            "utilities": 0.5,
            "fitness": 0.8,
            "atm": 0.2,
            "entertainment": 0.5,
        },
        monthly_total_spending_range=(80_000, 200_000),
    ),
    Persona(
        name="Минималист",
        # Сознательно ограничивает расходы — минимум подписок.
        typical_subscription_categories=[
            "food_delivery",
            "cloud_storage",
        ],
        n_subscriptions_range=(0, 2),
        monthly_transactions_range=(30, 50),
        regular_categories_weights={
            "groceries": 1.5,
            "transport": 1.0,
            "food_delivery_oneoff": 0.3,
            "pharmacy": 0.5,
            "clothing": 0.2,
            "fuel": 0.3,
            "cafe": 0.3,
            "marketplace": 0.5,
            "utilities": 0.8,
            "fitness": 0.0,
            "atm": 0.5,
            "entertainment": 0.2,
        },
        monthly_total_spending_range=(25_000, 55_000),
    ),
    Persona(
        name="Заядлый стример",
        # Основной досуг — потребление контента. Много стриминга.
        typical_subscription_categories=[
            "streaming_video",
            "streaming_music",
            "reading",
        ],
        n_subscriptions_range=(3, 7),
        monthly_transactions_range=(40, 70),
        regular_categories_weights={
            "groceries": 1.0,
            "transport": 0.8,
            "food_delivery_oneoff": 1.2,
            "pharmacy": 0.2,
            "clothing": 0.5,
            "fuel": 0.3,
            "cafe": 0.8,
            "marketplace": 0.8,
            "utilities": 0.3,
            "fitness": 0.0,
            "atm": 0.3,
            "entertainment": 0.3,
        },
        monthly_total_spending_range=(35_000, 75_000),
    ),
    Persona(
        name="Активный пользователь подписок",
        # Подписан на сервисы из всех категорий — максимальная нагрузка для ML.
        typical_subscription_categories=[
            "streaming_video",
            "streaming_music",
            "cloud_storage",
            "education",
            "gaming",
            "food_delivery",
            "productivity",
            "reading",
        ],
        n_subscriptions_range=(6, 12),
        monthly_transactions_range=(60, 100),
        regular_categories_weights={
            "groceries": 1.0,
            "transport": 1.0,
            "food_delivery_oneoff": 1.2,
            "pharmacy": 0.4,
            "clothing": 0.8,
            "fuel": 0.5,
            "cafe": 1.0,
            "marketplace": 1.5,
            "utilities": 0.5,
            "fitness": 0.5,
            "atm": 0.3,
            "entertainment": 0.8,
        },
        monthly_total_spending_range=(60_000, 150_000),
    ),
    Persona(
        name="Пенсионер с цифровыми привычками",
        # Освоил смартфон и базовые сервисы, но скромен в расходах.
        typical_subscription_categories=[
            "streaming_video",
            "cloud_storage",
        ],
        n_subscriptions_range=(1, 3),
        monthly_transactions_range=(30, 55),
        regular_categories_weights={
            "groceries": 2.0,
            "transport": 1.0,
            "food_delivery_oneoff": 0.3,
            "pharmacy": 1.5,
            "clothing": 0.5,
            "fuel": 0.3,
            "cafe": 0.3,
            "marketplace": 0.5,
            "utilities": 1.0,
            "fitness": 0.0,
            "atm": 1.0,
            "entertainment": 0.3,
        },
        monthly_total_spending_range=(30_000, 70_000),
    ),
]

# Быстрый доступ по имени.
PERSONA_BY_NAME: Dict[str, Persona] = {p.name: p for p in PERSONAS}
