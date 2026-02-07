"""
Precompute all data and save to cache/ so the API and UI load instantly.
Run once after putting CSVs in data/:  python scripts/build_cache.py
Then run the API and Streamlit; they will use cache/ only.
"""
import os
import sys
import json
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config.settings import DATA_DIR, CACHE_DIR, MAX_MERGED_PARTS
from src.models.data_loader import DataLoader


def compute_pnl_analytics(orders_df: pd.DataFrame) -> dict:
    """Compute Profit & Loss analytics from orders data."""
    pnl = {}
    
    # Ensure we have required columns
    if "price" not in orders_df.columns:
        return pnl
    
    # Clean data - ensure numeric
    orders_df = orders_df.copy()
    orders_df["price"] = pd.to_numeric(orders_df["price"], errors="coerce").fillna(0)
    orders_df["quantity"] = pd.to_numeric(orders_df["quantity"], errors="coerce").fillna(0)
    
    # Since the cost column in this dataset doesn't represent actual product cost,
    # we'll estimate margins based on typical food/retail industry standards:
    # - High-volume items: ~35% margin (competitive pricing)
    # - Low-volume items: ~45% margin (premium pricing)
    # - Average: ~40% margin
    
    orders_df["revenue"] = orders_df["price"] * orders_df["quantity"]
    
    # Estimate cost based on typical industry margins
    # We'll use variable margins based on price tiers
    def estimate_margin(price):
        if price <= 30:
            return 0.30  # Lower margin on cheap items
        elif price <= 100:
            return 0.40  # Average margin
        elif price <= 200:
            return 0.45  # Higher margin on mid-tier
        else:
            return 0.50  # Premium items have higher margins
    
    orders_df["estimated_margin"] = orders_df["price"].apply(estimate_margin)
    orders_df["estimated_cost"] = orders_df["price"] * (1 - orders_df["estimated_margin"])
    orders_df["total_cost"] = orders_df["estimated_cost"] * orders_df["quantity"]
    orders_df["profit"] = orders_df["revenue"] - orders_df["total_cost"]
    orders_df["margin_pct"] = orders_df["estimated_margin"] * 100
    
    # Overall P&L
    total_revenue = float(orders_df["revenue"].sum())
    total_cost = float(orders_df["total_cost"].sum())
    total_profit = float(orders_df["profit"].sum())
    avg_margin = float(orders_df["margin_pct"].mean())
    
    pnl["overall"] = {
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "profit_margin_pct": (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
        "avg_item_margin_pct": avg_margin,
    }
    
    # Per-item P&L analysis
    if "item_id" in orders_df.columns and "title" in orders_df.columns:
        item_pnl = orders_df.groupby(["item_id", "title"]).agg({
            "quantity": "sum",
            "revenue": "sum",
            "total_cost": "sum",
            "profit": "sum",
            "price": "mean",
            "estimated_margin": "mean",
        }).reset_index()
        
        item_pnl["margin_pct"] = item_pnl["estimated_margin"] * 100
        
        # Top profitable items
        top_profit = item_pnl.nlargest(20, "profit")
        pnl["top_profitable_items"] = [
            {
                "item_id": int(row["item_id"]),
                "title": str(row["title"])[:50],
                "quantity_sold": int(row["quantity"]),
                "revenue": float(row["revenue"]),
                "cost": float(row["total_cost"]),
                "profit": float(row["profit"]),
                "margin_pct": float(row["margin_pct"]),
            }
            for _, row in top_profit.iterrows()
        ]
        
        # Lowest margin items (potential problems)
        low_margin = item_pnl[item_pnl["quantity"] > 5].nsmallest(20, "margin_pct")
        pnl["low_margin_items"] = [
            {
                "item_id": int(row["item_id"]),
                "title": str(row["title"])[:50],
                "quantity_sold": int(row["quantity"]),
                "revenue": float(row["revenue"]),
                "cost": float(row["total_cost"]),
                "profit": float(row["profit"]),
                "margin_pct": float(row["margin_pct"]),
            }
            for _, row in low_margin.iterrows()
        ]
        
        # High margin items (stars)
        high_margin = item_pnl[item_pnl["quantity"] > 5].nlargest(20, "margin_pct")
        pnl["high_margin_items"] = [
            {
                "item_id": int(row["item_id"]),
                "title": str(row["title"])[:50],
                "quantity_sold": int(row["quantity"]),
                "revenue": float(row["revenue"]),
                "cost": float(row["total_cost"]),
                "profit": float(row["profit"]),
                "margin_pct": float(row["margin_pct"]),
            }
            for _, row in high_margin.iterrows()
        ]
        
        # Loss-making items
        loss_items = item_pnl[item_pnl["profit"] < 0].nsmallest(20, "profit")
        pnl["loss_making_items"] = [
            {
                "item_id": int(row["item_id"]),
                "title": str(row["title"])[:50],
                "quantity_sold": int(row["quantity"]),
                "revenue": float(row["revenue"]),
                "cost": float(row["total_cost"]),
                "profit": float(row["profit"]),
                "margin_pct": float(row["margin_pct"]),
            }
            for _, row in loss_items.iterrows()
        ]
        
        # Margin distribution
        margin_bins = [float('-inf'), 0, 10, 20, 30, 50, float('inf')]
        margin_labels = ["Negative", "0-10%", "10-20%", "20-30%", "30-50%", "50%+"]
        item_pnl["margin_category"] = pd.cut(item_pnl["margin_pct"], bins=margin_bins, labels=margin_labels)
        margin_dist = item_pnl.groupby("margin_category", observed=True).size().to_dict()
        pnl["margin_distribution"] = {str(k): int(v) for k, v in margin_dist.items()}
    
    return pnl


def compute_kpis(orders_df: pd.DataFrame, demand_df: pd.DataFrame) -> dict:
    """Compute KPIs for waste avoided, stockouts prevented, etc."""
    kpis = {}
    
    orders_df = orders_df.copy()
    orders_df["price"] = pd.to_numeric(orders_df["price"], errors="coerce").fillna(0)
    orders_df["cost"] = pd.to_numeric(orders_df["cost"], errors="coerce").fillna(0)
    orders_df["quantity"] = pd.to_numeric(orders_df["quantity"], errors="coerce").fillna(0)
    
    # --- Estimated Waste Metrics ---
    # Identify slow-moving items (avg daily demand < 1)
    if "item_id" in demand_df.columns and "quantity" in demand_df.columns:
        item_stats = demand_df.groupby("item_id").agg({
            "quantity": ["sum", "count"]
        }).reset_index()
        item_stats.columns = ["item_id", "total_qty", "sale_days"]
        
        # Calculate avg daily demand based on each item's active selling days
        # This is more realistic than total dataset days
        item_stats["avg_daily_demand"] = item_stats["total_qty"] / item_stats["sale_days"].clip(lower=1)
        
        # Categorize items based on percentiles for relative performance
        qty_median = item_stats["total_qty"].median()
        qty_25 = item_stats["total_qty"].quantile(0.25)
        qty_75 = item_stats["total_qty"].quantile(0.75)
        
        # Critical: bottom 25% by total quantity
        # Moderate: between 25th and 50th percentile
        # Healthy: above median
        slow_movers = item_stats[item_stats["total_qty"] <= qty_25]
        moderate_slow = item_stats[(item_stats["total_qty"] > qty_25) & (item_stats["total_qty"] <= qty_median)]
        healthy_items = item_stats[item_stats["total_qty"] > qty_median]
        
        # Calculate waste risk
        # Assume slow movers have 30% waste risk, moderate have 15% waste risk
        slow_waste_units = int(slow_movers["total_qty"].sum() * 0.30)
        moderate_waste_units = int(moderate_slow["total_qty"].sum() * 0.15)
        
        kpis["waste_risk"] = {
            "critical_items_count": int(len(slow_movers)),
            "moderate_risk_items_count": int(len(moderate_slow)),
            "healthy_items_count": int(len(healthy_items)),
            "estimated_waste_units": slow_waste_units + moderate_waste_units,
            "waste_at_risk_revenue": 0,  # Will calculate below
        }
        
        # Calculate revenue at risk
        if "item_id" in orders_df.columns:
            slow_item_ids = slow_movers["item_id"].tolist()
            slow_orders = orders_df[orders_df["item_id"].isin(slow_item_ids)]
            if len(slow_orders) > 0:
                avg_price = slow_orders["price"].mean()
                kpis["waste_risk"]["waste_at_risk_revenue"] = float(slow_waste_units * avg_price)
    
    # --- Estimated Waste Avoided (if recommendations are followed) ---
    # Assume bundles/surprise bags can save 60% of at-risk inventory
    waste_units = kpis.get("waste_risk", {}).get("estimated_waste_units", 0)
    waste_revenue = kpis.get("waste_risk", {}).get("waste_at_risk_revenue", 0)
    
    kpis["waste_avoided"] = {
        "units_saved": int(waste_units * 0.60),
        "revenue_protected": float(waste_revenue * 0.60),
    }
    
    # --- Stockout Prevention ---
    # Identify items with erratic demand (high variance) - prone to stockouts
    if "item_id" in demand_df.columns:
        item_variance = demand_df.groupby("item_id")["quantity"].agg(["mean", "std", "count"]).reset_index()
        item_variance.columns = ["item_id", "mean_demand", "std_demand", "data_points"]
        item_variance["cv"] = (item_variance["std_demand"] / item_variance["mean_demand"]).fillna(0)
        
        # High variance items (CV > 1) are stockout risks
        high_variance = item_variance[item_variance["cv"] > 1]
        
        kpis["stockout_risk"] = {
            "high_variance_items_count": int(len(high_variance)),
            "stockouts_prevented_estimate": int(len(high_variance) * 0.5),  # Assume forecasting prevents 50%
        }
    
    # --- Inventory Efficiency ---
    total_items = demand_df["item_id"].nunique() if "item_id" in demand_df.columns else 0
    critical = kpis.get("waste_risk", {}).get("critical_items_count", 0)
    moderate = kpis.get("waste_risk", {}).get("moderate_risk_items_count", 0)
    healthy_count = kpis.get("waste_risk", {}).get("healthy_items_count", total_items - critical - moderate)
    
    kpis["inventory_efficiency"] = {
        "total_items": total_items,
        "healthy_items": healthy_count,
        "efficiency_pct": float(healthy_count / total_items * 100) if total_items > 0 else 0,
        "improvement_potential_pct": 15.0,  # Estimated improvement from using the system
    }
    
    # --- High Risk Items Summary ---
    kpis["high_risk_summary"] = {
        "critical_count": kpis.get("waste_risk", {}).get("critical_items_count", 0),
        "moderate_count": kpis.get("waste_risk", {}).get("moderate_risk_items_count", 0),
        "total_at_risk": kpis.get("waste_risk", {}).get("critical_items_count", 0) + kpis.get("waste_risk", {}).get("moderate_risk_items_count", 0),
    }
    
    # --- Revenue Protected ---
    total_revenue = float(orders_df["price"].sum() * orders_df["quantity"].sum()) if len(orders_df) > 0 else 0
    kpis["revenue_impact"] = {
        "total_revenue_base": float((orders_df["price"] * orders_df["quantity"]).sum()) if len(orders_df) > 0 else 0,
        "revenue_protected": kpis.get("waste_avoided", {}).get("revenue_protected", 0),
        "potential_additional_revenue": kpis.get("waste_avoided", {}).get("revenue_protected", 0) * 0.3,  # Additional from better forecasting
    }
    
    return kpis


def compute_business_analytics(orders_df: pd.DataFrame) -> dict:
    """Compute business analytics from orders data."""
    analytics = {}
    
    # Channel analysis (App vs Web)
    if "channel" in orders_df.columns:
        channel_counts = orders_df["channel"].value_counts().to_dict()
        channel_revenue = orders_df.groupby("channel")["total_amount"].sum().to_dict() if "total_amount" in orders_df.columns else {}
        channel_qty = orders_df.groupby("channel")["quantity"].sum().to_dict()
        total_orders = len(orders_df["order_id"].unique()) if "order_id" in orders_df.columns else len(orders_df)
        
        analytics["channel"] = {
            "counts": {str(k): int(v) for k, v in channel_counts.items()},
            "revenue": {str(k): float(v) for k, v in channel_revenue.items()},
            "quantity": {str(k): int(v) for k, v in channel_qty.items()},
            "dominant": str(max(channel_counts, key=channel_counts.get)) if channel_counts else None,
        }
    
    # Order type analysis (Takeaway, Eat In, Delivery)
    if "type" in orders_df.columns:
        type_counts = orders_df["type"].value_counts().to_dict()
        type_revenue = orders_df.groupby("type")["total_amount"].sum().to_dict() if "total_amount" in orders_df.columns else {}
        type_qty = orders_df.groupby("type")["quantity"].sum().to_dict()
        
        analytics["order_type"] = {
            "counts": {str(k): int(v) for k, v in type_counts.items()},
            "revenue": {str(k): float(v) for k, v in type_revenue.items()},
            "quantity": {str(k): int(v) for k, v in type_qty.items()},
            "dominant": str(max(type_counts, key=type_counts.get)) if type_counts else None,
        }
    
    # Payment method analysis
    if "payment_method" in orders_df.columns:
        payment_counts = orders_df["payment_method"].value_counts().to_dict()
        payment_revenue = orders_df.groupby("payment_method")["total_amount"].sum().to_dict() if "total_amount" in orders_df.columns else {}
        
        analytics["payment_method"] = {
            "counts": {str(k): int(v) for k, v in payment_counts.items()},
            "revenue": {str(k): float(v) for k, v in payment_revenue.items()},
            "dominant": str(max(payment_counts, key=payment_counts.get)) if payment_counts else None,
        }
    
    # Source analysis (Cashier, QR code, Customer app, Link)
    if "source" in orders_df.columns:
        source_counts = orders_df["source"].value_counts().to_dict()
        source_revenue = orders_df.groupby("source")["total_amount"].sum().to_dict() if "total_amount" in orders_df.columns else {}
        
        analytics["source"] = {
            "counts": {str(k): int(v) for k, v in source_counts.items()},
            "revenue": {str(k): float(v) for k, v in source_revenue.items()},
            "dominant": str(max(source_counts, key=source_counts.get)) if source_counts else None,
        }
    
    # Time-based analysis
    if "order_date" in orders_df.columns:
        orders_df["hour"] = orders_df["order_date"].dt.hour
        orders_df["day_of_week"] = orders_df["order_date"].dt.dayofweek
        orders_df["month"] = orders_df["order_date"].dt.month
        
        # Hourly distribution
        hourly = orders_df.groupby("hour")["quantity"].sum().to_dict()
        analytics["hourly_distribution"] = {int(k): int(v) for k, v in hourly.items()}
        
        # Peak hour
        if hourly:
            peak_hour = max(hourly, key=hourly.get)
            analytics["peak_hour"] = int(peak_hour)
        
        # Day of week distribution (0=Monday, 6=Sunday)
        daily = orders_df.groupby("day_of_week")["quantity"].sum().to_dict()
        day_names = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
        analytics["day_of_week_distribution"] = {day_names.get(int(k), str(k)): int(v) for k, v in daily.items()}
        
        # Peak day
        if daily:
            peak_day = max(daily, key=daily.get)
            analytics["peak_day"] = day_names.get(int(peak_day), str(peak_day))
        
        # Monthly trends
        monthly = orders_df.groupby("month")["quantity"].sum().to_dict()
        month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 
                       7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
        analytics["monthly_distribution"] = {month_names.get(int(k), str(k)): int(v) for k, v in monthly.items()}
    
    # Revenue statistics
    if "total_amount" in orders_df.columns:
        analytics["revenue_stats"] = {
            "total": float(orders_df["total_amount"].sum()),
            "average_order": float(orders_df.groupby("order_id")["total_amount"].first().mean()) if "order_id" in orders_df.columns else 0,
            "max_order": float(orders_df.groupby("order_id")["total_amount"].first().max()) if "order_id" in orders_df.columns else 0,
        }
    
    # Order statistics
    if "order_id" in orders_df.columns:
        unique_orders = orders_df["order_id"].nunique()
        analytics["order_stats"] = {
            "total_orders": int(unique_orders),
            "avg_items_per_order": float(len(orders_df) / unique_orders) if unique_orders > 0 else 0,
        }
    
    return analytics


def main():
    print("Building cache from data/ ...")
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Clear existing cache to force fresh load from raw data
    import shutil
    for f in ["demand_daily.csv", "items.csv", "order_items.csv", "summary.json", "demand_history.json", "business_analytics.json", "pnl_analytics.json", "kpis.json"]:
        fpath = os.path.join(CACHE_DIR, f)
        if os.path.exists(fpath):
            os.remove(fpath)
            print(f"  Removed old {f}")

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

    # Business analytics
    print("  Computing business analytics...")
    analytics = compute_business_analytics(orders_df)
    print("  Writing cache/business_analytics.json ...")
    with open(os.path.join(CACHE_DIR, "business_analytics.json"), "w") as f:
        json.dump(analytics, f, indent=2)

    # P&L analytics
    print("  Computing P&L analytics...")
    pnl = compute_pnl_analytics(orders_df)
    print("  Writing cache/pnl_analytics.json ...")
    with open(os.path.join(CACHE_DIR, "pnl_analytics.json"), "w") as f:
        json.dump(pnl, f, indent=2)

    # KPIs
    print("  Computing KPIs...")
    kpis = compute_kpis(orders_df, demand_daily)
    print("  Writing cache/kpis.json ...")
    with open(os.path.join(CACHE_DIR, "kpis.json"), "w") as f:
        json.dump(kpis, f, indent=2)

    print("Done. Cache is in", CACHE_DIR)
    print("You can now run the API and UI; they will use the cache and start fast.")


if __name__ == "__main__":
    main()
