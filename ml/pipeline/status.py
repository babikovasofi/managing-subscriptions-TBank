"""
Subscription status detection and assignment.

Public API:
  detect_trial_ending(price_history, next_payment_date, today) -> (bool, confidence, reasons)
  detect_price_increase(price_history)                         -> (bool, confidence, reasons)
  detect_possibly_unused(subscription, all_client_txns, today) -> (bool, confidence, reasons)
  detect_active(subscription)                                  -> (bool, confidence, reasons)
  assign_status(subscription, all_client_txns, today)          -> (status, confidence, reasons)
  detect_pending_trials(client_txns, subscription_names,
                        subscription_ref_map, today)           -> list[Subscription]

Priority for assign_status: trial_ending > price_increased > possibly_unused > active
"""

import statistics
from datetime import date, timedelta
from typing import Any, Literal

import pandas as pd

from ml.features.extract import _SUBSCRIPTION_MCC_CODES
from ml.pipeline.next_payment import predict_next_payment
from ml.pipeline.schema import Subscription

# ── thresholds ────────────────────────────────────────────────────────────────

_TRIAL_MAX_AMOUNT: float = 10.0           # символический платёж < 10 ₽
_TRIAL_FULL_MIN_AMOUNT: float = 50.0      # полное списание должно быть ≥ 50 ₽
_TRIAL_WINDOW_DAYS: int = 7               # «скоро» = в ближайшие 7 дней
_TRIAL_RECENCY_DAYS: int = 60             # trial-транзакция не старше 60 дней

_PRICE_INCREASE_PCT: float = 0.15         # ≥ 15 % роста
_PRICE_INCREASE_RUB: float = 50.0         # или ≥ 50 ₽ для подписок < 500 ₽
_PRICE_INCREASE_CHEAP_THRESHOLD: float = 500.0
_PRICE_INCREASE_CLUSTER_SIZE: int = 3     # размер кластера «ранние/поздние» платежи
_PRICE_INCREASE_MIN_PAYMENTS: int = 6     # порог переключения алгоритмов

_UNUSED_GAMING_MONTHS: int = 3            # gaming: ≥ 3 мес без игровых трат


# ── детекторы ─────────────────────────────────────────────────────────────────

def detect_trial_ending(
    price_history: list[tuple[date, float]],
    next_payment_date: date,
    today: date,
) -> tuple[bool, Literal["high", "low"], list[str]]:
    """
    Статус trial_ending: последний платёж был символическим (< 10 ₽),
    а первое полное списание ожидается в течение 7 дней.
    Используется только для subscriptions с n≥3 (нормальный пайплайн).
    Для n<3 — см. detect_pending_trials.
    """
    if not price_history:
        return False, "high", []

    last_amount = price_history[-1][1]
    if last_amount >= _TRIAL_MAX_AMOUNT:
        return False, "high", []

    full_amounts = [amt for _, amt in price_history if amt >= _TRIAL_MAX_AMOUNT]
    if not full_amounts:
        return False, "high", []

    expected_amount = statistics.median(full_amounts)
    if expected_amount < _TRIAL_FULL_MIN_AMOUNT:
        return False, "high", []

    days_to_charge = (next_payment_date - today).days
    if not (0 <= days_to_charge <= _TRIAL_WINDOW_DAYS):
        return False, "high", []

    reasons = [
        f"Обнаружен пробный период: последнее списание составило {last_amount:.0f} ₽",
        f"Первое полное списание {expected_amount:.0f} ₽ ожидается через {days_to_charge} дн.",
    ]
    return True, "high", reasons


def detect_price_increase(
    price_history: list[tuple[date, float]],
) -> tuple[bool, Literal["high", "low"], list[str]]:
    """
    Статус price_increased.

    Алгоритм (n ≥ 6):
      Сравниваем медиану ПОСЛЕДНИХ 3 платежей с медианой ПЕРВЫХ 3.
      Точнее улавливает постепенный переход на новую цену, чем "последний vs все".

    Fallback (n < 6):
      Последний платёж vs медиана предыдущих.

    Пороги: ≥ 15 % относительный рост ИЛИ ≥ 50 ₽ абсолютный рост (если < 500 ₽).
    """
    if len(price_history) < 2:
        return False, "high", []

    amounts = [amt for _, amt in price_history]

    if len(amounts) >= _PRICE_INCREASE_MIN_PAYMENTS:
        median_old = statistics.median(amounts[:_PRICE_INCREASE_CLUSTER_SIZE])
        median_new = statistics.median(amounts[-_PRICE_INCREASE_CLUSTER_SIZE:])
    else:
        median_old = statistics.median(amounts[:-1])
        median_new = amounts[-1]

    if median_old <= 0:
        return False, "high", []

    pct = median_new / median_old - 1.0
    diff = median_new - median_old

    is_pct = pct >= _PRICE_INCREASE_PCT
    is_rub = (median_old < _PRICE_INCREASE_CHEAP_THRESHOLD) and (diff >= _PRICE_INCREASE_RUB)

    if not (is_pct or is_rub):
        return False, "high", []

    reasons = [
        f"Цена выросла с {median_old:.0f} ₽ до {median_new:.0f} ₽ "
        f"(+{diff:.0f} ₽, +{pct * 100:.0f}%)",
    ]
    return True, "high", reasons


