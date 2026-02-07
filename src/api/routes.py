"""
API endpoints for Fresh Flow Insights: demand prediction, prep suggestions, top items, bundles.
"""

import os
from flask import Flask, request, jsonify
from typing import Dict, Any, Optional

# Lazy-loaded service (set by main or on first use)
_inventory_service: Optional[Any] = None


def get_inventory_service():
    """Create and cache InventoryService from data (lazy load). Returns None if data files missing (e.g. Vercel)."""
    global _inventory_service
    if _inventory_service is not None:
        return _inventory_service
    try:
        from src.models.data_loader import DataLoader
        from config.settings import DATA_DIR, MAX_MERGED_PARTS
        from src.services.inventory_service import InventoryService
        loader = DataLoader(DATA_DIR)
        demand = loader.get_demand_daily(max_parts=MAX_MERGED_PARTS)
        items = loader.load_sorted_most_ordered()
        orders = loader.get_orders_df(max_parts=MAX_MERGED_PARTS)
        orders = orders[["order_id", "item_id"]].drop_duplicates() if "order_id" in orders.columns else None
        from config.settings import PROJECT_ROOT
        models_path = os.path.join(PROJECT_ROOT, "models")
        _inventory_service = InventoryService(demand, items, orders_df=orders, model_artifacts_path=models_path)
        return _inventory_service
    except FileNotFoundError:
        _inventory_service = None
        return None


def set_inventory_service(service: Any) -> None:
    """Inject service (e.g. from main after loading data)."""
    global _inventory_service
    _inventory_service = service


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/api/health", methods=["GET"])
    def health_check() -> Dict[str, str]:
        return jsonify({"status": "healthy", "message": "Fresh Flow Insights API is running"})

    def _require_service():
        svc = get_inventory_service()
        if svc is None:
            return None, jsonify({
                "error": "Data not available",
                "message": "CSV data not deployed (e.g. Vercel). Run locally with data files for full API.",
            }), 503
        return svc, None

    @app.route("/api/inventory/predict", methods=["POST"])
    def predict_inventory() -> tuple:
        """
        Predict demand for an item. Body: { "item_id": 123, "period": "daily"|"weekly"|"monthly", "place_id": optional }
        """
        try:
            data = request.get_json() or {}
            item_id = data.get("item_id")
            period = data.get("period", "daily")
            place_id = data.get("place_id")
            if item_id is None:
                return jsonify({"error": "item_id is required"}), 400
            svc, err = _require_service()
            if err is not None:
                return err
            pred = svc.predict_demand(item_id, period=period, place_id=place_id)
            return jsonify({
                "item_id": item_id,
                "predicted_demand": pred,
                "period": period,
                "place_id": place_id,
                "unit": "quantity",
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/inventory/prep", methods=["GET", "POST"])
    def prep_suggestions() -> tuple:
        """
        Prep quantity suggestions. Query or body: place_id (optional), top_n (default 20), safety_factor (default 1.2).
        """
        try:
            data = request.get_json() if request.is_json else {}
            place_id = data.get("place_id") or request.args.get("place_id")
            top_n = int(data.get("top_n") or request.args.get("top_n") or 20)
            safety_factor = float(data.get("safety_factor") or request.args.get("safety_factor") or 1.2)
            svc, err = _require_service()
            if err is not None:
                return err
            suggestions = svc.get_prep_suggestions(place_id=place_id, top_n=top_n, safety_factor=safety_factor)
            return jsonify({"prep_suggestions": suggestions, "place_id": place_id}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/inventory/reorder/<item_id>", methods=["GET"])
    def reorder_point(item_id: str) -> tuple:
        """Reorder point for item. Query: lead_time_days (default 3), place_id (optional)."""
        try:
            lead_time_days = int(request.args.get("lead_time_days") or 3)
            place_id = request.args.get("place_id")
            svc, err = _require_service()
            if err is not None:
                return err
            point = svc.calculate_reorder_point(int(item_id), lead_time_days=lead_time_days, place_id=place_id)
            return jsonify({
                "item_id": int(item_id),
                "reorder_point": point,
                "lead_time_days": lead_time_days,
                "place_id": place_id,
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/demand/summary", methods=["GET"])
    def demand_summary() -> tuple:
        """Demand summary. Query: item_id, place_id, last_n_days (optional)."""
        try:
            item_id = request.args.get("item_id")
            place_id = request.args.get("place_id")
            last_n_days = request.args.get("last_n_days", type=int)
            if item_id is not None:
                item_id = int(item_id)
            svc, err = _require_service()
            if err is not None:
                return err
            summary = svc.get_demand_summary(item_id=item_id, place_id=place_id, last_n_days=last_n_days)
            return jsonify(summary), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/demand/history", methods=["GET"])
    def demand_history() -> tuple:
        """Daily demand totals for charts. Query: last_n_days (default 90)."""
        try:
            last_n_days = int(request.args.get("last_n_days") or 90)
            svc, err = _require_service()
            if err is not None:
                return err
            history = svc.get_demand_history(last_n_days=last_n_days)
            return jsonify({"history": history}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/items/top", methods=["GET"])
    def top_items() -> tuple:
        """Top items by popularity. Query: n (default 50), by=order_count|demand."""
        try:
            n = int(request.args.get("n") or 50)
            by = request.args.get("by") or "order_count"
            svc, err = _require_service()
            if err is not None:
                return err
            items = svc.get_top_items(n=n, by=by)
            return jsonify({"top_items": items, "by": by}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/bundles/suggestions", methods=["GET"])
    def bundle_suggestions() -> tuple:
        """Items often bought together. Query: min_pairs (default 50), top_n (default 10)."""
        try:
            min_pairs = int(request.args.get("min_pairs") or 50)
            top_n = int(request.args.get("top_n") or 10)
            svc, err = _require_service()
            if err is not None:
                return err
            bundles = svc.get_bundle_suggestions(min_pairs=min_pairs, top_n=top_n)
            return jsonify({"bundle_suggestions": bundles}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/inventory/recommendations/<item_id>", methods=["GET"])
    def recommendations(item_id: str) -> tuple:
        """Full recommendations for one item. Query: place_id (optional)."""
        try:
            place_id = request.args.get("place_id")
            svc, err = _require_service()
            if err is not None:
                return err
            rec = svc.generate_recommendations(int(item_id), place_id=place_id)
            return jsonify(rec), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


# For running this file directly (Flask dev server)
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
