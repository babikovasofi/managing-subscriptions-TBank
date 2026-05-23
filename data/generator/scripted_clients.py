"""
10 функций-сценариев для режиссированных клиентов.

Каждая функция принимает:
  client_id           : str
  subs_ref            : list[dict]  — subscriptions.json
  reg_ref             : list[dict]  — regular_merchants.json
  rng                 : np.random.Generator

Возвращает ScriptedClientResult.

Поле pre_expanded позволяет сценарию передать уже готовые транзакции
для конкретного мерчанта — generate.py пропустит expand_to_transactions
для этих мерчантов.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from data.generator.config import SIMULATION_TODAY, TRIAL_AMOUNT_RUB, TRIAL_DURATION_DAYS
from data.generator.noise_generator import generate_noise_transactions
from data.generator.personas import PERSONA_BY_NAME, Persona
from data.generator.subscription_generator import SubscriptionPlan


# ---------------------------------------------------------------------------
# Возвращаемый тип
# ---------------------------------------------------------------------------

@dataclass
class ScriptedClientResult:
    client_id: str
    persona: Persona
    subscription_plans: list[SubscriptionPlan]

    # Если не None — использовать вместо вызова noise_generator в generate.py.
    custom_noise_transactions: list[dict[str, Any]] | None = None

    # merchant_name → готовые транзакции; generate.py НЕ вызывает
    # expand_to_transactions для этих мерчантов (нужно для сценариев
    # с точным контролем дат, например scenario_trial_ending).
    pre_expanded: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # Дополнительные транзакции, не привязанные к SubscriptionPlan
    # (например, платежи фитнес-клуба для ловушки).
    extra_transactions: list[dict[str, Any]] = field(default_factory=list)

    # Дополнительные строки для labels.csv (например, «не-подписка»).
    extra_label_rows: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _get_sub(ref: list[dict], name: str) -> dict[str, Any]:
    for s in ref:
        if s["name"] == name:
            return s
    raise KeyError(f"Subscription not found: {name!r}")


def _get_merchant(ref: list[dict], name: str) -> dict[str, Any]:
    for m in ref:
        if m["name"] == name:
            return m
    raise KeyError(f"Merchant not found: {name!r}")


def _make_plan(
    client_id: str,
    merchant: dict[str, Any],
    start_date: datetime,
    end_date: datetime | None,
    price_history: list[tuple[datetime, float]],
    has_trial: bool = False,
    scenario_tag: str | None = None,
) -> SubscriptionPlan:
    return SubscriptionPlan(
        client_id=client_id,
        merchant=merchant,
        start_date=start_date,
        end_date=end_date,
        price_history=price_history,
        has_trial=has_trial,
        scenario_tag=scenario_tag,
    )


def _make_txn(
    client_id: str,
    merchant: dict[str, Any],
    dt: datetime,
    amount: float,
    description: str | None = None,
) -> dict[str, Any]:
    return {
        "transaction_id": str(uuid.uuid4()),
        "client_id": client_id,
        "date": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "amount": -round(abs(amount), 2),
        "merchant_name": merchant["name"],
        "mcc_code": merchant["mcc_code"],
        "category": merchant["category"],
        "description": description or merchant["name"],
    }


# ---------------------------------------------------------------------------
# Сценарий 1. Явный рост цены (Кинопоиск 299 → 399₽)
# ---------------------------------------------------------------------------

def scenario_price_increase(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Кинопоиск HD: первые ~5 месяцев по 299₽, затем повышение до 399₽.
    Жюри видит статус price_increased.
    """
    persona = PERSONA_BY_NAME["Заядлый стример"]
    kinopoisk = _get_sub(subs_ref, "Кинопоиск HD")

    start = SIMULATION_TODAY - timedelta(days=300)
    price_change_date = start + timedelta(days=150)   # ~5 мес после старта

    kino_plan = _make_plan(
        client_id=client_id,
        merchant=kinopoisk,
        start_date=start,
        end_date=None,
        price_history=[(start, 299.0), (price_change_date, 399.0)],
        scenario_tag="price_increase",
    )

    # Нейтральная вторая подписка для реализма.
    ya_music = _get_sub(subs_ref, "Яндекс.Музыка")
    music_start = SIMULATION_TODAY - timedelta(days=250)
    music_plan = _make_plan(
        client_id=client_id,
        merchant=ya_music,
        start_date=music_start,
        end_date=None,
        price_history=[(music_start, float(ya_music["base_price_rub"]))],
        scenario_tag="regular",
    )

    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[kino_plan, music_plan],
    )


