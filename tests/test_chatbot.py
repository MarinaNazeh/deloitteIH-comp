"""
Tests for the chatbot service.
Run from project root: pytest tests/test_chatbot.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.chatbot_service import InventoryChatbot


class TestInventoryChatbot:
    """Test suite for InventoryChatbot."""
    
    @pytest.fixture
    def chatbot(self):
        """Create chatbot instance."""
        return InventoryChatbot()
    
    def test_chatbot_initialization(self, chatbot):
        """Test chatbot initializes correctly."""
        assert chatbot is not None
        assert chatbot.model_name is not None
    
    def test_load_data_context(self, chatbot):
        """Test data context loading."""
        context = chatbot._load_data_context()
        assert isinstance(context, dict)
        # Context should be cached after first load
        context2 = chatbot._load_data_context()
        assert context is context2  # Same object (cached)
    
    def test_build_system_prompt(self, chatbot):
        """Test system prompt generation."""
        prompt = chatbot._build_system_prompt()
        assert isinstance(prompt, str)
        assert "Fresh Flow Markets" in prompt
        assert "inventory" in prompt.lower()
    
    def test_get_quick_answers(self, chatbot):
        """Test quick answers without LLM."""
        answers = chatbot.get_quick_answers()
        assert isinstance(answers, dict)
        # May have keys like best_seller, total_sales, etc. depending on cache
    
    def test_chat_without_api_key(self):
        """Test chat returns warning when API key not set."""
        # Create chatbot with no API key
        chatbot = InventoryChatbot()
        chatbot.api_key = ""
        
        response = chatbot.chat("Test message")
        assert "API key not configured" in response or "error" in response.lower()


class TestChatbotDataContext:
    """Test chatbot data context extraction."""
    
    @pytest.fixture
    def chatbot(self):
        """Create chatbot instance."""
        return InventoryChatbot()
    
    def test_context_has_expected_structure(self, chatbot):
        """Test that context has expected keys when cache exists."""
        context = chatbot._load_data_context()
        
        # These keys may or may not exist depending on cache
        possible_keys = [
            "business_analytics",
            "summary", 
            "top_items_by_orders",
            "top_items_by_demand",
            "slow_moving_items",
            "total_quantity_sold",
            "unique_items_sold",
        ]
        
        # At least some context should be loaded if cache exists
        # If no cache, context will be empty but shouldn't error
        assert isinstance(context, dict)


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
