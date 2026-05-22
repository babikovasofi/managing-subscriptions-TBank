"""
Feature extraction per (client_id, merchant_name) group.

Public API:
  extract_features(txn_df, subscription_names, simulation_today) -> pd.DataFrame

Features per group:
  n_transactions, history_days, median_interval_days, std_interval_days,
  cv_interval, frac_monthly_interval, median_amount_abs, std_amount, cv_amount,
  last_amount, amount_trend, days_since_last, min_amount_abs,
  in_subscription_dict, is_subscription_mcc, category, mcc_code, has_trial_pattern
"""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

# MCC codes associated with subscription services
_SUBSCRIPTION_MCC_CODES: frozenset[str] = frozenset({
    "4816",  # cloud storage / internet services
    "4899",  # streaming video
    "5734",  # computer software stores
    "5812",  # food delivery subscriptions
    "5816",  # digital goods / gaming
    "5942",  # book stores / reading
    "7299",  # miscellaneous subscriptions
    "7372",  # productivity / SaaS
    "8299",  # educational services
})


def _compute_group_features(
    group: pd.DataFrame,
    merchant_name: str,
    subscription_names: set[str],
    simulation_today: datetime,
) -> dict[str, Any]:
    """Compute all features for one (client_id, merchant_name) group."""
    group = group.copy()
    group["_date"] = pd.to_datetime(group["date"])
    group = group.sort_values("_date").reset_index(drop=True)

    amounts: np.ndarray = group["amount"].abs().to_numpy(dtype=float)
    dates_ns: np.ndarray = group["_date"].to_numpy()  # datetime64[ns]

    n = int(len(group))

    # Amount features
    median_amount = float(np.median(amounts))
    std_amount = float(np.std(amounts, ddof=1)) if n > 1 else 0.0
    cv_amount = std_amount / median_amount if median_amount > 0 else 0.0
    min_amount = float(amounts.min())
    last_amount = float(amounts[-1])
    amount_trend = (last_amount / median_amount - 1.0) if median_amount > 0 else 0.0

    # Interval features
    if n >= 2:
        intervals_days = (np.diff(dates_ns) / np.timedelta64(1, "D")).astype(float)
        median_interval = float(np.median(intervals_days))
        std_interval = float(np.std(intervals_days, ddof=1)) if len(intervals_days) > 1 else 0.0
        cv_interval = std_interval / median_interval if median_interval > 0 else 0.0
        frac_monthly = float(np.mean((intervals_days >= 25) & (intervals_days <= 35)))
    else:
        median_interval = 0.0
        std_interval = 0.0
        cv_interval = 0.0
        frac_monthly = 0.0

    # Time features
    first_date = group["_date"].iloc[0]
    last_date = group["_date"].iloc[-1]
    history_days = int((last_date - first_date).days)
    days_since_last = int((pd.Timestamp(simulation_today) - last_date).days)

    # Categorical features (mode)
    mcc_code = str(group["mcc_code"].mode().iloc[0])
    category = str(group["category"].mode().iloc[0])

    return {
        "n_transactions": n,
        "history_days": history_days,
        "median_interval_days": median_interval,
        "std_interval_days": std_interval,
        "cv_interval": cv_interval,
        "frac_monthly_interval": frac_monthly,
        "median_amount_abs": median_amount,
        "std_amount": std_amount,
        "cv_amount": cv_amount,
        "last_amount": last_amount,
        "amount_trend": amount_trend,
        "days_since_last": days_since_last,
        "min_amount_abs": min_amount,
        "in_subscription_dict": merchant_name in subscription_names,
        "is_subscription_mcc": mcc_code in _SUBSCRIPTION_MCC_CODES,
        "category": category,
        "mcc_code": mcc_code,
        "has_trial_pattern": bool(min_amount < 10.0),
    }


def extract_features(
    txn_df: pd.DataFrame,
    subscription_names: set[str],
    simulation_today: datetime,
) -> pd.DataFrame:
    """
    Extract per-(client_id, merchant_name) features from transaction DataFrame.

    Parameters
    ----------
    txn_df : DataFrame with columns [transaction_id, client_id, date, amount,
              merchant_name, mcc_code, category, description]
    subscription_names : set of known subscription merchant names (from subscriptions.json)
    simulation_today : fixed "today" date (from meta.json)

    Returns
    -------
    DataFrame with one row per (client_id, merchant_name) and feature columns.
    """
    records: list[dict[str, Any]] = []

    for (client_id, merchant_name), group in txn_df.groupby(
        ["client_id", "merchant_name"], sort=False
    ):
        feats = _compute_group_features(
            group.reset_index(drop=True),
            str(merchant_name),
            subscription_names,
            simulation_today,
        )
        feats["client_id"] = client_id
        feats["merchant_name"] = merchant_name
        records.append(feats)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    cols = ["client_id", "merchant_name"] + [c for c in df.columns if c not in ("client_id", "merchant_name")]
    return df[cols].reset_index(drop=True)
