"""
Core data model for a detected subscription.

This is the contract between the ML pipeline and the API layer.
Any field additions must be discussed with the team first.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass
class Subscription:
    client_id: str
    merchant_name: str
    category: str

    # Payment amounts
    amount: float                       # последняя (текущая) сумма списания
    price_history: list[tuple[date, float]]  # [(date, amount_abs), ...] по дате

    # Periodicity
    period_days: int                    # медианный интервал, округлённый до целых дней
    first_payment_date: date
    last_payment_date: date
    next_payment_date: date             # прогноз: last_payment_date + period_days
    n_payments: int

    # Classification
    status: Literal["active", "price_increased", "possibly_unused", "trial_ending"]
    confidence: Literal["high", "low"]
    reasons: list[str]                  # человекочитаемые причины, на русском
    ml_probability: float               # вероятность P(подписка) от LightGBM
