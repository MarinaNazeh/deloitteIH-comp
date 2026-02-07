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
        Returns predictions from all models: linear_regression, random_forest, lightgbm, ensemble, plus moving_average.
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
            result = svc.predict_demand_detailed(item_id, period=period, place_id=place_id)
            return jsonify({
                "item_id": item_id,
                "period": period,
                "place_id": place_id,
                "unit": "quantity",
                # Individual model predictions
                "linear_regression": result["linear_regression"],
                "random_forest": result["random_forest"],
                "lightgbm": result["lightgbm"],
                "ensemble": result["ensemble"],
                "moving_average": result["moving_average"],
                # Keep backward compatibility
                "predicted_demand": result["ensemble"],
                # Additional context
                "total_historical_quantity": result["total_historical_quantity"],
                "data_points": result["data_points"],
                "method_used": result["method_used"],
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

    @app.route("/api/analytics/business", methods=["GET"])
    def business_analytics() -> tuple:
        """Business analytics: channel, order type, payment method, time patterns, revenue stats."""
        try:
            from config.settings import CACHE_DIR
            import json
            analytics_path = os.path.join(CACHE_DIR, "business_analytics.json")
            if os.path.isfile(analytics_path):
                with open(analytics_path) as f:
                    analytics = json.load(f)
                return jsonify(analytics), 200
            else:
                return jsonify({"error": "Business analytics not cached. Run scripts/build_cache.py first."}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/analytics/pnl", methods=["GET"])
    def pnl_analytics() -> tuple:
        """Profit & Loss analytics: margins, top/bottom performers, loss-making items."""
        try:
            from config.settings import CACHE_DIR
            import json
            pnl_path = os.path.join(CACHE_DIR, "pnl_analytics.json")
            if os.path.isfile(pnl_path):
                with open(pnl_path) as f:
                    pnl = json.load(f)
                return jsonify(pnl), 200
            else:
                return jsonify({"error": "P&L analytics not cached. Run scripts/build_cache.py first."}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/analytics/kpis", methods=["GET"])
    def kpis() -> tuple:
        """KPIs: waste avoided, stockouts prevented, revenue protected, efficiency metrics."""
        try:
            from config.settings import CACHE_DIR
            import json
            kpis_path = os.path.join(CACHE_DIR, "kpis.json")
            if os.path.isfile(kpis_path):
                with open(kpis_path) as f:
                    kpis_data = json.load(f)
                return jsonify(kpis_data), 200
            else:
                return jsonify({"error": "KPIs not cached. Run scripts/build_cache.py first."}), 404
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

    @app.route("/api/items/with-demand", methods=["GET"])
    def items_with_demand() -> tuple:
        """Items that have demand history (for prediction dropdown). Query: n (default 50)."""
        try:
            n = int(request.args.get("n") or 50)
            svc, err = _require_service()
            if err is not None:
                return err
            items = svc.get_items_with_demand(n=n)
            return jsonify({"items": items}), 200
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

    @app.route("/api/bundles/smart", methods=["GET", "POST"])
    def smart_bundles() -> tuple:
        """
        Smart bundle recommendations pairing best-sellers with slow-moving/near-expiry items.
        GET: Auto-generate bundles for slow-moving items.
        POST: Generate bundles for specific near-expiry items.
            Body: { "near_expiry_item_ids": [123, 456], "discount_pct": 15 }
        """
        try:
            svc, err = _require_service()
            if err is not None:
                return err
            
            if request.method == "POST":
                data = request.get_json() or {}
                near_expiry_ids = data.get("near_expiry_item_ids", [])
                discount_pct = float(data.get("discount_pct", 15)) / 100
                bundles = svc.generate_smart_bundles(
                    near_expiry_item_ids=near_expiry_ids,
                    discount_suggestion=discount_pct,
                )
            else:
                n_slow = int(request.args.get("n_slow_movers") or 20)
                discount_pct = float(request.args.get("discount_pct") or 15) / 100
                bundles = svc.generate_smart_bundles(
                    n_slow_movers=n_slow,
                    discount_suggestion=discount_pct,
                )
            
            return jsonify({"smart_bundles": bundles}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/items/slow-moving", methods=["GET"])
    def slow_moving_items() -> tuple:
        """Get slow-moving items (low sales velocity). Query: n (default 50), max_daily_avg (default 1.0)."""
        try:
            n = int(request.args.get("n") or 50)
            max_daily = float(request.args.get("max_daily_avg") or 1.0)
            svc, err = _require_service()
            if err is not None:
                return err
            items = svc.get_slow_moving_items(n=n, max_daily_avg=max_daily)
            return jsonify({"slow_moving_items": items}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/items/best-sellers", methods=["GET"])
    def best_sellers() -> tuple:
        """Get best-selling items by demand. Query: n (default 20)."""
        try:
            n = int(request.args.get("n") or 20)
            svc, err = _require_service()
            if err is not None:
                return err
            items = svc.get_best_sellers(n=n)
            return jsonify({"best_sellers": items}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/bundles/surprise-bags", methods=["GET", "POST"])
    def surprise_bags() -> tuple:
        """
        Generate Surprise Bag recommendations for clearing multiple items at once.
        GET: Auto-generate for slow-moving items.
        POST: Generate for specific near-expiry items.
            Body: { 
                "item_ids": [123, 456, ...], 
                "discount_pct": 50,
                "fixed_prices": {"small": 29, "medium": 49, "large": 79}  // optional
            }
        """
        try:
            svc, err = _require_service()
            if err is not None:
                return err
            
            if request.method == "POST":
                data = request.get_json() or {}
                item_ids = data.get("item_ids", [])
                discount_pct = float(data.get("discount_pct", 50)) / 100
                fixed_prices = data.get("fixed_prices")
                result = svc.generate_surprise_bags(
                    item_ids=item_ids if item_ids else None,
                    base_discount=discount_pct,
                    fixed_prices=fixed_prices,
                )
            else:
                n_slow = int(request.args.get("n_slow_movers") or 30)
                discount_pct = float(request.args.get("discount_pct") or 50) / 100
                result = svc.generate_surprise_bags(
                    n_slow_movers=n_slow,
                    base_discount=discount_pct,
                )
            
            return jsonify(result), 200
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

    # ===== Chatbot Endpoints =====
    _chatbot = None
    
    def get_chatbot():
        nonlocal _chatbot
        if _chatbot is None:
            from src.services.chatbot_service import InventoryChatbot
            _chatbot = InventoryChatbot()
        return _chatbot

    @app.route("/api/chat", methods=["POST"])
    def chat() -> tuple:
        """
        Chat with the inventory assistant.
        Body: { "message": "What is the best selling item?", "history": [...] }
        """
        try:
            data = request.get_json() or {}
            message = data.get("message", "")
            history = data.get("history", [])
            
            if not message.strip():
                return jsonify({"error": "Message is required"}), 400
            
            chatbot = get_chatbot()
            response = chatbot.chat(message, conversation_history=history)
            
            return jsonify({
                "response": response,
                "message": message,
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat/quick-answers", methods=["GET"])
    def quick_answers() -> tuple:
        """Get quick answers for common questions without calling the LLM."""
        try:
            chatbot = get_chatbot()
            answers = chatbot.get_quick_answers()
            return jsonify({"quick_answers": answers}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


# For running this file directly (Flask dev server)
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
