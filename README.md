# Fresh Flow Insights

**Deloitte x AUC Hackathon – Use Case 1: Fresh Flow Markets (Inventory Management)**

A data-driven solution for demand forecasting, prep quantity suggestions, and bundle recommendations to reduce waste and stockouts. Built on merged order data and item popularity.

---

## Project Name & Description

**Fresh Flow Insights** helps restaurant and grocery operators balance inventory by:

- **Predicting demand** (daily, weekly, monthly) per item and optionally per store
- **Suggesting prep quantities** for top-selling items with a configurable safety factor
- **Recommending reorder points** based on recent demand and lead time
- **Surfacing bundle opportunities** (items often bought together) for promotions

The system uses historical order data from `merged_complete` (order lines with store and item info) and `sorted_most_ordered` (item popularity) to drive forecasts and prep lists.

---

## Features

| Feature | Description | API / UI |
|--------|-------------|----------|
| **Demand prediction** | Predicted quantity for an item (daily/weekly/monthly), optionally by place | `POST /api/inventory/predict` |
| **Prep suggestions** | Top N items with suggested prep quantity (demand × safety factor) | `GET/POST /api/inventory/prep` |
| **Reorder point** | Recommended reorder point for an item given lead time | `GET /api/inventory/reorder/<item_id>` |
| **Demand summary** | Total quantity, unique items, date range (optional filters) | `GET /api/demand/summary` |
| **Top items** | Most popular items by order count or by demand in dataset | `GET /api/items/top` |
| **Bundle suggestions** | Pairs of items frequently bought together | `GET /api/bundles/suggestions` |
| **Full recommendations** | One-item summary: demand, reorder point, status | `GET /api/inventory/recommendations/<item_id>` |

**UI:** A Streamlit dashboard (`src/app_streamlit.py`) provides forms and tables for prediction, prep suggestions, top items, and bundles. Start the API first, then run Streamlit.

---

## Technologies Used

- **Python 3.x**
- **pandas, numpy** – data loading and aggregation
- **Flask** – REST API
- **Streamlit** – optional web UI
- **requests** – API client from Streamlit app
- **pytest** – tests

No external APIs; all logic uses the provided CSV data.

---

## Installation

1. **Clone and enter the project**
   ```bash
   cd path/to/deloitteIH-comp
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   # source venv/bin/activate  # Linux/macOS
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Data**
   - Place `merged_complete_part1.csv` … `merged_complete_part10.csv` and `sorted_most_ordered.csv` in the **`data/`** folder.
   - By default only **one part** is loaded for fast startup. To use more data, set `MAX_MERGED_PARTS` in `config/settings.py` or load more parts in code.

---

## How to run the whole system

Everything is **precomputed** into a **cache**. You build the cache once, then the API and UI only read from it (no slow first load).

### Step 1 — One-time setup

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Put data in `data/`:** `merged_complete_part1.csv` (and optionally more parts), `sorted_most_ordered.csv`
3. **Build the cache** (run once; takes 1–2 minutes):

```bash
cd path\to\deloitteIH-comp
set PYTHONPATH=%CD%        # Windows
python scripts/build_cache.py
```

This writes `cache/demand_daily.csv`, `cache/items.csv`, `cache/order_items.csv`, `cache/summary.json`, `cache/demand_history.json`. The API and UI use these only.

4. **(Optional)** Train models: `python scripts/train_demand_models.py`

### Step 2 — Run the app

**Option A — One command (Windows)**  
Double‑click **`run.bat`** or:

```bash
run.bat
```

Starts the API in a new window, then the Streamlit UI. Open **http://localhost:8501**.

**Option B — Two terminals**

**Terminal 1 — API:**
```bash
set PYTHONPATH=%CD%
python -m src.main
```

**Terminal 2 — UI:**
```bash
set PYTHONPATH=%CD%
python -m streamlit run src/app_streamlit.py
```

Open **http://localhost:8501**. The API loads from `cache/` and starts quickly.

---

## Usage (details)

### API only

From the project root:

```bash
set PYTHONPATH=%CD%   # Windows
python -m src.main
```

API runs at **http://127.0.0.1:5000**.

### Streamlit UI only (API must be running)

```bash
set PYTHONPATH=%CD%
python -m streamlit run src/app_streamlit.py
```

Open the URL shown in the terminal (e.g. http://localhost:8501).

### Example API calls

- **Health:** `GET http://127.0.0.1:5000/api/health`
- **Predict demand:** `POST http://127.0.0.1:5000/api/inventory/predict`  
  Body: `{"item_id": 5936269, "period": "daily"}`
- **Prep suggestions:** `GET http://127.0.0.1:5000/api/inventory/prep?top_n=20`
- **Top items:** `GET http://127.0.0.1:5000/api/items/top?n=50`
- **Bundles:** `GET http://127.0.0.1:5000/api/bundles/suggestions?top_n=10`

---

## Architecture

```
Project root
├── config/settings.py      # Paths, MERGED_COLS, MAX_MERGED_PARTS
├── src/
│   ├── main.py             # Entry point → Flask app
│   ├── api/routes.py       # Flask routes, lazy init of service
│   ├── models/data_loader.py   # Load merged parts + sorted_most_ordered, build demand_daily
│   ├── services/inventory_service.py  # Predict, prep, reorder, top items, bundles
│   ├── utils/helpers.py   # Date parsing (DD/MM/YYYY), aggregation
│   └── app_streamlit.py    # Streamlit UI (calls API)
├── tests/
│   └── test_helpers.py    # Unit tests for helpers
└── docs/
    ├── DATA_INVESTIGATION_AND_PLAN.md
    └── merged_columns.txt
```

**Flow:**  
`routes.py` lazily creates a `DataLoader` (using the `data/` folder), loads demand aggregates and `sorted_most_ordered`, then builds an `InventoryService`. Each endpoint calls into the service for predictions, prep list, reorder point, top items, or bundle pairs.

---

## Testing

From project root (with `PYTHONPATH` set to project root):

```bash
pytest tests/ -v
```

---

## Team Members

| Name | Role | Contributions |
|------|------|---------------|
| *[Add names]* | *[Role]* | *[Contributions]* |

*(Update with your team and run `git shortlog -sn --all` to check contribution distribution.)*

---

## Data & Business Value

- **Data:** Merged order-level data (item, quantity, date, place, order_id) and item popularity (`sorted_most_ordered`). See `docs/DATA_INVESTIGATION_AND_PLAN.md` for column list and usage.
- **Business questions addressed:**
  - **Daily/weekly/monthly demand** → prediction endpoint and prep suggestions
  - **Prep quantities to minimize waste** → prep suggestions with safety factor
  - **Prioritization** → top items and reorder points (expiry-based prioritization would require an expiry data source)
  - **Promotions/bundles** → bundle suggestions from co-occurrence in orders
  - **External factors** → date is available for weekend/holiday features; weather could be added via external API

All monetary values in the source data are in **DKK**.
