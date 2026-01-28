# maintenance.py

import pandas as pd

def suggest_maintenance_window(forecast_df):
    """
    Suggests a 2-hour window with lowest forecast cars.
    """
    df = forecast_df.copy()
    # sort by forecast
    df = df.sort_values("forecast_cars")
    # take the lowest two consecutive hours
    if df.empty:
        return None

    df = df.reset_index(drop=True)
    best_pair = None
    best_sum = None

    for i in range(len(df) - 1):
        pair_sum = df.loc[i, "forecast_cars"] + df.loc[i + 1, "forecast_cars"]
        if best_sum is None or pair_sum < best_sum:
            best_sum = pair_sum
            best_pair = df.loc[i:i + 1]

    return best_pair


def basic_maintenance_summary(df):
    """
    Very simple: total cars processed, can be mapped to brush life, etc.
    """
    total_cars = len(df)
    return {
        "total_cars": total_cars,
        # You can extend with thresholds, e.g., every 40,000 cars per brush.
    }
