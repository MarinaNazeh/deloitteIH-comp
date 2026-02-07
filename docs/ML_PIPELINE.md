# Demand forecasting ML pipeline

## Feature columns (from data)

Features are built from:

- **Calendar:** `day_of_week`, `month`, `is_weekend`, `day_of_month`
- **Item popularity:** `order_count` (from `sorted_most_ordered.csv`)
- **Lags:** `lag_1`, `lag_2`, `lag_3`, `lag_7`, `lag_14` (past daily quantity)
- **Rolling:** `rolling_mean_7`, `rolling_std_7` (over previous 7 days)

Target: **daily quantity** per (date, item_id).

## Feature engineering

1. **Build demand dataset:** `build_demand_dataset(demand_daily, items_df)` → (date, item_id, quantity, order_count, calendar).
2. **Add lags/rolling:** `add_lag_and_rolling_features(df)` → lag_1..lag_14, rolling_mean_7, rolling_std_7.
3. **Model matrix:** `prepare_model_matrix(df)` → X (features), y (quantity), meta (date, item_id). Rows with any NaN in features are dropped.

## Feature selection

- **SelectKBest** (F-regression) keeps top `k` features (default `k=10`). Used before training.

## Models

| Model            | Package   | Role                    |
|------------------|-----------|-------------------------|
| Linear Regression| sklearn   | Baseline, scaled input |
| Random Forest    | sklearn   | Non-linear              |
| LightGBM         | lightgbm  | Gradient boosting       |
| **Ensemble**     | —         | Mean of the three       |

## Training

From project root:

```bash
set PYTHONPATH=%CD%
python scripts/train_demand_models.py
```

- Reads `merged_complete_part1.csv` (or more parts via `MAX_MERGED_PARTS`) and `sorted_most_ordered.csv`.
- Saves to `models/`: `feature_cols.json`, `scaler.pkl`, `linear_regression.pkl`, `random_forest.pkl`, `lightgbm.txt` (or `lightgbm.pkl`), `metrics.json`.

## Inference

- **API:** If `models/` exists, `InventoryService` loads it and uses the **ensemble** for `predict_demand(item_id, period=...)`. Otherwise falls back to recent-average.
- **Programmatic:** `from src.models.demand_models import load_artifacts, predict_ensemble` then `predict_ensemble(X, load_artifacts("models"))`.

## Metrics (example run)

- Linear Regression: MAE ≈ 1.07, R² ≈ 0.33  
- Random Forest: MAE ≈ 1.11, R² ≈ 0.27  
- LightGBM: MAE ≈ 1.10, R² ≈ 0.27  
- **Ensemble:** MAE ≈ 1.08, R² ≈ 0.32  

(R² on test set; your numbers may vary with data size and split.)
