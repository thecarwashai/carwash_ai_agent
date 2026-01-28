# weather_api.py

import requests
import pandas as pd

def get_hourly_forecast(lat, lon, timezone="America/Chicago", days=2):
    """
    Returns a DataFrame with hourly weather forecast for the next `days`.
    Uses Open-Meteo (free).
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_2m", "precipitation_probability", "rain", "snowfall"],
        "timezone": timezone,
        "forecast_days": days,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    hourly = data["hourly"]

    df = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "temp_c": hourly["temperature_2m"],
        "precip_prob": hourly["precipitation_probability"],
        "rain_mm": hourly["rain"],
        "snow_mm": hourly["snowfall"],
    })

    df["hour"] = df["time"].dt.hour
    df["date"] = df["time"].dt.date
    df["weekday"] = df["time"].dt.weekday
    df["is_weekend"] = df["weekday"].isin([5, 6]).astype(int)
    return df
