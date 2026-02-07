"""
Fresh Flow Insights — Streamlit UI.
Run from project root: python -m streamlit run src/app_streamlit.py
Requires API running: python -m src.main
"""

import os
import sys
import json
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:5000")
METRICS_PATH = os.path.join(ROOT, "models", "metrics.json")

# First request loads all data — can take 1–2 min. Use long timeout and cache.
DATA_TIMEOUT = 300  # 5 minutes for data-loading endpoints
HEALTH_TIMEOUT = 10


def api_get(path: str, timeout: int = None, **kwargs):
    if timeout is None:
        timeout = DATA_TIMEOUT
    r = requests.get(f"{API_BASE}{path}", timeout=timeout, **kwargs)
    r.raise_for_status()
    return r.json()


def api_post(path: str, json_data: dict, timeout: int = None):
    if timeout is None:
        timeout = DATA_TIMEOUT
    r = requests.post(f"{API_BASE}{path}", json=json_data, timeout=timeout)
    r.raise_for_status()
    return r.json()


# Business-friendly explanations for forecast metrics
METRIC_EXPLANATIONS = {
    "mae": {
        "name": "Average forecast error (MAE)",
        "explanation": "On average, how many units our daily forecast is off. "
        "Lower is better — use this to decide how much extra stock to keep as buffer.",
    },
    "rmse": {
        "name": "Root mean squared error (RMSE)",
        "explanation": "Similar to average error, but big mistakes count more. Lower is better.",
    },
    "r2": {
        "name": "Model fit (R²)",
        "explanation": "How much of the variation in demand our model explains (0% to 100%). "
        "Higher means more reliable forecasts.",
    },
}


def _display_surprise_bags(st, resp, price_small, price_medium, price_large):
    """Helper function to display surprise bag recommendations."""
    import pandas as pd
    
    recommend = resp.get("recommend_surprise_bags", False)
    total_items = resp.get("total_items_to_clear", 0)
    bags = resp.get("bags", [])
    
    if not recommend:
        st.warning(f"""
        ⚠️ **Not enough items for Surprise Bags**
        
        You have {total_items} items to clear, but surprise bags work best with at least 5 items.
        Consider using **Smart Bundles** instead to pair individual items with best-sellers.
        """)
        return
    
    st.success(f"🎉 **Surprise Bags Recommended!** You have {total_items} items to clear.")
    
    # Sustainability impact
    impact = resp.get("sustainability_impact", {})
    st.info(f"🌱 **Sustainability Impact:** {impact.get('waste_reduction_message', '')}")
    
    st.markdown("---")
    st.markdown("### Available Bag Sizes")
    
    for bag in bags:
        size = bag["size"]
        size_emoji = {"small": "🥡", "medium": "🛍️", "large": "🎒"}.get(size, "📦")
        
        with st.container():
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 15px; margin-bottom: 15px; color: white;">
                <h3 style="margin: 0; color: white;">{size_emoji} {size.title()} Surprise Bag</h3>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Fixed Price", f"{bag['fixed_price']:.0f}")
            with col2:
                st.metric("Discount", f"{bag['discount_percentage']}% OFF")
            with col3:
                st.metric("Items per Bag", f"{bag['items_per_bag']['min']}-{bag['items_per_bag']['max']}")
            with col4:
                st.metric("Can Make", f"~{bag['potential_bags_available']} bags")
            
            st.markdown(f"**Marketing Copy:** {bag['marketing_copy']}")
            
            with st.expander(f"👀 Sample Contents ({len(bag['sample_contents'])} items)"):
                for item in bag["sample_contents"]:
                    st.write(f"• {item['item_name']} (ID: {item['item_id']})")
            
            st.markdown("---")
    
    # Tips section
    st.markdown("### 💡 Tips for Success")
    tips = resp.get("tips", [])
    for tip in tips:
        st.markdown(f"✓ {tip}")
    
    # All items to clear
    all_items = resp.get("all_items_to_clear", [])
    if all_items:
        with st.expander(f"📋 All {len(all_items)} Items to Include"):
            df = pd.DataFrame(all_items)
            st.dataframe(df, use_container_width=True, hide_index=True)


