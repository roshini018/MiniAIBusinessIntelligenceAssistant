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


def find_product(conn: sqlite3.Connection, query_name: str) -> str | None:
    """Find a product in the database matching or contained in query_name."""
    if not query_name:
        return None
    cleaned = re.sub(r"^the\s+|\s+product$", "", query_name.strip(), flags=re.IGNORECASE).strip()
    
    # 1. Exact match (case-insensitive)
    row = conn.execute(
        "SELECT DISTINCT product FROM sales WHERE counted = 1 AND LOWER(product) = LOWER(?)",
        (cleaned,),
    ).fetchone()
    if row:
        return row[0]
        
    # 2. Match against all known products
    known_products = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT product FROM sales WHERE counted = 1"
        ).fetchall()
    ]
    # Check if exact known product is substring of query
    for p in known_products:
        if p.lower() == cleaned.lower():
            return p
    for p in sorted(known_products, key=lambda x: len(x), reverse=True):
        if re.search(r"\b" + re.escape(p) + r"\b", query_name, re.IGNORECASE):
            return p
    for p in sorted(known_products, key=lambda x: len(x), reverse=True):
        if p.lower() in query_name.lower():
            return p
    return None


def find_region(conn: sqlite3.Connection, query_name: str) -> str | None:
    """Find a region in the database matching or contained in query_name."""
    if not query_name:
        return None
    cleaned = re.sub(r"^the\s+|\s+region$", "", query_name.strip(), flags=re.IGNORECASE).strip()
    
    row = conn.execute(
        "SELECT DISTINCT region FROM sales WHERE counted = 1 AND LOWER(region) = LOWER(?)",
        (cleaned,),
    ).fetchone()
    if row:
        return row[0]
        
    known_regions = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT region FROM sales WHERE counted = 1"
        ).fetchall()
    ]
    for r in known_regions:
        if r.lower() == cleaned.lower():
            return r
    for r in sorted(known_regions, key=lambda x: len(x), reverse=True):
        if re.search(r"\b" + re.escape(r) + r"\b", query_name, re.IGNORECASE):
            return r
    for r in sorted(known_regions, key=lambda x: len(x), reverse=True):
        if r.lower() in query_name.lower():
            return r
    return None


# 1. Total revenue ---------------------------------------------------------
def total_revenue(conn: sqlite3.Connection):
    sql = (
        "SELECT ROUND(SUM(revenue), 2) AS total_revenue, "
        "COUNT(*) AS orders_counted FROM sales WHERE counted = 1"
    )
    rows = _run(conn, sql)
    total = rows[0]["total_revenue"] if rows and rows[0]["total_revenue"] is not None else 0
    orders = rows[0]["orders_counted"] if rows and rows[0]["orders_counted"] is not None else 0
    answer = (
        f"Total revenue is {_fmt(total)} across {orders} completed orders."
    )
    data = [{"total_revenue": total, "orders_counted": orders}]
    return _result("total_revenue", answer, sql, (), data)


# 2. Top product -----------------------------------------------------------
def top_product(conn: sqlite3.Connection, target: str | None = None, product_name: str | None = None):
    if product_name:
        matched_product = find_product(conn, product_name)
        if not matched_product:
            raise AppError(f"No sales data found for product '{product_name}'.", 404)
        sql = (
            "SELECT product, ROUND(SUM(revenue), 2) AS revenue, COUNT(*) AS orders_counted "
            "FROM sales WHERE counted = 1 AND LOWER(product) = LOWER(?) "
            "GROUP BY product"
        )
        rows = _run(conn, sql, (matched_product,))
        if not rows:
            raise AppError(f"No sales data found for product '{matched_product}'.", 404)
        row = rows[0]
        answer = f"{row['product']} generated {_fmt(row['revenue'])} in revenue across {row['orders_counted']} completed orders."
        return _result("top_product", answer, sql, (matched_product,), rows)

    if target == "lowest":
        sql = (
            "SELECT product, ROUND(SUM(revenue), 2) AS revenue "
            "FROM sales WHERE counted = 1 "
            "GROUP BY product ORDER BY revenue ASC, product ASC"
        )
        rows = _run(conn, sql)
        if not rows:
            raise AppError("No sales data available.", 404)
        worst = rows[0]
        answer = f"{worst['product']} generated the lowest revenue: {_fmt(worst['revenue'])}."
        return _result("top_product", answer, sql, (), rows)

    sql = (
        "SELECT product, ROUND(SUM(revenue), 2) AS revenue "
        "FROM sales WHERE counted = 1 "
        "GROUP BY product ORDER BY revenue DESC, product ASC"
    )
    rows = _run(conn, sql)
    if not rows:
        raise AppError("No sales data available.", 404)

    if target == "ranking":
        rankings = ", ".join(f"{i+1}. {r['product']} ({_fmt(r['revenue'])})" for i, r in enumerate(rows))
        answer = f"Product revenue ranking: {rankings}."
        return _result("top_product", answer, sql, (), rows)

    best = rows[0]
    answer = (
        f"{best['product']} generated the highest revenue: {_fmt(best['revenue'])}."
    )
    return _result("top_product", answer, sql, (), rows)


