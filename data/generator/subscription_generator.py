"""
Генератор подписочных транзакций для одного клиента.

Публичный API:
  generate_subscriptions_for_client(...) -> list[SubscriptionPlan]
  expand_to_transactions(plan, rng)      -> list[dict]  (строки transactions.csv)
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from data.generator.config import (
    AMOUNT_NOISE_FRACTION,
    PAYMENT_DATE_JITTER_DAYS,
    PRICE_INCREASE_MAX_FACTOR,
    PRICE_INCREASE_MIN_FACTOR,
    PRICE_INCREASE_PROBABILITY,
    SIMULATION_TODAY,
    SUBSCRIPTION_MAX_AGE_MONTHS,
    SUBSCRIPTION_MIN_AGE_MONTHS,
    TRIAL_AMOUNT_RUB,
    TRIAL_DURATION_DAYS,
    TRIAL_PERIOD_PROBABILITY,
)
from data.generator.personas import Persona


@dataclass
class SubscriptionPlan:
    client_id: str
    merchant: dict[str, Any]          # запись из subscriptions.json
    start_date: datetime               # дата первого списания (или пробного)
    end_date: datetime | None          # None = подписка активна по сей день
    # Ценовая история: [(дата вступления в силу, сумма), ...].
    # Первый элемент — исходная цена. Второй — повышенная (если было).
    price_history: list[tuple[datetime, float]]
    has_trial: bool                    # был ли пробный период
    scenario_tag: str | None           # None для случайных клиентов


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _get_price_at(price_history: list[tuple[datetime, float]], at: datetime) -> float:
    """Возвращает цену, действующую на дату at."""
    price = price_history[0][1]
    for effective_from, amount in price_history:
        if at >= effective_from:
            price = amount
    return price


def _random_start_date(rng: np.random.Generator) -> datetime:
    """Случайная дата старта подписки в окне [min_age, max_age] мес до SIMULATION_TODAY."""
    min_days = SUBSCRIPTION_MIN_AGE_MONTHS * 30
    max_days = SUBSCRIPTION_MAX_AGE_MONTHS * 30
    days_ago = int(rng.integers(min_days, max_days + 1))
    return SIMULATION_TODAY - timedelta(days=days_ago)


def _build_price_history(
    merchant: dict[str, Any],
    start_date: datetime,
    rng: np.random.Generator,
) -> list[tuple[datetime, float]]:
    """
    Строит ценовую историю. С вероятностью PRICE_INCREASE_PROBABILITY
    добавляет одно повышение цены в середине истории.
    """
    base = float(merchant["base_price_rub"])
    history: list[tuple[datetime, float]] = [(start_date, base)]

    if rng.random() < PRICE_INCREASE_PROBABILITY:
        # Повышение происходит в случайный момент между 3 мес и 9 мес после старта.
        change_offset_days = int(rng.integers(90, 270))
        change_date = start_date + timedelta(days=change_offset_days)
        if change_date < SIMULATION_TODAY:
            factor = rng.uniform(PRICE_INCREASE_MIN_FACTOR, PRICE_INCREASE_MAX_FACTOR)
            new_price = round(base * factor)
            history.append((change_date, float(new_price)))

    return history


# ---------------------------------------------------------------------------
# Основная функция генерации
# ---------------------------------------------------------------------------

def generate_subscriptions_for_client(
    client_id: str,
    persona: Persona,
    subscriptions_ref: list[dict[str, Any]],
    rng: np.random.Generator,
) -> list[SubscriptionPlan]:
    """
    Генерирует набор подписок для одного случайного клиента.

    Алгоритм отбора сервисов:
      - Сервисы из типичных категорий персоны: вес = popularity * 2.0
      - Остальные сервисы: вес = popularity * 0.3
    Выборка без возвращения по этим весам.
    """
    n_subscriptions = int(rng.integers(
        persona.n_subscriptions_range[0],
        persona.n_subscriptions_range[1] + 1,
    ))

    if n_subscriptions == 0:
        return []

    # Вычисляем веса для каждого сервиса из справочника.
    weights = np.array([
        s["popularity"] * (2.0 if s["category"] in persona.typical_subscription_categories else 0.3)
        for s in subscriptions_ref
    ])
    weights = weights / weights.sum()  # нормируем

    n_sample = min(n_subscriptions, len(subscriptions_ref))
    chosen_indices = rng.choice(len(subscriptions_ref), size=n_sample, replace=False, p=weights)

    plans: list[SubscriptionPlan] = []
    for idx in chosen_indices:
        merchant = subscriptions_ref[int(idx)]
        start_date = _random_start_date(rng)
        price_history = _build_price_history(merchant, start_date, rng)
        has_trial = rng.random() < TRIAL_PERIOD_PROBABILITY

        # Небольшая вероятность отписки (~12%) — реализм.
        end_date: datetime | None = None
        if rng.random() < 0.12:
            # Отписка не позже чем за 30 дней до simulation_today.
            max_end = SIMULATION_TODAY - timedelta(days=30)
            min_end = start_date + timedelta(days=merchant["period_days"])
            if min_end < max_end:
                days_range = (max_end - min_end).days
                end_date = min_end + timedelta(days=int(rng.integers(0, days_range + 1)))

        plans.append(SubscriptionPlan(
            client_id=client_id,
            merchant=merchant,
            start_date=start_date,
            end_date=end_date,
            price_history=price_history,
            has_trial=has_trial,
            scenario_tag=None,
        ))

    return plans


# ---------------------------------------------------------------------------
# Разворачивание подписки в транзакции
# ---------------------------------------------------------------------------

def expand_to_transactions(
    plan: SubscriptionPlan,
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    """
    Превращает SubscriptionPlan в список транзакционных строк.

    Схема выходного dict:
      transaction_id, client_id, date, amount, merchant_name, mcc_code, category, description
    """
    period = timedelta(days=plan.merchant["period_days"])
    cutoff = plan.end_date if plan.end_date else SIMULATION_TODAY

    # --- Строим список дат биллинга ---
    billing_schedule: list[tuple[datetime, bool]] = []  # (nominal_date, is_trial)

    if plan.has_trial:
        billing_schedule.append((plan.start_date, True))
        regular_start = plan.start_date + timedelta(days=TRIAL_DURATION_DAYS)
    else:
        regular_start = plan.start_date

    date = regular_start
    while date <= SIMULATION_TODAY:
        billing_schedule.append((date, False))
        date += period

    # --- Генерируем транзакции ---
    transactions: list[dict[str, Any]] = []

    for nominal_date, is_trial in billing_schedule:
        if nominal_date > cutoff:
            break

        # Джиттер даты.
        jitter = int(rng.integers(-PAYMENT_DATE_JITTER_DAYS, PAYMENT_DATE_JITTER_DAYS + 1))
        txn_date = nominal_date + timedelta(days=jitter)

        # Не выходим за SIMULATION_TODAY после джиттера (сравниваем по дате).
        if txn_date.date() > SIMULATION_TODAY.date():
            break

        # Сумма.
        if is_trial:
            amount_rub = TRIAL_AMOUNT_RUB
        else:
            base = _get_price_at(plan.price_history, nominal_date)
            noise = rng.uniform(-AMOUNT_NOISE_FRACTION, AMOUNT_NOISE_FRACTION)
            amount_rub = round(base * (1.0 + noise), 2)

        # Время биллинга: 00:00–05:59 (ночной процессинг банка).
        hour = int(rng.integers(0, 6))
        minute = int(rng.integers(0, 60))
        txn_dt = txn_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

        transactions.append({
            "transaction_id": str(uuid.uuid4()),
            "client_id": plan.client_id,
            "date": txn_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": -amount_rub,          # отрицательное = списание
            "merchant_name": plan.merchant["name"],
            "mcc_code": plan.merchant["mcc_code"],
            "category": plan.merchant["category"],
            "description": f"Подписка {plan.merchant['name']}",
        })

    return transactions
