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


![WhatsApp Image 2026-02-07 at 11 39 37 PM](https://github.com/user-attachments/assets/9404ea2f-9e54-48a1-bb95-0c79daeb7377)
![WhatsApp Image 2026-02-07 at 11 39 37 PM (1)](https://github.com/user-attachments/assets/45e9269e-537b-47cc-8181-49b737c1747d)



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

![WhatsApp Image 2026-02-07 at 11 42 10 PM](https://github.com/user-attachments/assets/6eb626bb-b908-42c4-bb87-1d158af099b3)


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
  ![WhatsApp Image 2026-02-07 at 11 40 30 PM](https://github.com/user-attachments/assets/db03c15d-6b2b-4cdd-b6c6-2b7d6bc36a2c)
  ![WhatsApp Image 2026-02-07 at 11 41 17 PM](https://github.com/user-attachments/assets/2f74e5a7-6ac3-46dc-8bdb-dfae5435e6d8)



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

## **Installation, Setup, & Usage **

Follow the steps below to set up and run **FreshFlow AI** locally.

---

### **1. Clone the Repository**

```bash
git clone https://github.com/MarinaNazeh/deloitteIH-comp.git
```

---

### **2. Prepare the Dataset**

1. Place the provided `data.zip` file inside the project root directory  
2. Extract the ZIP file  
3. Ensure that all CSV files are located inside a folder named `data/`

Your project structure should look like this:
```
freshflow-ai/
├── data/
│   ├── *.csv
├── src/
├── requirements.txt
└── README.md
```

---

### **3. Install Dependencies**

Make sure you are using Python 3.9+.

```bash
pip install -r requirements.txt
```

---

### **4. Set the Python Path**

This ensures the project modules are correctly resolved.

**Windows (Command Prompt):**
```cmd
set PYTHONPATH=%CD%
```

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH = (Get-Location).Path
```

---

## **Running the Project**

### **1. Run the Data Pipeline**

This step performs data loading, cleaning, feature engineering, and forecasting.

```bash
python -m src.main
```

This will generate the processed outputs used by the dashboard.

---

### **2. Launch the Streamlit Dashboard**

```bash
python -m streamlit run src/app_streamlit.py
```

Once running, the application will open automatically in your browser.

Use the navigation panel to explore:
- KPI Dashboard & Impact Metrics
- Performance & Business Analytics
- Demand Predictions
- Inventory & Replenishment Recommendations
- AI-powered Chatbot

---

## **Chat API Configuration (Optional)**

The AI assistant requires an API key to function.

### **1. Create a `.env` File**

In the project root directory, create a file named `.env`.

### **2. Add the Configuration Below**

Replace the placeholder values with your own API credentials.

```env
# API Key for the chat model (required for chatbot functionality)
CHAT_API_KEY=your_api_key_here

# API Base URL (optional – defaults to OpenAI-style APIs)
# Examples:
# Groq: https://api.groq.com/openai/v1
# OpenRouter: https://openrouter.ai/api/v1
# Local models: your local endpoint
CHAT_API_BASE=https://api.groq.com/openai/v1

# Model name
CHAT_MODEL=moonshotai/kimi-k2-instruct-0905
```

### **3. Restart the Dashboard**

After saving the `.env` file, restart the Streamlit app for the changes to take effect.

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

## **Team Members**

Marina and Mariam were responsible for data cleaning, data merging, preprocessing, and the development of the dashboard.

Sama, AbdelRahman, and Areeg implemented the modeling phase, including the Linear Regression, LightGBM (LGBM), Random Forest, ensemble models, as well as the inventory management code.

---

## **Final Note**

FreshFlow AI was built with a **consulting mindset**: start from a real business problem, work with imperfect real-world data, and deliver insights that are explainable, actionable, and aligned with business decision-making.
