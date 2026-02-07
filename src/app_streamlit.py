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
        ["Performance & data", "Demand prediction", "Prep suggestions", "Top items", "Bundle ideas"],
        label_visibility="collapsed",
    )

    # ----- Performance & data -----
    if page == "Performance & data":
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
            ensemble = metrics.get("ensemble", {})
            if ensemble:
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
            st.dataframe(pd.DataFrame(metrics).T.round(4), use_container_width=True, hide_index=True)
        else:
            st.info("Run `python scripts/train_demand_models.py` to see model accuracy here.")

    # ----- Demand prediction -----
    elif page == "Demand prediction":
        st.header("Predict demand")
        col1, col2 = st.columns(2)
        with col1:
            item_id = st.number_input("Item ID", min_value=1, value=5936269, step=1)
            period = st.selectbox("Forecast period", ["daily", "weekly", "monthly"])
        with col2:
            place_id = st.text_input("Place ID (optional)", "")
        if st.button("Get forecast", type="primary"):
            with st.spinner("Loading…"):
                try:
                    body = {"item_id": item_id, "period": period}
                    if place_id and place_id.strip():
                        body["place_id"] = int(place_id) if place_id.strip().isdigit() else place_id.strip()
                    out = api_post("/api/inventory/predict", body)
                    st.metric("Predicted demand", f"{out['predicted_demand']:,.2f}", out.get("unit", "units"))
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

    # ----- Bundle ideas -----
    elif page == "Bundle ideas":
        st.header("Bundle suggestions")
        top_n = st.slider("Number of pairs", 5, 20, 10)
        if st.button("Get suggestions", type="primary"):
            with st.spinner("Loading…"):
                try:
                    out = api_get("/api/bundles/suggestions", params={"top_n": top_n})
                    st.dataframe(pd.DataFrame(out["bundle_suggestions"]), use_container_width=True, hide_index=True)
                except requests.exceptions.Timeout:
                    st.error("Timed out. Load the Performance page first, then try again.")
                except Exception as e:
                    st.error(str(e))

    st.sidebar.markdown("---")
    st.sidebar.caption("Fresh Flow Insights · Deloitte x AUC Hackathon")


run()
