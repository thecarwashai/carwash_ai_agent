# customer_intel.py

import pandas as pd

def classify_customers(df):
    """
    Adds columns:
    - is_member
    - visit_count
    - is_new_customer (this visit)
    """
    df = df.copy()

    # Membership detection: adjust keywords as needed
    df["is_member"] = df["type"].str.contains("member").astype(int)

    # Sort by time to ensure chronological
    df = df.sort_values("time")

    # Count visits per plate
    visit_counts = df.groupby("licensePlate").cumcount() + 1
    df["visit_number"] = visit_counts

    # New vs returning
    df["is_new_customer"] = (df["visit_number"] == 1).astype(int)

    return df


def customer_summary(df):
    """
    Returns simple metrics and grouped stats for dashboard.
    """
    total_visits = len(df)
    total_unique_customers = df["licensePlate"].nunique()
    new_customers = df["is_new_customer"].sum()
    member_visits = df["is_member"].sum()
    unique_members = df.loc[df["is_member"] == 1, "licensePlate"].nunique()

    # New customers per day
    new_per_day = (
        df.groupby("date")["is_new_customer"]
        .sum()
        .reset_index(name="new_customers")
    )

    # New customers by hour-of-day
    new_by_hour = (
        df.groupby("hour")["is_new_customer"]
        .sum()
        .reset_index(name="new_customers")
    )

    return {
        "total_visits": total_visits,
        "total_unique_customers": total_unique_customers,
        "new_customers": new_customers,
        "member_visits": member_visits,
        "unique_members": unique_members,
        "new_per_day": new_per_day,
        "new_by_hour": new_by_hour,
    }
