"""
Precompute all data and save to cache/ so the API and UI load instantly.
Run once after putting CSVs in data/:  python scripts/build_cache.py
Then run the API and Streamlit; they will use cache/ only.
"""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config.settings import DATA_DIR, CACHE_DIR, MAX_MERGED_PARTS
from src.models.data_loader import DataLoader


def main():
    print("Building cache from data/ ...")
    os.makedirs(CACHE_DIR, exist_ok=True)

    loader = DataLoader(DATA_DIR)
    print("  Loading raw data (this may take 1-2 minutes)...")
    demand_daily = loader.get_demand_daily(max_parts=MAX_MERGED_PARTS)
    items_df = loader.load_sorted_most_ordered()
    orders_df = loader.get_orders_df(max_parts=MAX_MERGED_PARTS)

    print("  Writing cache/demand_daily.csv ...")
    demand_daily.to_csv(os.path.join(CACHE_DIR, "demand_daily.csv"), index=False)

    print("  Writing cache/items.csv ...")
    items_df.to_csv(os.path.join(CACHE_DIR, "items.csv"), index=False)

    print("  Writing cache/order_items.csv ...")
    order_items = orders_df[["order_id", "item_id"]].drop_duplicates()
    order_items.to_csv(os.path.join(CACHE_DIR, "order_items.csv"), index=False)

    # Summary (for UI and quick checks)
    total_quantity = int(demand_daily["quantity"].sum())
    unique_items = demand_daily["item_id"].nunique()
    demand_daily["date"] = demand_daily["date"].astype("datetime64[ns]")
    date_min = demand_daily["date"].min().isoformat()
    date_max = demand_daily["date"].max().isoformat()
    summary = {
        "total_quantity": total_quantity,
        "unique_items": unique_items,
        "date_range": {"min": date_min, "max": date_max},
    }
    print("  Writing cache/summary.json ...")
    with open(os.path.join(CACHE_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # Daily totals for chart (last 180 days)
    daily_totals = demand_daily.groupby("date", as_index=False)["quantity"].sum()
    daily_totals = daily_totals.sort_values("date").tail(180)
    history = [
        {"date": row["date"].strftime("%Y-%m-%d"), "quantity": int(row["quantity"])}
        for _, row in daily_totals.iterrows()
    ]
    print("  Writing cache/demand_history.json ...")
    with open(os.path.join(CACHE_DIR, "demand_history.json"), "w") as f:
        json.dump(history, f, indent=0)

    print("Done. Cache is in", CACHE_DIR)
    print("You can now run the API and UI; they will use the cache and start fast.")


if __name__ == "__main__":
    main()
