"""
spend_functions.py  —  SpendSense AI analytics engine

Three parts:
  (a) DATA + 6 analytics functions  — plain pandas; this is where the real math happens.
  (b) TOOLS                         — JSON "tool schemas" describing each function to GPT
                                       (this is what OpenAI "function calling" reads).
  (c) run_tool(name, arguments)     — dispatcher: maps a GPT tool-call to the Python function.

The AI never computes numbers itself — it only picks a function + arguments. These functions
do the work and return plain JSON-serializable dicts that we hand back to the model.
"""

import os
import json
import pandas as pd

# ----------------------------------------------------------------------------- #
# (a) DATA LOADING + ANALYTICS FUNCTIONS
# ----------------------------------------------------------------------------- #

_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "procurement_spend.csv")

# Allowed values (also used in the tool schemas so GPT passes valid values)
CATEGORIES  = ["IT Hardware", "Software & SaaS", "Logistics & Freight", "Raw Materials",
               "Office Supplies", "Professional Services", "MRO", "Marketing"]
DEPARTMENTS = ["IT", "Operations", "Finance", "Marketing", "R&D", "Facilities", "Sales", "HR"]
REGIONS     = ["North America", "EMEA", "APAC", "LATAM"]

_DF = None


def _load():
    """Load the spend CSV once and cache it. Returns a fresh copy each call."""
    global _DF
    if _DF is None:
        df = pd.read_csv(_DATA_PATH)
        df["po_date"] = pd.to_datetime(df["po_date"])
        # contract_id: empty => off-contract ("maverick"). Normalise blanks to "".
        df["contract_id"] = df["contract_id"].fillna("").astype(str).str.strip()
        _DF = df
    return _DF.copy()


