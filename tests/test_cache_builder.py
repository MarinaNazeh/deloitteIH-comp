"""
Tests for cache builder functions.
Run from project root: pytest tests/test_cache_builder.py -v
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestPnLAnalytics:
    """Test P&L analytics computation."""
    
    @pytest.fixture
    def sample_orders(self):
        """Create sample orders data for testing."""
        return pd.DataFrame({
            "item_id": [1, 1, 2, 2, 3],
            "title": ["Item A", "Item A", "Item B", "Item B", "Item C"],
            "price": [25.0, 25.0, 100.0, 100.0, 250.0],
            "quantity": [10, 5, 3, 2, 1],
        })
    
    def test_margin_estimation(self, sample_orders):
        """Test that margin estimation works correctly."""
        from scripts.build_cache import compute_pnl_analytics
        
        pnl = compute_pnl_analytics(sample_orders)
        
        assert "overall" in pnl
        assert pnl["overall"]["total_revenue"] > 0
        assert pnl["overall"]["total_profit"] > 0
        assert 0 < pnl["overall"]["profit_margin_pct"] < 100
    
    def test_top_profitable_items(self, sample_orders):
        """Test top profitable items extraction."""
        from scripts.build_cache import compute_pnl_analytics
        
        pnl = compute_pnl_analytics(sample_orders)
        
        if "top_profitable_items" in pnl:
            assert isinstance(pnl["top_profitable_items"], list)
            for item in pnl["top_profitable_items"]:
                assert "item_id" in item
                assert "profit" in item
                assert "margin_pct" in item


class TestKPIsComputation:
    """Test KPI computation."""
    
    @pytest.fixture
    def sample_demand(self):
        """Create sample demand data for testing."""
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        data = []
        for date in dates:
            # High seller
            data.append({"date": date, "item_id": 100, "quantity": np.random.randint(10, 20)})
            # Medium seller
            data.append({"date": date, "item_id": 200, "quantity": np.random.randint(3, 8)})
            # Low seller (appears less frequently)
            if np.random.random() > 0.5:
                data.append({"date": date, "item_id": 300, "quantity": 1})
        return pd.DataFrame(data)
    
    @pytest.fixture
    def sample_orders(self):
        """Create sample orders data for testing."""
        return pd.DataFrame({
            "item_id": [100, 100, 200, 200, 300],
            "price": [50.0, 50.0, 30.0, 30.0, 100.0],
            "quantity": [10, 5, 3, 2, 1],
        })
    
    def test_kpis_structure(self, sample_orders, sample_demand):
        """Test that KPIs have expected structure."""
        from scripts.build_cache import compute_kpis
        
        kpis = compute_kpis(sample_orders, sample_demand)
        
        assert "waste_risk" in kpis
        assert "waste_avoided" in kpis
        assert "stockout_risk" in kpis
        assert "inventory_efficiency" in kpis
        assert "high_risk_summary" in kpis
        assert "revenue_impact" in kpis
    
    def test_waste_avoided_calculation(self, sample_orders, sample_demand):
        """Test waste avoided is calculated correctly."""
        from scripts.build_cache import compute_kpis
        
        kpis = compute_kpis(sample_orders, sample_demand)
        
        waste_avoided = kpis["waste_avoided"]
        assert "units_saved" in waste_avoided
        assert "revenue_protected" in waste_avoided
        assert waste_avoided["units_saved"] >= 0
        assert waste_avoided["revenue_protected"] >= 0
    
    def test_efficiency_percentage(self, sample_orders, sample_demand):
        """Test inventory efficiency is a valid percentage."""
        from scripts.build_cache import compute_kpis
        
        kpis = compute_kpis(sample_orders, sample_demand)
        
        efficiency = kpis["inventory_efficiency"]
        assert 0 <= efficiency["efficiency_pct"] <= 100


class TestBusinessAnalytics:
    """Test business analytics computation."""
    
    @pytest.fixture
    def sample_orders(self):
        """Create sample orders with business columns."""
        return pd.DataFrame({
            "order_id": [1, 1, 2, 2, 3],
            "item_id": [100, 101, 100, 102, 101],
            "quantity": [2, 1, 3, 1, 2],
            "channel": ["App", "App", "Web", "App", "Web"],
            "type": ["Takeaway", "Takeaway", "Delivery", "Takeaway", "Delivery"],
            "payment_method": ["Card", "Card", "Cash", "Card", "Card"],
            "total_amount": [50.0, 50.0, 75.0, 75.0, 40.0],
            "order_date": pd.to_datetime(["2024-01-01 10:00", "2024-01-01 10:00", 
                                          "2024-01-01 14:00", "2024-01-01 14:00",
                                          "2024-01-02 11:00"]),
        })
    
    def test_channel_analysis(self, sample_orders):
        """Test channel analysis extraction."""
        from scripts.build_cache import compute_business_analytics
        
        analytics = compute_business_analytics(sample_orders)
        
        assert "channel" in analytics
        assert "counts" in analytics["channel"]
        assert "dominant" in analytics["channel"]
    
    def test_order_type_analysis(self, sample_orders):
        """Test order type analysis."""
        from scripts.build_cache import compute_business_analytics
        
        analytics = compute_business_analytics(sample_orders)
        
        assert "order_type" in analytics
        assert "counts" in analytics["order_type"]
        assert "dominant" in analytics["order_type"]


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
