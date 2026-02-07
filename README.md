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
   git clone https://github.com/your-repo-name/freshflow-ai.git

2. **Navigate to the project folder**
   cd freshflow-ai

3. **Install dependencies**
   pip install -r requirements.txt

## **Usage**

1. Place the provided datasets in the **data/** folder
2. Run the main pipeline:
   python src/run_freshflow_pipeline.py
3. Review the outputs in the **outputs/** folder or dashboard, including demand forecasts, inventory risk tables, and recommendations

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


