# forecasting.py

import pandas as pd
import numpy as np

def build_baseline_profile(hourly_df):
    """
    Build baseline expected cars per weekday/hour using median.
    """
    profile = (
        hourly_df
        .groupby(["weekday", "hour"])["cars"]
        .median()
        .reset_index()
        .rename(columns={"cars": "median_cars"})
    )
    return profile


def forecast_with_weather(profile_df, weather_df, rain_impact=0.7):
    """
    Merge baseline profile with weather forecast and adjust for rain heuristic.
    """
    # Merge on weekday + hour
    merged = pd.merge(
        weather_df,
        profile_df,
        how="left",
        on=["weekday", "hour"],
    )

    # Fill missing medians with global median
    global_median = profile_df["median_cars"].median() if not profile_df.empty else 0
    merged["median_cars"] = merged["median_cars"].fillna(global_median)

    # Heuristic: reduce expected cars when high rain probability
    merged["forecast_cars"] = merged["median_cars"]
    high_rain_mask = merged["precip_prob"] >= 60
    merged.loc[high_rain_mask, "forecast_cars"] = (
        merged.loc[high_rain_mask, "median_cars"] * rain_impact
    )

    merged["forecast_cars"] = merged["forecast_cars"].round(1)
    return merged