def run():
    import streamlit as st
    import pandas as pd

    st.set_page_config(
        page_title="Fresh Flow Insights",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Session cache for API responses (avoids re-fetching on every click)
    if "cache_summary" not in st.session_state:
        st.session_state.cache_summary = None
    if "cache_history" not in st.session_state:
        st.session_state.cache_history = None
    if "cache_history_days" not in st.session_state:
        st.session_state.cache_history_days = None
    if "cache_clear" not in st.session_state:
        st.session_state.cache_clear = 0

    st.markdown("""
        <style>
        .big-title { font-size: 1.8rem; font-weight: 600; color: #1e3a5f; margin-bottom: 0.2rem; }
        .subtitle { color: #5a6c7d; font-size: 0.95rem; margin-bottom: 1.5rem; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="big-title">📦 Fresh Flow Insights</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Demand forecasting & prep suggestions</p>', unsafe_allow_html=True)

    # Health check (short timeout)
    try:
        api_get("/api/health", timeout=HEALTH_TIMEOUT)
        st.sidebar.success("✓ API connected")
    except Exception as e:
        st.error(f"**API not reachable.** Start it first: `python -m src.main` — {e}")
        return

    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["KPI Dashboard", "P&L Analytics", "Performance & data", "Business Analytics", "AI Assistant", "Demand prediction", "Prep suggestions", "Top items", "Inventory Health", "Bundle ideas"],
        label_visibility="collapsed",
    )

    # ----- KPI Dashboard -----
    if page == "KPI Dashboard":
        st.header("📊 Key Performance Indicators")
        st.markdown("Track the impact of inventory optimization on waste reduction and revenue protection.")
        
        try:
            kpis = api_get("/api/analytics/kpis")
            
            # Main KPI Cards Row 1
            st.markdown("### 🎯 Impact Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            waste_avoided = kpis.get("waste_avoided", {})
            stockout = kpis.get("stockout_risk", {})
            revenue = kpis.get("revenue_impact", {})
            efficiency = kpis.get("inventory_efficiency", {})
            
            with col1:
                units_saved = waste_avoided.get("units_saved", 0)
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                            padding: 25px; border-radius: 15px; text-align: center; color: white;">
                    <h1 style="margin: 0; color: white; font-size: 2.5rem;">{units_saved:,}</h1>
                    <p style="margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;">Units of Waste Avoided</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                stockouts_prevented = stockout.get("stockouts_prevented_estimate", 0)
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 25px; border-radius: 15px; text-align: center; color: white;">
                    <h1 style="margin: 0; color: white; font-size: 2.5rem;">{stockouts_prevented:,}</h1>
                    <p style="margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;">Stockouts Prevented</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                revenue_protected = revenue.get("revenue_protected", 0)
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                            padding: 25px; border-radius: 15px; text-align: center; color: white;">
                    <h1 style="margin: 0; color: white; font-size: 2.5rem;">{revenue_protected:,.0f}</h1>
                    <p style="margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;">Revenue Protected</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                eff_pct = efficiency.get("efficiency_pct", 0)
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                            padding: 25px; border-radius: 15px; text-align: center; color: white;">
                    <h1 style="margin: 0; color: white; font-size: 2.5rem;">{eff_pct:.1f}%</h1>
                    <p style="margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;">Inventory Efficiency</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Risk Summary Row
            st.markdown("### ⚠️ Risk Assessment")
            high_risk = kpis.get("high_risk_summary", {})
            waste_risk = kpis.get("waste_risk", {})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                critical = high_risk.get("critical_count", 0)
                st.markdown(f"""
                <div style="background: #fff3cd; border-left: 5px solid #dc3545; padding: 20px; border-radius: 10px;">
                    <h2 style="margin: 0; color: #dc3545;">{critical}</h2>
                    <p style="margin: 5px 0 0 0; color: #856404;">Critical Risk Items</p>
                    <small style="color: #666;">Very low demand, high waste risk</small>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                moderate = high_risk.get("moderate_count", 0)
                st.markdown(f"""
                <div style="background: #fff3cd; border-left: 5px solid #fd7e14; padding: 20px; border-radius: 10px;">
                    <h2 style="margin: 0; color: #fd7e14;">{moderate}</h2>
                    <p style="margin: 5px 0 0 0; color: #856404;">Moderate Risk Items</p>
                    <small style="color: #666;">Below-average demand</small>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                total_risk = high_risk.get("total_at_risk", 0)
                total_items = efficiency.get("total_items", 1)
                risk_pct = (total_risk / total_items * 100) if total_items > 0 else 0
                st.markdown(f"""
                <div style="background: #d4edda; border-left: 5px solid #28a745; padding: 20px; border-radius: 10px;">
                    <h2 style="margin: 0; color: #28a745;">{100 - risk_pct:.1f}%</h2>
                    <p style="margin: 5px 0 0 0; color: #155724;">Healthy Inventory</p>
                    <small style="color: #666;">{efficiency.get('healthy_items', 0):,} of {total_items:,} items</small>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Detailed Metrics
            st.markdown("### 📈 Detailed Breakdown")
            
            tab1, tab2, tab3 = st.tabs(["💰 Revenue Impact", "📦 Waste Analysis", "📊 Efficiency"])
            
            with tab1:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Revenue Base", f"{revenue.get('total_revenue_base', 0):,.0f}")
                    st.metric("Revenue Protected", f"{revenue.get('revenue_protected', 0):,.0f}", 
                             delta=f"+{revenue.get('revenue_protected', 0) / max(revenue.get('total_revenue_base', 1), 1) * 100:.1f}% saved")
                with col2:
                    st.metric("Potential Additional Revenue", f"{revenue.get('potential_additional_revenue', 0):,.0f}")
                    st.info("💡 This is additional revenue possible through better demand forecasting and reduced waste.")
            
            with tab2:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Estimated Waste Units (at risk)", f"{waste_risk.get('estimated_waste_units', 0):,}")
                    st.metric("Waste Revenue at Risk", f"{waste_risk.get('waste_at_risk_revenue', 0):,.0f}")
                with col2:
                    st.metric("Units Saved via Bundles/Bags", f"{waste_avoided.get('units_saved', 0):,}", delta="60% recovery rate")
                    st.success("🌱 Using bundles and surprise bags can save approximately 60% of at-risk inventory.")
            
            with tab3:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total SKUs Tracked", f"{efficiency.get('total_items', 0):,}")
                    st.metric("Healthy SKUs", f"{efficiency.get('healthy_items', 0):,}")
                with col2:
                    st.metric("Current Efficiency", f"{efficiency.get('efficiency_pct', 0):.1f}%")
                    st.metric("Improvement Potential", f"+{efficiency.get('improvement_potential_pct', 0):.1f}%",
                             help="Estimated improvement from following system recommendations")
            
            # Action Items
            st.markdown("---")
            st.markdown("### ✅ Recommended Actions")
            
            actions = []
            if high_risk.get("critical_count", 0) > 10:
                actions.append(("🔴 High Priority", "Create Surprise Bags for critical items to clear inventory quickly"))
            if high_risk.get("moderate_count", 0) > 20:
                actions.append(("🟠 Medium Priority", "Bundle moderate-risk items with best-sellers"))
            if stockout.get("high_variance_items_count", 0) > 5:
                actions.append(("🔵 Low Priority", f"Review {stockout.get('high_variance_items_count', 0)} high-variance items for stockout prevention"))
            
            if actions:
                for priority, action in actions:
                    st.markdown(f"**{priority}:** {action}")
            else:
                st.success("✨ Your inventory is in good shape! Keep monitoring the KPIs regularly.")
                
        except Exception as e:
            st.error(f"Could not load KPIs: {e}")
            st.info("Make sure to run `python scripts/build_cache.py` to generate KPI data.")

    # ----- P&L Analytics -----
    elif page == "P&L Analytics":
        st.header("💰 Profit & Loss Analytics")
        st.markdown("Analyze margins, identify high/low performers, and optimize pricing.")
        
        try:
            pnl = api_get("/api/analytics/pnl")
            
            if not pnl:
                st.warning("No P&L data available. Run `python scripts/build_cache.py` first.")
            else:
                # Overall P&L Summary
                overall = pnl.get("overall", {})
                
                st.markdown("### 📊 Overall Financial Summary")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Revenue", f"{overall.get('total_revenue', 0):,.0f}")
                with col2:
                    st.metric("Total Cost", f"{overall.get('total_cost', 0):,.0f}")
                with col3:
                    profit = overall.get('total_profit', 0)
                    st.metric("Total Profit", f"{profit:,.0f}", 
                             delta=f"{overall.get('profit_margin_pct', 0):.1f}% margin",
                             delta_color="normal" if profit > 0 else "inverse")
                with col4:
                    st.metric("Avg Item Margin", f"{overall.get('avg_item_margin_pct', 0):.1f}%")
                
                st.markdown("---")
                
                # Margin Distribution
                st.markdown("### 📈 Margin Distribution")
                margin_dist = pnl.get("margin_distribution", {})
                if margin_dist:
                    # Create a bar chart
                    import pandas as pd
                    margin_df = pd.DataFrame([
                        {"Margin Range": k, "Item Count": v}
                        for k, v in margin_dist.items()
                    ])
                    # Sort by margin range
                    order = ["Negative", "0-10%", "10-20%", "20-30%", "30-50%", "50%+"]
                    margin_df["sort_order"] = margin_df["Margin Range"].apply(lambda x: order.index(x) if x in order else 99)
                    margin_df = margin_df.sort_values("sort_order")
                    
                    st.bar_chart(margin_df.set_index("Margin Range")["Item Count"])
                    
                    # Color-coded summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        neg = margin_dist.get("Negative", 0)
                        st.markdown(f"""
                        <div style="background: #f8d7da; padding: 15px; border-radius: 10px; text-align: center;">
                            <h3 style="color: #721c24; margin: 0;">{neg}</h3>
                            <p style="color: #721c24; margin: 0;">Loss-Making Items</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        low = margin_dist.get("0-10%", 0) + margin_dist.get("10-20%", 0)
                        st.markdown(f"""
                        <div style="background: #fff3cd; padding: 15px; border-radius: 10px; text-align: center;">
                            <h3 style="color: #856404; margin: 0;">{low}</h3>
                            <p style="color: #856404; margin: 0;">Low Margin (0-20%)</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col3:
                        high = margin_dist.get("30-50%", 0) + margin_dist.get("50%+", 0)
                        st.markdown(f"""
                        <div style="background: #d4edda; padding: 15px; border-radius: 10px; text-align: center;">
                            <h3 style="color: #155724; margin: 0;">{high}</h3>
                            <p style="color: #155724; margin: 0;">High Margin (30%+)</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Item Analysis Tabs
                st.markdown("### 🔍 Item-Level Analysis")
                tab1, tab2, tab3, tab4 = st.tabs(["🌟 Top Profitable", "📈 High Margin", "⚠️ Low Margin", "🔴 Loss-Making"])
                
                with tab1:
                    st.markdown("**Most profitable items by total profit generated:**")
                    top_profit = pnl.get("top_profitable_items", [])
                    if top_profit:
                        df = pd.DataFrame(top_profit)
                        # Format columns
                        df["profit"] = df["profit"].apply(lambda x: f"{x:,.0f}")
                        df["revenue"] = df["revenue"].apply(lambda x: f"{x:,.0f}")
                        df["margin_pct"] = df["margin_pct"].apply(lambda x: f"{x:.1f}%")
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No data available.")
                
                with tab2:
                    st.markdown("**Items with highest profit margins (stars for promotions):**")
                    high_margin = pnl.get("high_margin_items", [])
                    if high_margin:
                        df = pd.DataFrame(high_margin)
                        df["profit"] = df["profit"].apply(lambda x: f"{x:,.0f}")
                        df["revenue"] = df["revenue"].apply(lambda x: f"{x:,.0f}")
                        df["margin_pct"] = df["margin_pct"].apply(lambda x: f"{x:.1f}%")
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.success("💡 **Tip:** Promote these high-margin items more prominently to maximize profit.")
                    else:
                        st.info("No data available.")
                
                with tab3:
                    st.markdown("**Items with lowest margins (consider price adjustments):**")
                    low_margin = pnl.get("low_margin_items", [])
                    if low_margin:
                        df = pd.DataFrame(low_margin)
                        df["profit"] = df["profit"].apply(lambda x: f"{x:,.0f}")
                        df["revenue"] = df["revenue"].apply(lambda x: f"{x:,.0f}")
                        df["margin_pct"] = df["margin_pct"].apply(lambda x: f"{x:.1f}%")
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.warning("⚠️ **Action:** Review pricing or supplier costs for these items.")
                    else:
                        st.info("No data available.")
                
                with tab4:
                    st.markdown("**Items generating losses (urgent attention needed):**")
                    loss_items = pnl.get("loss_making_items", [])
                    if loss_items:
                        df = pd.DataFrame(loss_items)
                        df["profit"] = df["profit"].apply(lambda x: f"{x:,.0f}")
                        df["revenue"] = df["revenue"].apply(lambda x: f"{x:,.0f}")
                        df["margin_pct"] = df["margin_pct"].apply(lambda x: f"{x:.1f}%")
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.error("🚨 **Urgent:** These items are losing money. Consider discontinuing or renegotiating costs.")
                    else:
                        st.success("✨ Great news! No loss-making items detected.")
                
                # Recommendations
                st.markdown("---")
                st.markdown("### 💡 Revenue Optimization Recommendations")
                
                recommendations = []
                
                if margin_dist.get("Negative", 0) > 0:
                    recommendations.append({
                        "priority": "High",
                        "icon": "🔴",
                        "title": "Address Loss-Making Items",
                        "action": f"Review {margin_dist.get('Negative', 0)} loss-making items - consider price increases or supplier renegotiation"
                    })
                
                if margin_dist.get("0-10%", 0) > 10:
                    recommendations.append({
                        "priority": "Medium",
                        "icon": "🟠",
                        "title": "Improve Low-Margin Items",
                        "action": "Items with 0-10% margin should be reviewed for cost reduction opportunities"
                    })
                
                high_margin_count = margin_dist.get("50%+", 0)
                if high_margin_count > 0:
                    recommendations.append({
                        "priority": "Opportunity",
                        "icon": "🟢",
                        "title": "Promote High-Margin Winners",
                        "action": f"Feature {high_margin_count} high-margin items (50%+) in bundles and promotions"
                    })
                
                for rec in recommendations:
                    color = {"High": "#dc3545", "Medium": "#fd7e14", "Opportunity": "#28a745"}.get(rec["priority"], "#6c757d")
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid {color};">
                        <strong>{rec['icon']} {rec['title']}</strong>
                        <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 10px;">{rec['priority']}</span>
                        <br/><span style="color: #333;">{rec['action']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Could not load P&L analytics: {e}")
            st.info("Make sure to run `python scripts/build_cache.py` to generate P&L data.")

    # ----- Performance & data -----
    elif page == "Performance & data":
        st.header("Performance & historical data")
        if st.sidebar.button("🔄 Refresh data", help="Reload summary and chart from API"):
            st.session_state.cache_summary = None
            st.session_state.cache_history = None
            st.session_state.cache_clear += 1
            st.rerun()

        # Data summary (cached)
        summary = st.session_state.cache_summary
        if summary is None:
            with st.spinner("Loading data summary… (first time can take 1–2 minutes while we load the dataset)"):
                try:
                    summary = api_get("/api/demand/summary", timeout=DATA_TIMEOUT)
                    st.session_state.cache_summary = summary
                except requests.exceptions.Timeout:
                    st.error("Request timed out. The API is still loading the data. Wait a minute and click **Refresh data**.")
                    summary = None
                except Exception as e:
                    st.error(f"Could not load summary: {e}")
                    summary = None

        if summary is not None:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total units sold", f"{summary.get('total_quantity', 0):,}", help="In the loaded dataset")
            with col2:
                st.metric("Unique menu items", f"{summary.get('unique_items', 0):,}", help="Items with at least one sale")
            with col3:
                dr = summary.get("date_range") or {}
                range_str = "—"
                if dr.get("min") and dr.get("max"):
                    range_str = f"{dr['min'][:10]} → {dr['max'][:10]}"
                st.metric("Date range", range_str, help="Earliest and latest order date")

        st.markdown("---")
        st.markdown("#### 📈 Daily demand over time")
        days = st.slider("Show last (days)", 30, 180, 90, key="history_days")
        history = st.session_state.cache_history
        if st.session_state.cache_history_days != days:
            history = None
        if history is None:
            with st.spinner("Loading daily demand…"):
                try:
                    hist = api_get("/api/demand/history", params={"last_n_days": days}, timeout=DATA_TIMEOUT)
                    history = hist.get("history") or []
                    st.session_state.cache_history = history
                    st.session_state.cache_history_days = days
                except requests.exceptions.Timeout:
                    st.warning("Timed out loading history. Click **Refresh data** in the sidebar and try again.")
                    history = []
                except Exception as e:
                    st.warning(f"Could not load history: {e}")
                    history = []

        if history:
            df_hist = pd.DataFrame(history)
            df_hist["date"] = pd.to_datetime(df_hist["date"])
            df_hist = df_hist.set_index("date").sort_index()
            st.line_chart(df_hist["quantity"], height=320)
        else:
            st.info("No daily history yet. Use **Refresh data** after the API has finished loading.")

        st.markdown("---")
        st.markdown("#### 📊 Forecast model performance")
        if os.path.isfile(METRICS_PATH):
            with open(METRICS_PATH) as f:
                metrics = json.load(f)
            
            # Model display names
            MODEL_NAMES = {
                "linear_regression": "Linear Regression",
                "random_forest": "Random Forest",
                "lightgbm": "LightGBM",
                "ensemble": "Ensemble (Average)",
            }
            
            # Find best model by MAE (lower is better)
            model_mae = {k: v.get("mae", float("inf")) for k, v in metrics.items() if isinstance(v, dict)}
            best_model = min(model_mae, key=model_mae.get) if model_mae else None
            
            # Find best model by R² (higher is better)
            model_r2 = {k: v.get("r2", float("-inf")) for k, v in metrics.items() if isinstance(v, dict)}
            best_r2_model = max(model_r2, key=model_r2.get) if model_r2 else None
            
            ensemble = metrics.get("ensemble", {})
            if ensemble:
                st.markdown("##### Overall Ensemble Performance")
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    st.metric("Average error (MAE)", f"{ensemble.get('mae', 0):.2f}", "units per day")
                with ec2:
                    st.metric("RMSE", f"{ensemble.get('rmse', 0):.2f}", "units")
                with ec3:
                    st.metric("Model fit (R²)", f"{ensemble.get('r2', 0):.1%}", "explained variance")
                with st.expander("What do these metrics mean?"):
                    for key, info in METRIC_EXPLANATIONS.items():
                        st.markdown(f"**{info['name']}** — {info['explanation']}")
            
            st.markdown("##### Individual Model Comparison")
            
            # Display each model's metrics with highlighting
            for model_key in ["linear_regression", "random_forest", "lightgbm", "ensemble"]:
                if model_key not in metrics:
                    continue
                m = metrics[model_key]
                model_name = MODEL_NAMES.get(model_key, model_key)
                is_best = (model_key == best_model)
                
                # Create styled container for best model
                if is_best:
                    st.markdown(f"""
                    <div style="background-color: #d4edda; border: 2px solid #28a745; border-radius: 10px; padding: 15px; margin-bottom: 10px;">
                        <h4 style="color: #155724; margin: 0;">🏆 {model_name} <span style="font-size: 0.8em;">(Best Model)</span></h4>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"**{model_name}**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    mae_val = m.get('mae', 0)
                    if is_best:
                        st.success(f"MAE: {mae_val:.2f}")
                    else:
                        st.metric("MAE", f"{mae_val:.2f}")
                with col2:
                    rmse_val = m.get('rmse', 0)
                    if is_best:
                        st.success(f"RMSE: {rmse_val:.2f}")
                    else:
                        st.metric("RMSE", f"{rmse_val:.2f}")
                with col3:
                    r2_val = m.get('r2', 0)
                    if is_best:
                        st.success(f"R²: {r2_val:.1%}")
                    else:
                        st.metric("R²", f"{r2_val:.1%}")
                
                if model_key != "ensemble":
                    st.markdown("---")
            
            # Summary table
            st.markdown("##### Summary Table")
            df_metrics = pd.DataFrame(metrics).T
            df_metrics.index = [MODEL_NAMES.get(idx, idx) for idx in df_metrics.index]
            df_metrics = df_metrics.round(4)
            df_metrics.index.name = "Model"
            st.dataframe(df_metrics, use_container_width=True)
            
            st.caption(f"🏆 **Best performing model:** {MODEL_NAMES.get(best_model, best_model)} (lowest MAE: {model_mae[best_model]:.2f})")
        else:
            st.info("Run `python scripts/train_demand_models.py` to see model accuracy here.")

    # ----- Business Analytics -----
    elif page == "Business Analytics":
        st.header("📊 Business Analytics Dashboard")
        st.markdown("**Actionable insights for stakeholders** — understand customer behavior, channel performance, and optimize your strategy.")
        
        # Load analytics data
        analytics = None
        with st.spinner("Loading business analytics..."):
            try:
                analytics = api_get("/api/analytics/business")
            except Exception as e:
                st.error(f"Could not load analytics: {e}")
                st.info("Make sure to run `python scripts/build_cache.py` to generate analytics data.")
        
        if analytics:
            # ===== Channel Analysis =====
            st.markdown("---")
            st.subheader("📱 Channel Analysis: App vs Web")
            st.markdown("*Where are your customers ordering from? Focus your improvements on the dominant channel.*")
            
            channel_data = analytics.get("channel", {})
            if channel_data:
                channel_counts = channel_data.get("counts", {})
                channel_revenue = channel_data.get("revenue", {})
                channel_qty = channel_data.get("quantity", {})
                dominant = channel_data.get("dominant", "Unknown")
                
                total_count = sum(channel_counts.values())
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Dominant Channel", f"📱 {dominant}", help="Channel with most orders")
                with col2:
                    app_pct = (channel_counts.get("App", 0) / total_count * 100) if total_count > 0 else 0
                    st.metric("App Orders", f"{app_pct:.1f}%", f"{channel_counts.get('App', 0):,} orders")
                with col3:
                    web_pct = (channel_counts.get("Web", 0) / total_count * 100) if total_count > 0 else 0
                    st.metric("Web Orders", f"{web_pct:.1f}%", f"{channel_counts.get('Web', 0):,} orders")
                
                # Visual comparison
                ch1, ch2 = st.columns(2)
                with ch1:
                    st.markdown("**Orders by Channel**")
                    chart_data = pd.DataFrame({
                        "Channel": list(channel_counts.keys()),
                        "Orders": list(channel_counts.values())
                    })
                    st.bar_chart(chart_data.set_index("Channel"))
                
                with ch2:
                    st.markdown("**Quantity Sold by Channel**")
                    qty_data = pd.DataFrame({
                        "Channel": list(channel_qty.keys()),
                        "Quantity": list(channel_qty.values())
                    })
                    st.bar_chart(qty_data.set_index("Channel"))
                
                # Insights box
                if dominant == "App":
                    st.success(f"""
                    💡 **Insight:** **{app_pct:.0f}%** of orders come from the **Mobile App**. 
                    
                    **Recommendations:**
                    - Focus promotional bundles and discounts on the app to maximize reach
                    - Consider app-exclusive deals to drive even more engagement
                    - Invest in app UX improvements for better conversion
                    """)
                else:
                    st.info(f"""
                    💡 **Insight:** **{web_pct:.0f}%** of orders come from the **Website**. 
                    
                    **Recommendations:**
                    - Optimize website for mobile responsiveness
                    - Consider push notifications to drive app adoption
                    - Run web-exclusive promotions to maintain engagement
                    """)
            
            # ===== Order Type Analysis =====
            st.markdown("---")
            st.subheader("🍽️ Order Type Analysis")
            st.markdown("*How do customers prefer to get their food?*")
            
            order_type_data = analytics.get("order_type", {})
            if order_type_data:
                type_counts = order_type_data.get("counts", {})
                type_revenue = order_type_data.get("revenue", {})
                dominant_type = order_type_data.get("dominant", "Unknown")
                
                total_type = sum(type_counts.values())
                
                type_cols = st.columns(len(type_counts) + 1)
                with type_cols[0]:
                    st.metric("Most Popular", f"🏆 {dominant_type}")
                
                type_icons = {"Takeaway": "🥡", "Eat In": "🍽️", "Delivery": "🚗"}
                for i, (order_type, count) in enumerate(type_counts.items()):
                    with type_cols[i + 1]:
                        pct = (count / total_type * 100) if total_type > 0 else 0
                        icon = type_icons.get(order_type, "📦")
                        st.metric(f"{icon} {order_type}", f"{pct:.1f}%", f"{count:,} orders")
                
                # Chart
                type_df = pd.DataFrame({
                    "Order Type": list(type_counts.keys()),
                    "Count": list(type_counts.values())
                })
                st.bar_chart(type_df.set_index("Order Type"))
                
                # Insight
                if dominant_type == "Takeaway":
                    st.info("💡 **Takeaway dominates!** Optimize packaging, consider grab-and-go bundles, and ensure quick service times.")
                elif dominant_type == "Delivery":
                    st.info("💡 **Delivery is king!** Focus on delivery-friendly items, partner with delivery apps, and consider delivery-exclusive bundles.")
                else:
                    st.info("💡 **Eat-in is popular!** Create dine-in specials, upsell combos at the table, and optimize table turnover.")
            
            # ===== Payment Method Analysis =====
            st.markdown("---")
            st.subheader("💳 Payment Method Analysis")
            
            payment_data = analytics.get("payment_method", {})
            if payment_data:
                payment_counts = payment_data.get("counts", {})
                dominant_payment = payment_data.get("dominant", "Unknown")
                
                total_payments = sum(payment_counts.values())
                
                pay_cols = st.columns(min(len(payment_counts), 5))
                payment_icons = {"Card": "💳", "Cash": "💵", "Counter": "🏪", "Online": "🌐", "VivaWallet": "📱"}
                
                for i, (method, count) in enumerate(list(payment_counts.items())[:5]):
                    with pay_cols[i]:
                        pct = (count / total_payments * 100) if total_payments > 0 else 0
                        icon = payment_icons.get(method, "💰")
                        st.metric(f"{icon} {method}", f"{pct:.1f}%", f"{count:,}")
                
                if dominant_payment == "Card":
                    st.success("💡 **Card payments dominate.** Ensure card terminals are fast and reliable. Consider contactless payment promotions.")
                elif dominant_payment == "Cash":
                    st.info("💡 **Cash is still popular.** Keep sufficient change, but consider incentives for digital payments to speed up service.")
            
            # ===== Time-Based Analysis =====
            st.markdown("---")
            st.subheader("⏰ Time-Based Patterns")
            st.markdown("*When are your peak hours and days? Schedule staff and promotions accordingly.*")
            
            time_col1, time_col2 = st.columns(2)
            
            with time_col1:
                peak_hour = analytics.get("peak_hour")
                if peak_hour is not None:
                    st.metric("🕐 Peak Hour", f"{peak_hour}:00 - {peak_hour+1}:00", "Most orders")
                
                hourly = analytics.get("hourly_distribution", {})
                if hourly:
                    hourly_df = pd.DataFrame({
                        "Hour": [f"{h}:00" for h in sorted(hourly.keys())],
                        "Orders": [hourly[h] for h in sorted(hourly.keys())]
                    })
                    st.markdown("**Hourly Distribution**")
                    st.bar_chart(hourly_df.set_index("Hour"))
            
            with time_col2:
                peak_day = analytics.get("peak_day")
                if peak_day:
                    st.metric("📅 Peak Day", peak_day, "Busiest day of week")
                
                daily = analytics.get("day_of_week_distribution", {})
                if daily:
                    # Sort by day order
                    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    sorted_daily = {d: daily.get(d, 0) for d in day_order if d in daily}
                    daily_df = pd.DataFrame({
                        "Day": list(sorted_daily.keys()),
                        "Orders": list(sorted_daily.values())
                    })
                    st.markdown("**Daily Distribution**")
                    st.bar_chart(daily_df.set_index("Day"))
            
            # Peak time insights
            if peak_hour is not None and peak_day:
                st.success(f"""
                💡 **Peak Times Insight:** Your busiest time is **{peak_day}** around **{peak_hour}:00**.
                
                **Recommendations:**
                - Schedule extra staff during peak hours
                - Run flash sales during slower hours (e.g., 14:00-16:00) to balance load
                - Prep surprise bags before the end of peak hours
                """)
            
            # ===== Revenue & Order Stats =====
            st.markdown("---")
            st.subheader("💰 Revenue & Order Statistics")
            
            revenue_stats = analytics.get("revenue_stats", {})
            order_stats = analytics.get("order_stats", {})
            
            rev_cols = st.columns(4)
            with rev_cols[0]:
                total_rev = revenue_stats.get("total", 0)
                st.metric("Total Revenue", f"{total_rev:,.0f}", "in dataset")
            with rev_cols[1]:
                avg_order = revenue_stats.get("average_order", 0)
                st.metric("Avg Order Value", f"{avg_order:,.2f}")
            with rev_cols[2]:
                total_orders = order_stats.get("total_orders", 0)
                st.metric("Total Orders", f"{total_orders:,}")
            with rev_cols[3]:
                avg_items = order_stats.get("avg_items_per_order", 0)
                st.metric("Avg Items/Order", f"{avg_items:.1f}")
            
            # Upsell opportunity
            if avg_items < 2:
                st.warning("""
                💡 **Upsell Opportunity:** Average items per order is low. Consider:
                - Bundle deals (buy 2, get discount)
                - Combo meals
                - "Frequently bought together" suggestions
                """)
            

    # ----- AI Assistant -----
    elif page == "AI Assistant":
        st.header("🤖 AI Inventory Assistant")
        st.markdown("""
        Ask me anything about your inventory, sales, and business metrics! I have access to your data and can help you understand trends, find best sellers, and get insights.
        """)
        
        # Initialize chat history in session state
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "chat_input_key" not in st.session_state:
            st.session_state.chat_input_key = 0
        
        # Quick answers section
        with st.expander("⚡ Quick Answers (No AI needed)", expanded=False):
            try:
                quick = api_get("/api/chat/quick-answers")
                answers = quick.get("quick_answers", {})
                if answers:
                    qa_cols = st.columns(2)
                    with qa_cols[0]:
                        if "best_seller" in answers:
                            st.metric("🏆 Best Seller", answers["best_seller"])
                        if "total_sales" in answers:
                            st.metric("📦 Total Sales", answers["total_sales"])
                    with qa_cols[1]:
                        if "peak_hour" in answers:
                            st.metric("⏰ Peak Hour", answers["peak_hour"])
                        if "peak_day" in answers:
                            st.metric("📅 Peak Day", answers["peak_day"])
                        if "dominant_channel" in answers:
                            st.metric("📱 Dominant Channel", answers["dominant_channel"])
            except Exception as e:
                st.warning(f"Could not load quick answers: {e}")
        
        st.markdown("---")
        
        # Suggested questions
        st.markdown("**💡 Try asking:**")
        suggestions = [
            "What is the best selling item?",
            "How many items were sold in total?",
            "What are the slowest moving items?",
            "When is the peak hour for orders?",
            "What channel do most customers use?",
            "Give me a summary of the business performance",
        ]
        
        # Create suggestion buttons in a row
        suggestion_cols = st.columns(3)
        for i, suggestion in enumerate(suggestions):
            with suggestion_cols[i % 3]:
                if st.button(f"💬 {suggestion[:30]}...", key=f"suggest_{i}", help=suggestion):
                    st.session_state.pending_question = suggestion
        
        st.markdown("---")
        
        # Chat container with custom styling
        st.markdown("""
        <style>
        .chat-message {
            padding: 15px;
            border-radius: 15px;
            margin-bottom: 10px;
            max-width: 85%;
        }
        .user-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            text-align: right;
        }
        .assistant-message {
            background: #f0f2f6;
            color: #333;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 18px; border-radius: 18px 18px 4px 18px; max-width: 80%;">
                            <strong>You:</strong><br/>{msg["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">
                        <div style="background: #f0f2f6; color: #333; padding: 12px 18px; border-radius: 18px 18px 18px 4px; max-width: 80%;">
                            <strong>🤖 Assistant:</strong><br/>{msg["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Check for pending question from suggestion buttons
        if "pending_question" in st.session_state and st.session_state.pending_question:
            pending = st.session_state.pending_question
            st.session_state.pending_question = None
            
            # Add to history and get response
            st.session_state.chat_history.append({"role": "user", "content": pending})
            
            with st.spinner("🤔 Thinking..."):
                try:
                    # Build history for API
                    api_history = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in st.session_state.chat_history[:-1]  # Exclude current message
                    ]
                    
                    response = api_post("/api/chat", {
                        "message": pending,
                        "history": api_history
                    })
                    
                    assistant_response = response.get("response", "Sorry, I couldn't process that.")
                    st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
                except Exception as e:
                    error_msg = f"⚠️ Error: {str(e)}"
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
            
            st.rerun()
        
        # Input area
        st.markdown("---")
        col_input, col_send = st.columns([5, 1])
        
        with col_input:
            user_input = st.text_input(
                "Ask a question about your inventory...",
                key=f"chat_input_{st.session_state.chat_input_key}",
                placeholder="e.g., What is the best selling item?",
                label_visibility="collapsed"
            )
        
        with col_send:
            send_clicked = st.button("📤 Send", type="primary", use_container_width=True)
        
        # Clear chat button
        col_clear, _ = st.columns([1, 5])
        with col_clear:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.chat_input_key += 1
                st.rerun()
        
        # Process input
        if send_clicked and user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            with st.spinner("🤔 Thinking..."):
                try:
                    # Build history for API
                    api_history = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in st.session_state.chat_history[:-1]  # Exclude current message
                    ]
                    
                    response = api_post("/api/chat", {
                        "message": user_input,
                        "history": api_history
                    })
                    
                    assistant_response = response.get("response", "Sorry, I couldn't process that.")
                    st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
                except Exception as e:
                    error_msg = f"⚠️ Error: {str(e)}"
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
            
            # Increment key to clear input
            st.session_state.chat_input_key += 1
            st.rerun()
        
    # ----- Demand prediction -----
    elif page == "Demand prediction":
        st.header("Predict demand")
        
        # Load items with demand data (cached)
        if "cache_items_with_demand" not in st.session_state:
            st.session_state.cache_items_with_demand = None
        
        items_list = st.session_state.cache_items_with_demand
        if items_list is None:
            with st.spinner("Loading available items..."):
                try:
                    resp = api_get("/api/items/with-demand?n=100")
                    items_list = resp.get("items", [])
                    st.session_state.cache_items_with_demand = items_list
                except Exception:
                    items_list = []
        
        if not items_list:
            st.warning("No items with demand data found. Make sure the API is running and cache is built.")
        else:
            # Build dropdown options: "item_name (ID: item_id)"
            item_options = {
                f"{it['item_name']} (ID: {it['item_id']})": it['item_id']
                for it in items_list
            }
            option_labels = list(item_options.keys())
            
            col1, col2 = st.columns(2)
            with col1:
                selected = st.selectbox("Select item", option_labels, index=0)
                item_id = item_options[selected]
                period = st.selectbox("Forecast period", ["daily", "weekly", "monthly"])
            with col2:
                place_id = st.text_input("Place ID (optional)", "")
                st.caption(f"Selected item ID: **{item_id}**")
            
            if st.button("Get forecast", type="primary"):
                with st.spinner("Loading…"):
                    try:
                        body = {"item_id": item_id, "period": period}
                        if place_id and place_id.strip():
                            body["place_id"] = int(place_id) if place_id.strip().isdigit() else place_id.strip()
                        out = api_post("/api/inventory/predict", body)
                        
                        # Show historical context
                        st.subheader("Historical Data")
                        hist_col1, hist_col2 = st.columns(2)
                        with hist_col1:
                            st.metric("Total historical sales", f"{out.get('total_historical_quantity', 0):,}", "units")
                        with hist_col2:
                            st.metric("Data points", f"{out.get('data_points', 0):,}", "days with sales")
                        
                        method = out.get('method_used', 'unknown')
                        if method == "ml_models":
                            st.success("Using trained ML models for prediction")
                        elif method == "moving_average":
                            st.info("Using moving average (ML models not trained yet)")
                        elif method == "no_data":
                            st.warning("No historical data for this item")
                        
                        # Show individual model predictions
                        st.subheader(f"Predictions ({period})")
                        
                        # Model predictions in columns
                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric("Linear Regression", f"{out.get('linear_regression', 0):,.2f}", "units")
                        with m2:
                            st.metric("Random Forest", f"{out.get('random_forest', 0):,.2f}", "units")
                        with m3:
                            st.metric("LightGBM", f"{out.get('lightgbm', 0):,.2f}", "units")
                        
                        # Ensemble and moving average
                        e1, e2 = st.columns(2)
                        with e1:
                            st.metric("**Ensemble (Average)**", f"{out.get('ensemble', 0):,.2f}", "units", help="Average of all 3 models")
                        with e2:
                            st.metric("Moving Average (baseline)", f"{out.get('moving_average', 0):,.2f}", "units", help="Simple 14-day average")
                        
                        # Warning for sparse data
                        if out.get('data_points', 0) < 7:
                            st.warning("⚠️ This item has very few data points. Predictions may be unreliable.")
                        
                    except requests.exceptions.Timeout:
                        st.error("Request timed out. Try **Refresh data** on the Performance page first, then try again.")
                    except Exception as e:
                        st.error(str(e))

    # ----- Prep suggestions -----
    elif page == "Prep suggestions":
        st.header("Prep quantity suggestions")
        top_n = st.slider("Number of items", 5, 50, 20)
        safety = st.slider("Safety factor", 1.0, 2.0, 1.2, 0.1)
        if st.button("Get prep list", type="primary"):
            with st.spinner("Loading…"):
                try:
                    out = api_get("/api/inventory/prep", params={"top_n": top_n, "safety_factor": safety})
                    st.dataframe(pd.DataFrame(out["prep_suggestions"]), use_container_width=True, hide_index=True)
                except requests.exceptions.Timeout:
                    st.error("Timed out. Load the Performance page first (so data is ready), then try again.")
                except Exception as e:
                    st.error(str(e))

    # ----- Top items -----
    elif page == "Top items":
        st.header("Top items by popularity")
        n = st.slider("Show top", 10, 100, 50)
        by = st.radio("Sort by", ["order_count", "demand"], format_func=lambda x: "Total orders (all-time)" if x == "order_count" else "Demand in dataset")
        if st.button("Load list", type="primary"):
            with st.spinner("Loading…"):
                try:
                    out = api_get("/api/items/top", params={"n": n, "by": by})
                    st.dataframe(pd.DataFrame(out["top_items"]), use_container_width=True, hide_index=True)
                except requests.exceptions.Timeout:
                    st.error("Timed out. Load the Performance page first, then try again.")
                except Exception as e:
                    st.error(str(e))

    # ----- Inventory Health -----
    elif page == "Inventory Health":
        st.header("📊 Inventory Health Dashboard")
        st.markdown("""
        Get a clear view of your **best performers** and **items that need attention**. 
        Use this data to make informed decisions about promotions, bundles, and stock management.
        """)
        
        # Load data on page load
        col_best, col_slow = st.columns(2)
        
        with col_best:
            st.subheader("🌟 Best Sellers")
            st.caption("Your top-performing items driving revenue")
        
        with col_slow:
            st.subheader("🐢 Slow Movers")
            st.caption("Items that need attention - consider bundling or promotions")
        
        st.markdown("---")
        
        # Controls
        ctrl1, ctrl2, ctrl3 = st.columns(3)
        with ctrl1:
            n_best = st.slider("Number of best sellers", 5, 30, 10, key="health_n_best")
        with ctrl2:
            n_slow = st.slider("Number of slow movers", 5, 30, 15, key="health_n_slow")
        with ctrl3:
            max_daily = st.slider("Max daily demand for slow movers", 0.1, 3.0, 1.0, 0.1, key="health_max_daily")
        
        if st.button("🔄 Load Inventory Health Data", type="primary"):
            # Load both datasets
            best_sellers = None
            slow_movers = None
            
            with st.spinner("Loading best sellers and slow movers..."):
                try:
                    best_resp = api_get(f"/api/items/best-sellers?n={n_best}")
                    best_sellers = best_resp.get("best_sellers", [])
                except Exception as e:
                    st.error(f"Error loading best sellers: {e}")
                
                try:
                    slow_resp = api_get(f"/api/items/slow-moving?n={n_slow}&max_daily_avg={max_daily}")
                    slow_movers = slow_resp.get("slow_moving_items", [])
                except Exception as e:
                    st.error(f"Error loading slow movers: {e}")
            
            if best_sellers or slow_movers:
                # Display side by side
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 🌟 Best Sellers")
                    if best_sellers:
                        # Calculate total for percentage
                        total_qty = sum(item["total_quantity"] for item in best_sellers)
                        
                        for i, item in enumerate(best_sellers):
                            pct = (item["total_quantity"] / total_qty * 100) if total_qty > 0 else 0
                            
                            # Medal for top 3
                            medal = ""
                            if i == 0:
                                medal = "🥇 "
                            elif i == 1:
                                medal = "🥈 "
                            elif i == 2:
                                medal = "🥉 "
                            
                            st.markdown(f"""
                            <div style="background: linear-gradient(90deg, #d4edda {pct}%, #f8f9fa {pct}%); 
                                        padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid #28a745;">
                                <strong>{medal}{item['item_name']}</strong><br/>
                                <small style="color: #666;">ID: {item['item_id']} · <strong>{item['total_quantity']:,}</strong> units sold</small>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.caption(f"Total: {total_qty:,} units from top {len(best_sellers)} items")
                    else:
                        st.info("No best sellers found.")
                
                with col2:
                    st.markdown("### 🐢 Slow Movers")
                    if slow_movers:
                        for item in slow_movers:
                            # Color based on how slow
                            if item["avg_daily_demand"] < 0.1:
                                color = "#dc3545"  # Red - very slow
                                status = "Critical"
                            elif item["avg_daily_demand"] < 0.5:
                                color = "#fd7e14"  # Orange - slow
                                status = "Slow"
                            else:
                                color = "#ffc107"  # Yellow - moderate
                                status = "Moderate"
                            
                            st.markdown(f"""
                            <div style="background: #fff3cd; padding: 10px; border-radius: 8px; margin-bottom: 8px; 
                                        border-left: 4px solid {color};">
                                <strong>{item['item_name']}</strong> 
                                <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 8px;">{status}</span><br/>
                                <small style="color: #666;">ID: {item['item_id']} · <strong>{item['avg_daily_demand']:.3f}</strong> units/day · {item['total_quantity']} total · {item['sale_days']} days with sales</small>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.caption(f"Showing {len(slow_movers)} items with avg daily demand ≤ {max_daily}")
                    else:
                        st.info("No slow-moving items found with these criteria.")
                
                # Summary stats
                st.markdown("---")
                st.markdown("### 📈 Summary & Recommendations")
                
                sum1, sum2, sum3 = st.columns(3)
                with sum1:
                    if best_sellers:
                        top_item = best_sellers[0]
                        st.success(f"**Top Performer:** {top_item['item_name']} with {top_item['total_quantity']:,} units")
                
                with sum2:
                    if slow_movers:
                        critical_count = len([i for i in slow_movers if i["avg_daily_demand"] < 0.1])
                        if critical_count > 0:
                            st.warning(f"**{critical_count} Critical Items** need immediate attention!")
                        else:
                            st.info(f"**{len(slow_movers)} Slow Items** could benefit from bundling")
                
                with sum3:
                    if best_sellers and slow_movers:
                        st.info(f"💡 **Tip:** Bundle slow movers with best sellers to boost sales!")
                
                # Action buttons
                st.markdown("---")
                action1, action2 = st.columns(2)
                with action1:
                    st.markdown("**🎁 Ready to create bundles?**")
                    st.markdown("Go to **Bundle Ideas** page to pair slow movers with best sellers.")
                with action2:
                    st.markdown("**📦 Too many slow movers?**")
                    st.markdown("Consider creating **Surprise Bags** to clear multiple items at once.")

    # ----- Bundle ideas -----
    elif page == "Bundle ideas":
        st.header("🎁 Smart Bundle Recommendations")
        st.markdown("""
        **Reduce waste & boost sales** by bundling best-selling items with slow-moving or near-expiry products.
        Customers get a discount, you clear inventory before it expires!
        """)
        
        tab1, tab2, tab3, tab4 = st.tabs(["📦 Smart Bundles", "🎁 Surprise Bags", "🐢 Slow-Moving Items", "🌟 Best Sellers"])
        
        with tab1:
            st.subheader("Generate Smart Bundles")
            
            bundle_mode = st.radio(
                "Bundle generation mode",
                ["Auto (slow-moving items)", "Manual (specify near-expiry items)"],
                horizontal=True
            )
            
            discount_pct = st.slider("Suggested discount (%)", 5, 50, 15, 5)
            
            if bundle_mode == "Auto (slow-moving items)":
                n_slow = st.slider("Number of slow-moving items to bundle", 5, 30, 10)
                
                if st.button("🚀 Generate Smart Bundles", type="primary"):
                    with st.spinner("Analyzing inventory and generating bundles..."):
                        try:
                            resp = api_get(f"/api/bundles/smart?n_slow_movers={n_slow}&discount_pct={discount_pct}")
                            bundles = resp.get("smart_bundles", [])
                            
                            if not bundles:
                                st.info("No bundle recommendations found. Try adjusting the parameters.")
                            else:
                                st.success(f"Generated {len(bundles)} bundle recommendations!")
                                
                                for i, bundle in enumerate(bundles[:20]):  # Show top 20
                                    with st.expander(
                                        f"**{bundle['bundle_id']}**: {bundle['best_seller']['item_name']} + {bundle['item_to_clear']['item_name']}",
                                        expanded=(i < 3)
                                    ):
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.markdown("**🌟 Best Seller**")
                                            st.write(f"**{bundle['best_seller']['item_name']}**")
                                            st.caption(f"ID: {bundle['best_seller']['item_id']} · Sales: {bundle['best_seller']['total_sales']:,} units")
                                        with col2:
                                            reason_icon = "⏰" if bundle['item_to_clear']['reason'] == "near_expiry" else "🐢"
                                            st.markdown(f"**{reason_icon} Item to Clear**")
                                            st.write(f"**{bundle['item_to_clear']['item_name']}**")
                                            st.caption(f"ID: {bundle['item_to_clear']['item_id']} · Reason: {bundle['item_to_clear']['reason'].replace('_', ' ').title()}")
                                        
                                        st.markdown("---")
                                        m1, m2, m3 = st.columns(3)
                                        with m1:
                                            st.metric("Co-purchase History", f"{bundle['copurchase_history']} orders")
                                        with m2:
                                            st.metric("Pairing Score", f"{bundle['pairing_score']:.1f}")
                                        with m3:
                                            st.metric("Suggested Discount", f"{bundle['suggested_discount_pct']}%")
                                        
                                        st.info(f"💡 **Recommendation:** {bundle['recommendation']}")
                                        
                        except requests.exceptions.Timeout:
                            st.error("Request timed out. Make sure the API has loaded data first.")
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            else:  # Manual mode
                st.markdown("#### Enter Near-Expiry Item IDs")
                st.caption("Enter item IDs that are approaching their expiry date, separated by commas.")
                
                # Load items for reference
                if "cache_items_with_demand" not in st.session_state:
                    st.session_state.cache_items_with_demand = None
                
                items_list = st.session_state.cache_items_with_demand
                if items_list is None:
                    try:
                        resp = api_get("/api/items/with-demand?n=100")
                        items_list = resp.get("items", [])
                        st.session_state.cache_items_with_demand = items_list
                    except:
                        items_list = []
                
                if items_list:
                    with st.expander("📋 View available item IDs for reference"):
                        df_items = pd.DataFrame(items_list)[["item_id", "item_name", "total_quantity"]]
                        st.dataframe(df_items, use_container_width=True, hide_index=True)
                
                near_expiry_input = st.text_area(
                    "Near-expiry item IDs (comma-separated)",
                    placeholder="e.g., 60036, 60822, 59915",
                    help="Enter the IDs of items that are close to their expiry date"
                )
                
                if st.button("🚀 Generate Bundles for Near-Expiry Items", type="primary"):
                    if not near_expiry_input.strip():
                        st.warning("Please enter at least one item ID.")
                    else:
                        try:
                            # Parse item IDs
                            item_ids = [int(x.strip()) for x in near_expiry_input.split(",") if x.strip().isdigit()]
                            if not item_ids:
                                st.error("No valid item IDs found. Please enter numeric IDs separated by commas.")
                            else:
                                with st.spinner(f"Generating bundles for {len(item_ids)} near-expiry items..."):
                                    resp = api_post("/api/bundles/smart", {
                                        "near_expiry_item_ids": item_ids,
                                        "discount_pct": discount_pct
                                    })
                                    bundles = resp.get("smart_bundles", [])
                                    
                                    if not bundles:
                                        st.info("No bundle recommendations found for the specified items.")
                                    else:
                                        st.success(f"Generated {len(bundles)} bundle recommendations for near-expiry items!")
                                        
                                        for i, bundle in enumerate(bundles[:20]):
                                            with st.expander(
                                                f"**{bundle['bundle_id']}**: {bundle['best_seller']['item_name']} + {bundle['item_to_clear']['item_name']}",
                                                expanded=(i < 3)
                                            ):
                                                col1, col2 = st.columns(2)
                                                with col1:
                                                    st.markdown("**🌟 Best Seller**")
                                                    st.write(f"**{bundle['best_seller']['item_name']}**")
                                                    st.caption(f"Sales: {bundle['best_seller']['total_sales']:,} units")
                                                with col2:
                                                    st.markdown("**⏰ Near-Expiry Item**")
                                                    st.write(f"**{bundle['item_to_clear']['item_name']}**")
                                                    st.caption(f"ID: {bundle['item_to_clear']['item_id']}")
                                                
                                                st.markdown("---")
                                                m1, m2, m3 = st.columns(3)
                                                with m1:
                                                    st.metric("Co-purchase History", f"{bundle['copurchase_history']} orders")
                                                with m2:
                                                    st.metric("Pairing Score", f"{bundle['pairing_score']:.1f}")
                                                with m3:
                                                    st.metric("Suggested Discount", f"{bundle['suggested_discount_pct']}%")
                                                
                                                st.info(f"💡 **Recommendation:** {bundle['recommendation']}")
                                                
                        except Exception as e:
                            st.error(f"Error: {e}")
        
        with tab2:
            st.subheader("🎁 Surprise Bags")
            st.markdown("""
            **Surprise Bags** are mystery bags sold at a fixed low price. Customers don't know the exact contents - 
            they just know they're getting great value while helping reduce food waste!
            
            *Perfect when you have many near-expiry items to clear at once.*
            """)
            
            st.markdown("---")
            
            surprise_mode = st.radio(
                "Generation mode",
                ["Auto (slow-moving items)", "Manual (specify near-expiry items)"],
                horizontal=True,
                key="surprise_mode"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                surprise_discount = st.slider("Discount (%)", 30, 70, 50, 5, key="surprise_discount")
            with col2:
                st.markdown("**Fixed Prices (customize below)**")
            
            # Custom pricing
            with st.expander("⚙️ Customize Bag Prices"):
                price_col1, price_col2, price_col3 = st.columns(3)
                with price_col1:
                    price_small = st.number_input("Small Bag Price", min_value=1.0, value=29.0, step=5.0)
                with price_col2:
                    price_medium = st.number_input("Medium Bag Price", min_value=1.0, value=49.0, step=5.0)
                with price_col3:
                    price_large = st.number_input("Large Bag Price", min_value=1.0, value=79.0, step=5.0)
            
            if surprise_mode == "Auto (slow-moving items)":
                n_slow_surprise = st.slider("Number of slow-moving items to consider", 10, 50, 30, key="n_slow_surprise")
                
                if st.button("🎁 Generate Surprise Bag Plan", type="primary"):
                    with st.spinner("Creating surprise bag recommendations..."):
                        try:
                            resp = api_get(f"/api/bundles/surprise-bags?n_slow_movers={n_slow_surprise}&discount_pct={surprise_discount}")
                            _display_surprise_bags(st, resp, price_small, price_medium, price_large)
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            else:  # Manual mode
                st.markdown("#### Enter Near-Expiry Item IDs")
                
                # Show reference items
                if "cache_items_with_demand" in st.session_state and st.session_state.cache_items_with_demand:
                    with st.expander("📋 View available item IDs"):
                        df_items = pd.DataFrame(st.session_state.cache_items_with_demand)[["item_id", "item_name", "total_quantity"]]
                        st.dataframe(df_items, use_container_width=True, hide_index=True)
                
                surprise_items_input = st.text_area(
                    "Near-expiry item IDs (comma-separated)",
                    placeholder="e.g., 60036, 60822, 59915, 59908, 59949, 59911",
                    help="Enter IDs of items approaching expiry. The more items, the more surprise bags!",
                    key="surprise_items"
                )
                
                if st.button("🎁 Generate Surprise Bags for These Items", type="primary"):
                    if not surprise_items_input.strip():
                        st.warning("Please enter at least 5 item IDs for surprise bags.")
                    else:
                        try:
                            item_ids = [int(x.strip()) for x in surprise_items_input.split(",") if x.strip().isdigit()]
                            if len(item_ids) < 5:
                                st.warning(f"You entered {len(item_ids)} items. Surprise bags work best with at least 5 items.")
                            
                            with st.spinner(f"Creating surprise bags for {len(item_ids)} items..."):
                                resp = api_post("/api/bundles/surprise-bags", {
                                    "item_ids": item_ids,
                                    "discount_pct": surprise_discount,
                                    "fixed_prices": {
                                        "small": price_small,
                                        "medium": price_medium,
                                        "large": price_large
                                    }
                                })
                                _display_surprise_bags(st, resp, price_small, price_medium, price_large)
                        except Exception as e:
                            st.error(f"Error: {e}")
        
        with tab3:
            st.subheader("🐢 Slow-Moving Items")
            st.markdown("Items with low sales velocity that should be prioritized for bundling or clearance.")
            
            max_daily = st.slider("Max average daily demand", 0.1, 5.0, 1.0, 0.1)
            n_items = st.slider("Number of items to show", 10, 100, 30)
            
            if st.button("Load Slow-Moving Items", type="primary"):
                with st.spinner("Loading..."):
                    try:
                        resp = api_get(f"/api/items/slow-moving?n={n_items}&max_daily_avg={max_daily}")
                        items = resp.get("slow_moving_items", [])
                        if items:
                            df = pd.DataFrame(items)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            st.caption(f"Showing {len(items)} items with avg daily demand ≤ {max_daily}")
                        else:
                            st.info("No slow-moving items found with these criteria.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with tab4:
            st.subheader("🌟 Best Sellers")
            st.markdown("Top-performing items ideal for pairing with slow-movers in bundles.")
            
            n_best = st.slider("Number of best sellers to show", 10, 50, 20)
            
            if st.button("Load Best Sellers", type="primary"):
                with st.spinner("Loading..."):
                    try:
                        resp = api_get(f"/api/items/best-sellers?n={n_best}")
                        items = resp.get("best_sellers", [])
                        if items:
                            df = pd.DataFrame(items)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No items found.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.sidebar.markdown("---")
    st.sidebar.caption("Fresh Flow Insights · Deloitte x AUC Hackathon")


run()
