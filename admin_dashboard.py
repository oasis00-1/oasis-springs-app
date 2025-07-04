import streamlit as st
import pandas as pd

st.set_page_config(page_title="Oasis Springs - Admin Dashboard", layout="wide")
st.title("📊 Oasis Springs - Admin Dashboard")

# Load orders
try:
    df = pd.read_csv("orders.csv")
except FileNotFoundError:
    st.warning("No order data found (orders.csv not found). Make sure orders have been saved.")
    st.stop()

# Sidebar filters
st.sidebar.header("🔍 Filter Orders")
name_filter = st.sidebar.text_input("Search by Customer Name")
location_filter = st.sidebar.selectbox("Filter by Location", ["All"] + sorted(df["Location"].dropna().unique()))
date_range = st.sidebar.date_input("Filter by Date Range", [])

# Convert 'Date' column to datetime
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Apply filters
if name_filter:
    df = df[df["Name"].str.contains(name_filter, case=False, na=False)]
if location_filter != "All":
    df = df[df["Location"] == location_filter]
if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range)
    df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

# Summary stats
st.subheader("📈 Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Orders", len(df))
col2.metric("Total Sales (Ksh)", f"{df['Total'].sum():,.0f}")
col3.metric("Unique Customers", df['Name'].nunique())

# Orders table
st.subheader("📋 Order Details")
st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)

# Optional export
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download Filtered Orders (CSV)",
    data=csv,
    file_name="filtered_orders.csv",
    mime="text/csv"
)
