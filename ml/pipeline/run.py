"""
Full subscription detection pipeline: transactions.csv → dict[client_id, list[Subscription]].

Public API:
  run_pipeline(transactions_path, ...) -> dict[str, list[Subscription]]
  run_pipeline_for_client(client_id, txn_df, ...) -> list[Subscription]

CLI:
  python -m ml.pipeline.run [--transactions PATH]
"""

import argparse
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from data.generator.config import META_OUTPUT_PATH, SUBSCRIPTIONS_REF_PATH
from ml.features.extract import extract_features
from ml.models.classifier import load_model, predict_subscriptions
from ml.models.dataset import FEATURE_COLUMNS, _CATEGORICAL_FEATURES
from ml.models.rule_based import select_candidates
from ml.pipeline.next_payment import predict_next_payment
from ml.pipeline.schema import Subscription
from ml.pipeline.status import assign_status, detect_pending_trials
from ml.pipeline.time_utils import get_simulation_today

_MODEL_PATH = Path("ml/models/saved/classifier.pkl")
_METRICS_PATH = Path("ml/models/saved/metrics.json")


def _build_subscription(
    feat_row: pd.Series,
    merchant_txns: pd.DataFrame,
    ml_probability: float,
) -> Subscription:
    """Construct a Subscription dataclass from a feature row and raw transactions."""
    txns = merchant_txns.copy()
    txns["_date"] = pd.to_datetime(txns["date"])
    txns = txns.sort_values("_date")

    amounts: list[float] = txns["amount"].abs().tolist()
    dates: list[date] = [d.date() for d in txns["_date"]]
    price_history: list[tuple[date, float]] = list(zip(dates, amounts))

    last_date = dates[-1]
    period_days = max(1, round(float(feat_row["median_interval_days"])))
    next_date = predict_next_payment(last_date, period_days)

    return Subscription(
        client_id=str(feat_row["client_id"]),
        merchant_name=str(feat_row["merchant_name"]),
        category=str(feat_row["category"]),
        amount=float(feat_row["last_amount"]),
        price_history=price_history,
        period_days=period_days,
        first_payment_date=dates[0],
        last_payment_date=last_date,
        next_payment_date=next_date,
        n_payments=int(feat_row["n_transactions"]),
        status="active",
        confidence="high",
        reasons=[],
        ml_probability=ml_probability,
    )


def run_pipeline_for_client(
    client_id: str,
    txn_df: pd.DataFrame,
    subscription_names: set[str],
    subscription_ref_map: dict[str, dict[str, Any]],
    simulation_today: datetime,
    model: Any,
    threshold: float = 0.30,
) -> list[Subscription]:
    """
    Detect subscriptions for one client.

    Two detection channels run in sequence:
      1. detect_pending_trials — catches trial-period merchants with n<3 transactions
         before rule-based would filter them out.
      2. extract_features → select_candidates → ML classifier → assign_status —
         the main pipeline for merchants with n≥3 transactions.

    Parameters
    ----------
    client_id : target client identifier
    txn_df : full transactions DataFrame (all clients); filtered internally
    subscription_names : set of known subscription merchant names
    subscription_ref_map : name → reference dict from subscriptions.json
    simulation_today : fixed "today" date (from meta.json via get_simulation_today)
    model : fitted LGBMClassifier
    threshold : ML decision boundary (loaded from metrics.json best_threshold)

    Returns
    -------
    List of detected Subscription objects with status, confidence, and reasons set.
    """
    client_txns = txn_df[txn_df["client_id"] == client_id].copy()
    if client_txns.empty:
        return []

    today = simulation_today.date()

    # Channel 1: trial-period merchants (n < 3) — must run before feature extraction
    pending = detect_pending_trials(
        client_txns, subscription_names, subscription_ref_map, today
    )
    pending_merchants = {s.merchant_name for s in pending}

    # Channel 2: rule-based + ML for remaining merchants
    features_df = extract_features(client_txns, subscription_names, simulation_today)
    candidates_df = select_candidates(features_df)

    subscriptions: list[Subscription] = list(pending)

    if candidates_df.empty:
        return subscriptions

    X = candidates_df[FEATURE_COLUMNS].copy()
    for col in ["in_subscription_dict", "is_subscription_mcc", "has_trial_pattern"]:
        X[col] = X[col].astype(int)
    for col in _CATEGORICAL_FEATURES:
        X[col] = pd.Categorical(X[col])

    preds, probas = predict_subscriptions(model, X, threshold=threshold)

    for i, (pred, proba) in enumerate(zip(preds, probas)):
        if pred == 0:
            continue
        feat_row = candidates_df.iloc[i]
        merchant_name = str(feat_row["merchant_name"])

        if merchant_name in pending_merchants:
            continue  # already captured via trial channel

        merchant_txns = client_txns[client_txns["merchant_name"] == merchant_name]
        sub = _build_subscription(feat_row, merchant_txns, float(proba))
        status, confidence, reasons = assign_status(sub, client_txns, today)
        sub.status = status
        sub.confidence = confidence
        sub.reasons = reasons
        subscriptions.append(sub)

    return subscriptions