# ---------------------------------------------------------------------------
# Сценарий 2. Пробный период заканчивается через 2 дня
# ---------------------------------------------------------------------------

def scenario_trial_ending(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    ivi: пробная транзакция (1₽) 32 дня назад. Первое полное списание
    ожидается ровно через 2 дня (SIMULATION_TODAY + 2) — в истории его нет.
    Используем pre_expanded, чтобы не вызывать expand_to_transactions
    (там есть джиттер, который может сдвинуть дату в прошлое).
    """
    persona = PERSONA_BY_NAME["Студент"]
    ivi = _get_sub(subs_ref, "ivi")

    # start + TRIAL_DURATION_DAYS = SIMULATION_TODAY + 2  →  start = TODAY - 28
    start = SIMULATION_TODAY - timedelta(days=TRIAL_DURATION_DAYS - 2)

    plan = _make_plan(
        client_id=client_id,
        merchant=ivi,
        start_date=start,
        end_date=None,
        price_history=[(start, float(ivi["base_price_rub"]))],
        has_trial=False,           # вручную управляем транзакциями ниже
        scenario_tag="trial_period",
    )

    # Единственная транзакция в истории — пробное списание 1₽.
    trial_dt = start.replace(hour=1, minute=0, second=0, microsecond=0)
    trial_txn = _make_txn(client_id, ivi, trial_dt, TRIAL_AMOUNT_RUB,
                          description=f"Подписка {ivi['name']} (пробный период)")

    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[plan],
        pre_expanded={ivi["name"]: [trial_txn]},
    )


# ---------------------------------------------------------------------------
# Сценарий 3. Заброшенный гейминг (VK Play Cloud — нет игровых трат 4 мес)
# ---------------------------------------------------------------------------

def scenario_abandoned_gaming(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    VK Play Cloud активен 10 месяцев. Шумовой фон за последние 4 месяца
    не содержит gaming-транзакций — признак заброшенности. Статус: possibly_unused.
    """
    persona = PERSONA_BY_NAME["Геймер"]
    vk_play = _get_sub(subs_ref, "VK Play Cloud")

    start = SIMULATION_TODAY - timedelta(days=300)
    plan = _make_plan(
        client_id=client_id,
        merchant=vk_play,
        start_date=start,
        end_date=None,
        price_history=[(start, float(vk_play["base_price_rub"]))],
        scenario_tag="abandoned",
    )

    # Генерируем шум, затем вычищаем gaming за последние 4 мес.
    gaming_cutoff = SIMULATION_TODAY - timedelta(days=120)
    noise = generate_noise_transactions(client_id, persona, reg_ref, rng)
    filtered = [
        t for t in noise
        if not (
            t["category"] == "gaming"
            and datetime.strptime(t["date"], "%Y-%m-%d %H:%M:%S") > gaming_cutoff
        )
    ]

    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[plan],
        custom_noise_transactions=filtered,
    )


# ---------------------------------------------------------------------------
# Сценарий 4. Тяжёлый пользователь (8 подписок, >5000₽/мес)
# ---------------------------------------------------------------------------

