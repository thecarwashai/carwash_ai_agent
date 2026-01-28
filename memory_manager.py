# memory_manager.py

from supabase_client import get_supabase

def save_ai_summary(site_code: str, summary_type: str, content: str, metadata=None):
    sb = get_supabase()
    rec = {
        "site_code": site_code,
        "summary_type": summary_type,
        "content": content,
        "metadata": metadata or {}
    }
    sb.table("ai_memory").insert(rec).execute()

def load_recent_memory(site_code: str, limit: int = 20):
    sb = get_supabase()
    resp = (
        sb.table("ai_memory")
        .select("*")
        .eq("site_code", site_code)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data
