import os
from pathlib import Path

# Resolve base directories relative to this file so paths work from any working directory
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Default file paths
DEFAULT_CSV_PATH = str(DATA_DIR / "sales.csv")
DEFAULT_DB_PATH = str(DATA_DIR / "sales.db")

# Default business year for month extraction when omitted by user
DEFAULT_YEAR = 2026

# Timeout in milliseconds for LLM requests (15 seconds)
DEFAULT_LLM_TIMEOUT_MS = 15_000

# Supported intents
ALLOWED_INTENTS = {
    "total_revenue",
    "top_product",
    "monthly_trend",
    "top_region",
    "month_comparison",
    "ambiguous",
    "unsupported",
}
