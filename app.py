# app.py — FINAL, CLEAN, OPERATOR-SAFE VERSION

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from data_loader import load_and_clean, aggregate_hourly_counts
from weather_api import get_hourly_forecast
from forecasting import build_baseline_profile, forecast_with_weather
from customer_intel import classify_customers, customer_summary
from scheduling import build_staff_schedule
from maintenance import suggest_maintenance_window, basic_maintenance_summary
from config import TIMEZONE
from supabase_client import get_sites, insert_transactions, load_full_history
from memory_manager import save_ai_summary, load_recent_memory
from groq import Groq


# ----------------------------
# REALISM HELPERS
# ----------------------------
OPEN_HOUR = 8
CLOSE_HOUR = 20


def get_historical_daily_cap(df, buffer=1.15):
    daily_counts = df.groupby("date").size()
    if daily_counts.empty:
        return None
    return int(daily_counts.max() * buffer)


# ----------------------------
# STREAMLIT SETUP
# ----------------------------
st.set_page_config(page_title="Shine & Roll AI Operations Agent", layout="wide")

st.title("🚗 Shine & Roll — AI Operations Agent")
st.caption("Weather-adaptive forecasting • Scheduling • Customer intelligence • Maintenance windows")


# ----------------------------
# SIDEBAR
# ----------------------------
with st.sidebar:
    st.header("Setup")

    sites = get_sites()
    site_codes = [s["site_code"] for s in sites]
    site_map = {s["site_code"]: s for s in sites}

    selected_site = st.selectbox("Select Site", site_codes)
    site_info = site_map[selected_site]

    uploaded_file = st.file_uploader("Upload car wash CSV", type=["csv"])

    lat = float(site_info.get("latitude") or 35.0484)
    lon = float(site_info.get("longitude") or -89.8679)

    traffic_index = st.slider("Traffic Index (1–5)", 1, 5, int(site_info.get("default_traffic_index") or 3))
    days_forecast = st.slider("Days ahead to forecast", 1, 3, 1)


# ----------------------------
# LOAD DATA
# ----------------------------
if uploaded_file:
    new_df = load_and_clean(uploaded_file)
    new_df = classify_customers(new_df)

    try:
        insert_transactions(new_df, selected_site)
        st.success("Uploaded data saved to cloud.")
    except Exception as e:
        st.warning(f"Could not save to Supabase: {e}")

    history_df = load_full_history(selected_site)
    df = pd.concat([history_df, new_df], ignore_index=True) if not history_df.empty else new_df
else:
    df = load_full_history(selected_site)
    if df.empty:
        st.info("Upload a CSV to begin.")
        st.stop()

df = classify_customers(df)


# ----------------------------
# FORECAST PIPELINE
# ----------------------------
hourly = aggregate_hourly_counts(df)
profile = build_baseline_profile(hourly)

weather_df = get_hourly_forecast(lat, lon, timezone=TIMEZONE, days=days_forecast)
forecast_df = forecast_with_weather(profile, weather_df)

# OPERATING HOURS FILTER (CRITICAL)
forecast_df = forecast_df[
    (forecast_df["time"].dt.hour >= OPEN_HOUR) &
    (forecast_df["time"].dt.hour <= CLOSE_HOUR)
]

# TRAFFIC ADJUSTMENT
traffic_factor = 1.0 + (traffic_index - 3) * 0.1
forecast_df["forecast_cars"] *= traffic_factor

# DAILY CAP (CRITICAL)
daily_cap = get_historical_daily_cap(df)
raw_total = int(forecast_df["forecast_cars"].sum())
total_forecast = min(raw_total, daily_cap) if daily_cap else raw_total

peak_row = forecast_df.loc[forecast_df["forecast_cars"].idxmax()]


# ----------------------------
# METRICS
# ----------------------------
cust_summary = customer_summary(df)
maint_summary = basic_maintenance_summary(df)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Visits", cust_summary["total_visits"])
c2.metric("Unique Customers", cust_summary["total_unique_customers"])
c3.metric(f"Forecast ({days_forecast} day)", total_forecast)
c4.metric("Traffic Index", traffic_index)


# ----------------------------
# FORECAST CHART
# ----------------------------
st.subheader("📈 Hourly Forecast")

fig = px.line(
    forecast_df,
    x="time",
    y="forecast_cars",
    template="plotly_dark",
    labels={"forecast_cars": "Cars", "time": "Time"}
)
st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# STAFFING + MAINTENANCE
# ----------------------------
st.subheader("👥 Suggested Staff Schedule")
st.dataframe(build_staff_schedule(forecast_df))

st.subheader("🛠 Maintenance Window")
mw = suggest_maintenance_window(forecast_df)
if mw is not None:
    st.dataframe(mw[["time", "forecast_cars"]])


# ----------------------------
# AI SUMMARY
# ----------------------------
st.subheader("🧠 Daily AI Summary")

summary = f"""
Expected total volume: ~{total_forecast} cars.

Peak hour: {str(peak_row['time'])[:16]} with ~{int(peak_row['forecast_cars'])} cars.

Traffic index set to {traffic_index}.
"""

st.markdown(summary)

if st.button("Save Summary to AI Memory"):
    save_ai_summary(selected_site, "daily", summary)
    st.success("Saved to AI memory.")


# ----------------------------
# AI CHAT
# ----------------------------
st.subheader("🤖 Carwash AI Chat")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
memory = load_recent_memory(selected_site)

context = "\n\n".join(m["content"] for m in memory)
user_msg = st.chat_input("Ask about this site...")

if user_msg:
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are an AI operations manager for a car wash."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{user_msg}"}
            ],
            temperature=0.3,
            max_tokens=512,
        )

        reply = response.choices[0].message.content

    except Exception as e:
        reply = "⚠️ AI service temporarily unavailable. Please try again."

