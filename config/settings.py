"""
Configuration for Fresh Flow Insights.
Data files live in the data/ folder under project root.
"""
import os

# Project root (directory containing src/, config/, data/, etc.)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data folder: place merged_complete_part*.csv and sorted_most_ordered.csv here
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Cache folder: precomputed outputs from scripts/build_cache.py (app uses these for fast startup)
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache")

# Data file patterns (inside data/)
MERGED_PART_GLOB = "merged_complete_part*.csv"
SORTED_MOST_ORDERED_FILE = "sorted_most_ordered.csv"

# Use at most this many merged parts on load (1 = fast startup, 10 = full data)
MAX_MERGED_PARTS = 1

# Columns we need from merged (to reduce memory)
MERGED_COLS = [
    "item_id", "order_id", "quantity", "price", "cost", "title",
    "created_order", "place_id", "status_order", "type",
    # Business analytics columns
    "channel", "payment_method", "source", "total_amount",
]
