"""
LightGBM subscription classifier.

Public API:
  train_classifier(X, y, groups) -> (model, metrics, feature_importance)
  save_model(model, path)
  load_model(path) -> model
  predict_subscriptions(model, X, threshold) -> (predictions, probabilities)
  tune_threshold(model, X, y, target_metric) -> best_threshold
"""

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit

from ml.models.dataset import FEATURE_COLUMNS, _CATEGORICAL_FEATURES

_N_ESTIMATORS: int = 200
_LEARNING_RATE: float = 0.05
_NUM_LEAVES: int = 31
_RANDOM_STATE: int = 42


def _make_model() -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=_N_ESTIMATORS,
        learning_rate=_LEARNING_RATE,
        num_leaves=_NUM_LEAVES,
        class_weight="balanced",
        random_state=_RANDOM_STATE,
        verbosity=-1,
    )


def train_classifier(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
) -> tuple[LGBMClassifier, dict[str, Any], pd.DataFrame]:
    """
    Train LightGBM with GroupKFold CV and an honest held-out test.

    Parameters
    ----------
    X : feature DataFrame (FEATURE_COLUMNS), from build_training_dataset()
    y : binary labels (0/1)
    groups : client_id per row, for group-aware splits

    Returns
    -------
    model : LGBMClassifier fitted on 80% of clients
    metrics : CV and test metrics dict; internal keys prefixed with "_"
              are stripped before JSON serialization
    feature_importance : DataFrame[feature, importance] sorted descending
    """
    # --- 5-fold GroupKFold cross-validation ---
    cv = GroupKFold(n_splits=5)
    cv_precisions: list[float] = []
    cv_recalls: list[float] = []
    cv_f1s: list[float] = []
    cv_aucs: list[float] = []

    for train_idx, val_idx in cv.split(X, y, groups):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        m = _make_model()
        m.fit(X_tr, y_tr, categorical_feature=_CATEGORICAL_FEATURES)
        proba = m.predict_proba(X_val)[:, 1]
        pred = (proba >= 0.5).astype(int)

        cv_precisions.append(precision_score(y_val, pred, zero_division=0))
        cv_recalls.append(recall_score(y_val, pred, zero_division=0))
        cv_f1s.append(f1_score(y_val, pred, zero_division=0))

        # roc_auc requires both classes present in validation fold
        if len(np.unique(y_val)) > 1:
            cv_aucs.append(roc_auc_score(y_val, proba))

    # --- Final train/test split: 80% / 20% of clients ---
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=_RANDOM_STATE)
    train_idx, test_idx = next(splitter.split(X, y, groups))

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model = _make_model()
    model.fit(X_train, y_train, categorical_feature=_CATEGORICAL_FEATURES)

    test_proba = model.predict_proba(X_test)[:, 1]
    test_pred = (test_proba >= 0.5).astype(int)

    metrics: dict[str, Any] = {
        "cv_precision_mean": float(np.mean(cv_precisions)),
        "cv_precision_std": float(np.std(cv_precisions)),
        "cv_recall_mean": float(np.mean(cv_recalls)),
        "cv_recall_std": float(np.std(cv_recalls)),
        "cv_f1_mean": float(np.mean(cv_f1s)),
        "cv_f1_std": float(np.std(cv_f1s)),
        "cv_roc_auc_mean": float(np.mean(cv_aucs)) if cv_aucs else float("nan"),
        "cv_roc_auc_std": float(np.std(cv_aucs)) if cv_aucs else float("nan"),
        "test_precision": float(precision_score(y_test, test_pred, zero_division=0)),
        "test_recall": float(recall_score(y_test, test_pred, zero_division=0)),
        "test_f1": float(f1_score(y_test, test_pred, zero_division=0)),
        "test_roc_auc": (
            float(roc_auc_score(y_test, test_proba))
            if len(np.unique(y_test)) > 1
            else float("nan")
        ),
        "test_n_clients": int(groups.iloc[test_idx].nunique()),
        "train_n_clients": int(groups.iloc[train_idx].nunique()),
        # Internal: used for confusion matrix in train.py, stripped before JSON save
        "_test_y": y_test.tolist(),
        "_test_pred": test_pred.tolist(),
    }

    importance_df = pd.DataFrame({
        "feature": FEATURE_COLUMNS,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    return model, metrics, importance_df


def save_model(model: LGBMClassifier, path: Path | str) -> None:
    """Persist model via joblib."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path | str) -> LGBMClassifier:
    """Load model from joblib file."""
    return joblib.load(path)


def predict_subscriptions(
    model: LGBMClassifier,
    X: pd.DataFrame,
    threshold: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Run inference on feature matrix X.

    Parameters
    ----------
    model : fitted LGBMClassifier
    X : feature DataFrame with FEATURE_COLUMNS
    threshold : decision boundary for positive class

    Returns
    -------
    predictions : int array (0/1)
    probabilities : float array P(subscription)
    """
    probabilities: np.ndarray = model.predict_proba(X)[:, 1]
    predictions: np.ndarray = (probabilities >= threshold).astype(int)
    return predictions, probabilities


def tune_threshold(
    model: LGBMClassifier,
    X: pd.DataFrame,
    y: pd.Series,
    target_metric: str = "f1",
) -> float:
    """
    Search thresholds in [0.30, 0.70] step 0.05 maximising target_metric.

    Prints a table: threshold | precision | recall | f1.
    Returns the best threshold.
    """
    _, proba = predict_subscriptions(model, X, threshold=0.0)

    thresholds = np.arange(0.30, 0.71, 0.05)
    rows: list[dict[str, float]] = []

    for t in thresholds:
        pred = (proba >= t).astype(int)
        rows.append({
            "threshold": round(float(t), 2),
            "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)),
        })

    table = pd.DataFrame(rows)
    print("\nThreshold tuning:")
    print(table.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    best_row = table.loc[table[target_metric].idxmax()]
    best_threshold = float(best_row["threshold"])
    print(f"\nBest threshold ({target_metric}): {best_threshold:.2f}")
    return best_threshold
