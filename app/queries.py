import os
import re
import sqlite3
from app.config import DEFAULT_DB_PATH

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class AppError(Exception):
    """An error we expect and want to show the user cleanly."""
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def get_conn(db_path: str | None = None) -> sqlite3.Connection:
    """Open the database read-only so queries can never change data."""
    target_path = db_path if db_path is not None else DEFAULT_DB_PATH
    if not os.path.exists(target_path):
        raise AppError("Database not found. Run: python -m app.data_loader", 503)

    resolved_path = os.path.abspath(target_path)
    conn = sqlite3.connect(f"file:{resolved_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _run(conn: sqlite3.Connection, sql: str, params: tuple = ()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _fmt_indian(n) -> str:
    """Format a number using the Indian numbering system (e.g., 14,39,200)."""
    n = round(n)
    is_negative = n < 0
    n = abs(n)
    s = str(n)
    if len(s) <= 3:
        result = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        # Group the remaining digits in pairs from right to left
        pairs = []
        while rest:
            pairs.append(rest[-2:] if len(rest) >= 2 else rest)
            rest = rest[:-2]
        pairs.reverse()
        result = ",".join(pairs) + "," + last3
    return ("-" if is_negative else "") + "₹" + result


def _fmt(n) -> str:
    """Format a number as Indian currency with ₹ symbol."""
    return _fmt_indian(n)


def _result(intent: str, answer: str, sql: str, params: tuple, data: list):
    return {
        "intent": intent,
        "answer": answer,
        "sql": sql,
        "params": list(params),
        "data": data,
    }


# 1. Total revenue ---------------------------------------------------------
def total_revenue(conn: sqlite3.Connection):
    sql = (
        "SELECT ROUND(SUM(revenue), 2) AS total_revenue, "
        "COUNT(*) AS orders_counted FROM sales WHERE counted = 1"
    )
    rows = _run(conn, sql)
    total = rows[0]["total_revenue"] or 0
    orders = rows[0]["orders_counted"] or 0
    answer = (
        f"Total revenue is {_fmt(total)} across {orders} completed orders."
    )
    return _result("total_revenue", answer, sql, (), rows)


# 2. Top product -----------------------------------------------------------
def top_product(conn: sqlite3.Connection):
    sql = (
        "SELECT product, ROUND(SUM(revenue), 2) AS revenue "
        "FROM sales WHERE counted = 1 "
        "GROUP BY product ORDER BY revenue DESC, product ASC"
    )
    rows = _run(conn, sql)
    if not rows:
        raise AppError("No sales data available.", 404)
    best = rows[0]
    answer = (
        f"{best['product']} generated the highest revenue: {_fmt(best['revenue'])}."
    )
    return _result("top_product", answer, sql, (), rows)


# 3. Monthly trend ---------------------------------------------------------
def monthly_trend(conn: sqlite3.Connection):
    sql = (
        "SELECT month, ROUND(SUM(revenue), 2) AS revenue "
        "FROM sales WHERE counted = 1 GROUP BY month ORDER BY month"
    )
    rows = _run(conn, sql)
    if not rows:
        raise AppError("No sales data available.", 404)
    peak = max(rows, key=lambda r: r["revenue"])
    answer = (
        f"Monthly revenue from {rows[0]['month']} to {rows[-1]['month']}. "
        f"Peak month: {peak['month']} ({_fmt(peak['revenue'])})."
    )
    return _result("monthly_trend", answer, sql, (), rows)


# 4. Top region ------------------------------------------------------------
def top_region(conn: sqlite3.Connection):
    sql = (
        "SELECT region, ROUND(SUM(revenue), 2) AS revenue "
        "FROM sales WHERE counted = 1 "
        "GROUP BY region ORDER BY revenue DESC, region ASC"
    )
    rows = _run(conn, sql)
    if not rows:
        raise AppError("No sales data available.", 404)
    best = rows[0]
    answer = (
        f"{best['region']} generated the highest sales: {_fmt(best['revenue'])}."
    )
    return _result("top_region", answer, sql, (), rows)


# 5. Compare two months ----------------------------------------------------
def month_comparison(conn: sqlite3.Connection, month_a: str, month_b: str):
    for m in (month_a, month_b):
        if not isinstance(m, str) or not MONTH_RE.match(m):
            raise AppError(f"'{m}' is not a valid month. Use YYYY-MM.", 400)

    if month_a == month_b:
        raise AppError("Please name two distinct months to compare.", 400)

    sql = (
        "SELECT month, ROUND(SUM(revenue), 2) AS revenue "
        "FROM sales WHERE counted = 1 AND month IN (?, ?) "
        "GROUP BY month ORDER BY month"
    )
    rows = _run(conn, sql, (month_a, month_b))
    found = {r["month"]: r["revenue"] for r in rows}
    for m in (month_a, month_b):
        if m not in found:
            raise AppError(f"No sales data found for {m}.", 404)

    a, b = found[month_a], found[month_b]
    change = round(b - a, 2)
    pct = round(change / a * 100, 1) if a and a != 0 else None
    direction = (
        "increased" if change > 0 else "decreased" if change < 0 else "did not change"
    )
    answer = f"Revenue {direction} from {_fmt(a)} in {month_a} to {_fmt(b)} in {month_b}"
    if change != 0:
        answer += f" ({'+' if change > 0 else '-'}{_fmt(abs(change))}"
        answer += f", {pct:+.1f}%)." if pct is not None else ")."
    else:
        answer += "."

    data = [
        {"month": month_a, "revenue": a},
        {"month": month_b, "revenue": b},
        {"month": "change", "revenue": change, "percent_change": pct},
    ]
    return _result("month_comparison", answer, sql, (month_a, month_b), data)