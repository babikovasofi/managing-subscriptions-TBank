"""
Entry point for training the subscription classifier.

Usage:
    python -m ml.models.train
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from data.generator.config import LABELS_OUTPUT_PATH, TRANSACTIONS_OUTPUT_PATH
from ml.models.classifier import (
    save_model,
    train_classifier,
    tune_threshold,
)
from ml.models.dataset import build_training_dataset

_MODEL_PATH = Path("ml/models/saved/classifier.pkl")
_METRICS_PATH = Path("ml/models/saved/metrics.json")

_TEST_SIZE = 0.2
_RANDOM_STATE = 42


def _print_confusion_matrix(y_true: list[int], y_pred: list[int]) -> None:
    tp = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 0)
    tn = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 0)
    print("\nConfusion matrix (test, threshold=0.5):")
    print("                   Predicted 0   Predicted 1")
    print(f"  Actual 0 (neg):      {tn:5d}         {fp:5d}")
    print(f"  Actual 1 (pos):      {fn:5d}         {tp:5d}")


def main() -> None:
    print("Loading data...")
    txn_df = pd.read_csv(TRANSACTIONS_OUTPUT_PATH)
    labels_df = pd.read_csv(LABELS_OUTPUT_PATH)
    print(f"  Transactions: {len(txn_df):,}   Labels: {len(labels_df):,}")

    print("\nBuilding training dataset...")
    X, y, groups = build_training_dataset(txn_df, labels_df)
    n_pos = int(y.sum())
    n_neg = int((y == 0).sum())
    print(f"  Candidates: {len(X):,}   Positives: {n_pos}   Negatives: {n_neg}")
    print(f"  Class balance: {y.mean():.3f} fraction positive")
    print(f"  Unique clients: {groups.nunique()}")

    print("\nTraining classifier (GroupKFold CV + final split)...")
    model, metrics, importance_df = train_classifier(X, y, groups)

    print("\n=== Cross-validation metrics (5-fold GroupKFold) ===")
    for m_name in ("precision", "recall", "f1", "roc_auc"):
        mean_val = metrics[f"cv_{m_name}_mean"]
        std_val = metrics[f"cv_{m_name}_std"]
        if np.isnan(mean_val):
            print(f"  {m_name:<12}: n/a  (no negative class in some folds)")
        else:
            print(f"  {m_name:<12}: {mean_val:.4f} +/- {std_val:.4f}")

    print(f"\n=== Test metrics ({metrics['train_n_clients']} train / {metrics['test_n_clients']} test clients) ===")
    for m_name in ("precision", "recall", "f1", "roc_auc"):
        val = metrics[f"test_{m_name}"]
        if np.isnan(val):
            print(f"  {m_name:<12}: n/a")
        else:
            print(f"  {m_name:<12}: {val:.4f}")

    _print_confusion_matrix(metrics["_test_y"], metrics["_test_pred"])

    print("\n=== Top-10 feature importance ===")
    print(importance_df.head(10).to_string(index=False))

    # Threshold tuning on the same test split (reproducible via fixed seed)
    splitter = GroupShuffleSplit(n_splits=1, test_size=_TEST_SIZE, random_state=_RANDOM_STATE)
    _, test_idx = next(splitter.split(X, y, groups))
    X_test = X.iloc[test_idx]
    y_test = y.iloc[test_idx]

    best_threshold = tune_threshold(model, X_test, y_test, target_metric="f1")

    # Save model
    save_model(model, _MODEL_PATH)
    print(f"\nModel saved: {_MODEL_PATH}")

    # Save metrics (strip internal "_" keys)
    save_metrics = {k: v for k, v in metrics.items() if not k.startswith("_")}
    save_metrics["best_threshold"] = best_threshold
    _METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(save_metrics, f, indent=2, ensure_ascii=False)
    print(f"Metrics saved: {_METRICS_PATH}")


if __name__ == "__main__":
    main()
