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
        result = self.predict_demand_detailed(item_id, period, place_id, window_days)
        return result["ensemble"]

    def predict_demand_detailed(
        self,
        item_id: Any,
        period: str = "daily",
        place_id: Optional[Any] = None,
        window_days: int = 14,
    ) -> Dict[str, Any]:
        """
        Detailed demand predictions with all model outputs.
        Returns dict with: linear_regression, random_forest, lightgbm, ensemble, moving_average,
                          total_historical_quantity, data_points, method_used.
        """
        item_id = int(item_id)
        df = self.demand_daily[self.demand_daily["item_id"] == item_id].copy()
        if place_id is not None and "place_id" in df.columns:
            df = df[df["place_id"] == place_id]
        
        # Period multiplier
        multiplier = 1
        if period == "weekly":
            multiplier = 7
        elif period == "monthly":
            multiplier = 30
        
        # Calculate historical stats
        total_qty = int(df["quantity"].sum()) if not df.empty else 0
        data_points = len(df)
        
        if df.empty:
            return {
                "linear_regression": 0.0,
                "random_forest": 0.0,
                "lightgbm": 0.0,
                "ensemble": 0.0,
                "moving_average": 0.0,
                "total_historical_quantity": 0,
                "data_points": 0,
                "method_used": "no_data",
            }

        # Calculate moving average (always available as fallback/comparison)
        df_sorted = df.sort_values("date").tail(window_days)
        daily_avg = df_sorted["quantity"].mean()
        moving_avg = round(float(daily_avg * multiplier), 2)

        # Try ML models
        if self._model_artifacts is not None:
            preds = self._predict_demand_all_models(item_id, df)
            if preds is not None:
                return {
                    "linear_regression": round(float(preds["linear_regression"] * multiplier), 2),
                    "random_forest": round(float(preds["random_forest"] * multiplier), 2),
                    "lightgbm": round(float(preds["lightgbm"] * multiplier), 2),
                    "ensemble": round(float(preds["ensemble"] * multiplier), 2),
                    "moving_average": moving_avg,
                    "total_historical_quantity": total_qty,
                    "data_points": data_points,
                    "method_used": "ml_models",
                }

        # Fallback to moving average only
        return {
            "linear_regression": moving_avg,
            "random_forest": moving_avg,
            "lightgbm": moving_avg,
            "ensemble": moving_avg,
            "moving_average": moving_avg,
            "total_historical_quantity": total_qty,
            "data_points": data_points,
            "method_used": "moving_average",
        }

    def _predict_demand_ensemble(self, item_id: int, item_demand_df: pd.DataFrame) -> Optional[float]:
        """Use trained ensemble to predict next-day demand for this item."""
        preds = self._predict_demand_all_models(item_id, item_demand_df)
        if preds is None:
            return None
        return preds.get("ensemble")

    def _predict_demand_all_models(self, item_id: int, item_demand_df: pd.DataFrame) -> Optional[Dict[str, float]]:
        """Use all trained models to predict next-day demand. Returns dict with each model's prediction."""
        from src.models.feature_engineering import build_feature_row_for_prediction
        from src.models.demand_models import predict_all_models
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
        preds = predict_all_models(feature_row, self._model_artifacts)
        return {
            "linear_regression": float(preds["linear_regression"][0]),
            "random_forest": float(preds["random_forest"][0]),
            "lightgbm": float(preds["lightgbm"][0]),
            "ensemble": float(preds["ensemble"][0]),
        }

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

    def get_items_with_demand(self, n: int = 50) -> List[Dict[str, Any]]:
        """Top N items that have demand data (for prediction dropdown). Sorted by total quantity."""
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

    def get_slow_moving_items(self, n: int = 50, max_daily_avg: float = 1.0) -> List[Dict[str, Any]]:
        """
        Get slow-moving items (low sales velocity). These are candidates for bundling/clearance.
        Returns items with average daily demand <= max_daily_avg.
        """
        # Calculate average daily demand per item
        df = self.demand_daily.copy()
        df["date"] = pd.to_datetime(df["date"])
        
        # Get date range for each item and total quantity
        item_stats = df.groupby("item_id").agg({
            "quantity": "sum",
            "date": ["min", "max", "count"]
        })
        item_stats.columns = ["total_qty", "first_sale", "last_sale", "sale_days"]
        item_stats = item_stats.reset_index()
        
        # Calculate days in range and avg daily demand
        item_stats["days_range"] = (item_stats["last_sale"] - item_stats["first_sale"]).dt.days + 1
        item_stats["avg_daily"] = item_stats["total_qty"] / item_stats["days_range"].clip(lower=1)
        
        # Filter slow movers
        slow = item_stats[item_stats["avg_daily"] <= max_daily_avg].nsmallest(n, "avg_daily")
        
        return [
            {
                "item_id": int(r["item_id"]),
                "item_name": self._item_name(r["item_id"]),
                "total_quantity": int(r["total_qty"]),
                "sale_days": int(r["sale_days"]),
                "avg_daily_demand": round(float(r["avg_daily"]), 3),
                "status": "slow_moving",
            }
            for _, r in slow.iterrows()
        ]

    def get_best_sellers(self, n: int = 20) -> List[Dict[str, Any]]:
        """
        Get best-selling items by total quantity in demand data.
        """
        agg = self.demand_daily.groupby("item_id", as_index=False)["quantity"].sum()
        top = agg.nlargest(n, "quantity")
        
        return [
            {
                "item_id": int(r["item_id"]),
                "item_name": self._item_name(r["item_id"]),
                "total_quantity": int(r["quantity"]),
                "status": "best_seller",
            }
            for _, r in top.iterrows()
        ]

    def generate_smart_bundles(
        self,
        near_expiry_item_ids: Optional[List[int]] = None,
        n_best_sellers: int = 10,
        n_slow_movers: int = 20,
        bundles_per_item: int = 3,
        discount_suggestion: float = 0.15,
    ) -> List[Dict[str, Any]]:
        """
        Generate smart bundle recommendations pairing best-sellers with near-expiry/slow-moving items.
        
        Strategy:
        - Pair each slow-moving or near-expiry item with top best-sellers
        - Suggest a discount to incentivize the bundle purchase
        - Prioritize items that have been bought together before (if data available)
        
        Args:
            near_expiry_item_ids: List of item IDs that are near expiry (manual input)
            n_best_sellers: Number of top best-sellers to consider for pairing
            n_slow_movers: Number of slow-moving items to include if no near_expiry provided
            bundles_per_item: How many bundle suggestions per slow-moving item
            discount_suggestion: Suggested discount percentage (e.g., 0.15 = 15%)
        
        Returns:
            List of bundle suggestions with best-seller + slow-mover pairs
        """
        # Get best sellers
        best_sellers = self.get_best_sellers(n=n_best_sellers)
        best_seller_ids = {item["item_id"] for item in best_sellers}
        
        # Get items to clear (near-expiry or slow-moving)
        items_to_clear = []
        if near_expiry_item_ids:
            for item_id in near_expiry_item_ids:
                item_id = int(item_id)
                if item_id in best_seller_ids:
                    continue  # Don't bundle best-sellers with themselves
                items_to_clear.append({
                    "item_id": item_id,
                    "item_name": self._item_name(item_id),
                    "reason": "near_expiry",
                })
        else:
            slow_movers = self.get_slow_moving_items(n=n_slow_movers)
            for item in slow_movers:
                if item["item_id"] in best_seller_ids:
                    continue
                item["reason"] = "slow_moving"
                items_to_clear.append(item)
        
        # Build co-purchase data for smarter pairing
        copurchase_scores: Dict[tuple, int] = {}
        if self.orders_df is not None and "order_id" in self.orders_df.columns:
            orders = self.orders_df[["order_id", "item_id"]].drop_duplicates()
            orders["item_id"] = orders["item_id"].astype(int)
            from itertools import combinations
            for oid, g in orders.groupby("order_id"):
                ids = g["item_id"].unique().tolist()
                if len(ids) < 2:
                    continue
                for a, b in combinations(ids, 2):
                    key = tuple(sorted([a, b]))
                    copurchase_scores[key] = copurchase_scores.get(key, 0) + 1
        
        # Generate bundles
        bundles = []
        for clear_item in items_to_clear:
            clear_id = clear_item["item_id"]
            clear_name = clear_item["item_name"]
            clear_reason = clear_item.get("reason", "slow_moving")
            
            # Score best-sellers by co-purchase history with this item
            seller_scores = []
            for seller in best_sellers:
                seller_id = seller["item_id"]
                key = tuple(sorted([clear_id, seller_id]))
                copurchase = copurchase_scores.get(key, 0)
                # Score = co-purchase count + base popularity
                score = copurchase * 10 + seller["total_quantity"] / 100
                seller_scores.append((seller, score, copurchase))
            
            # Sort by score (best pairing first)
            seller_scores.sort(key=lambda x: -x[1])
            
            # Create bundle suggestions
            for i, (seller, score, copurchase) in enumerate(seller_scores[:bundles_per_item]):
                bundle = {
                    "bundle_id": f"B{len(bundles)+1:03d}",
                    "best_seller": {
                        "item_id": seller["item_id"],
                        "item_name": seller["item_name"],
                        "total_sales": seller["total_quantity"],
                    },
                    "item_to_clear": {
                        "item_id": clear_id,
                        "item_name": clear_name,
                        "reason": clear_reason,
                    },
                    "copurchase_history": copurchase,
                    "pairing_score": round(score, 2),
                    "suggested_discount_pct": int(discount_suggestion * 100),
                    "recommendation": self._get_bundle_recommendation(copurchase, clear_reason),
                }
                bundles.append(bundle)
        
        # Sort all bundles by pairing score
        bundles.sort(key=lambda x: -x["pairing_score"])
        
        return bundles

    def _get_bundle_recommendation(self, copurchase: int, reason: str) -> str:
        """Generate a human-readable recommendation for the bundle."""
        if copurchase > 10:
            strength = "Strong pairing"
            rationale = f"These items have been purchased together {copurchase} times before."
        elif copurchase > 0:
            strength = "Good pairing"
            rationale = f"These items have been purchased together {copurchase} times."
        else:
            strength = "Strategic pairing"
            rationale = "Pairing based on complementary popularity."
        
        if reason == "near_expiry":
            action = "Offer this bundle with a discount to clear near-expiry stock quickly."
        else:
            action = "Offer this bundle to boost sales of slow-moving inventory."
        
        return f"{strength}: {rationale} {action}"

    def generate_surprise_bags(
        self,
        item_ids: Optional[List[int]] = None,
        n_slow_movers: int = 30,
        bag_sizes: Optional[List[str]] = None,
        base_discount: float = 0.50,
        fixed_prices: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Surprise Bag recommendations for clearing multiple near-expiry/slow-moving items.
        
        Surprise Bags contain random items at a fixed low price - customer doesn't know exact contents.
        Perfect for clearing many items at once while reducing food waste.
        
        Args:
            item_ids: Specific item IDs to include (near-expiry items). If None, uses slow-movers.
            n_slow_movers: Number of slow-moving items to consider if item_ids not provided.
            bag_sizes: List of bag sizes to generate. Default: ["small", "medium", "large"]
            base_discount: Base discount percentage (e.g., 0.50 = 50% off)
            fixed_prices: Optional dict of fixed prices per size. E.g., {"small": 29, "medium": 49, "large": 79}
        
        Returns:
            Dict with surprise bag configurations and item assignments.
        """
        bag_sizes = bag_sizes or ["small", "medium", "large"]
        
        # Default fixed prices (in local currency units)
        if fixed_prices is None:
            fixed_prices = {
                "small": 29.0,    # ~3-4 items
                "medium": 49.0,   # ~5-7 items
                "large": 79.0,    # ~8-12 items
            }
        
        # Get items to clear
        items_to_clear = []
        if item_ids:
            for item_id in item_ids:
                item_id = int(item_id)
                items_to_clear.append({
                    "item_id": item_id,
                    "item_name": self._item_name(item_id),
                    "reason": "near_expiry",
                })
        else:
            slow_movers = self.get_slow_moving_items(n=n_slow_movers)
            for item in slow_movers:
                item["reason"] = "slow_moving"
                items_to_clear.append(item)
        
        total_items = len(items_to_clear)
        
        # Determine if we should recommend surprise bags
        # Threshold: if more than 5 items to clear, surprise bags make sense
        min_items_for_surprise_bag = 5
        recommend_surprise_bags = total_items >= min_items_for_surprise_bag
        
        # Bag configurations
        bag_configs = {
            "small": {"min_items": 3, "max_items": 4, "variety_score": "low"},
            "medium": {"min_items": 5, "max_items": 7, "variety_score": "medium"},
            "large": {"min_items": 8, "max_items": 12, "variety_score": "high"},
        }
        
        # Generate bag recommendations
        bags = []
        for size in bag_sizes:
            config = bag_configs.get(size, bag_configs["medium"])
            price = fixed_prices.get(size, 49.0)
            
            # Calculate how many bags of this size we can make
            min_items = config["min_items"]
            max_items = config["max_items"]
            
            if total_items < min_items:
                continue
            
            # Estimate potential bags
            avg_items_per_bag = (min_items + max_items) // 2
            potential_bags = total_items // avg_items_per_bag
            
            # Sample items for example bag contents (randomize in production)
            sample_items = items_to_clear[:max_items]
            
            bag = {
                "bag_id": f"SB-{size.upper()[:1]}{len(bags)+1:02d}",
                "size": size,
                "fixed_price": price,
                "discount_percentage": int(base_discount * 100),
                "items_per_bag": {
                    "min": min_items,
                    "max": max_items,
                },
                "potential_bags_available": potential_bags,
                "variety_score": config["variety_score"],
                "sample_contents": [
                    {"item_id": item["item_id"], "item_name": item["item_name"]}
                    for item in sample_items
                ],
                "marketing_copy": self._get_surprise_bag_copy(size, price, base_discount),
            }
            bags.append(bag)
        
        # Calculate statistics
        result = {
            "recommend_surprise_bags": recommend_surprise_bags,
            "total_items_to_clear": total_items,
            "min_items_threshold": min_items_for_surprise_bag,
            "reason": "near_expiry" if item_ids else "slow_moving",
            "bags": bags,
            "all_items_to_clear": [
                {"item_id": item["item_id"], "item_name": item["item_name"], "reason": item.get("reason", "unknown")}
                for item in items_to_clear
            ],
            "sustainability_impact": {
                "potential_items_saved": total_items,
                "waste_reduction_message": f"By selling surprise bags, you could save up to {total_items} items from going to waste!",
            },
            "tips": [
                "Keep bag contents a mystery - customers love the surprise element!",
                "Maintain consistent quality - always include at least one popular item if possible",
                "Set a daily limit on bags to create urgency",
                "Promote on social media with photos of happy customers",
                "Partner with apps like Too Good To Go for wider reach",
            ],
        }
        
        return result

    def _get_surprise_bag_copy(self, size: str, price: float, discount: float) -> str:
        """Generate marketing copy for surprise bags."""
        discount_pct = int(discount * 100)
        
        copies = {
            "small": f"🎁 **Small Surprise Bag** - Just {price:.0f}! Perfect for a quick snack or trying something new. Save {discount_pct}% while helping reduce food waste!",
            "medium": f"🎁 **Medium Surprise Bag** - Only {price:.0f}! Great value with a variety of treats. Save {discount_pct}% and be a food waste hero!",
            "large": f"🎁 **Large Surprise Bag** - Amazing deal at {price:.0f}! Feed the whole family with this mystery selection. Save {discount_pct}% and make a big impact!",
        }
        
        return copies.get(size, f"🎁 **Surprise Bag ({size})** - {price:.0f}! Save {discount_pct}% while reducing food waste!")

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
