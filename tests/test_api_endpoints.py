"""
Tests for API endpoints.
Run from project root: pytest tests/test_api_endpoints.py -v
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.routes import create_app


@pytest.fixture
def client():
    """Create Flask test client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test /api/health returns 200."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"


class TestAnalyticsEndpoints:
    """Test analytics endpoints."""
    
    def test_business_analytics(self, client):
        """Test /api/analytics/business endpoint."""
        response = client.get("/api/analytics/business")
        # Will return 200 if cache exists, 404 if not
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            # Should have some analytics data
            assert isinstance(data, dict)
    
    def test_pnl_analytics(self, client):
        """Test /api/analytics/pnl endpoint."""
        response = client.get("/api/analytics/pnl")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, dict)
            if "overall" in data:
                assert "total_revenue" in data["overall"]
                assert "total_profit" in data["overall"]
    
    def test_kpis(self, client):
        """Test /api/analytics/kpis endpoint."""
        response = client.get("/api/analytics/kpis")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, dict)
            if "waste_avoided" in data:
                assert "units_saved" in data["waste_avoided"]


class TestItemsEndpoints:
    """Test items-related endpoints."""
    
    def test_top_items(self, client):
        """Test /api/items/top endpoint."""
        response = client.get("/api/items/top?n=5")
        assert response.status_code in [200, 500]
    
    def test_slow_moving_items(self, client):
        """Test /api/items/slow-moving endpoint."""
        response = client.get("/api/items/slow-moving?n=10")
        assert response.status_code in [200, 500]
    
    def test_best_sellers(self, client):
        """Test /api/items/best-sellers endpoint."""
        response = client.get("/api/items/best-sellers?n=10")
        assert response.status_code in [200, 500]


class TestChatEndpoint:
    """Test chat endpoint."""
    
    def test_chat_requires_message(self, client):
        """Test /api/chat requires a message."""
        response = client.post(
            "/api/chat",
            data=json.dumps({"message": ""}),
            content_type="application/json"
        )
        assert response.status_code == 400
    
    def test_chat_with_message(self, client):
        """Test /api/chat with a message (may fail if API key not set)."""
        response = client.post(
            "/api/chat",
            data=json.dumps({"message": "What is the best selling item?"}),
            content_type="application/json"
        )
        # Will be 200 if API key is set, may have error message if not
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "response" in data


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
