"""
Loads data for Fresh Flow Insights.
If cache/ exists (from scripts/build_cache.py), loads from cache for fast startup.
Otherwise loads from data/ (merged_complete parts + sorted_most_ordered).
"""

import os
import glob
import json
import pandas as pd
from typing import Optional, List


REQUIRED_MERGED_COLS = [
    "item_id", "order_id", "quantity", "price", "cost", "title",
    "created_order", "place_id", "status_order", "type"
]


class DataLoader:
    """
    Loads demand aggregates and items. Prefers cache/ if present; else builds from data/.
    """

    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            from config.settings import DATA_DIR
            data_path = DATA_DIR
        self.data_path = data_path
        self._cache_dir: Optional[str] = None
        self._orders_df: Optional[pd.DataFrame] = None
        self._items_df: Optional[pd.DataFrame] = None
        self._demand_daily: Optional[pd.DataFrame] = None

    def _cache_available(self) -> bool:
        if self._cache_dir is None:
            from config.settings import CACHE_DIR
            self._cache_dir = CACHE_DIR
        return (
            os.path.isfile(os.path.join(self._cache_dir, "demand_daily.csv"))
            and os.path.isfile(os.path.join(self._cache_dir, "items.csv"))
        )

    def _load_from_cache(self) -> None:
        """Load demand_daily, items, orders from cache. Fast."""
        cache = self._cache_dir
        self._demand_daily = pd.read_csv(os.path.join(cache, "demand_daily.csv"))
        self._demand_daily["date"] = pd.to_datetime(self._demand_daily["date"])
        self._items_df = pd.read_csv(os.path.join(cache, "items.csv"))
        self._items_df["item_id"] = pd.to_numeric(self._items_df["item_id"], errors="coerce").astype("Int64")
        order_items_path = os.path.join(cache, "order_items.csv")
        if os.path.isfile(order_items_path):
            self._orders_df = pd.read_csv(order_items_path)
        else:
            self._orders_df = pd.DataFrame(columns=["order_id", "item_id"])

    def _ensure_orders_loaded(self, max_parts: Optional[int] = None) -> None:
        if self._orders_df is not None:
            return
        if self._cache_available():
            self._load_from_cache()
            return
        from config.settings import MAX_MERGED_PARTS, MERGED_COLS
        max_parts = max_parts or MAX_MERGED_PARTS
        pattern = os.path.join(self.data_path, "merged_complete_part*.csv")
        files = sorted(glob.glob(pattern))
        if not files:
            raise FileNotFoundError(f"No merged_complete_part*.csv in {self.data_path}. Run scripts/build_cache.py first or add data/.")
        files = files[:max_parts]
        dfs = []
        for f in files:
            df = pd.read_csv(f, low_memory=False)
            use_cols = [c for c in MERGED_COLS if c in df.columns]
            df = df[use_cols] if use_cols else df
            dfs.append(df)
        self._orders_df = pd.concat(dfs, ignore_index=True)
        from src.utils.helpers import parse_order_date
        self._orders_df["order_date"] = parse_order_date(self._orders_df["created_order"])
        self._orders_df = self._orders_df.dropna(subset=["order_date"])
        if "status_order" in self._orders_df.columns:
            self._orders_df = self._orders_df[
                self._orders_df["status_order"].astype(str).str.strip().str.lower() == "closed"
            ]
        self._orders_df["quantity"] = pd.to_numeric(self._orders_df["quantity"], errors="coerce").fillna(0).astype(int)
        self._orders_df["item_id"] = pd.to_numeric(self._orders_df["item_id"], errors="coerce")
        self._orders_df = self._orders_df[self._orders_df["item_id"].notna()].copy()
        self._orders_df["item_id"] = self._orders_df["item_id"].astype(int)

    def load_sorted_most_ordered(self) -> pd.DataFrame:
        if self._items_df is not None:
            return self._items_df
        if self._cache_available():
            if self._items_df is None:
                self._load_from_cache()
            return self._items_df
        path = os.path.join(self.data_path, "sorted_most_ordered.csv")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"sorted_most_ordered.csv not found at {path}")
        self._items_df = pd.read_csv(path)
        self._items_df["item_id"] = pd.to_numeric(self._items_df["item_id"], errors="coerce").astype("Int64")
        return self._items_df

    def get_orders_df(self, max_parts: Optional[int] = None) -> pd.DataFrame:
        self._ensure_orders_loaded(max_parts)
        return self._orders_df

    def get_demand_daily(
        self,
        max_parts: Optional[int] = None,
        by_place: bool = False,
    ) -> pd.DataFrame:
        if self._demand_daily is not None and not by_place:
            return self._demand_daily
        if self._cache_available() and not by_place:
            if self._demand_daily is None:
                self._load_from_cache()
            return self._demand_daily
        orders = self.get_orders_df(max_parts)
        orders["date"] = orders["order_date"].dt.date
        group = ["date", "item_id"]
        if by_place and "place_id" in orders.columns:
            orders["place_id"] = pd.to_numeric(orders["place_id"], errors="coerce")
            orders = orders.dropna(subset=["place_id"])
            group.append("place_id")
        demand = orders.groupby(group, as_index=False)["quantity"].sum()
        demand["date"] = pd.to_datetime(demand["date"])
        if not by_place:
            self._demand_daily = demand
        return demand

    def load_csv(self, filename: str, parse_dates: Optional[List[str]] = None) -> pd.DataFrame:
        path = os.path.join(self.data_path, filename)
        return pd.read_csv(path, parse_dates=parse_dates)
