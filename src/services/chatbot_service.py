"""
RAG-like chatbot service for inventory data questions.
Uses moonshootai/kimi-k2-instruct-0905 model via OpenAI-compatible API.
"""

import os
import json
from typing import Optional, Dict, Any, List


class InventoryChatbot:
    """
    Chatbot that can answer questions about inventory data.
    Loads data context from cache and uses LLM to generate responses.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            from config.settings import CACHE_DIR
            cache_dir = cache_dir or CACHE_DIR
        self.cache_dir = cache_dir
        self._data_context = None
        self._client = None
        
        # Model configuration from environment
        self.api_key = os.environ.get("CHAT_API_KEY", "")
        self.api_base = os.environ.get("CHAT_API_BASE", "https://api.openai.com/v1")
        self.model_name = os.environ.get("CHAT_MODEL", "moonshotai/kimi-k2-instruct-0905")
    
    def _get_client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                )
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client
    
    def _load_data_context(self) -> Dict[str, Any]:
        """Load all cached data to build context for the chatbot."""
        if self._data_context is not None:
            return self._data_context
        
        context = {}
        
        # Load business analytics
        analytics_path = os.path.join(self.cache_dir, "business_analytics.json")
        if os.path.isfile(analytics_path):
            with open(analytics_path) as f:
                context["business_analytics"] = json.load(f)
        
        # Load summary
        summary_path = os.path.join(self.cache_dir, "summary.json")
        if os.path.isfile(summary_path):
            with open(summary_path) as f:
                context["summary"] = json.load(f)
        
        # Load top items (best sellers and slow movers)
        import pandas as pd
        
        items_path = os.path.join(self.cache_dir, "items.csv")
        if os.path.isfile(items_path):
            items_df = pd.read_csv(items_path)
            # Top 20 best sellers by order_count
            top_items = items_df.nlargest(20, "order_count")[["item_id", "item_name", "order_count"]].to_dict("records")
            context["top_items_by_orders"] = top_items
        
        demand_path = os.path.join(self.cache_dir, "demand_daily.csv")
        if os.path.isfile(demand_path):
            demand_df = pd.read_csv(demand_path)
            # Aggregate by item
            item_totals = demand_df.groupby("item_id")["quantity"].sum().reset_index()
            item_totals = item_totals.nlargest(20, "quantity")
            
            # Merge with item names if available
            if os.path.isfile(items_path):
                items_df = pd.read_csv(items_path)
                item_totals = item_totals.merge(items_df[["item_id", "item_name"]], on="item_id", how="left")
            
            context["top_items_by_demand"] = item_totals.to_dict("records")
            
            # Slow movers
            all_items = demand_df.groupby("item_id").agg({
                "quantity": ["sum", "count"]
            }).reset_index()
            all_items.columns = ["item_id", "total_qty", "sale_days"]
            slow_items = all_items.nsmallest(20, "total_qty")
            if os.path.isfile(items_path):
                slow_items = slow_items.merge(items_df[["item_id", "item_name"]], on="item_id", how="left")
            context["slow_moving_items"] = slow_items.to_dict("records")
            
            # Overall stats
            context["total_quantity_sold"] = int(demand_df["quantity"].sum())
            context["unique_items_sold"] = int(demand_df["item_id"].nunique())
            context["total_sale_days"] = int(demand_df["date"].nunique())
        
        self._data_context = context
        return context
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with data context."""
        context = self._load_data_context()
        
        # Format context as readable text
        context_text = "You are an AI assistant for Fresh Flow Markets inventory management system. You help business stakeholders understand their sales data and make informed decisions.\n\n"
        context_text += "## Available Data Context:\n\n"
        
        # Summary
        if "summary" in context:
            s = context["summary"]
            context_text += f"### Overall Summary:\n"
            context_text += f"- Total quantity sold: {s.get('total_quantity', 'N/A'):,}\n"
            context_text += f"- Unique items: {s.get('unique_items', 'N/A'):,}\n"
            context_text += f"- Date range: {s.get('date_range', {}).get('min', 'N/A')} to {s.get('date_range', {}).get('max', 'N/A')}\n\n"
        
        # Business Analytics
        if "business_analytics" in context:
            ba = context["business_analytics"]
            
            # Channel
            if "channel" in ba:
                ch = ba["channel"]
                context_text += f"### Channel Analysis:\n"
                context_text += f"- Dominant channel: {ch.get('dominant', 'N/A')}\n"
                for channel, count in ch.get("counts", {}).items():
                    context_text += f"- {channel}: {count:,} orders\n"
                context_text += "\n"
            
            # Order type
            if "order_type" in ba:
                ot = ba["order_type"]
                context_text += f"### Order Types:\n"
                context_text += f"- Dominant type: {ot.get('dominant', 'N/A')}\n"
                for otype, count in ot.get("counts", {}).items():
                    context_text += f"- {otype}: {count:,} orders\n"
                context_text += "\n"
            
            # Peak times
            if "peak_hour" in ba:
                context_text += f"### Time Patterns:\n"
                context_text += f"- Peak hour: {ba.get('peak_hour', 'N/A')}:00\n"
                context_text += f"- Peak day: {ba.get('peak_day', 'N/A')}\n\n"
            
            # Revenue
            if "revenue_stats" in ba:
                rs = ba["revenue_stats"]
                context_text += f"### Revenue:\n"
                context_text += f"- Total revenue: {rs.get('total', 0):,.2f}\n"
                context_text += f"- Average order value: {rs.get('average_order', 0):,.2f}\n\n"
            
            # Order stats
            if "order_stats" in ba:
                os_stats = ba["order_stats"]
                context_text += f"### Order Statistics:\n"
                context_text += f"- Total orders: {os_stats.get('total_orders', 0):,}\n"
                context_text += f"- Avg items per order: {os_stats.get('avg_items_per_order', 0):.2f}\n\n"
        
        # Top items
        if "top_items_by_demand" in context:
            context_text += "### Top 10 Best Selling Items (by quantity):\n"
            for i, item in enumerate(context["top_items_by_demand"][:10], 1):
                name = item.get("item_name", f"Item {item['item_id']}")
                qty = item.get("quantity", 0)
                context_text += f"{i}. {name} (ID: {item['item_id']}) - {qty:,} units\n"
            context_text += "\n"
        
        # Slow movers
        if "slow_moving_items" in context:
            context_text += "### Top 10 Slow-Moving Items (lowest sales):\n"
            for i, item in enumerate(context["slow_moving_items"][:10], 1):
                name = item.get("item_name", f"Item {item['item_id']}")
                qty = item.get("total_qty", 0)
                context_text += f"{i}. {name} (ID: {item['item_id']}) - {qty:,} units total\n"
            context_text += "\n"
        
        context_text += """
## Instructions:
- Answer questions about the inventory, sales, and business metrics based on the data above.
- Be helpful and provide actionable insights when relevant.
- If asked about specific items not in the top lists, explain that you have summary data and suggest they check the full system.
- Format numbers with commas for readability.
- Be concise but informative.
- If you don't have the data to answer a question, say so honestly.
"""
        
        return context_text
    
    def chat(self, user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Send a message to the chatbot and get a response.
        
        Args:
            user_message: The user's question
            conversation_history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]
        
        Returns:
            The assistant's response
        """
        if not self.api_key:
            return "⚠️ Chat API key not configured. Please set the CHAT_API_KEY environment variable."
        
        try:
            client = self._get_client()
            
            # Build messages
            messages = [
                {"role": "system", "content": self._build_system_prompt()}
            ]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call the API
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"⚠️ Error communicating with the chat model: {str(e)}"
    
    def get_quick_answers(self) -> Dict[str, str]:
        """Get quick answers for common questions without calling the LLM."""
        context = self._load_data_context()
        
        answers = {}
        
        # Best seller
        if "top_items_by_demand" in context and context["top_items_by_demand"]:
            top = context["top_items_by_demand"][0]
            answers["best_seller"] = f"{top.get('item_name', 'Unknown')} with {top.get('quantity', 0):,} units sold"
        
        # Total sales
        if "total_quantity_sold" in context:
            answers["total_sales"] = f"{context['total_quantity_sold']:,} units"
        
        # Peak hour
        if "business_analytics" in context:
            ba = context["business_analytics"]
            if "peak_hour" in ba:
                answers["peak_hour"] = f"{ba['peak_hour']}:00"
            if "peak_day" in ba:
                answers["peak_day"] = ba["peak_day"]
            if "channel" in ba:
                answers["dominant_channel"] = ba["channel"].get("dominant", "Unknown")
        
        return answers
