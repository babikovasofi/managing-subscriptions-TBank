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
from pathlib import Path
from typing import Any

import pandas as pd

from data.generator.config import (
    LABELS_OUTPUT_PATH,
    SUBSCRIPTIONS_REF_PATH,
    TRANSACTIONS_OUTPUT_PATH,
    META_OUTPUT_PATH,
)
from ml.models.classifier import load_model
from ml.pipeline.run import run_pipeline_for_client
from ml.pipeline.schema import Subscription
from ml.pipeline.time_utils import get_simulation_today

_MODEL_PATH = Path("ml/models/saved/classifier.pkl")


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
