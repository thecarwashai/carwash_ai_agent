import os

TIMEZONE = "America/Chicago"

STAFFING_THRESHOLDS = [
    (0, 20, 2),
    (20, 40, 3),
    (40, 60, 4),
    (60, 80, 5),
    (80, 9999, 6),
]

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
