# data_loader.py

import pandas as pd
import pytz
from config import TIMEZONE

def load_and_clean(file):
    """
    file: uploaded file-like object or file path
    Returns cleaned DataFrame.
    """
    df = pd.read_csv(file)

    # Ensure required columns exist
    required_cols = ["orderId", "location", "licensePlate", "package",
                     "employee", "type", "time", "total"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse time
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    # Localize to Central time (naive -> timezone-aware)
    tz = pytz.timezone(TIMEZONE)
    df["time"] = df["time"].dt.tz_localize(tz, ambiguous="NaT")

    # Separate date and time-of-day
    df["date"] = df["time"].dt.date
    df["time_of_day"] = df["time"].dt.time

    # Extra features
    df["hour"] = df["time"].dt.hour
    df["weekday"] = df["time"].dt.weekday  # 0=Mon
    df["month"] = df["time"].dt.month
    df["year"] = df["time"].dt.year
    df["is_weekend"] = df["weekday"].isin([5, 6]).astype(int)

    # Clean text fields
    df["licensePlate"] = df["licensePlate"].fillna("UNKNOWN").astype(str).str.strip()
    df["package"] = df["package"].fillna("UNKNOWN").astype(str).str.strip()
    df["type"] = df["type"].fillna("").astype(str).str.strip().str.lower()
    df["location"] = df["location"].fillna("").astype(str).str.strip()

    # Numeric total (if you ever need it internally)
    df["total_numeric"] = (
        df["total"]
        .astype(str)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .replace("", "0")
        .astype(float)
    )

    return df


def aggregate_hourly_counts(df):
    """
    Aggregates hourly car counts for forecasting and scheduling.
    """
    hourly = (
        df.groupby(["date", "hour", "weekday", "is_weekend"])
        .size()
        .reset_index(name="cars")
    )
    return hourly
