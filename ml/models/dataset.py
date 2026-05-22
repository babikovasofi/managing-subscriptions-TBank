"""
Training dataset preparation for the subscription classifier.

Public API:
  build_training_dataset(transactions_df, labels_df, ...) -> (X, y, groups)
  FEATURE_COLUMNS  — ordered list of feature column names used by the model
"""

import json
from datetime import datetime
from typing import Any

import pandas as pd

from data.generator.config import META_OUTPUT_PATH, SUBSCRIPTIONS_REF_PATH
from ml.features.extract import extract_features
from ml.models.rule_based import select_candidates

# Numeric features computed per (client_id, merchant_name) group
_NUMERIC_FEATURES: list[str] = [
    "n_transactions",
    "history_days",
    "median_interval_days",
    "std_interval_days",
    "cv_interval",
    "frac_monthly_interval",
    "median_amount_abs",
    "std_amount",
    "cv_amount",
    "last_amount",
    "amount_trend",
    "days_since_last",
    "min_amount_abs",
]

# Boolean flags (stored as 0/1 int)
_BOOL_FEATURES: list[str] = [
    "in_subscription_dict",
    "is_subscription_mcc",
    "has_trial_pattern",
]

# Categorical features — encoded as pandas.Categorical for LightGBM
_CATEGORICAL_FEATURES: list[str] = ["category", "mcc_code"]

FEATURE_COLUMNS: list[str] = _NUMERIC_FEATURES + _BOOL_FEATURES + _CATEGORICAL_FEATURES


def build_training_dataset(
    transactions_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    subscription_names: set[str] | None = None,
    simulation_today: datetime | None = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Build feature matrix X, target y, and client groups for GroupKFold.

    Steps
    -----
    1. Extract features per (client_id, merchant_name).
    2. Apply rule-based candidate filter — ML learns within the candidate pool,
       not against random noise.
    3. Left-join with labels to obtain y = is_subscription (0/1).
       Pairs absent from labels are treated as negatives.
    4. Encode bool features as int, categorical features as pandas.Categorical.

    Parameters
    ----------
    transactions_df : raw transaction DataFrame
    labels_df : ground truth with columns [client_id, merchant_name, is_subscription]
    subscription_names : known subscription merchant names; loaded from
                         SUBSCRIPTIONS_REF_PATH if None
    simulation_today : fixed "today" date; loaded from META_OUTPUT_PATH if None

    Returns
    -------
    X : DataFrame with FEATURE_COLUMNS columns
    y : Series (int, 0/1), name="label"
    groups : Series of client_id strings, name="client_id"
    """
    if subscription_names is None:
        with open(SUBSCRIPTIONS_REF_PATH, encoding="utf-8") as f:
            subs_ref: list[dict[str, Any]] = json.load(f)
        subscription_names = {s["name"] for s in subs_ref}

    if simulation_today is None:
        with open(META_OUTPUT_PATH, encoding="utf-8") as f:
            meta: dict[str, Any] = json.load(f)
        simulation_today = datetime.strptime(meta["simulation_today"], "%Y-%m-%d")

    features_df = extract_features(transactions_df, subscription_names, simulation_today)
    candidates_df = select_candidates(features_df)

    label_cols = (
        labels_df[["client_id", "merchant_name", "is_subscription"]]
        .copy()
        .assign(is_subscription=lambda df: df["is_subscription"].astype(bool))
    )

    merged = candidates_df.merge(
        label_cols, on=["client_id", "merchant_name"], how="left"
    )
    # Candidates absent from labels are non-subscriptions
    merged["is_subscription"] = merged["is_subscription"].fillna(False)

    y: pd.Series = merged["is_subscription"].astype(int).rename("label")

    X = merged[FEATURE_COLUMNS].copy()
    for col in _BOOL_FEATURES:
        X[col] = X[col].astype(int)
    for col in _CATEGORICAL_FEATURES:
        X[col] = pd.Categorical(X[col])

    groups: pd.Series = merged["client_id"].rename("client_id")

    return X, y, groups
