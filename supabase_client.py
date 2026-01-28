# supabase_client.py

import os
import pandas as pd
from supabase import create_client

from config import SUPABASE_URL, SUPABASE_KEY

_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def get_sites():
    sb = get_supabase()
    resp = sb.table("sites").select("*").eq("active", True).execute()
    return resp.data

def insert_transactions(df, site_code: str):
    """
    Save cleaned/classified dataframe to Supabase transactions table for a site.
    """
    sb = get_supabase()
    recs = []
    for _, row in df.iterrows():
        recs.append({
            "site_code": site_code,
            "order_id": str(row.get("orderId")),
            "license_plate": row.get("licensePlate"),
            "package": row.get("package"),
            "wash_type": row.get("type"),
            "employee": row.get("employee"),
            "time": row.get("time").isoformat() if not pd.isna(row.get("time")) else None,
            "date": row.get("date"),
            "hour": int(row.get("hour")),
            "weekday": int(row.get("weekday")),
            "is_weekend": bool(row.get("is_weekend")),
            "is_member": bool(row.get("is_member")),
            "is_new_customer": bool(row.get("is_new_customer")),
        })

    if recs:
        sb.table("transactions").insert(recs).execute()

def load_full_history(site_code: str):
    """
    Load all historical transactions for a site from Supabase.
    Return as pandas DataFrame.
    """
    import pandas as pd

    sb = get_supabase()
    resp = sb.table("transactions").select("*").eq("site_code", site_code).execute()
    data = resp.data or []
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    # convert time back to datetime
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df
