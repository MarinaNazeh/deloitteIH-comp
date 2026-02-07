# Fresh Flow Markets – Data Investigation & Solution Plan

**Use case:** Inventory Management (Deloitte x AUC Hackathon)  
**Data sources:** `merged_complete` (10 parts) + `sorted_most_ordered.csv`

---

## 1. Dataset overview

| Dataset | Rows (approx.) | Description |
|--------|----------------|-------------|
| **merged_complete** | ~676,782 | One row per **order line**: order items joined with orders and place (store) attributes. |
| **sorted_most_ordered** | ~53,147 | One row per **item**: items ranked by total number of orders (demand popularity). |

**Note:** All monetary values are in **DKK** (Danish Krone). If you have raw UNIX timestamps elsewhere, use `FROM_UNIXTIME()` (MySQL) or `pd.to_datetime(..., unit='s')` (Python).

---

## 2. sorted_most_ordered.csv

### 2.1 Columns (3)

| Column | Type | Description |
|--------|------|-------------|
| **item_id** | int | Unique product/menu item identifier. |
| **item_name** | string | Display name (e.g. "Chinabox Lille", "ØL", "Ristet Hotdog"). |
| **order_count** | int | Total number of times this item was ordered (across all time/locations). |

### 2.2 What it’s good for

- **Demand prioritization:** Focus forecasting and inventory on high-velocity items (e.g. top 100–500 by `order_count`).
- **Prep quantities:** Use relative popularity to set base prep levels (e.g. “Chinabox Lille” vs “Chinabox Stor”).
- **Bundles/promotions:** Identify items that already move well and pair them with slower or near-expiry items.
- **Join key:** Use `item_id` to join with `merged_complete` for time-series and store-level analysis.

### 2.3 Sample (top items)

- Unspecified (215,644), Chinabox Lille (143,976), Øl/Vand/Spiritus (143,596), Entré (137,115), Chinabox Mellem (126,788), ØL (110,748), etc.

---

## 3. merged_complete (parts 1–10)

Single wide table: **order item** + **order** + **place (store)**. 245 columns total.

### 3.1 Column groups

#### A. Order item (rows = order lines) — indices 0–22

| Index | Column | Use for inventory / demand |
|-------|--------|----------------------------|
| 0 | id_item | Line ID |
| 2 | created_item | **Order line date/time** (time series, daily/weekly demand) |
| 4 | title | Item name at time of order |
| 7 | cost | **Cost (DKK)** – waste/cost analysis |
| 12 | **item_id** | **Join to sorted_most_ordered, aggregate demand** |
| 13 | order_id | Order grouping |
| 16 | price | **Price (DKK)** – revenue, margin |
| 17 | **quantity** | **Demand per line – core for forecasting** |
| 21 | status_item | Filter (e.g. exclude cancelled) |
| 22 | vat_amount_item | Optional for margin |

**Key for demand:** `item_id`, `quantity`, `created_item` (or `created_order`), `place_id`.

#### B. Order — indices 23–55

| Index | Column | Use for inventory / demand |
|-------|--------|----------------------------|
| 23 | id_order | Order ID |
| 25 | **created_order** | **Order date/time** – alternative for daily/weekly aggregation |
| 38 | payment_method | Optional segmentation |
| 40 | **place_id** | **Store/location – demand by place** |
| 46 | source | Channel (e.g. App, Counter) |
| 49 | status_order | Filter (e.g. Closed only) |
| 52 | total_amount | Order value (DKK) |
| 54 | type | Takeaway / Eat-in / Delivery – **weekend vs weekday, channel** |

**Key for demand:** `place_id`, `created_order`, `type`, `status_order`.

#### C. Place (store) — indices 56–244

| Index | Column | Use for inventory / demand |
|-------|--------|----------------------------|
| 56 | id | Place ID (same as place_id on order) |
| 60 | title_store | Store name |
| 108 | timezone | **Correct local date for daily demand** |
| 110 | business_name | Store label |
| 111 | area | **Region/area – external factors (e.g. weather by area)** |
| 112 | street_address | Location |
| 139 | **inventory_management** | **Flag: stores using inventory – target for prep/waste features** |
| 205–206 | latitude, longitude | Optional: weather, events |

**Key for demand:** `id` (place), `timezone`, `area`, `inventory_management`.

### 3.2 Date/time handling

- In the current merged file, **created_item** and **created_order** appear as **date strings** (e.g. `12/02/2021 14:17`). Use them for:
  - Extracting **date** (day) for daily demand.
  - Extracting **day of week** (weekends vs weekdays).
  - Extracting **hour** for intraday patterns (prep timing).
- If you (re-)generate data from raw tables with **UNIX timestamps**, convert with `pd.to_datetime(..., unit='s')` and respect **timezone** (e.g. `Europe/Copenhagen`) for correct daily buckets.

### 3.3 Suggested filters

- **status_order** = Closed (or equivalent “completed”) so demand reflects actual sales.
- **status_item** = completed/pending (exclude cancelled lines).
- Optionally **inventory_management** = 1 for stores that use inventory (if you want to focus there).

---

## 4. How to use the data – business questions → features

### 4.1 “How do we accurately predict daily, weekly, and monthly demand?”

- **From merged_complete:**
  - Aggregate by **(date, item_id)** or **(date, item_id, place_id)**:
    - `date` from `created_order` or `created_item`
    - Sum of `quantity` = demand per day (optionally by place).
  - Use **place_id** and **timezone** for store-level or chain-level forecasts.
- **From sorted_most_ordered:**
  - Restrict modelling to top N items by `order_count` to reduce noise and scale.
- **Features to engineer:** day of week, week of year, month, holiday flag (external), “weekend” flag.