def run_pipeline(
    transactions_path: Path | str,
    model_path: Path | str = _MODEL_PATH,
    metrics_path: Path | str = _METRICS_PATH,
    subscriptions_ref_path: Path | str = SUBSCRIPTIONS_REF_PATH,
    meta_path: Path | str = META_OUTPUT_PATH,
) -> dict[str, list[Subscription]]:
    """
    Run the full detection pipeline on every client in transactions_path.

    Parameters
    ----------
    transactions_path : path to transactions.csv
    model_path : path to classifier.pkl
    metrics_path : path to metrics.json (supplies best_threshold)
    subscriptions_ref_path : path to subscriptions.json
    meta_path : path to meta.json (supplies simulation_today)

    Returns
    -------
    dict mapping client_id → list[Subscription] (empty list = no subscriptions found)
    """
    txn_df = pd.read_csv(transactions_path)

    with open(subscriptions_ref_path, encoding="utf-8") as f:
        subs_ref: list[dict[str, Any]] = json.load(f)
    with open(metrics_path, encoding="utf-8") as f:
        saved_metrics: dict[str, Any] = json.load(f)

    subscription_names: set[str] = {s["name"] for s in subs_ref}
    subscription_ref_map: dict[str, dict[str, Any]] = {s["name"]: s for s in subs_ref}

    simulation_today = get_simulation_today()
    threshold = float(saved_metrics.get("best_threshold", 0.30))
    model = load_model(model_path)

    client_ids: list[str] = txn_df["client_id"].unique().tolist()
    results: dict[str, list[Subscription]] = {}

    for client_id in client_ids:
        results[client_id] = run_pipeline_for_client(
            client_id,
            txn_df,
            subscription_names,
            subscription_ref_map,
            simulation_today,
            model,
            threshold,
        )

    return results


def _print_summary(results: dict[str, list[Subscription]]) -> None:
    total_clients = len(results)
    clients_with_subs = sum(1 for subs in results.values() if subs)
    total_subs = sum(len(subs) for subs in results.values())

    status_counts: Counter[str] = Counter()
    for subs in results.values():
        for s in subs:
            status_counts[s.status] += 1

    print(f"\n=== Pipeline summary ===")
    print(f"  Clients processed:          {total_clients}")
    print(f"  Clients with subscriptions: {clients_with_subs}")
    print(f"  Total subscriptions found:  {total_subs}")
    print(f"  Average per active client:  {total_subs / max(clients_with_subs, 1):.1f}")
    print("\n  Status breakdown:")
    for status in ("active", "price_increased", "possibly_unused", "trial_ending"):
        print(f"    {status:<22} {status_counts[status]:>4}")
    print(f"    {'TOTAL':<22} {total_subs:>4}")


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Run subscription detection pipeline on transactions.csv."
    )
    parser.add_argument(
        "--transactions",
        type=Path,
        default=Path("data/output/transactions.csv"),
        help="Path to transactions.csv (default: data/output/transactions.csv)",
    )
    args = parser.parse_args()

    print(f"Transactions: {args.transactions}")
    results = run_pipeline(args.transactions)
    _print_summary(results)


if __name__ == "__main__":
    main()