# 3. Monthly trend ---------------------------------------------------------
def monthly_trend(conn: sqlite3.Connection, target: str | None = None, month: str | None = None):
    if month:
        if not isinstance(month, str) or not MONTH_RE.match(month):
            raise AppError(f"'{month}' is not a valid month. Use YYYY-MM.", 400)
        sql = (
            "SELECT month, ROUND(SUM(revenue), 2) AS revenue, COUNT(*) AS orders_counted "
            "FROM sales WHERE counted = 1 AND month = ? "
            "GROUP BY month"
        )
        rows = _run(conn, sql, (month,))
        if not rows:
            raise AppError(f"No sales data found for {month}.", 404)
        row = rows[0]
        answer = f"Revenue for {month} was {_fmt(row['revenue'])} across {row['orders_counted']} completed orders."
        return _result("monthly_trend", answer, sql, (month,), rows)

    sql = (
        "SELECT month, ROUND(SUM(revenue), 2) AS revenue "
        "FROM sales WHERE counted = 1 GROUP BY month ORDER BY month"
    )
    rows = _run(conn, sql)
    if not rows:
        raise AppError("No sales data available.", 404)

    peak = max(rows, key=lambda r: r["revenue"])
    lowest = min(rows, key=lambda r: r["revenue"])

    if target == "highest":
        answer = f"{peak['month']} had the highest revenue: {_fmt(peak['revenue'])}."
        return _result("monthly_trend", answer, sql, (), rows)

    if target == "lowest":
        answer = f"{lowest['month']} had the lowest revenue: {_fmt(lowest['revenue'])}."
        return _result("monthly_trend", answer, sql, (), rows)

    if target == "trajectory":
        first_val = rows[0]["revenue"]
        last_val = rows[-1]["revenue"]
        if last_val > first_val:
            dir_str = "increasing"
        elif last_val < first_val:
            dir_str = "decreasing"
        else:
            dir_str = "steady"
        answer = (
            f"Revenue is overall {dir_str}, moving from {_fmt(first_val)} in {rows[0]['month']} "
            f"to {_fmt(last_val)} in {rows[-1]['month']} (peak: {peak['month']} at {_fmt(peak['revenue'])})."
        )
        return _result("monthly_trend", answer, sql, (), rows)

    answer = (
        f"Monthly revenue from {rows[0]['month']} to {rows[-1]['month']}. "
        f"Peak month: {peak['month']} ({_fmt(peak['revenue'])})."
    )
    return _result("monthly_trend", answer, sql, (), rows)


# 4. Top region ------------------------------------------------------------
def top_region(conn: sqlite3.Connection, target: str | None = None, region_name: str | None = None):
    if region_name:
        matched_region = find_region(conn, region_name)
        if not matched_region:
            raise AppError(f"No sales data found for region '{region_name}'.", 404)
        sql = (
            "SELECT region, ROUND(SUM(revenue), 2) AS revenue, COUNT(*) AS orders_counted "
            "FROM sales WHERE counted = 1 AND LOWER(region) = LOWER(?) "
            "GROUP BY region"
        )
        rows = _run(conn, sql, (matched_region,))
        if not rows:
            raise AppError(f"No sales data found for region '{matched_region}'.", 404)
        row = rows[0]
        answer = f"The {row['region']} region generated {_fmt(row['revenue'])} in sales across {row['orders_counted']} completed orders."
        return _result("top_region", answer, sql, (matched_region,), rows)

    if target == "lowest":
        sql = (
            "SELECT region, ROUND(SUM(revenue), 2) AS revenue "
            "FROM sales WHERE counted = 1 "
            "GROUP BY region ORDER BY revenue ASC, region ASC"
        )
        rows = _run(conn, sql)
        if not rows:
            raise AppError("No sales data available.", 404)
        worst = rows[0]
        answer = f"{worst['region']} generated the lowest sales: {_fmt(worst['revenue'])}."
        return _result("top_region", answer, sql, (), rows)

    sql = (
        "SELECT region, ROUND(SUM(revenue), 2) AS revenue "
        "FROM sales WHERE counted = 1 "
        "GROUP BY region ORDER BY revenue DESC, region ASC"
    )
    rows = _run(conn, sql)
    if not rows:
        raise AppError("No sales data available.", 404)

    if target == "ranking":
        rankings = ", ".join(f"{i+1}. {r['region']} ({_fmt(r['revenue'])})" for i, r in enumerate(rows))
        answer = f"Regional revenue breakdown: {rankings}."
        return _result("top_region", answer, sql, (), rows)

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
    if b > a:
        higher_stmt = f"{month_b} had higher revenue than {month_a} ({_fmt(b)} vs {_fmt(a)}). "
    elif a > b:
        higher_stmt = f"{month_a} had higher revenue than {month_b} ({_fmt(a)} vs {_fmt(b)}). "
    else:
        higher_stmt = f"Both {month_a} and {month_b} generated equal revenue ({_fmt(a)}). "

    answer = f"{higher_stmt}Revenue {direction} from {_fmt(a)} in {month_a} to {_fmt(b)} in {month_b}"
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