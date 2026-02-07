# **FreshFlow AI**

## **Project Name and Description**

**FreshFlow AI** is an inventory intelligence system built for the **Fresh Flow Markets** challenge in the **Deloitte x AUC Hackathon**.

Fresh food businesses often face two costly problems at the same time: **waste from overstocking** and **lost sales from stockouts**. These issues usually come from reactive inventory decisions and poor demand visibility. FreshFlow AI helps solve this by forecasting short-term demand, translating it into ingredient-level consumption, and generating clear, data-backed recommendations that allow businesses to act before problems happen.

Our focus was not just building models, but creating a solution that a business could actually use.

## **Features**

### **Data Preparation and Cleaning**
- Handled missing and inconsistent IDs across tables
- Safely merged transactional datasets and standardized numeric fields
- Ensured reliable demand signals before forecasting

### **Demand Forecasting**
- Built a clean daily demand dataset per menu item
- Forecasted short-term demand (up to **30 days ahead**) using historical trends and weekly patterns

### **Ingredient Consumption Mapping**
- Converted menu-item demand into ingredient-level usage using **Bill of Materials (BOM)** data

### **Inventory Simulation**
- Simulated future inventory levels day by day using forecasted consumption and inventory snapshots

### **Risk Identification**
- Flagged **stockout-risk** and **waste-risk** items based on inventory levels, expiry risk, and demand variability

### **Actionable Recommendations**
- Suggested actions such as reordering early, reducing prep quantities, or discounting near-expiry items

### **Dashboard and Insights**
- Displayed forecasts, inventory risks, and recommendations in a simple, easy-to-read interface

## **Technologies Used**

- **Python** for data processing, modeling, and analysis
- **Pandas & NumPy** for data cleaning, aggregation, and feature engineering

### **Machine Learning Models**
- **Linear Regression** as a baseline forecasting model
- **Random Forest** to capture non-linear demand patterns
- **XGBoost** for higher-performance forecasting and comparison

- **Scikit-learn & XGBoost** for model training and evaluation
- **GitHub** for version control and team collaboration

## **Installation**

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo-name/freshflow-ai.git
   ```

2. **Navigate to the project folder**
   ```bash
   cd freshflow-ai
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (for AI chatbot)
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

## **Usage**

### Quick Start

1. Place the provided datasets in the **data/** folder

2. **Build the cache** (required before first run):
   ```bash
   python scripts/build_cache.py
   ```

3. **Start the API server** (in one terminal):
   ```bash
   # Windows PowerShell
   $env:PYTHONPATH = (Get-Location).Path; python -m src.main
   
   # Linux/Mac
   PYTHONPATH=. python -m src.main
   ```

4. **Start the Streamlit UI** (in another terminal):
   ```bash
   python -m streamlit run src/app_streamlit.py
   ```

5. Open http://localhost:8501 in your browser

## **Testing**

We use **pytest** for testing. Tests are located in the `tests/` directory.

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api_endpoints.py -v

# Run tests with coverage report
pytest tests/ --cov=src --cov-report=html

# Run only fast tests (skip slow/integration tests)
pytest tests/ -v -m "not slow"
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── test_helpers.py          # Tests for utility functions
├── test_inventory_service.py # Tests for inventory service
├── test_api_endpoints.py    # Tests for API endpoints
├── test_chatbot.py          # Tests for AI chatbot service
└── test_cache_builder.py    # Tests for P&L and KPI calculations
```

### Writing New Tests

1. Create a new file in `tests/` named `test_<feature>.py`
2. Use pytest fixtures for setup/teardown
3. Group related tests in classes
4. Use descriptive test names: `test_<what>_<expected_behavior>`

Example:
```python
import pytest

class TestMyFeature:
    def test_feature_returns_expected_value(self):
        result = my_function(input)
        assert result == expected
```

## **Architecture**

**FreshFlow AI** follows a clear end-to-end flow:

Raw Transactional Data  
→ Data Cleaning & Validation  
→ Demand Dataset Creation  
→ Demand Forecasting  
→ Ingredient Consumption (BOM)  
→ Inventory Simulation  
→ Risk Scoring  
→ Business Recommendations

This modular structure keeps the solution easy to explain, maintain, and extend.

## **Team Contribution**

All team members contributed **equally** across data preparation, modeling, analysis, and presentation.

## **Final Note**

FreshFlow AI was built with a **consulting mindset**: start from the business problem, work with imperfect real-world data, and deliver practical recommendations with measurable impact.

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
