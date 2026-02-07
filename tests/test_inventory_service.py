"""
Tests for InventoryService using mock demand and items data.
Run from project root: pytest tests/ -v
"""

import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.inventory_service import InventoryService


@pytest.fixture
def demand_daily():
    """Mock daily demand: date, item_id, quantity."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-01", "2024-01-02"]),
        "item_id": [100, 100, 100, 200, 200],
        "quantity": [10, 12, 11, 3, 5],
    })


@pytest.fixture
def items_df():
    """Mock sorted_most_ordered."""
    return pd.DataFrame({
        "item_id": [100, 200],
        "item_name": ["Item A", "Item B"],
        "order_count": [1000, 100],
    })


class TestInventoryService:
    def test_predict_demand_daily(self, demand_daily, items_df):
        svc = InventoryService(demand_daily, items_df)
        pred = svc.predict_demand(100, period="daily")
        assert pred > 0
        assert pred == pytest.approx(11.0, rel=0.5)  # avg of 10,12,11

    def test_predict_demand_weekly(self, demand_daily, items_df):
        svc = InventoryService(demand_daily, items_df)
        pred = svc.predict_demand(100, period="weekly")
        assert pred >= 7 * 10  # at least 7 * daily

    def test_predict_demand_unknown_item(self, demand_daily, items_df):
        svc = InventoryService(demand_daily, items_df)
        pred = svc.predict_demand(999, period="daily")
        assert pred == 0.0

    def test_reorder_point(self, demand_daily, items_df):
        svc = InventoryService(demand_daily, items_df)
        r = svc.calculate_reorder_point(100, lead_time_days=3)
        assert r >= 1

    def test_prep_suggestions(self, demand_daily, items_df):
        svc = InventoryService(demand_daily, items_df)
        prep = svc.get_prep_suggestions(top_n=5, safety_factor=1.2)
        assert len(prep) <= 5
        if prep:
            assert "item_id" in prep[0]
            assert "suggested_prep_quantity" in prep[0]

    def test_top_items(self, demand_daily, items_df):
        svc = InventoryService(demand_daily, items_df)
        top = svc.get_top_items(n=5, by="order_count")
        assert len(top) <= 5
        assert top[0]["item_id"] == 100
        assert top[0]["item_name"] == "Item A"

    def test_demand_summary(self, demand_daily, items_df):
        svc = InventoryService(demand_daily, items_df)
        summary = svc.get_demand_summary()
        assert summary["total_quantity"] == 10 + 12 + 11 + 3 + 5
        assert summary["unique_items"] == 2

    def test_recommendations(self, demand_daily, items_df):
        svc = InventoryService(demand_daily, items_df)
        rec = svc.generate_recommendations(100)
        assert rec["item_id"] == 100
        assert "predicted_daily_demand" in rec
        assert "reorder_point" in rec
