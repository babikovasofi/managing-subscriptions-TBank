"""
Генератор фоновых (не-подписочных) транзакций клиента.

Публичный API:
  generate_noise_transactions(...) -> list[dict]  (строки transactions.csv)

Алгоритм:
  Для каждого из 12 месяцев истории:
    1. Определяем целевое число шумовых транзакций из persona.monthly_transactions_range.
    2. Распределяем их по мерчантам через multinomial-выборку с весами
       = frequency_per_month × persona_category_weight.
    3. Для каждого мерчанта генерируем N случайных транзакций: дата — равномерно
       по дням периода, сумма — логнормально с центром в середине диапазона.
"""
import math
import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from data.generator.config import HISTORY_MONTHS, SIMULATION_TODAY
from data.generator.personas import Persona


def _lognormal_amount(
    lo: float,
    hi: float,
    rng: np.random.Generator,
) -> float:
    """
    Сумма из логнормального распределения, центрированного в геометрическом
    среднем диапазона [lo, hi]. Мягко ограничиваем результат.
    """
    log_lo = math.log(max(lo, 1.0))
    log_hi = math.log(max(hi, 1.0))
    mu = (log_lo + log_hi) / 2.0
    sigma = (log_hi - log_lo) / 4.0   # ~95% значений попадают в диапазон
    amount = math.exp(rng.normal(mu, sigma))
    # Мягкий клэмп: не уходим дальше ×1.5 от границ.
    return round(max(lo * 0.5, min(hi * 1.5, amount)), 2)


def _iter_months(simulation_today: datetime, n_months: int):
    """
    Генерирует пары (month_start, month_end) за последние n_months месяцев.
    Последний период заканчивается не позже simulation_today.
    """
    # Начинаем с 1-го числа месяца, который был n_months назад.
    y, m = simulation_today.year, simulation_today.month
    for _ in range(n_months):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    current = datetime(y, m, 1)

    for _ in range(n_months):
        if current.month == 12:
            next_month = datetime(current.year + 1, 1, 1)
        else:
            next_month = datetime(current.year, current.month + 1, 1)

        month_end = min(next_month - timedelta(seconds=1), simulation_today)
        yield current, month_end
        current = next_month
        if current > simulation_today:
            break


def generate_noise_transactions(
    client_id: str,
    persona: Persona,
    regular_merchants_ref: list[dict[str, Any]],
    rng: np.random.Generator,
    simulation_today: datetime = SIMULATION_TODAY,
) -> list[dict[str, Any]]:
    """
    Возвращает фоновые транзакции за 12 месяцев для одного клиента.

    Строки соответствуют схеме transactions.csv:
      transaction_id, client_id, date, amount, merchant_name, mcc_code,
      category, description
    """
    # --- Формируем список активных мерчантов и их весов ---
    eligible_merchants: list[dict[str, Any]] = []
    raw_weights: list[float] = []

    for merchant in regular_merchants_ref:
        cat_weight = persona.regular_categories_weights.get(merchant["category"], 0.0)
        if cat_weight <= 0.0:
            continue
        eligible_merchants.append(merchant)
        raw_weights.append(merchant["frequency_per_month"] * cat_weight)

    if not eligible_merchants:
        return []

    weights_arr = np.array(raw_weights)
    weights_norm = weights_arr / weights_arr.sum()

    transactions: list[dict[str, Any]] = []

    for month_start, month_end in _iter_months(simulation_today, HISTORY_MONTHS):
        days_in_period = max((month_end - month_start).days + 1, 1)

        # Целевое число шумовых транзакций в этом месяце.
        target = int(rng.integers(
            persona.monthly_transactions_range[0],
            persona.monthly_transactions_range[1] + 1,
        ))

        # Если период короче месяца (начало истории) — масштабируем.
        target = max(1, round(target * days_in_period / 30))

        # Распределяем транзакции по мерчантам (multinomial).
        counts: np.ndarray = rng.multinomial(target, weights_norm)

        for i, count in enumerate(counts):
            if count == 0:
                continue
            merchant = eligible_merchants[i]
            lo, hi = float(merchant["typical_amount_range"][0]), float(merchant["typical_amount_range"][1])

            for _ in range(int(count)):
                # Случайная дата внутри периода.
                day_offset = int(rng.integers(0, days_in_period))
                txn_date = month_start + timedelta(days=day_offset)
                if txn_date.date() > simulation_today.date():
                    txn_date = simulation_today

                # Дневное время (07:00–22:59) — не-подписочные транзакции.
                hour = int(rng.integers(7, 23))
                minute = int(rng.integers(0, 60))
                txn_dt = txn_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

                amount = _lognormal_amount(lo, hi, rng)

                transactions.append({
                    "transaction_id": str(uuid.uuid4()),
                    "client_id": client_id,
                    "date": txn_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount": -amount,      # отрицательное = списание
                    "merchant_name": merchant["name"],
                    "mcc_code": merchant["mcc_code"],
                    "category": merchant["category"],
                    "description": merchant["name"],
                })

    return transactions