def detect_possibly_unused(
    subscription: Subscription,
    all_client_txns: pd.DataFrame,
    today: date,
) -> tuple[bool, Literal["high", "low"], list[str]]:
    """
    Статус possibly_unused — только для gaming (высокая уверенность).

    Условие: подписка gaming ≥ 3 мес И за последние 3 месяца у клиента
    нет других non-subscription транзакций в категории gaming.

    Для всех остальных категорий статус не выставляется: без надёжного
    активностного сигнала не делаем рекомендацию.
    """
    if subscription.category != "gaming":
        return False, "high", []

    age_days = (today - subscription.first_payment_date).days
    if age_days < _UNUSED_GAMING_MONTHS * 30:
        return False, "high", []

    cutoff = today - timedelta(days=_UNUSED_GAMING_MONTHS * 30)
    related = all_client_txns[
        (all_client_txns["category"] == "gaming")
        & (all_client_txns["merchant_name"] != subscription.merchant_name)
        & (pd.to_datetime(all_client_txns["date"]).dt.date >= cutoff)
    ]
    if not related.empty:
        return False, "high", []

    months = age_days // 30
    reasons = [
        f"За последние {_UNUSED_GAMING_MONTHS} месяца не было покупок "
        f"в категории «игры» — возможно, вы не пользуетесь подпиской.",
        f"Подписка активна {months} мес.",
    ]
    return True, "high", reasons


def detect_active(
    subscription: Subscription,
) -> tuple[bool, Literal["high", "low"], list[str]]:
    """Дефолтный статус active — всегда совпадает."""
    reasons = [
        f"Регулярные списания {subscription.n_payments} раз "
        f"с интервалом {subscription.period_days} дн.",
        "Сумма списаний стабильна.",
    ]
    return True, "high", reasons


# ── сборка статуса ────────────────────────────────────────────────────────────

def assign_status(
    subscription: Subscription,
    all_client_txns: pd.DataFrame,
    today: date,
) -> tuple[
    Literal["active", "price_increased", "possibly_unused", "trial_ending"],
    Literal["high", "low"],
    list[str],
]:
    """
    Применяет детекторы в порядке приоритета:
      trial_ending > price_increased > possibly_unused > active
    """
    common: list[str] = []
    if subscription.ml_probability >= 0.8:
        common.append("Мерчант распознан как подписочный сервис.")

    matched, conf, reasons = detect_trial_ending(
        subscription.price_history, subscription.next_payment_date, today
    )
    if matched:
        return "trial_ending", conf, reasons + common

    matched, conf, reasons = detect_price_increase(subscription.price_history)
    if matched:
        return "price_increased", conf, reasons + common

    matched, conf, reasons = detect_possibly_unused(subscription, all_client_txns, today)
    if matched:
        return "possibly_unused", conf, reasons + common

    _, conf, reasons = detect_active(subscription)
    return "active", conf, reasons + common


# ── отдельный канал: подписки на испытательном периоде (n < 3) ────────────────

def detect_pending_trials(
    client_txns: pd.DataFrame,
    subscription_names: set[str],
    subscription_ref_map: dict[str, dict[str, Any]],
    today: date,
) -> list[Subscription]:
    """
    Обнаруживает подписки в пробном периоде до того, как накопилось ≥ 3 платежей.

    Для каждой пары (client_id, merchant_name) с n ≤ 2 транзакциями:
      - Последний платёж < 10 ₽ (пробный)
      - Мерчант подписочный (в словаре ИЛИ MCC совпадает)
      - Транзакция не старше 60 дней
      - Прогноз первого полного списания попадает в [today, today+7]
    → возвращает Subscription со статусом trial_ending, confidence=high.

    Вызывается ДО rule-based + ML, результаты добавляются напрямую.
    """
    results: list[Subscription] = []

    for (client_id, merchant_name), group in client_txns.groupby(
        ["client_id", "merchant_name"], sort=False
    ):
        if len(group) > 2:
            continue  # нормальный пайплайн справится

        grp = group.copy()
        grp["_date"] = pd.to_datetime(grp["date"])
        grp = grp.sort_values("_date").reset_index(drop=True)

        last_amount = float(grp["amount"].abs().iloc[-1])
        if last_amount >= _TRIAL_MAX_AMOUNT:
            continue

        mcc_code = str(grp["mcc_code"].mode().iloc[0])
        is_sub = str(merchant_name) in subscription_names or mcc_code in _SUBSCRIPTION_MCC_CODES
        if not is_sub:
            continue

        last_date: date = grp["_date"].iloc[-1].date()
        if (today - last_date).days >= _TRIAL_RECENCY_DAYS:
            continue

        ref = subscription_ref_map.get(str(merchant_name))
        period_days = int(ref["period_days"]) if ref else 30
        next_payment = predict_next_payment(last_date, period_days)

        days_to_charge = (next_payment - today).days
        if not (0 <= days_to_charge <= _TRIAL_WINDOW_DAYS):
            continue

        if ref is None:
            continue  # без ожидаемой суммы не создаём карточку
        expected_amount = float(ref["base_price_rub"])
        if expected_amount < _TRIAL_FULL_MIN_AMOUNT:
            continue

        amounts = grp["amount"].abs().tolist()
        dates_list: list[date] = [d.date() for d in grp["_date"]]
        price_history: list[tuple[date, float]] = list(zip(dates_list, amounts))
        category = str(grp["category"].mode().iloc[0])

        reasons = [
            f"Обнаружен пробный период: последнее списание составило {last_amount:.0f} ₽",
            f"Первое полное списание {expected_amount:.0f} ₽ ожидается через {days_to_charge} дн.",
        ]

        results.append(Subscription(
            client_id=str(client_id),
            merchant_name=str(merchant_name),
            category=category,
            amount=expected_amount,
            price_history=price_history,
            period_days=period_days,
            first_payment_date=dates_list[0],
            last_payment_date=last_date,
            next_payment_date=next_payment,
            n_payments=len(grp),
            status="trial_ending",
            confidence="high",
            reasons=reasons,
            ml_probability=1.0,  # rule-based channel, no ML score
        ))

    return results
