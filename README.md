# Pioneer Market Analytics Dashboard

An interactive analytics dashboard built with **Streamlit** to explore customer behavior, sales performance, temporal patterns and geographic insights using e-commerce transaction data.

---

## Business Questions

This dashboard is developed to answer the following key business questions:

1. **How can customers be characterized based on their purchasing behavior using RFM (Recency, Frequency, Monetary) Analysis?**  
2. **Which product categories contribute the most to total revenue, and how do their purchasing patterns differ?**  
3. **Are there specific temporal patterns that influence transaction volume and total revenue?**  
4. **Which regions contribute the most to revenue and customer volume?**

---

## Dashboard Sections

### 1. Customer Segmentation
- Distribution of RFM Scores  
- Customer Segment Distribution  
- Revenue Contribution by Segment  
- Key Insights  

*Provides an overview of customer value, loyalty, and purchasing behavior using RFM analysis.*

---

### 2. Temporal Insights
- Daily Transaction Volume (Day of Week)  
- Hourly Transaction Distribution  
- Monthly Transaction Trend  
- Key Insights  

*Identifies peak transaction periods, time-based purchasing behavior, and overall sales trends.*

---

### 3. Category Overview
- Revenue by Product Category  
- Product Count by Category  
- Average Order Value (AOV) by Category  
- Top 10 Products by Revenue  
- Key Insights  

*Highlights top-performing categories and products from both revenue and purchasing pattern perspectives.*

---

### 4. Geographic Analysis
- Revenue Distribution by State  
- Top States by Number of Orders  
- Customer Distribution by State  
- Regional Performance Summary  
- Key Insights  

*Shows geographic contribution to revenue and customer distribution across regions.*

---

## Deployed Application
The interactive dashboard is available at:  

---

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
