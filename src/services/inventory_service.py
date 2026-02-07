"""
Business logic for demand forecasting, prep suggestions, reorder points, and bundle ideas.
Uses real demand aggregates and optional ML ensemble (LR + RF + LightGBM).
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional


class InventoryService:
    """
    Demand prediction and prep recommendations from historical order data.
    Uses daily demand by item (and optionally by place) and item popularity.
    Optionally uses trained ensemble model (Linear Regression + Random Forest + LightGBM).
    """

    def __init__(
        self,
        demand_daily: pd.DataFrame,
        items_df: pd.DataFrame,
        orders_df: Optional[pd.DataFrame] = None,
        model_artifacts_path: Optional[str] = None,
    ):
        """
        Args:
            demand_daily: columns [date, item_id, quantity] optionally [place_id].
            items_df: sorted_most_ordered [item_id, item_name, order_count].
            orders_df: optional; order_id + item_id for basket/bundle analysis.
            model_artifacts_path: optional path to trained models (models/); if set, predict_demand uses ensemble.
        """
        self.demand_daily = demand_daily
        self.items_df = items_df
        self.orders_df = orders_df
        self._model_artifacts: Optional[Dict[str, Any]] = None
        if model_artifacts_path and os.path.isdir(model_artifacts_path):
            try:
                from src.models.demand_models import load_artifacts
                self._model_artifacts = load_artifacts(model_artifacts_path)
            except Exception:
                self._model_artifacts = None

    def predict_demand(
        self,
        item_id: Any,
        period: str = "daily",
        place_id: Optional[Any] = None,
        window_days: int = 14,
    ) -> float:
        """
        Predicted demand for an item. Uses ensemble model if loaded; else recent average.
        period: 'daily' returns per-day; 'weekly' = 7x, 'monthly' = 30x.
        """
        item_id = int(item_id)
        df = self.demand_daily[self.demand_daily["item_id"] == item_id].copy()
        if place_id is not None and "place_id" in df.columns:
            df = df[df["place_id"] == place_id]
        if df.empty:
            return 0.0

        if self._model_artifacts is not None:
            pred = self._predict_demand_ensemble(item_id, df)
            if pred is not None:
                if period == "daily":
                    return round(float(pred), 2)
                if period == "weekly":
                    return round(float(pred * 7), 2)
                if period == "monthly":
                    return round(float(pred * 30), 2)
                return round(float(pred), 2)

        df = df.sort_values("date").tail(window_days)
        daily_avg = df["quantity"].mean()
        if period == "daily":
            return round(float(daily_avg), 2)
        if period == "weekly":
            return round(float(daily_avg * 7), 2)
        if period == "monthly":
            return round(float(daily_avg * 30), 2)
        return round(float(daily_avg), 2)

    def _predict_demand_ensemble(self, item_id: int, item_demand_df: pd.DataFrame) -> Optional[float]:
        """Use trained ensemble to predict next-day demand for this item."""
        from src.models.feature_engineering import build_feature_row_for_prediction
        from src.models.demand_models import predict_ensemble
        item_demand_df = item_demand_df.copy()
        item_demand_df["date"] = pd.to_datetime(item_demand_df["date"])
        series = item_demand_df.set_index("date")["quantity"].sort_index()
        order_count = 0.0
        row = self.items_df[self.items_df["item_id"] == item_id]
        if not row.empty:
            order_count = float(row["order_count"].iloc[0])
        last_date = series.index.max()
        target_date = last_date + pd.Timedelta(days=1)
        feature_row = build_feature_row_for_prediction(series, order_count, target_date)
        if feature_row is None:
            return None
        pred = predict_ensemble(feature_row, self._model_artifacts)
        return float(pred[0])

    def calculate_reorder_point(
        self, item_id: Any, lead_time_days: int = 3, place_id: Optional[Any] = None
    ) -> int:
        """Reorder point = (avg daily demand * lead time) + safety stock (50% of lead-time demand)."""
        daily = self.predict_demand(item_id, "daily", place_id=place_id)
        if daily <= 0:
            return 0
        safety = (daily * lead_time_days) * 0.5
        return int(np.ceil((daily * lead_time_days) + safety))

    def get_prep_suggestions(
        self,
        place_id: Optional[Any] = None,
        top_n: int = 20,
        safety_factor: float = 1.2,
    ) -> List[Dict[str, Any]]:
        """
        Suggested prep quantities for top items by demand.
        Prep = predicted daily demand * safety_factor, rounded up.
        """
        # Top items by total quantity in demand_daily (or from items_df order_count if no place filter)
        if place_id is not None and "place_id" in self.demand_daily.columns:
            agg = (
                self.demand_daily[self.demand_daily["place_id"] == place_id]
                .groupby("item_id", as_index=False)["quantity"]
                .sum()
            )
        else:
            agg = self.demand_daily.groupby("item_id", as_index=False)["quantity"].sum()
        agg = agg.nlargest(top_n * 2, "quantity")  # get more then take top_n with names
        out = []
        for _, row in agg.head(top_n).iterrows():
            iid = int(row["item_id"])
            pred = self.predict_demand(iid, "daily", place_id=place_id)
            prep = max(1, int(np.ceil(pred * safety_factor)))
            name = self._item_name(iid)
            out.append({
                "item_id": iid,
                "item_name": name,
                "predicted_daily_demand": round(pred, 2),
                "suggested_prep_quantity": prep,
                "safety_factor": safety_factor,
            })
        return out

    def _item_name(self, item_id: Any) -> str:
        """Resolve item_id to item_name from items_df."""
        row = self.items_df[self.items_df["item_id"] == item_id]
        if row.empty:
            return str(item_id)
        return str(row["item_name"].iloc[0])

    def get_top_items(self, n: int = 50, by: str = "order_count") -> List[Dict[str, Any]]:
        """Top N items from sorted_most_ordered (by order_count or by demand in our sample)."""
        if by == "order_count":
            top = self.items_df.nlargest(n, "order_count")
            return [
                {"item_id": int(r["item_id"]), "item_name": str(r["item_name"]), "order_count": int(r["order_count"])}
                for _, r in top.iterrows()
            ]
        # by demand in demand_daily
        agg = self.demand_daily.groupby("item_id", as_index=False)["quantity"].sum().nlargest(n, "quantity")
        return [
            {
                "item_id": int(r["item_id"]),
                "item_name": self._item_name(r["item_id"]),
                "total_quantity": int(r["quantity"]),
            }
            for _, r in agg.iterrows()
        ]

    def get_demand_history(self, last_n_days: int = 90) -> List[Dict[str, Any]]:
        """Daily total quantity for the last N days (for charts). Returns list of {date, quantity}."""
        df = self.demand_daily.copy()
        if "date" not in df.columns:
            return []
        df["date"] = pd.to_datetime(df["date"])
        cutoff = df["date"].max() - pd.Timedelta(days=last_n_days)
        df = df[df["date"] >= cutoff]
        daily = df.groupby("date", as_index=False)["quantity"].sum()
        daily = daily.sort_values("date")
        return [
            {"date": row["date"].strftime("%Y-%m-%d"), "quantity": int(row["quantity"])}
            for _, row in daily.iterrows()
        ]

    def get_demand_summary(
        self,
        item_id: Optional[Any] = None,
        place_id: Optional[Any] = None,
        last_n_days: Optional[int] = 30,
    ) -> Dict[str, Any]:
        """Summary stats: total orders, unique items, date range, optional per-item or per-place."""
        df = self.demand_daily
        if place_id is not None and "place_id" in df.columns:
            df = df[df["place_id"] == place_id]
        if item_id is not None:
            df = df[df["item_id"] == item_id]
        if last_n_days and "date" in df.columns:
            cutoff = df["date"].max() - pd.Timedelta(days=last_n_days)
            df = df[df["date"] >= cutoff]
        total_quantity = int(df["quantity"].sum())
        unique_items = df["item_id"].nunique()
        date_min = df["date"].min().isoformat() if len(df) else None
        date_max = df["date"].max().isoformat() if len(df) else None
        return {
            "total_quantity": total_quantity,
            "unique_items": unique_items,
            "date_range": {"min": date_min, "max": date_max},
            "item_id": item_id,
            "place_id": place_id,
        }

    def get_bundle_suggestions(self, min_pairs: int = 50, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Items often bought together (same order_id). Returns top_n pairs by co-occurrence.
        Uses orders_df with columns order_id, item_id.
        """
        if self.orders_df is None or "order_id" not in self.orders_df.columns:
            return []
        orders = self.orders_df[["order_id", "item_id"]].drop_duplicates()
        orders["item_id"] = orders["item_id"].astype(int)
        # Count pairs: for each order, list item_ids; then count (a,b) with a < b
        from itertools import combinations
        pair_counts: Dict[tuple, int] = {}
        for oid, g in orders.groupby("order_id"):
            ids = sorted(g["item_id"].unique().tolist())
            if len(ids) < 2:
                continue
            for a, b in combinations(ids, 2):
                pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1
        sorted_pairs = sorted(pair_counts.items(), key=lambda x: -x[1])
        out = []
        for (a, b), count in sorted_pairs[:top_n]:
            if count < min_pairs:
                continue
            out.append({
                "item_id_a": a,
                "item_id_b": b,
                "item_name_a": self._item_name(a),
                "item_name_b": self._item_name(b),
                "orders_together": int(count),
            })
        return out

    def generate_recommendations(self, item_id: Any, place_id: Optional[Any] = None) -> Dict[str, Any]:
        """Full recommendation block for one item."""
        daily = self.predict_demand(item_id, "daily", place_id=place_id)
        weekly = self.predict_demand(item_id, "weekly", place_id=place_id)
        reorder = self.calculate_reorder_point(item_id, place_id=place_id)
        return {
            "item_id": item_id,
            "item_name": self._item_name(item_id),
            "predicted_daily_demand": daily,
            "predicted_weekly_demand": weekly,
            "reorder_point": reorder,
            "status": "optimal" if daily > 0 else "no_history",
            "action": "prep_and_monitor" if daily > 0 else "collect_more_data",
        }
