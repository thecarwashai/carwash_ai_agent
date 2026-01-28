# scheduling.py

import pandas as pd
from config import STAFFING_THRESHOLDS

def staff_for_cars(cars):
    for low, high, staff in STAFFING_THRESHOLDS:
        if low <= cars < high:
            return staff
    return STAFFING_THRESHOLDS[-1][2]


def build_staff_schedule(forecast_df):
    """
    forecast_df: output of forecast_with_weather
    Returns schedule df with staff recommendations.
    """
    df = forecast_df.copy()
    df["staff"] = df["forecast_cars"].apply(lambda x: staff_for_cars(x))
    return df
