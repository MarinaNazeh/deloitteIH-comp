# **FreshFlow AI**

## **Project Name and Description**

**FreshFlow AI** is an end-to-end inventory and demand intelligence platform built for the **Fresh Flow Markets** challenge in the **Deloitte x AUC Hackathon**.

Fresh food businesses struggle with two recurring problems: **waste caused by overstocking** and **lost revenue from stockouts**. These challenges are often driven by limited visibility into historical performance and short-term demand. FreshFlow AI addresses this by combining data cleaning, demand forecasting, and business analytics into a single interactive dashboard that helps decision-makers understand what is happening, what is likely to happen next, and what actions to take.

Our focus was not just building predictive models, but delivering an **AI-assisted decision-support tool** that a business team could realistically use.

---

## **Features**

All features listed below are accessible directly through the application’s navigation menu.

### **Demand Prediction**
- User selects a menu item and forecast horizon
- Demand is predicted using:
  - Linear Regression
  - Random Forest
  - LightGBM
- The system displays individual model outputs and an averaged ensemble prediction to provide a balanced forecasttimereveperformanceforecaallmodelpredicttopinveite

  ![predictdemand](https://github.com/user-attachments/assets/e8ffe75c-5d19-477f-ac8d-1da56faf64e3)


### **KPI Dashboard & Impact Metrics**
- High-level overview of key business KPIs
- Profit & Loss analytics and operational performance indicators
- Simulated business impact metrics to quantify improvements from data-driven decisions

### **Performance & Historical Data**
- Analysis of cleaned historical transactional data
- Visualization of sales, quantities, and performance trends over time
- Provides context and grounding for all downstream analytics

  ![performanceandhistoricaldata](https://github.com/user-attachments/assets/5b9cb8a8-c37f-444a-80f9-de27ba45bb94)


### **Model Performance Analytics**
- Evaluation of forecasting models on held-out test data
- Comparison of model accuracy using metrics such as **Mean Squared Error**
- Visualization of model fit and performance to support transparent model selection

![allmodelprediction](https://github.com/user-attachments/assets/a2e62aa5-00af-48c1-8393-09e2b06c0ed9)


### **Business Analytics Dashboard**
- Channel-level analysis of customer behavior
  - Website vs mobile app
  - Takeaway vs eat-in
- Helps identify which channels drive volume and revenue
  
![ordertypeanalysis](https://github.com/user-attachments/assets/bfdb229e-922d-41e5-8e57-fb9d0a8a416e)


### **AI Assistant (Chatbot)**
- Interactive AI assistant connected to the cleaned dataset
- Allows users to ask natural-language questions about the data
- Designed to support quick exploration without manual analysis

![aiassistant](https://github.com/user-attachments/assets/358e5ace-2ed7-46db-a6e2-4dbbda7a98b4)

### **Prep Suggestions**
- Uses forecasted demand to recommend preparation quantities
- Designed to reduce over-prepping while maintaining service levels




### **Top Sellers**
- Identification of the highest-selling items based on historical data
- Supports prioritization, planning, and inventory focus

  ![topitems](https://github.com/user-attachments/assets/b521f1e6-12db-4dc1-bdbb-fe76734698db)


### **Inventory Health**
- Monitoring of inventory signals derived from forecasted consumption
- Highlights potential risk areas requiring attention

![inventoryhealthdashboard](https://github.com/user-attachments/assets/2d3180e4-7ac2-4955-9884-42b6e54c65a5)

### **Bundle Ideas**
- Identifies low-performing items and pairs them with strong sellers
- Uses an association score based on item co-occurrence in orders
- Designed to support promotions and reduce slow-moving stock

---

## **Technologies Used**

- **Python** – core language for data processing, modeling, and analysis  
- **Pandas & NumPy** – data cleaning, aggregation, and feature engineering  

### **Machine Learning Models**
- **Linear Regression** – baseline demand forecasting  
- **Random Forest** – captures non-linear demand patterns  
- **LightGBM (LGBM)** – efficient gradient-boosted model for higher accuracy  

### **Libraries & Tools**
- **Streamlit** – interactive dashboard and user interface  
- **GitHub** – version control and team collaboration  

---

## **Installation**

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo-name/freshflow-ai.git
   ```

2. **Navigate to the project directory**
   ```bash
   cd freshflow-ai
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## **Usage**

1. Place the provided datasets in the `data/` directory  
2. Run the data pipeline and model scripts to generate outputs  
3. Launch the dashboard:
   ```bash
   streamlit run app.py
   ```
4. Use the navigation panel to explore KPIs, analytics dashboards, predictions, and recommendations interactively

---

## **Architecture**

FreshFlow AI follows a modular, end-to-end architecture:

Raw Transactional Data  
→ Data Cleaning & Validation  
→ Exploratory & Business Analytics  
→ Demand Forecasting Models  
→ Ensemble Predictions  
→ Inventory & Bundle Insights  
→ Interactive Dashboard (Streamlit)

This structure keeps the solution easy to explain, maintain, and extend.

---

## **Team Members Contributions**

All team members contributed across **data preparation, modeling, analytics, UI development, and presentation**.  
Work was distributed collaboratively to ensure coverage of both technical implementation and business framing.

Marina and Mariam were responsible for data cleaning, data merging, preprocessing, and the development of the dashboard.

Sama, AbdelRahman, and Argeed implemented the modeling phase, including the Linear Regression, LightGBM (LGBM), Random Forest, ensemble models, as well as the inventory management code.
---

## **Final Note**

FreshFlow AI was built with a **consulting mindset**: start from a real business problem, work with imperfect real-world data, and deliver insights that are explainable, actionable, and aligned with business decision-making.
