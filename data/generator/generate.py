"""
Главный скрипт генерации синтетического датасета.

Запуск:
    python -m data.generator.generate

Выходные файлы (data/output/):
    transactions.csv  — все транзакции (~110 000 строк)
    labels.csv        — ground truth (is_subscription, scenario_tag, ...)
    meta.json         — параметры генерации
"""

import json
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from data.generator.config import (
    CLIENT_ID_RANDOM_PREFIX,
    CLIENT_ID_SCRIPTED_PREFIX,
    GENERATOR_VERSION,
    HISTORY_MONTHS,
    LABELS_OUTPUT_PATH,
    META_OUTPUT_PATH,
    N_CLIENTS_RANDOM,
    N_CLIENTS_SCRIPTED,
    OUTPUT_DIR,
    RANDOM_SEED,
    REGULAR_MERCHANTS_REF_PATH,
    SIMULATION_TODAY,
    SUBSCRIPTIONS_REF_PATH,
    TRANSACTIONS_OUTPUT_PATH,
)
from data.generator.noise_generator import generate_noise_transactions
from data.generator.personas import PERSONAS, Persona
from data.generator.scripted_clients import SCRIPTED_SCENARIOS, ScriptedClientResult
from data.generator.subscription_generator import SubscriptionPlan, expand_to_transactions


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _plans_to_label_rows(plans: list[SubscriptionPlan]) -> list[dict[str, Any]]:
    """Строки labels.csv для списка SubscriptionPlan."""
    rows = []
    for plan in plans:
        true_amount = plan.price_history[-1][1]   # последняя (текущая) цена
        rows.append({
            "client_id": plan.client_id,
            "merchant_name": plan.merchant["name"],
            "is_subscription": True,
            "true_period_days": plan.merchant["period_days"],
            "true_amount": true_amount,
            "scenario_tag": plan.scenario_tag or "regular",
        })
    return rows