**Deliverable:** Daily/weekly/monthly demand forecasts per item (and optionally per place), e.g. with a simple model (moving average, exponential smoothing) or ML (ARIMA, Prophet, or lightweight ML).

---

### 4.2 “What prep quantities should kitchens prepare to minimize waste?”

- **From merged_complete:**
  - Historical **quantity** by **item_id** (and optionally **place_id**) by day/hour.
  - **cost** and **price** to quantify waste (cost of over-prep) and stockout (lost margin).
- **From sorted_most_ordered:**
  - **order_count** to set base prep tiers (high/medium/low volume).
- **Approach:**
  - Use demand forecasts (above) to set **prep quantity** (e.g. percentile of forecast, or forecast + safety stock).
  - Optionally output “prep list” per store/date (top items + suggested quantities).

**Deliverable:** Prep suggestions per item (and per place/date) that balance waste and stockouts.

---

### 4.3 “How can we prioritize inventory based on expiration dates?”

- **Data gap:** No expiration-date column in these two datasets. Options:
  - **Assumption layer:** Assume short shelf-life for certain categories (e.g. fresh, dairy) and use **item_id** (or item name / category if you add it) to assign “shelf-life tier”.
  - **External:** If you get inventory/expiry data later, join by **item_id** and **place_id**.
- **From current data:**
  - Use **sorted_most_ordered** and **merged_complete** demand to prioritize **which items** get expiry-based rules first (e.g. high value + high velocity).

**Deliverable:** Priority list or “expiry risk” score per item (and place), plus a note that full expiry prioritization needs an expiry data source.

---

### 4.4 “What promotions or bundles can move near-expired items profitably?”

- **From merged_complete:**
  - **item_id**, **price**, **cost**, **quantity** to compute margin and volume per item.
  - **order_id** to see which items are often in the same basket (association rules / co-occurrence).
- **From sorted_most_ordered:**
  - High `order_count` items as “anchors” for bundles; low `order_count` or declining items as “candidates” for promotions.
- **Approach:**
  - Basket analysis (e.g. “items often bought with X”) to suggest bundles.
  - Margin and volume to rank promotions (move volume without killing margin).

**Deliverable:** Suggested bundles or promotions (e.g. “pair item A with item B” or “discount item C by X%”) with simple revenue/margin impact.

---

### 4.5 “How do external factors (weather, holidays, weekends) impact sales?”

- **From merged_complete:**
  - **created_order** / **created_item** → **date**, **day of week**, **month**.
  - **place_id** → join to **area**, **latitude/longitude** for weather/region.
  - **type** (Takeaway / Eat-in / Delivery) to see channel mix by day type.
- **Approach:**
  - Add **weekend** and **holiday** (e.g. Danish holidays) flags.
  - Correlate or model daily demand vs day type; optionally integrate weather API by area/coordinates later.

**Deliverable:** Insights (e.g. “weekends +20% demand for item X”) and optional demand model that includes weekend/holiday (and later weather) features.

---

## 5. Technical implementation plan

### 5.1 Data loading

- **Merged data:** Load one or more parts with `pd.read_csv("merged_complete_partN.csv")`; optionally use `chunksize` for very large parts. Concatenate parts only if you need full history in memory; otherwise process per part and aggregate.
- **Sorted items:** `pd.read_csv("sorted_most_ordered.csv")` once; use for joins and filters.

### 5.2 Core pipelines

1. **Demand aggregation**
   - Parse `created_order` or `created_item` to date (and optionally hour).
   - Filter by `status_order` / `status_item`.
   - Aggregate: `groupby([date, item_id])` or `groupby([date, item_id, place_id])` → sum(`quantity`), optionally mean(`cost`), mean(`price`).

2. **Store-level and item-level views**
   - Join aggregated demand to `sorted_most_ordered` on `item_id` for popularity and naming.
   - Join to place attributes (from one row per place in merged) for `timezone`, `area`, `inventory_management`.

3. **Forecasting**
   - Time series per (item_id) or (item_id, place_id): daily (or weekly) demand.
   - Features: day of week, month, weekend, holiday; then add prep suggestions.

4. **Basket / bundles**
   - From merged: group by `order_id`, collect `item_id` (and names); run association rules or co-occurrence; combine with margin from `price`/`cost`.

### 5.3 Suggested repo structure (align with hackathon)

```
src/
  models/       # Data models, demand model, prep model
  services/     # Demand aggregation, forecasting, prep logic, bundles
  utils/        # Date/time (incl. timezone), parsing, helpers
  api/          # Endpoints: demand by item/place/date, prep suggestions, bundles
data/           # Keep part files and sorted_most_ordered here or linked
docs/           # This file, architecture, column list
```

### 5.4 Column reference

- Full list of 245 columns: see **docs/merged_columns.txt**.
- For demand and inventory, the main columns are:
  - **Demand:** `item_id`, `quantity`, `created_order` or `created_item`, `place_id`, `order_id`
  - **Value:** `cost`, `price`, `total_amount`
  - **Context:** `type`, `source`, `status_order`, `status_item`, `timezone`, `area`, `inventory_management`

---

## 6. Summary

| Asset | Best use |
|-------|----------|
| **sorted_most_ordered** | Item popularity; prioritization; join key; prep tiers; bundle anchors. |
| **merged_complete (parts)** | Time-series demand (date + item + place); cost/price; baskets; store and channel context. |

Using **item_id**, **quantity**, **created_order**/ **created_item**, and **place_id** from merged, plus **order_count** and **item_name** from sorted_most_ordered, you can support demand forecasting, prep quantities, prioritization (with assumptions or future expiry data), bundles/promotions, and weekend/holiday (and later weather) impact – and document clear business value for the Fresh Flow Markets use case.
