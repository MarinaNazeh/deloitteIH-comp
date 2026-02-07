"""
Demand forecasting models: Linear Regression, LightGBM, Random Forest, and Ensemble.
Feature selection and train/predict API.
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict, Any

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


# Default feature set (must match feature_engineering.get_feature_columns())
DEFAULT_FEATURE_COLS = [
    "day_of_week", "month", "is_weekend", "day_of_month", "order_count",
    "lag_1", "lag_2", "lag_3", "lag_7", "lag_14",
    "rolling_mean_7", "rolling_std_7",
]


def select_features(
    X: pd.DataFrame,
    y: pd.Series,
    k: int = 10,
    method: str = "kbest",
) -> Tuple[np.ndarray, List[str]]:
    """
    Select top k features. Returns selector-fitted X and list of selected feature names.
    """
    cols = list(X.columns)
    if len(cols) <= k:
        return X.values, cols
    if method == "kbest":
        sel = SelectKBest(score_func=f_regression, k=min(k, len(cols)))
        X_sel = sel.fit_transform(X, y)
        mask = sel.get_support()
        selected = [cols[i] for i in range(len(cols)) if mask[i]]
        return X_sel, selected
    return X.values, cols


def train_models(
    X: pd.DataFrame,
    y: pd.Series,
    feature_cols: Optional[List[str]] = None,
    test_size: float = 0.2,
    random_state: int = 42,
    select_k: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Train Linear Regression, Random Forest, LightGBM and ensemble.
    Returns dict with models, scaler, selected features, and metrics.
    """
    feature_cols = feature_cols or list(X.columns)
    X = X[feature_cols].copy()
    X = X.fillna(0)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, shuffle=True
    )

    # Optional feature selection
    selected_cols = feature_cols
    if select_k and select_k < len(feature_cols):
        X_sel, selected_cols = select_features(X_train, y_train, k=select_k)
        X_train_sel = pd.DataFrame(X_sel, columns=selected_cols, index=X_train.index)
        X_test_sel = X_test[selected_cols].fillna(0)
    else:
        X_train_sel = X_train
        X_test_sel = X_test

    # Scale for Linear Regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_sel)
    X_test_scaled = scaler.transform(X_test_sel)

    models = {}
    predictions = {}

    # 1. Linear Regression
    lr = LinearRegression()
    lr.fit(X_train_scaled, y_train)
    pred_lr = lr.predict(X_test_scaled)
    pred_lr = np.maximum(0, pred_lr)
    models["linear_regression"] = lr
    predictions["linear_regression"] = pred_lr

    # 2. Random Forest (n_jobs=1 avoids multiprocessing issues on Windows/sandbox)
    rf = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=random_state, n_jobs=1)
    rf.fit(X_train_sel, y_train)
    pred_rf = np.maximum(0, rf.predict(X_test_sel))
    models["random_forest"] = rf
    predictions["random_forest"] = pred_rf

    # 3. LightGBM
    if HAS_LIGHTGBM:
        lgb_train = lgb.Dataset(X_train_sel, y_train)
        params = {
            "objective": "regression",
            "metric": "mae",
            "verbosity": -1,
            "random_state": random_state,
            "n_estimators": 100,
            "max_depth": 8,
            "learning_rate": 0.1,
        }
        lgbm = lgb.train(
            params,
            lgb_train,
            num_boost_round=100,
        )
        pred_lgb = np.maximum(0, lgbm.predict(X_test_sel))
        models["lightgbm"] = lgbm
        predictions["lightgbm"] = pred_lgb
    else:
        # Fallback: use RF again with different params as placeholder
        lgbm = RandomForestRegressor(n_estimators=80, max_depth=10, random_state=random_state + 1, n_jobs=1)
        lgbm.fit(X_train_sel, y_train)
        pred_lgb = np.maximum(0, lgbm.predict(X_test_sel))
        models["lightgbm"] = lgbm
        predictions["lightgbm"] = pred_lgb

    # 4. Ensemble (simple average)
    pred_ensemble = np.mean(
        [predictions["linear_regression"], predictions["random_forest"], predictions["lightgbm"]],
        axis=0,
    )
    pred_ensemble = np.maximum(0, pred_ensemble)
    predictions["ensemble"] = pred_ensemble

    # Metrics
    def _metrics(y_true, y_pred):
        return {
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "r2": float(r2_score(y_true, y_pred)),
        }

    metrics = {
        name: _metrics(y_test, pred)
        for name, pred in predictions.items()
    }

    return {
        "models": models,
        "scaler": scaler,
        "feature_cols": selected_cols,
        "metrics": metrics,
        "predictions": predictions,
        "y_test": y_test.values,
    }


