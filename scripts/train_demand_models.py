"""
Train demand forecasting models: feature engineering -> feature selection -> LR, RF, LightGBM, ensemble.
Saves artifacts to config/models/ (or PROJECT_ROOT/models/).
Run from project root: python scripts/train_demand_models.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.models.data_loader import DataLoader
from src.models.feature_engineering import (
    build_demand_dataset,
    add_lag_and_rolling_features,
    get_feature_columns,
    prepare_model_matrix,
)
from src.models.demand_models import train_models, save_artifacts


def main():
    from config.settings import PROJECT_ROOT, MAX_MERGED_PARTS

    print("Loading data...")
    loader = DataLoader()  # uses DATA_DIR (data/ folder)
    demand_daily = loader.get_demand_daily(max_parts=MAX_MERGED_PARTS)
    items_df = loader.load_sorted_most_ordered()
    print(f"Demand rows: {len(demand_daily)}, Items: {len(items_df)}")

    print("Building dataset and engineering features...")
    df = build_demand_dataset(demand_daily, items_df, min_demand_days=1)
    df = add_lag_and_rolling_features(df, lag_days=[1, 2, 3, 7, 14], rolling_window=7)
    print(f"Rows after lags: {len(df)}")

    X, y, meta = prepare_model_matrix(df, feature_cols=get_feature_columns(), drop_na_target=True)
    print(f"Model matrix: X {X.shape}, y {len(y)}")

    # Feature selection: keep top 10 (or all if fewer)
    select_k = min(10, X.shape[1])
    print(f"Training models (feature selection k={select_k})...")
    result = train_models(
        X, y,
        feature_cols=list(X.columns),
        test_size=0.2,
        random_state=42,
        select_k=select_k,
    )

    print("Metrics:")
    for name, m in result["metrics"].items():
        print(f"  {name}: MAE={m['mae']:.4f}, RMSE={m['rmse']:.4f}, R2={m['r2']:.4f}")

    out_dir = os.path.join(PROJECT_ROOT, "models")
    save_artifacts(result, out_dir)
    print(f"Artifacts saved to {out_dir}")


if __name__ == "__main__":
    main()
