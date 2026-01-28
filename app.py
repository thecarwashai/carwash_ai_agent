# app.py

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


st.set_page_config(
    page_title="Shine & Roll AI Operations Agent",
    layout="wide",
)

st.markdown(
    """
    <style>
    .big-title {
        font-size: 32px !important;
        font-weight: 700 !important;
    }
    .sub-title {
        font-size: 18px !important;
        color: #cccccc !important;
    }
    .metric-card {
        padding: 16px;
        border-radius: 16px;
        background: #121212;
        border: 1px solid #333333;
    }
    body {
        background-color: #050505 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="big-title">🚗 Shine & Roll — AI Operations Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Weather-adaptive forecasting • Scheduling • Customer intelligence • Maintenance windows</div><br>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Setup")

    # 1) Select site
    sites = get_sites()
    site_codes = [s["site_code"] for s in sites]
    site_map = {s["site_code"]: s for s in sites}

    selected_site = st.selectbox("Select Site", site_codes, index=0)
    site_info = site_map[selected_site]

    st.write(f"**Site:** {site_info.get('name') or selected_site}")
    st.write(f"ZIP: {site_info.get('zip') or 'TBD'}")
    st.write(f"Road: {site_info.get('road') or 'TBD'}")

    uploaded_file = st.file_uploader(
        "Upload car wash CSV",
        type=["csv"],
        help="Columns: orderId, location, licensePlate, package, employee, type, time, total"
    )

    # 2) Site-specific location
    lat_default = site_info.get("latitude") or 35.0484
    lon_default = site_info.get("longitude") or -89.8679
    lat = st.number_input("Latitude", value=float(lat_default), format="%.6f")
    lon = st.number_input("Longitude", value=float(lon_default), format="%.6f")

    # 3) Site-specific traffic index
    traffic_default = site_info.get("default_traffic_index") or 3
    traffic_index = st.slider(
        "Traffic Index (1=low, 5=very high)",
        min_value=1, max_value=5, value=int(traffic_default)
    )

    days_forecast = st.slider("Days ahead to forecast", 1, 3, 1)


if uploaded_file is None:
    st.info("👆 Upload a CSV to begin. Historical data will still be used if present.")
    # even if no upload, allow using past data
    history_df = load_full_history(selected_site)
    if history_df.empty:
        st.stop()
    df = history_df
else:
    # New upload
    try:
        new_df = load_and_clean(uploaded_file)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

    new_df = classify_customers(new_df)

    # Save this batch to Supabase
    try:
        insert_transactions(new_df, selected_site)
        st.success("Uploaded data saved to cloud for this site.")
    except Exception as e:
        st.warning(f"Could not save to Supabase: {e}")

    # Combine old + new
    history_df = load_full_history(selected_site)
    if not history_df.empty:
        df = pd.concat([history_df, new_df], ignore_index=True)
    else:
        df = new_df

# Now df contains full history for this site
df = classify_customers(df)  # ensure new/old both classified
hourly = aggregate_hourly_counts(df)


if hourly.empty:
    st.warning("No rows after cleaning. Check your CSV.")
    st.stop()

# Build baseline profile
profile = build_baseline_profile(hourly)

# Get weather forecast
weather_df = get_hourly_forecast(lat, lon, timezone=TIMEZONE, days=days_forecast)

# Build forecast
forecast_df = forecast_with_weather(profile, weather_df)

# Apply traffic heuristic: simple multiplier
traffic_factor = 1.0 + (traffic_index - 3) * 0.1  # [0.8, 1.2] approx
forecast_df["forecast_cars"] = (forecast_df["forecast_cars"] * traffic_factor).round(1)

# Build schedule
schedule_df = build_staff_schedule(forecast_df)

# Maintenance info
maint_summary = basic_maintenance_summary(df)
maint_window = suggest_maintenance_window(forecast_df)

cust_summary = customer_summary(df)

# === TOP CARDS ===
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Total Visits (historical)", value=cust_summary["total_visits"])
    st.metric("Unique Customers", value=cust_summary["total_unique_customers"])
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("New Customers (total)", value=cust_summary["new_customers"])
    st.metric("Members (unique)", value=cust_summary["unique_members"])
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    total_forecast = int(forecast_df["forecast_cars"].sum())
    st.metric(f"Forecast ({days_forecast} day(s))", value=total_forecast)
    peak_row = forecast_df.loc[forecast_df["forecast_cars"].idxmax()]
    st.metric("Peak Hour (forecast)", f"{str(peak_row['time'])[:16]} — {int(peak_row['forecast_cars'])} cars")
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Total Cars (for maintenance)", value=maint_summary["total_cars"])
    st.metric("Traffic Index", value=traffic_index)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# === FORECAST CHART ===
st.subheader("📈 Forecast vs Weather (Hourly)")

fig = px.line(
    forecast_df,
    x="time",
    y="forecast_cars",
    title="Forecasted Cars per Hour",
    labels={"forecast_cars": "Forecast Cars", "time": "Time"},
)
fig.update_layout(template="plotly_dark", height=400)
st.plotly_chart(fig, use_container_width=True)

# Show weather overlay
with st.expander("Show weather forecast table"):
    st.dataframe(
        forecast_df[["time", "forecast_cars", "temp_c", "precip_prob", "rain_mm", "snow_mm"]]
    )

# === STAFF SCHEDULE ===
st.subheader("👥 Suggested Staff Schedule")

schedule_display = schedule_df[["time", "forecast_cars", "staff"]].copy()
schedule_display["time"] = schedule_display["time"].astype(str).str.slice(0, 16)
st.dataframe(schedule_display)

# === MAINTENANCE WINDOW ===
st.subheader("🛠 Suggested Maintenance Window")

if maint_window is not None and not maint_window.empty:
    mw = maint_window.copy()
    mw_display = mw[["time", "forecast_cars"]].copy()
    mw_display["time"] = mw_display["time"].astype(str).str.slice(0, 16)
    st.write("Lowest-impact 2-hour window (based on forecast):")
    st.dataframe(mw_display)
else:
    st.write("Could not determine a maintenance window.")

# === CUSTOMER ACQUISITION PATTERNS ===
st.subheader("🧭 Customer Acquisition Intelligence")

c1, c2 = st.columns(2)

with c1:
    st.markdown("**New Customers per Day**")
    new_per_day = cust_summary["new_per_day"]
    if not new_per_day.empty:
        fig_new_day = px.bar(new_per_day, x="date", y="new_customers", title="", labels={"new_customers": "New Customers"})
        fig_new_day.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_new_day, use_container_width=True)
    else:
        st.write("Not enough data.")

with c2:
    st.markdown("**New Customers by Hour of Day (all-time)**")
    new_by_hour = cust_summary["new_by_hour"]
    if not new_by_hour.empty:
        fig_new_hour = px.bar(new_by_hour, x="hour", y="new_customers", title="", labels={"new_customers": "New Customers"})
        fig_new_hour.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_new_hour, use_container_width=True)
    else:
        st.write("Not enough data.")

st.markdown("---")

# === SIMPLE "AI-LIKE" TEXT SUMMARY ===
st.subheader("🧠 Daily AI Summary")

# We'll synthesize a text summary based on the stats we have
today = date.today()
peak_hour_str = str(peak_row["time"])[:16]
rainy_hours = forecast_df[forecast_df["precip_prob"] >= 60]

summary_parts = []

summary_parts.append(
    f"For the next {days_forecast} day(s), the system expects around **{total_forecast} total cars**."
)

summary_parts.append(
    f"The **busiest hour** in the forecast is around **{peak_hour_str}**, with about **{int(peak_row['forecast_cars'])} cars**."
)

if not rainy_hours.empty:
    summary_parts.append(
        f"There are **{len(rainy_hours)} hour(s)** with high rain probability (≥60%). "
        "Expect softer demand in those windows compared to a typical day."
)

summary_parts.append(
    f"Historically, you have **{cust_summary['new_customers']} total new customers** in this dataset "
    f"out of **{cust_summary['total_unique_customers']} unique plates**, which helps the system learn "
    f"how often first-timers become repeats or members."
)

summary_parts.append(
    f"The current **traffic index** is set to **{traffic_index}**, so the forecast has been adjusted "
    "up or down accordingly to reflect the road exposure you selected."
)

st.markdown("\n\n".join(summary_parts))

st.caption(
    "This is a V1 of your AI Ops Agent: combining historical patterns, weather, traffic factor, "
    "and customer behavior into a single operational brain for your site."
)
from memory_manager import save_ai_summary

if st.button("Save Today’s Summary to AI Memory"):
    summary_text = "\n\n".join(summary_parts)
    save_ai_summary(selected_site, "daily", summary_text)
    st.success("Saved to AI Memory!")
import streamlit as st
from groq import Groq
from memory_manager import load_recent_memory

st.subheader("🤖 Carwash AI Chat Agent")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Load memory for selected site (last 20 AI summaries)
memory_data = load_recent_memory(selected_site)

long_term_context = "\n\n".join([
    f"{m['summary_type'].upper()} SUMMARY ({m['date']}):\n{m['content']}"
    for m in memory_data
])

# Chat UI
user_msg = st.chat_input(f"Ask anything about site {selected_site}...")

if user_msg:
    with st.chat_message("user"):
        st.write(user_msg)

    # Build the context prompt
    full_prompt = f"""
You are the AI Operations Manager for site {selected_site}.

You have access to long-term site memory:
{long_term_context}

Use this memory to respond intelligently to the user's question.

User: {user_msg}
"""

    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {"role": "user", "content": full_prompt}
        ]
    )

    reply = response.choices[0].message["content"]

    with st.chat_message("assistant"):
        st.write(reply)