def scenario_heavy_user(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    8 активных подписок суммарно ~10 635₽/мес. Стресс для аналитики и UI.
    """
    persona = PERSONA_BY_NAME["Активный пользователь подписок"]
    # Итого: 4990 + 169 + 1190 + 449 + 399 + 399 + 99 + 399 = 8 094₽
    services = [
        ("Skillbox",                  0),
        ("VK Combo",                 10),
        ("Битрикс24 Базовый",        20),
        ("GFN.RU",                   30),
        ("Кинопоиск HD",             40),
        ("Яндекс.Плюс",              50),
        ("МегаФон Облако",           60),
        ("Литрес Букмейт",           70),
    ]
    plans = []
    for name, offset in services:
        merchant = _get_sub(subs_ref, name)
        start = SIMULATION_TODAY - timedelta(days=300 - offset)
        plans.append(_make_plan(
            client_id=client_id,
            merchant=merchant,
            start_date=start,
            end_date=None,
            price_history=[(start, float(merchant["base_price_rub"]))],
            scenario_tag="regular",
        ))
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=plans,
    )


# ---------------------------------------------------------------------------
# Сценарий 5. Новичок (1 подписка, 2 месяца истории)
# ---------------------------------------------------------------------------

def scenario_newbie(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Яндекс.Плюс — единственная подписка, стартовала 60 дней назад.
    Простейший кейс: 2 списания, никаких аномалий.
    """
    persona = PERSONA_BY_NAME["Студент"]
    merchant = _get_sub(subs_ref, "Яндекс.Плюс")
    start = SIMULATION_TODAY - timedelta(days=60)
    plan = _make_plan(
        client_id=client_id,
        merchant=merchant,
        start_date=start,
        end_date=None,
        price_history=[(start, float(merchant["base_price_rub"]))],
        scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[plan],
    )


# ---------------------------------------------------------------------------
# Сценарий 6. Перекрывающиеся даты списания (стресс на UI)
# ---------------------------------------------------------------------------

def scenario_overlapping_dates(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    4 подписки с одинаковым днём старта: все биллинги кластеризуются
    в ±2 дня каждого месяца — проверяем, что UI не ломается.
    """
    persona = PERSONA_BY_NAME["Активный пользователь подписок"]
    common_start = SIMULATION_TODAY - timedelta(days=240)
    services = ["Кинопоиск HD", "Яндекс.Музыка", "Telegram Premium", "МегаФон Облако"]
    plans = []
    for name in services:
        merchant = _get_sub(subs_ref, name)
        plans.append(_make_plan(
            client_id=client_id,
            merchant=merchant,
            start_date=common_start,
            end_date=None,
            price_history=[(common_start, float(merchant["base_price_rub"]))],
            scenario_tag="regular",
        ))
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=plans,
    )


# ---------------------------------------------------------------------------
# Сценарий 7. Бывший пользователь (был активен 6 мес, отписался месяц назад)
# ---------------------------------------------------------------------------

def scenario_former_user(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Кинопоиск + Яндекс.Музыка: обе подписки завершились ~35 дней назад.
    Последний месяц — без списаний. Система не должна «ругаться».
    """
    persona = PERSONA_BY_NAME["Заядлый стример"]
    end_date = SIMULATION_TODAY - timedelta(days=35)
    plans = []
    for name in ["Кинопоиск HD", "Яндекс.Музыка"]:
        merchant = _get_sub(subs_ref, name)
        start = end_date - timedelta(days=180)
        plans.append(_make_plan(
            client_id=client_id,
            merchant=merchant,
            start_date=start,
            end_date=end_date,
            price_history=[(start, float(merchant["base_price_rub"]))],
            scenario_tag="regular",
        ))
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=plans,
    )


# ---------------------------------------------------------------------------
# Сценарий 8. Дублирующиеся музыкальные сервисы
# ---------------------------------------------------------------------------

def scenario_duplicate_services(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Яндекс.Музыка + VK Музыка — обе активны одновременно.
    Аналитика предложит задуматься о дублировании.
    """
    persona = PERSONA_BY_NAME["Забывашка"]
    plans = []
    for name, days_ago in [("Яндекс.Музыка", 280), ("VK Музыка", 200)]:
        merchant = _get_sub(subs_ref, name)
        start = SIMULATION_TODAY - timedelta(days=days_ago)
        plans.append(_make_plan(
            client_id=client_id,
            merchant=merchant,
            start_date=start,
            end_date=None,
            price_history=[(start, float(merchant["base_price_rub"]))],
            scenario_tag="regular",
        ))
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=plans,
    )


# ---------------------------------------------------------------------------
# Сценарий 9. Ложный положительный (абонемент в зал ≠ подписка)
# ---------------------------------------------------------------------------

def scenario_false_positive_trap(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    World Class: 11 ежемесячных платежей по 4 200₽ — НЕ подписка.
    Стабильная сумма и период — ловушка для rule-based модели.
    Плюс Telegram Premium как настоящая подписка для контраста.
    """
    persona = PERSONA_BY_NAME["IT-специалист"]
    gym = _get_merchant(reg_ref, "World Class")
    gym_amount = 4200.0

    gym_txns: list[dict[str, Any]] = []
    for i in range(11):
        # День 5-го числа каждого месяца, за последние 11 месяцев.
        dt = (SIMULATION_TODAY - timedelta(days=330 - i * 30)).replace(
            day=5, hour=9, minute=0, second=0, microsecond=0
        )
        if dt > SIMULATION_TODAY:
            break
        gym_txns.append(_make_txn(
            client_id, gym, dt, gym_amount,
            description=f"Абонемент {gym['name']}",
        ))

    # Метка для labels.csv: World Class = НЕ подписка.
    gym_label = {
        "client_id": client_id,
        "merchant_name": gym["name"],
        "is_subscription": False,
        "true_period_days": 30,
        "true_amount": gym_amount,
        "scenario_tag": "false_positive_trap",
    }

    # Реальная подписка для контраста.
    tg = _get_sub(subs_ref, "Telegram Premium")
    tg_start = SIMULATION_TODAY - timedelta(days=270)
    tg_plan = _make_plan(
        client_id=client_id,
        merchant=tg,
        start_date=tg_start,
        end_date=None,
        price_history=[(tg_start, float(tg["base_price_rub"]))],
        scenario_tag="regular",
    )

    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[tg_plan],
        extra_transactions=gym_txns,
        extra_label_rows=[gym_label],
    )


# ---------------------------------------------------------------------------
# Сценарий 10. Семейный план (Яндекс.Плюс Семейный по 699₽)
# ---------------------------------------------------------------------------

def scenario_family_plan(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Яндекс.Плюс Семейный: одна подписка, цена 699₽ (выше стандартной 399₽).
    Проверяем, что система не дублирует её для «членов семьи».
    """
    persona = PERSONA_BY_NAME["Семейный"]
    ya_plus = _get_sub(subs_ref, "Яндекс.Плюс")
    # Создаём вариант мерчанта с семейным названием и ценой.
    ya_family: dict[str, Any] = {**ya_plus, "name": "Яндекс.Плюс Семейный"}
    family_price = 699.0

    start = SIMULATION_TODAY - timedelta(days=270)
    plan = _make_plan(
        client_id=client_id,
        merchant=ya_family,
        start_date=start,
        end_date=None,
        price_history=[(start, family_price)],
        scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[plan],
    )


# ---------------------------------------------------------------------------
# Вспомогательная функция для hard-negative транзакций
# ---------------------------------------------------------------------------

def _generate_hard_neg_txns(
    client_id: str,
    merchant: dict[str, Any],
    amount: float,
    interval_days: int,
    n_payments: int,
    rng: np.random.Generator,
    jitter_days: int = 1,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Генерирует транзакции с фиксированной суммой и стабильным интервалом.

    Гарантирует прохождение rule-based фильтра (cv_amount≈0, cv_interval<0.1),
    при этом мерчант маркируется is_subscription=False в labels.csv.

    Возвращает (list[txn], label_row).
    """
    txns: list[dict[str, Any]] = []
    start_dt = (
        SIMULATION_TODAY - timedelta(days=interval_days * n_payments)
    ).replace(hour=10, minute=0, second=0, microsecond=0)
    current_dt = start_dt

    for _ in range(n_payments):
        jitter = int(rng.integers(-jitter_days, jitter_days + 1))
        dt = current_dt + timedelta(days=jitter)
        if dt > SIMULATION_TODAY:
            break
        txns.append(_make_txn(client_id, merchant, dt, amount))
        current_dt += timedelta(days=interval_days)

    label_row: dict[str, Any] = {
        "client_id": client_id,
        "merchant_name": merchant["name"],
        "is_subscription": False,
        "true_period_days": interval_days,
        "true_amount": amount,
        "scenario_tag": "hard_negative",
    }
    return txns, label_row


# ---------------------------------------------------------------------------
# Сценарий 11. Арендатор (3 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_renter(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Аренда жилья + Дом.ру + УК Жилой Дом — все три регулярные, но не подписки.
    Реальная подписка Яндекс.Плюс добавлена для реализма.
    """
    persona = PERSONA_BY_NAME["Семейный"]
    rent_txns, rent_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Аренда жилья"), 38_000.0, 30, 11, rng, 1
    )
    domru_txns, domru_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Дом.ру"), 650.0, 30, 11, rng, 2
    )
    uk_txns, uk_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "УК Жилой Дом"), 2_100.0, 30, 11, rng, 2
    )
    ya_plus = _get_sub(subs_ref, "Яндекс.Плюс")
    sub_start = SIMULATION_TODAY - timedelta(days=200)
    sub_plan = _make_plan(
        client_id, ya_plus, sub_start, None,
        [(sub_start, float(ya_plus["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=rent_txns + domru_txns + uk_txns,
        extra_label_rows=[rent_lbl, domru_lbl, uk_lbl],
    )


# ---------------------------------------------------------------------------
# Сценарий 12. Ипотечник с паркингом и страховкой (3 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_mortgager_1(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Тинькофф Ипотека (jitter=0, банковский автоплатёж) + Паркинг Центр
    + АльфаСтрахование. Ипотека — максимально стабильный интервал, cv_interval≈0.
    Реальная подписка МегаФон Облако.
    """
    persona = PERSONA_BY_NAME["Семейный"]
    ipoteka_txns, ipoteka_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Тинькофф Ипотека"), 35_000.0, 30, 11, rng, 0
    )
    parking_txns, parking_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Паркинг Центр"), 8_500.0, 30, 11, rng, 1
    )
    insurance_txns, insurance_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "АльфаСтрахование"), 2_200.0, 30, 11, rng, 1
    )
    megafon = _get_sub(subs_ref, "МегаФон Облако")
    sub_start = SIMULATION_TODAY - timedelta(days=250)
    sub_plan = _make_plan(
        client_id, megafon, sub_start, None,
        [(sub_start, float(megafon["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=ipoteka_txns + parking_txns + insurance_txns,
        extra_label_rows=[ipoteka_lbl, parking_lbl, insurance_lbl],
    )


# ---------------------------------------------------------------------------
# Сценарий 13. Ипотечник с интернетом и страховкой (3 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_mortgager_2(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Тинькофф Ипотека + Дом.ру (MCC 4816 — подписочный!) + АльфаСтрахование.
    Дом.ру — самый сложный: MCC совпадает с подписками (МегаФон Облако, Яндекс 360).
    Реальная подписка Кинопоиск HD.
    """
    persona = PERSONA_BY_NAME["IT-специалист"]
    ipoteka_txns, ipoteka_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Тинькофф Ипотека"), 42_000.0, 30, 11, rng, 0
    )
    domru_txns, domru_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Дом.ру"), 650.0, 30, 11, rng, 2
    )
    insurance_txns, insurance_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "АльфаСтрахование"), 1_900.0, 30, 11, rng, 1
    )
    kino = _get_sub(subs_ref, "Кинопоиск HD")
    sub_start = SIMULATION_TODAY - timedelta(days=260)
    sub_plan = _make_plan(
        client_id, kino, sub_start, None,
        [(sub_start, float(kino["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=ipoteka_txns + domru_txns + insurance_txns,
        extra_label_rows=[ipoteka_lbl, domru_lbl, insurance_lbl],
    )


# ---------------------------------------------------------------------------
# Сценарий 14. BNPL-рассрочка и паркинг (2 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_bnpl(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Тинькофф Рассрочка (8 платежей, конечная, jitter=0) + Паркинг Центр.
    Рассрочка отличается от подписки конечным числом платежей.
    Реальная подписка Telegram Premium.
    """
    persona = PERSONA_BY_NAME["Фрилансер"]
    bnpl_txns, bnpl_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Тинькофф Рассрочка"), 4_500.0, 30, 8, rng, 0
    )
    parking_txns, parking_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Паркинг Центр"), 7_000.0, 30, 11, rng, 1
    )
    tg = _get_sub(subs_ref, "Telegram Premium")
    sub_start = SIMULATION_TODAY - timedelta(days=270)
    sub_plan = _make_plan(
        client_id, tg, sub_start, None,
        [(sub_start, float(tg["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=bnpl_txns + parking_txns,
        extra_label_rows=[bnpl_lbl, parking_lbl],
    )


# ---------------------------------------------------------------------------
# Сценарий 15. Учащийся — сложнейшие hard negatives (2 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_learner(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Школа английского (MCC 8299 — подписочный, category='education') +
    Дом.ру (MCC 4816 — подписочный, category='utilities').
    Оба имеют подписочный MCC — отличает только in_subscription_dict=False.
    Реальная подписка Stepik Pro.
    """
    persona = PERSONA_BY_NAME["IT-специалист"]
    school_txns, school_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Школа английского"), 5_500.0, 30, 11, rng, 2
    )
    domru_txns, domru_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Дом.ру"), 650.0, 30, 11, rng, 2
    )
    stepik = _get_sub(subs_ref, "Stepik Pro")
    sub_start = SIMULATION_TODAY - timedelta(days=220)
    sub_plan = _make_plan(
        client_id, stepik, sub_start, None,
        [(sub_start, float(stepik["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=school_txns + domru_txns,
        extra_label_rows=[school_lbl, domru_lbl],
    )


# ---------------------------------------------------------------------------
# Сценарий 16. Студент с двухнедельным репетитором (2 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_tutor_student(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Репетитор (интервал 14 дней — отличается от типичных 30-дневных подписок) +
    УК Жилой Дом. Репетитор: 22 платежа за ~10 месяцев.
    Реальная подписка Яндекс.Музыка.
    """
    persona = PERSONA_BY_NAME["Студент"]
    tutor_txns, tutor_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Репетитор"), 5_000.0, 14, 22, rng, 1
    )
    uk_txns, uk_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "УК Жилой Дом"), 1_800.0, 30, 11, rng, 2
    )
    ya_music = _get_sub(subs_ref, "Яндекс.Музыка")
    sub_start = SIMULATION_TODAY - timedelta(days=230)
    sub_plan = _make_plan(
        client_id, ya_music, sub_start, None,
        [(sub_start, float(ya_music["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=tutor_txns + uk_txns,
        extra_label_rows=[tutor_lbl, uk_lbl],
    )


# ---------------------------------------------------------------------------
# Сценарий 17. Фитнес и страхование (2 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_fitness(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Фитнес Хаус + АльфаСтрахование. Фитнес — аналог сценария 9 (World Class),
    но другой клуб и другой клиент; добавляет разнообразие негативов в fitness.
    Реальная подписка VK Музыка.
    """
    persona = PERSONA_BY_NAME["Фрилансер"]
    fitness_txns, fitness_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Фитнес Хаус"), 2_900.0, 30, 11, rng, 2
    )
    insurance_txns, insurance_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "АльфаСтрахование"), 2_400.0, 30, 11, rng, 1
    )
    vk_music = _get_sub(subs_ref, "VK Музыка")
    sub_start = SIMULATION_TODAY - timedelta(days=180)
    sub_plan = _make_plan(
        client_id, vk_music, sub_start, None,
        [(sub_start, float(vk_music["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=fitness_txns + insurance_txns,
        extra_label_rows=[fitness_lbl, insurance_lbl],
    )


# ---------------------------------------------------------------------------
# Сценарий 18. Стример-арендатор (2 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_streamer_renter(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Аренда жилья (другая сумма, чем scripted_11) + Фитнес Хаус.
    Реальная подписка ivi.
    """
    persona = PERSONA_BY_NAME["Заядлый стример"]
    rent_txns, rent_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Аренда жилья"), 31_000.0, 30, 11, rng, 1
    )
    fitness_txns, fitness_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Фитнес Хаус"), 3_200.0, 30, 11, rng, 2
    )
    ivi = _get_sub(subs_ref, "ivi")
    sub_start = SIMULATION_TODAY - timedelta(days=240)
    sub_plan = _make_plan(
        client_id, ivi, sub_start, None,
        [(sub_start, float(ivi["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=rent_txns + fitness_txns,
        extra_label_rows=[rent_lbl, fitness_lbl],
    )


# ---------------------------------------------------------------------------
# Сценарий 19. Минималист с рассрочкой и курсами (3 hard negatives)
# ---------------------------------------------------------------------------

def scenario_hard_negative_minimalist_bnpl(
    client_id: str,
    subs_ref: list[dict],
    reg_ref: list[dict],
    rng: np.random.Generator,
) -> ScriptedClientResult:
    """
    Тинькофф Рассрочка (7 платежей) + Школа английского (education/MCC 8299)
    + УК Жилой Дом. Самый богатый по числу hard-негативов: 3 штуки.
    Реальная подписка Яндекс 360.
    """
    persona = PERSONA_BY_NAME["Минималист"]
    bnpl_txns, bnpl_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Тинькофф Рассрочка"), 3_800.0, 30, 7, rng, 0
    )
    school_txns, school_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "Школа английского"), 4_800.0, 30, 11, rng, 2
    )
    uk_txns, uk_lbl = _generate_hard_neg_txns(
        client_id, _get_merchant(reg_ref, "УК Жилой Дом"), 1_700.0, 30, 11, rng, 2
    )
    ya360 = _get_sub(subs_ref, "Яндекс 360")
    sub_start = SIMULATION_TODAY - timedelta(days=180)
    sub_plan = _make_plan(
        client_id, ya360, sub_start, None,
        [(sub_start, float(ya360["base_price_rub"]))], scenario_tag="regular",
    )
    return ScriptedClientResult(
        client_id=client_id,
        persona=persona,
        subscription_plans=[sub_plan],
        extra_transactions=bnpl_txns + school_txns + uk_txns,
        extra_label_rows=[bnpl_lbl, school_lbl, uk_lbl],
    )


# ---------------------------------------------------------------------------
# Реестр (порядок соответствует нумерации в CLAUDE.md)
# ---------------------------------------------------------------------------

SCRIPTED_SCENARIOS = [
    scenario_price_increase,                  # 1
    scenario_trial_ending,                    # 2
    scenario_abandoned_gaming,                # 3
    scenario_heavy_user,                      # 4
    scenario_newbie,                          # 5
    scenario_overlapping_dates,               # 6
    scenario_former_user,                     # 7
    scenario_duplicate_services,              # 8
    scenario_false_positive_trap,             # 9
    scenario_family_plan,                     # 10
    scenario_hard_negative_renter,            # 11
    scenario_hard_negative_mortgager_1,       # 12
    scenario_hard_negative_mortgager_2,       # 13
    scenario_hard_negative_bnpl,              # 14
    scenario_hard_negative_learner,           # 15
    scenario_hard_negative_tutor_student,     # 16
    scenario_hard_negative_fitness,           # 17
    scenario_hard_negative_streamer_renter,   # 18
    scenario_hard_negative_minimalist_bnpl,   # 19
]