def _generate_random_client(
    client_id: str,
    persona: Persona,
    subs_ref: list[dict[str, Any]],
    reg_ref: list[dict[str, Any]],
    rng: np.random.Generator,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Возвращает (транзакции, метки) для одного случайного клиента."""
    from data.generator.subscription_generator import generate_subscriptions_for_client

    plans = generate_subscriptions_for_client(client_id, persona, subs_ref, rng)

    txns: list[dict[str, Any]] = []
    for plan in plans:
        txns.extend(expand_to_transactions(plan, rng))

    txns.extend(generate_noise_transactions(client_id, persona, reg_ref, rng))

    labels = _plans_to_label_rows(plans)
    return txns, labels


def _generate_scripted_client(
    result: ScriptedClientResult,
    reg_ref: list[dict[str, Any]],
    rng: np.random.Generator,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Возвращает (транзакции, метки) для режиссированного клиента.
    Уважает pre_expanded и custom_noise_transactions.
    """
    txns: list[dict[str, Any]] = []

    # Подписочные транзакции.
    for plan in result.subscription_plans:
        if plan.merchant["name"] in result.pre_expanded:
            txns.extend(result.pre_expanded[plan.merchant["name"]])
        else:
            txns.extend(expand_to_transactions(plan, rng))

    # Шумовой фон.
    if result.custom_noise_transactions is not None:
        txns.extend(result.custom_noise_transactions)
    else:
        txns.extend(generate_noise_transactions(
            result.client_id, result.persona, reg_ref, rng
        ))

    # Дополнительные транзакции (абонемент в зал и т.п.).
    txns.extend(result.extra_transactions)

    # Метки.
    labels = _plans_to_label_rows(result.subscription_plans)
    labels.extend(result.extra_label_rows)

    return txns, labels


# ---------------------------------------------------------------------------
# Sanity-checks
# ---------------------------------------------------------------------------

def run_sanity_checks(
    txn_df: pd.DataFrame,
    labels_df: pd.DataFrame,
    meta: dict[str, Any],
) -> list[str]:
    """
    Проверяет корректность сгенерированного датасета.
    Возвращает список строк с описанием ошибок (пустой = всё ОК).
    """
    errors: list[str] = []

    txn_clients = set(txn_df["client_id"].unique())
    label_clients = set(labels_df["client_id"].unique())

    # 1. Все client_id из labels есть в транзакциях.
    missing_in_txns = label_clients - txn_clients
    if missing_in_txns:
        errors.append(f"Клиенты в labels но не в transactions: {missing_in_txns}")

    # 2. Нет транзакций позже simulation_today.
    dates = pd.to_datetime(txn_df["date"])
    future_count = int((dates.dt.date > SIMULATION_TODAY.date()).sum())
    if future_count:
        errors.append(f"{future_count} транзакций позже SIMULATION_TODAY")

    # 3. Нет дублей transaction_id.
    dupe_count = int(txn_df["transaction_id"].duplicated().sum())
    if dupe_count:
        errors.append(f"{dupe_count} дублированных transaction_id")

    # 4. Все 10 режиссированных клиентов присутствуют.
    expected_scripted = {
        f"{CLIENT_ID_SCRIPTED_PREFIX}_{i:02d}" for i in range(1, N_CLIENTS_SCRIPTED + 1)
    }
    missing_scripted = expected_scripted - txn_clients
    if missing_scripted:
        errors.append(f"Отсутствующие режиссированные клиенты: {missing_scripted}")

    # 5. У каждого клиента ≥ 1 транзакция.
    client_counts = txn_df.groupby("client_id").size()
    zero_clients = client_counts[client_counts == 0]
    if len(zero_clients):
        errors.append(f"{len(zero_clients)} клиентов без транзакций")

    # 6. Разумное распределение числа транзакций.
    min_txn = int(client_counts.min())
    max_txn = int(client_counts.max())
    if min_txn < 5:
        errors.append(f"Клиент с подозрительно малым числом транзакций: {min_txn}")
    if max_txn > 20_000:
        errors.append(f"Клиент с подозрительно большим числом транзакций: {max_txn}")

    # 7. Все суммы отрицательные (только списания, поступлений нет).
    positive_count = int((txn_df["amount"] > 0).sum())
    if positive_count:
        errors.append(f"{positive_count} транзакций с положительной суммой")

    # 8. Для каждой is_subscription=True-метки есть транзакции того же мерчанта.
    sub_labels = labels_df[labels_df["is_subscription"] == True]
    txn_pairs = set(zip(txn_df["client_id"], txn_df["merchant_name"]))
    missing_merchants = [
        (row["client_id"], row["merchant_name"])
        for _, row in sub_labels.iterrows()
        if (row["client_id"], row["merchant_name"]) not in txn_pairs
    ]
    if missing_merchants:
        errors.append(
            f"{len(missing_merchants)} меток подписки без транзакций: "
            f"{missing_merchants[:3]}{'...' if len(missing_merchants) > 3 else ''}"
        )

    return errors


def _print_report(
    txn_df: pd.DataFrame,
    labels_df: pd.DataFrame,
) -> None:
    client_counts = txn_df.groupby("client_id").size()
    sub_labels = labels_df[labels_df["is_subscription"] == True]

    print("\n=== Итоговая статистика датасета ===")
    print(f"  Транзакций всего:           {len(txn_df):>8,}")
    print(f"  Клиентов:                   {txn_df['client_id'].nunique():>8}")
    print(f"  Транзакций на клиента:      "
          f"min={client_counts.min()}, "
          f"median={int(client_counts.median())}, "
          f"max={client_counts.max()}")
    print(f"  Меток подписок (is_sub=True): {len(sub_labels):>6}")
    print(f"  Уникальных подписочных мерчантов: {sub_labels['merchant_name'].nunique():>4}")
    print(f"  Scenario tags: {dict(labels_df['scenario_tag'].value_counts())}")


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"[generate.py] SIMULATION_TODAY={SIMULATION_TODAY.date()}  seed={RANDOM_SEED}")

    # --- Загрузка справочников ---
    with open(SUBSCRIPTIONS_REF_PATH, encoding="utf-8") as f:
        subs_ref: list[dict[str, Any]] = json.load(f)
    with open(REGULAR_MERCHANTS_REF_PATH, encoding="utf-8") as f:
        reg_ref: list[dict[str, Any]] = json.load(f)

    rng = np.random.default_rng(RANDOM_SEED)

    all_transactions: list[dict[str, Any]] = []
    all_labels: list[dict[str, Any]] = []

    # --- 140 случайных клиентов ---
    print(f"Генерация {N_CLIENTS_RANDOM} случайных клиентов...")
    persona_indices = rng.integers(0, len(PERSONAS), size=N_CLIENTS_RANDOM)
    for i in range(N_CLIENTS_RANDOM):
        cid = f"{CLIENT_ID_RANDOM_PREFIX}_{i + 1:04d}"
        persona = PERSONAS[int(persona_indices[i])]
        txns, labels = _generate_random_client(cid, persona, subs_ref, reg_ref, rng)
        all_transactions.extend(txns)
        all_labels.extend(labels)
        if (i + 1) % 28 == 0:
            print(f"  {i + 1}/{N_CLIENTS_RANDOM}...")

    # --- 10 режиссированных клиентов ---
    print(f"Генерация {N_CLIENTS_SCRIPTED} режиссированных клиентов...")
    for idx, scenario_fn in enumerate(SCRIPTED_SCENARIOS, 1):
        cid = f"{CLIENT_ID_SCRIPTED_PREFIX}_{idx:02d}"
        result = scenario_fn(cid, subs_ref, reg_ref, rng)
        txns, labels = _generate_scripted_client(result, reg_ref, rng)
        all_transactions.extend(txns)
        all_labels.extend(labels)
        print(f"  [{idx:02d}] {scenario_fn.__name__}  +{len(txns)} txns, +{len(labels)} labels")

    # --- Сборка DataFrame ---
    print("Сборка и сортировка DataFrames...")
    txn_df = pd.DataFrame(all_transactions)
    txn_df["date"] = pd.to_datetime(txn_df["date"])
    txn_df = txn_df.sort_values(["client_id", "date"]).reset_index(drop=True)
    txn_df["date"] = txn_df["date"].dt.strftime("%Y-%m-%d %H:%M:%S")

    labels_df = pd.DataFrame(all_labels).drop_duplicates(
        subset=["client_id", "merchant_name"]
    ).reset_index(drop=True)

    # --- Сохранение ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    txn_df.to_csv(TRANSACTIONS_OUTPUT_PATH, index=False, encoding="utf-8")
    labels_df.to_csv(LABELS_OUTPUT_PATH, index=False, encoding="utf-8")

    history_start = SIMULATION_TODAY - timedelta(days=HISTORY_MONTHS * 30)
    meta: dict[str, Any] = {
        "simulation_today": SIMULATION_TODAY.strftime("%Y-%m-%d"),
        "random_seed": RANDOM_SEED,
        "n_clients_random": N_CLIENTS_RANDOM,
        "n_clients_scripted": N_CLIENTS_SCRIPTED,
        "n_clients_total": N_CLIENTS_RANDOM + N_CLIENTS_SCRIPTED,
        "n_transactions": len(txn_df),
        "n_labels": len(labels_df),
        "history_start": history_start.strftime("%Y-%m-%d"),
        "generator_version": GENERATOR_VERSION,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(META_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Сохранено: {TRANSACTIONS_OUTPUT_PATH.name} ({len(txn_df):,} строк)")
    print(f"Сохранено: {LABELS_OUTPUT_PATH.name} ({len(labels_df):,} строк)")
    print(f"Сохранено: {META_OUTPUT_PATH.name}")

    # --- Sanity-checks ---
    print("\nЗапуск sanity-checks...")
    errors = run_sanity_checks(txn_df, labels_df, meta)

    if errors:
        print("\n[FAIL] Sanity-checks не пройдены:")
        for err in errors:
            print(f"  [FAIL] {err}")
        sys.exit(1)

    print("[OK] Все sanity-checks пройдены.")
    _print_report(txn_df, labels_df)


if __name__ == "__main__":
    main()
