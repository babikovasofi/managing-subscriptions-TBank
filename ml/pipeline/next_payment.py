"""
Next payment date prediction.

Public API:
  predict_next_payment(last_payment_date, period_days) -> date
"""

from datetime import date, timedelta


def predict_next_payment(last_payment_date: date, period_days: int) -> date:
    """
    Predict the next subscription payment date.

    For MVP: last_payment_date + period_days.
    period_days is the median observed interval rounded to the nearest integer.

    Parameters
    ----------
    last_payment_date : date of the most recent recorded payment
    period_days : median interval between payments (integer days)

    Returns
    -------
    Predicted date of the next charge.
    """
    return last_payment_date + timedelta(days=max(1, period_days))
