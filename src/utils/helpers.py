"""
Utility functions for data processing and common operations.
Handles date parsing (DD/MM/YYYY and UNIX), aggregation, and formatting.
"""

import pandas as pd
from datetime import datetime
from typing import Union, List, Optional


def parse_order_date(date_series: pd.Series) -> pd.Series:
    """
    Parse created_order column: DD/MM/YYYY HH:MM or mixed with UNIX timestamps.
    Returns datetime series with timezone-naive Europe/Copenhagen interpretation.
    """
    out = pd.Series(index=date_series.index, dtype="datetime64[ns]")
    for i, v in date_series.items():
        if pd.isna(v):
            out.iloc[i] = pd.NaT
            continue
        v = str(v).strip()
        if v.isdigit():
            out.iloc[i] = pd.to_datetime(int(v), unit="s")
        else:
            try:
                out.iloc[i] = pd.to_datetime(v, format="%d/%m/%Y %H:%M", dayfirst=True)
            except Exception:
                try:
                    out.iloc[i] = pd.to_datetime(v)
                except Exception:
                    out.iloc[i] = pd.NaT
    return out


def convert_unix_timestamp(timestamp: int) -> datetime:
    """Converts a UNIX timestamp to a datetime object."""
    return datetime.fromtimestamp(timestamp)


def convert_timestamp_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Converts a timestamp column from UNIX to datetime in a DataFrame."""
    df = df.copy()
    df[column_name] = pd.to_datetime(df[column_name], unit="s", errors="coerce")
    return df


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Percentage change between two values. Raises ValueError if old_value is zero."""
    if old_value == 0:
        raise ValueError("Cannot calculate percentage change when old value is zero")
    return ((new_value - old_value) / old_value) * 100


def filter_by_date_range(
    df: pd.DataFrame, date_column: str, start_date: str, end_date: str
) -> pd.DataFrame:
    """Filters a DataFrame by date range (start_date and end_date inclusive, YYYY-MM-DD)."""
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
        df[date_column] = pd.to_datetime(df[date_column])
    mask = (df[date_column].dt.date >= pd.to_datetime(start_date).date()) & (
        df[date_column].dt.date <= pd.to_datetime(end_date).date()
    )
    return df[mask]


def categorize_performance(value: float, thresholds: dict) -> str:
    """Categorizes a performance metric (poor/fair/good/excellent)."""
    if value < thresholds["low"]:
        return "poor"
    elif value < thresholds["medium"]:
        return "fair"
    elif value < thresholds["high"]:
        return "good"
    else:
        return "excellent"


def aggregate_demand_by_period(
    df: pd.DataFrame,
    date_column: str,
    value_column: str = "quantity",
    period: str = "D",
    group_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Aggregates demand (quantity) by date period and optional group (e.g. item_id, place_id).
    period: 'D' daily, 'W' weekly, 'M' monthly.
    """
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
    df = df.dropna(subset=[date_column])
    if group_cols:
        df = df.groupby([pd.Grouper(key=date_column, freq=period)] + group_cols)[value_column].sum().reset_index()
    else:
        df = df.set_index(date_column)
        df = df[value_column].resample(period).sum().reset_index()
    return df


def aggregate_by_period(
    df: pd.DataFrame, date_column: str, value_column: str, period: str = "D"
) -> pd.DataFrame:
    """Legacy: aggregates single value column by period."""
    return aggregate_demand_by_period(df, date_column, value_column, period, group_cols=None)


def format_currency(amount: float, currency: str = "DKK") -> str:
    """Formats monetary value (DKK by default)."""
    return f"{currency} {amount:,.2f}"
