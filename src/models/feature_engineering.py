"""
Feature engineering for demand forecasting.
Builds (date, item_id) level dataset with target = daily quantity and engineered features.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


# Columns we use as base for features (from merged + items)
DATE_COL = "date"
ITEM_ID_COL = "item_id"
TARGET_COL = "quantity"
ORDER_COUNT_COL = "order_count"  # from sorted_most_ordered

# Default lag days and rolling window
LAG_DAYS = [1, 2, 3, 7, 14]
ROLLING_WINDOW = 7


def build_demand_dataset(
    demand_daily: pd.DataFrame,
    items_df: pd.DataFrame,
    min_demand_days: int = 5,
) -> pd.DataFrame:
    """
    Build (date, item_id) level dataset with target and base features.
    Keeps only items with at least min_demand_days of history for lag features.
    """
    demand_daily = demand_daily.copy()
    demand_daily[DATE_COL] = pd.to_datetime(demand_daily[DATE_COL])
    demand_daily = demand_daily.sort_values([ITEM_ID_COL, DATE_COL])

    # Merge item popularity (order_count)
    items_agg = items_df[[ITEM_ID_COL, ORDER_COUNT_COL]].drop_duplicates(ITEM_ID_COL)
    items_agg[ITEM_ID_COL] = items_agg[ITEM_ID_COL].astype(int)
    df = demand_daily.merge(items_agg, on=ITEM_ID_COL, how="left")
    df[ORDER_COUNT_COL] = df[ORDER_COUNT_COL].fillna(0).astype(float)

    # Calendar features from date
    df["day_of_week"] = df[DATE_COL].dt.dayofweek
    df["month"] = df[DATE_COL].dt.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["day_of_month"] = df[DATE_COL].dt.day

    return df


def add_lag_and_rolling_features(
    df: pd.DataFrame,
    lag_days: Optional[List[int]] = None,
    rolling_window: int = ROLLING_WINDOW,
) -> pd.DataFrame:
    """
    Add lag and rolling stats per item_id. Requires sorted (item_id, date).
    """
    lag_days = lag_days or LAG_DAYS
    df = df.sort_values([ITEM_ID_COL, DATE_COL]).copy()

    for lag in lag_days:
        df[f"lag_{lag}"] = df.groupby(ITEM_ID_COL)[TARGET_COL].shift(lag)

    df["rolling_mean_7"] = df.groupby(ITEM_ID_COL)[TARGET_COL].transform(
        lambda x: x.shift(1).rolling(rolling_window, min_periods=1).mean()
    )
    df["rolling_std_7"] = df.groupby(ITEM_ID_COL)[TARGET_COL].transform(
        lambda x: x.shift(1).rolling(rolling_window, min_periods=1).std().fillna(0)
    )

    return df


def get_feature_columns() -> List[str]:
    """Names of columns used as model features (after engineering)."""
    lag_cols = [f"lag_{d}" for d in LAG_DAYS]
    return [
        "day_of_week",
        "month",
        "is_weekend",
        "day_of_month",
        ORDER_COUNT_COL,
        *lag_cols,
        "rolling_mean_7",
        "rolling_std_7",
    ]


def prepare_model_matrix(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    drop_na_target: bool = True,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """
    Return X (features), y (target), and metadata (date, item_id) for modeling.
    Drops rows where any feature is NaN (e.g. first days without lags).
    """
    feature_cols = feature_cols or get_feature_columns()
    available = [c for c in feature_cols if c in df.columns]
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")

    use = df[[DATE_COL, ITEM_ID_COL, TARGET_COL] + available].copy()
    if drop_na_target:
        use = use.dropna(subset=[TARGET_COL])
    use = use.dropna(subset=available)

    X = use[available]
    y = use[TARGET_COL]
    meta = use[[DATE_COL, ITEM_ID_COL]]
    return X, y, meta


def build_feature_row_for_prediction(
    item_demand_series: pd.Series,
    order_count: float,
    target_date: pd.Timestamp,
    lag_days: Optional[List[int]] = None,
    rolling_window: int = ROLLING_WINDOW,
) -> Optional[pd.DataFrame]:
    """
    Build a single row of features for predicting demand on target_date for one item.
    item_demand_series: index = date (datetime), value = quantity (daily). Sorted by date.
    """
    lag_days = lag_days or LAG_DAYS
    if item_demand_series.empty:
        return None
    item_demand_series = item_demand_series.sort_index()
    dates_before = item_demand_series.index[item_demand_series.index < target_date]
    if len(dates_before) < 1:
        return None
    window = item_demand_series.loc[dates_before].tail(max(lag_days) + 1)
    row = {}
    row["day_of_week"] = target_date.dayofweek
    row["month"] = target_date.month
    row["is_weekend"] = 1 if target_date.dayofweek >= 5 else 0
    row["day_of_month"] = target_date.day
    row["order_count"] = order_count
    for lag in lag_days:
        if len(window) >= lag:
            row[f"lag_{lag}"] = window.iloc[-lag]
        else:
            row[f"lag_{lag}"] = 0.0
    use_for_rolling = window.tail(rolling_window)
    row["rolling_mean_7"] = use_for_rolling.mean() if len(use_for_rolling) else 0.0
    row["rolling_std_7"] = use_for_rolling.std() if len(use_for_rolling) >= 2 else 0.0
    return pd.DataFrame([row])
