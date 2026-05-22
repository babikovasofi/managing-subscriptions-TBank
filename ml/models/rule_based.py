"""
Rule-based candidate selection for subscription detection.

Public API:
  select_candidates(features_df) -> pd.DataFrame

Filters:
  - n_transactions >= 3
  - median_interval_days in [6, 45]
  - cv_interval < 0.5
  - cv_amount < 0.3  (relaxed to < 0.5 when has_trial_pattern)
  - category not in clearly non-subscription set
"""

import pandas as pd

# Categories that are clearly not subscriptions
_NON_SUBSCRIPTION_CATEGORIES: frozenset[str] = frozenset({
    "groceries",
    "cafe",
    "transport",
    "atm",
    "pharmacy",
    "fuel",
    "clothing",
    "marketplace",
})

_MIN_TRANSACTIONS: int = 3
_MIN_INTERVAL_DAYS: float = 6.0
_MAX_INTERVAL_DAYS: float = 45.0
_MAX_CV_INTERVAL: float = 0.5
_MAX_CV_AMOUNT: float = 0.3
_MAX_CV_AMOUNT_TRIAL: float = 0.5  # relaxed when a trial payment (< 10 rub) is present


def select_candidates(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter feature rows to subscription candidates.

    Parameters
    ----------
    features_df : output of extract_features()

    Returns
    -------
    Filtered DataFrame (copy) with only candidate rows, reset index.
    """
    df = features_df

    mask_n = df["n_transactions"] >= _MIN_TRANSACTIONS
    mask_interval = (
        (df["median_interval_days"] >= _MIN_INTERVAL_DAYS)
        & (df["median_interval_days"] <= _MAX_INTERVAL_DAYS)
    )
    mask_cv_interval = df["cv_interval"] < _MAX_CV_INTERVAL
    mask_cv_amount = (df["cv_amount"] < _MAX_CV_AMOUNT) | (
        df["has_trial_pattern"] & (df["cv_amount"] < _MAX_CV_AMOUNT_TRIAL)
    )
    mask_category = ~df["category"].isin(_NON_SUBSCRIPTION_CATEGORIES)

    mask = mask_n & mask_interval & mask_cv_interval & mask_cv_amount & mask_category

    return df[mask].copy().reset_index(drop=True)
