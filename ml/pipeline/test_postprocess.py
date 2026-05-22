"""
Verification script for the full postprocessing pipeline on scripted clients.

Usage:
    python -m ml.pipeline.test_postprocess
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from data.generator.config import (
    LABELS_OUTPUT_PATH,
    SUBSCRIPTIONS_REF_PATH,
    TRANSACTIONS_OUTPUT_PATH,
    META_OUTPUT_PATH,
)
from ml.features.extract import extract_features
from ml.models.classifier import load_model, predict_subscriptions
from ml.models.dataset import FEATURE_COLUMNS, _CATEGORICAL_FEATURES
from ml.models.rule_based import select_candidates
from ml.pipeline.next_payment import predict_next_payment
from ml.pipeline.schema import Subscription
from ml.pipeline.status import assign_status, detect_pending_trials
from ml.pipeline.time_utils import get_simulation_today

_MODEL_PATH = Path("ml/models/saved/classifier.pkl")


# ── построение Subscription из features + транзакций ─────────────────────────

def _build_subscription(
    feat_row: pd.Series,
    merchant_txns: pd.DataFrame,
    ml_probability: float,
) -> Subscription:
    txns = merchant_txns.copy()
    txns["_date"] = pd.to_datetime(txns["date"])
    txns = txns.sort_values("_date")

    amounts = txns["amount"].abs().tolist()
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


# ── полный пайплайн для одного клиента ───────────────────────────────────────

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
    Full pipeline for one client:
      1. detect_pending_trials (n<3, trial channel)
      2. extract_features → select_candidates → ML classifier → assign_status
    """
    client_txns = txn_df[txn_df["client_id"] == client_id].copy()
    if client_txns.empty:
        return []

    today = simulation_today.date()

    # ── канал 1: пробные периоды (n<3) ──────────────────────────────────────
    pending = detect_pending_trials(
        client_txns, subscription_names, subscription_ref_map, today
    )
    pending_merchants = {s.merchant_name for s in pending}

    # ── канал 2: rule-based + ML ─────────────────────────────────────────────
    features_df = extract_features(client_txns, subscription_names, simulation_today)
    candidates_df = select_candidates(features_df)

    subscriptions: list[Subscription] = list(pending)

    if not candidates_df.empty:
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
                continue  # уже добавлена через pending-канал

            merchant_txns = client_txns[client_txns["merchant_name"] == merchant_name]
            sub = _build_subscription(feat_row, merchant_txns, float(proba))
            status, confidence, reasons = assign_status(sub, client_txns, today)
            sub.status = status
            sub.confidence = confidence
            sub.reasons = reasons
            subscriptions.append(sub)

    return subscriptions


# ── ожидаемые результаты ──────────────────────────────────────────────────────

@dataclass
class ScenarioExpectation:
    client_id: str
    scenario_name: str
    expected_merchant: str
    expected_status: str
    should_be_detected: bool = True


EXPECTATIONS = [
    ScenarioExpectation("scripted_01", "price_increase",      "Кинопоиск HD",         "price_increased"),
    ScenarioExpectation("scripted_02", "trial_ending",        "ivi",                  "trial_ending"),
    ScenarioExpectation("scripted_03", "abandoned_gaming",    "VK Play Cloud",        "possibly_unused"),
    ScenarioExpectation("scripted_04", "heavy_user",          "Skillbox",             "active"),
    ScenarioExpectation("scripted_05", "newbie",              "Яндекс.Плюс",          "active"),
    ScenarioExpectation("scripted_06", "overlapping_dates",   "Кинопоиск HD",         "active"),
    ScenarioExpectation("scripted_07", "former_user",         "Кинопоиск HD",         "active"),
    ScenarioExpectation("scripted_08", "duplicate_services",  "Яндекс.Музыка",        "active"),
    ScenarioExpectation("scripted_09", "false_positive_trap", "World Class",          "active",
                        should_be_detected=False),
    ScenarioExpectation("scripted_10", "family_plan",         "Яндекс.Плюс Семейный", "active"),
]


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading data and model...")
    txn_df = pd.read_csv(TRANSACTIONS_OUTPUT_PATH)

    with open(SUBSCRIPTIONS_REF_PATH, encoding="utf-8") as f:
        subs_ref: list[dict[str, Any]] = json.load(f)
    with open("ml/models/saved/metrics.json", encoding="utf-8") as f:
        saved_metrics = json.load(f)

    subscription_names: set[str] = {s["name"] for s in subs_ref}
    subscription_ref_map: dict[str, dict[str, Any]] = {s["name"]: s for s in subs_ref}
    simulation_today = get_simulation_today()
    threshold = float(saved_metrics.get("best_threshold", 0.30))

    model = load_model(_MODEL_PATH)

    # ── run pipeline ──────────────────────────────────────────────────────────
    results: dict[str, list[Subscription]] = {}
    for exp in EXPECTATIONS:
        subs = run_pipeline_for_client(
            exp.client_id, txn_df, subscription_names,
            subscription_ref_map, simulation_today, model, threshold,
        )
        results[exp.client_id] = subs

        print(f"\n[{exp.client_id}] scenario={exp.scenario_name}")
        if not subs:
            print("  (нет обнаруженных подписок)")
        for s in subs:
            print(f"  {s.merchant_name:<32} status={s.status:<18} conf={s.confidence}  p={s.ml_probability:.3f}")
            for r in s.reasons:
                print(f"    - {r}")

    # ── verification table ────────────────────────────────────────────────────
    print("\n" + "=" * 84)
    print(f"{'Сценарий':<22} {'Мерчант':<28} {'Ожидание':<18} {'Факт':<18} {'Итог'}")
    print("-" * 84)

    passes = 0
    fails = 0

    for exp in EXPECTATIONS:
        subs = results[exp.client_id]
        detected_map = {s.merchant_name: s for s in subs}

        if not exp.should_be_detected:
            if exp.expected_merchant not in detected_map:
                verdict, actual, expected_str = "OK", "не обнаружен", "не обнаружен"
                passes += 1
            else:
                s = detected_map[exp.expected_merchant]
                verdict, actual, expected_str = "FAIL", f"обнаружен ({s.status})", "не обнаружен"
                fails += 1
        else:
            if exp.expected_merchant in detected_map:
                actual_status = detected_map[exp.expected_merchant].status
                verdict = "OK" if actual_status == exp.expected_status else "FAIL"
                actual, expected_str = actual_status, exp.expected_status
                passes += (1 if verdict == "OK" else 0)
                fails += (1 if verdict == "FAIL" else 0)
            else:
                verdict, actual, expected_str = "FAIL", "не обнаружен", exp.expected_status
                fails += 1

        print(
            f"{exp.scenario_name:<22} {exp.expected_merchant:<28} "
            f"{expected_str:<18} {actual:<18} {verdict}"
        )

    print("-" * 84)
    print(f"Итого: {passes} OK, {fails} FAIL")


if __name__ == "__main__":
    main()