def _filter(df, start_date=None, end_date=None, category=None, supplier=None,
            department=None, region=None):
    """Apply the common optional filters. Text matches are case-insensitive."""
    if start_date:
        df = df[df["po_date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["po_date"] <= pd.to_datetime(end_date)]
    for col, val in [("category", category), ("supplier", supplier),
                     ("department", department), ("region", region)]:
        if val:
            df = df[df[col].str.lower() == str(val).strip().lower()]
    return df


def _money(x):
    """Cast a numpy/pandas number to a plain rounded float (JSON-safe)."""
    return round(float(x), 2)


def get_total_spend(start_date=None, end_date=None, category=None, supplier=None,
                    department=None, region=None):
    """Total spend (sum of `amount`) for the given filters."""
    df = _filter(_load(), start_date, end_date, category, supplier, department, region)
    return {
        "total_spend": _money(df["amount"].sum()) if len(df) else 0.0,
        "po_count": int(len(df)),
        "currency": "USD",
        "filters": {k: v for k, v in dict(start_date=start_date, end_date=end_date,
                    category=category, supplier=supplier, department=department,
                    region=region).items() if v},
    }


def top_suppliers(n=5, start_date=None, end_date=None, category=None):
    """Top N suppliers ranked by total spend."""
    df = _filter(_load(), start_date, end_date, category=category)
    if not len(df):
        return {"suppliers": [], "note": "No purchase orders match these filters."}
    g = (df.groupby("supplier")
           .agg(spend=("amount", "sum"), po_count=("po_id", "count"))
           .sort_values("spend", ascending=False)
           .head(max(0, int(n))))   # max(0,..) so a negative n yields [] not "all-but-last-n"
    return {"suppliers": [
        {"supplier": idx, "spend": _money(row.spend), "po_count": int(row.po_count)}
        for idx, row in g.iterrows()
    ]}


def spend_by_category(start_date=None, end_date=None):
    """Break total spend down by category (descending)."""
    df = _filter(_load(), start_date, end_date)
    if not len(df):
        return {"categories": [], "note": "No purchase orders match these filters."}
    total = df["amount"].sum()
    g = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    return {"total_spend": _money(total), "categories": [
        {"category": idx, "spend": _money(val), "pct_of_total": round(float(val) / float(total) * 100, 1)}
        for idx, val in g.items()
    ]}


def maverick_spend(group_by="category", start_date=None, end_date=None):
    """Off-contract ('maverick') spend = purchase orders with no contract_id.
    Optionally broken down by category / supplier / department / region."""
    df = _filter(_load(), start_date, end_date)
    total = float(df["amount"].sum()) if len(df) else 0.0
    mav = df[df["contract_id"] == ""]
    mav_total = float(mav["amount"].sum()) if len(mav) else 0.0
    result = {
        "maverick_spend": _money(mav_total),
        "total_spend": _money(total),
        "maverick_pct_of_total": round(mav_total / total * 100, 1) if total else 0.0,
        "maverick_po_count": int(len(mav)),
    }
    if group_by and group_by != "none" and len(mav):
        g = mav.groupby(group_by)["amount"].sum().sort_values(ascending=False)
        result["breakdown"] = [{group_by: idx, "maverick_spend": _money(val)} for idx, val in g.items()]
    return result


def supplier_performance(supplier):
    """Delivery performance for one supplier: on-time rate + average delay."""
    df = _filter(_load(), supplier=supplier)
    if not len(df):
        return {"found": False, "note": f"No purchase orders found for supplier '{supplier}'."}
    on_time_rate = (df["on_time"] == "Yes").mean() * 100
    avg_delay = (df["delivery_days_actual"] - df["delivery_days_promised"]).mean()
    return {
        "found": True,
        "supplier": df["supplier"].iloc[0],
        "po_count": int(len(df)),
        "total_spend": _money(df["amount"].sum()),
        "on_time_rate_pct": round(float(on_time_rate), 1),
        "avg_delay_days": round(float(avg_delay), 1),
    }


def spend_trend(period="quarter", category=None, supplier=None):
    """Spend over time, grouped by 'month' or 'quarter'."""
    df = _filter(_load(), category=category, supplier=supplier)
    if not len(df):
        return {"period": period, "points": [], "note": "No purchase orders match these filters."}
    if period == "month":
        key = df["po_date"].dt.to_period("M").astype(str)
    else:  # quarter
        key = df["fiscal_quarter"]
    g = df.groupby(key)["amount"].sum()
    g = g.sort_index()
    return {"period": period, "points": [
        {"period": str(idx), "spend": _money(val)} for idx, val in g.items()
    ]}


# ----------------------------------------------------------------------------- #
# (b) TOOL SCHEMAS  —  what GPT sees (OpenAI "tools" / function-calling format)
# ----------------------------------------------------------------------------- #

_DATE = {"type": "string", "description": "Date in YYYY-MM-DD format"}

TOOLS = [
    {"type": "function", "function": {
        "name": "get_total_spend",
        "description": "Total procurement spend (sum of amount in USD) with optional filters.",
        "parameters": {"type": "object", "properties": {
            "start_date": {**_DATE, "description": "Inclusive start of po_date, YYYY-MM-DD"},
            "end_date": {**_DATE, "description": "Inclusive end of po_date, YYYY-MM-DD"},
            "category": {"type": "string", "enum": CATEGORIES},
            "supplier": {"type": "string"},
            "department": {"type": "string", "enum": DEPARTMENTS},
            "region": {"type": "string", "enum": REGIONS},
        }},
    }},
    {"type": "function", "function": {
        "name": "top_suppliers",
        "description": "List the top N suppliers ranked by total spend, with optional date/category filters.",
        "parameters": {"type": "object", "properties": {
            "n": {"type": "integer", "minimum": 1, "description": "How many suppliers to return", "default": 5},
            "start_date": _DATE, "end_date": _DATE,
            "category": {"type": "string", "enum": CATEGORIES},
        }},
    }},
    {"type": "function", "function": {
        "name": "spend_by_category",
        "description": "Break total spend down by category, with percentage of total.",
        "parameters": {"type": "object", "properties": {
            "start_date": _DATE, "end_date": _DATE,
        }},
    }},
    {"type": "function", "function": {
        "name": "maverick_spend",
        "description": "Off-contract ('maverick') spend = POs with no contract. Optionally grouped.",
        "parameters": {"type": "object", "properties": {
            "group_by": {"type": "string", "enum": ["category", "supplier", "department", "region", "none"],
                         "description": "Dimension to break maverick spend down by"},
            "start_date": _DATE, "end_date": _DATE,
        }},
    }},
    {"type": "function", "function": {
        "name": "supplier_performance",
        "description": "On-time delivery rate and average delay (days) for a specific supplier.",
        "parameters": {"type": "object", "properties": {
            "supplier": {"type": "string", "description": "Exact supplier name"},
        }, "required": ["supplier"]},
    }},
    {"type": "function", "function": {
        "name": "spend_trend",
        "description": "Spend over time, grouped by month or quarter, with optional category/supplier filter.",
        "parameters": {"type": "object", "properties": {
            "period": {"type": "string", "enum": ["month", "quarter"], "default": "quarter"},
            "category": {"type": "string", "enum": CATEGORIES},
            "supplier": {"type": "string"},
        }},
    }},
]


# ----------------------------------------------------------------------------- #
# (c) DISPATCHER  —  connect a GPT tool-call (name + args) to the Python function
# ----------------------------------------------------------------------------- #

_REGISTRY = {
    "get_total_spend": get_total_spend,
    "top_suppliers": top_suppliers,
    "spend_by_category": spend_by_category,
    "maverick_spend": maverick_spend,
    "supplier_performance": supplier_performance,
    "spend_trend": spend_trend,
}


def run_tool(name, arguments):
    """Execute the function GPT asked for. `arguments` is a dict (already JSON-parsed).
    Always returns a dict (never raises) so the model can see any error as data."""
    fn = _REGISTRY.get(name)
    if fn is None:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return fn(**(arguments or {}))
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