def save_artifacts(
    result: Dict[str, Any],
    path_dir: str,
) -> None:
    """Save models, scaler, and feature list to path_dir."""
    os.makedirs(path_dir, exist_ok=True)
    feature_cols = result["feature_cols"]
    with open(os.path.join(path_dir, "feature_cols.json"), "w") as f:
        json.dump(feature_cols, f, indent=2)
    with open(os.path.join(path_dir, "scaler.pkl"), "wb") as f:
        pickle.dump(result["scaler"], f)
    with open(os.path.join(path_dir, "linear_regression.pkl"), "wb") as f:
        pickle.dump(result["models"]["linear_regression"], f)
    with open(os.path.join(path_dir, "random_forest.pkl"), "wb") as f:
        pickle.dump(result["models"]["random_forest"], f)
    lgbm = result["models"]["lightgbm"]
    if HAS_LIGHTGBM and hasattr(lgbm, "save_model"):
        lgbm.save_model(os.path.join(path_dir, "lightgbm.txt"))
    else:
        with open(os.path.join(path_dir, "lightgbm.pkl"), "wb") as f:
            pickle.dump(lgbm, f)
    with open(os.path.join(path_dir, "metrics.json"), "w") as f:
        json.dump(result["metrics"], f, indent=2)


def load_artifacts(path_dir: str) -> Dict[str, Any]:
    """Load models, scaler, feature list from path_dir."""
    with open(os.path.join(path_dir, "feature_cols.json")) as f:
        feature_cols = json.load(f)
    with open(os.path.join(path_dir, "scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    with open(os.path.join(path_dir, "linear_regression.pkl"), "rb") as f:
        lr = pickle.load(f)
    with open(os.path.join(path_dir, "random_forest.pkl"), "rb") as f:
        rf = pickle.load(f)
    lgb_path = os.path.join(path_dir, "lightgbm.txt")
    if os.path.isfile(lgb_path) and HAS_LIGHTGBM:
        lgbm = lgb.Booster(model_file=lgb_path)
    else:
        with open(os.path.join(path_dir, "lightgbm.pkl"), "rb") as f:
            lgbm = pickle.load(f)
    return {
        "models": {"linear_regression": lr, "random_forest": rf, "lightgbm": lgbm},
        "scaler": scaler,
        "feature_cols": feature_cols,
    }


def predict_ensemble(
    X: pd.DataFrame,
    artifacts: Dict[str, Any],
) -> np.ndarray:
    """Predict using ensemble (average of LR, RF, LightGBM). X must have feature_cols."""
    preds = predict_all_models(X, artifacts)
    return preds["ensemble"]


def predict_all_models(
    X: pd.DataFrame,
    artifacts: Dict[str, Any],
) -> Dict[str, np.ndarray]:
    """
    Predict using all models individually and return dict with each model's prediction.
    Returns: {"linear_regression": [...], "random_forest": [...], "lightgbm": [...], "ensemble": [...]}
    """
    feature_cols = artifacts["feature_cols"]
    X = X[[c for c in feature_cols if c in X.columns]].copy()
    for c in feature_cols:
        if c not in X.columns:
            X[c] = 0
    X = X[feature_cols].fillna(0)

    scaler = artifacts["scaler"]
    lr = artifacts["models"]["linear_regression"]
    rf = artifacts["models"]["random_forest"]
    lgbm = artifacts["models"]["lightgbm"]

    X_scaled = scaler.transform(X)
    pred_lr = np.maximum(0, lr.predict(X_scaled))
    pred_rf = np.maximum(0, rf.predict(X))
    if HAS_LIGHTGBM and hasattr(lgbm, "predict"):
        pred_lgb = np.maximum(0, lgbm.predict(X))
    else:
        pred_lgb = np.maximum(0, lgbm.predict(X))

    pred_ensemble = np.maximum(0, (pred_lr + pred_rf + pred_lgb) / 3.0)

    return {
        "linear_regression": pred_lr,
        "random_forest": pred_rf,
        "lightgbm": pred_lgb,
        "ensemble": pred_ensemble,
    }
