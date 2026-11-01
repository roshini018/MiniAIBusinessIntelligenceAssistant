import sqlite3
import pytest
from app.data_loader import clean_data, load_to_db
from app import queries


CSV_REVENUE_CORRECTNESS = """transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status
TXN01,05-01-2026,Laptop,Electronics,North,Online,2,1000,100,Completed
TXN02,10-01-2026,Mouse,Accessories,South,Retail,5,200,,Completed
TXN03,15-01-2026,Keyboard,Accessories,North,Online,4,300,0,Completed
TXN04,02-02-2026,Laptop,Electronics,South,Retail,1,1000,200,Completed
TXN05,10-02-2026,Monitor,Electronics,North,Online,2,1500,500,Completed
TXN01,05-01-2026,Laptop,Electronics,North,Online,10,1000,0,Completed
TXN06,99-99-2026,Laptop,Electronics,North,Online,1,1000,0,Completed
TXN07,invalid-date,Laptop,Electronics,North,Online,1,1000,0,Completed
TXN08,01-01-2026,Laptop,Electronics,North,Online,0,1000,0,Completed
TXN09,02-01-2026,Laptop,Electronics,North,Online,-2,1000,0,Completed
TXN10,03-01-2026,Laptop,Electronics,North,Online,1,-500,0,Completed
TXN11,04-01-2026,Laptop,Electronics,North,Online,invalid,1000,0,Completed
TXN12,05-01-2026,Laptop,Electronics,North,Online,1,,0,Completed
TXN13,06-01-2026,Laptop,Electronics,North,Online,1,1000,0,Pending
TXN14,07-01-2026,Laptop,Electronics,North,Online,1,1000,0,Cancelled
TXN15,08-01-2026,Laptop,Electronics,North,Online,1,1000,0,Returned
TXN16,09-01-2026,Laptop,Electronics,North,Online,1,1000,0,Refunded
TXN17,10-01-2026,Laptop,Electronics,North,Online,1,1000,-50,Completed
TXN18,11-01-2026,Laptop,Electronics,North,Online,1,1000,1200,Completed
TXN19,12-01-2026,Mouse,Accessories,South,Retail,1,200,200,Completed
"""


@pytest.fixture(scope="module")
def revenue_db(tmp_path_factory):
    folder = tmp_path_factory.mktemp("rev_data")
    csv_file = folder / "sales.csv"
    csv_file.write_text(CSV_REVENUE_CORRECTNESS)
    db_file = str(folder / "sales.db")
    report = load_to_db(str(csv_file), db_file)
    return db_file, report


def test_data_cleaning_exclusions_summary(revenue_db):
    """Verify that duplicates, invalid dates, bad numerics, non-completed, and invalid discounts are excluded."""
    _, report = revenue_db
    assert report["rows_read"] == 20
    assert report["duplicates_removed"] == 1
    # 6 counted: TXN01, TXN02, TXN03, TXN04, TXN05, TXN19
    assert report["rows_counted"] == 6
    assert report["rows_excluded"] == 13

    reasons = {x["transaction_id"]: x["exclusion_reason"] for x in report["exclusions"]}
    assert reasons["TXN06"] == "invalid date"
    assert reasons["TXN07"] == "invalid date"
    assert reasons["TXN08"] == "non-positive quantity or negative price"
    assert reasons["TXN09"] == "non-positive quantity or negative price"
    assert reasons["TXN10"] == "non-positive quantity or negative price"
    assert reasons["TXN11"] == "missing quantity or price"
    assert reasons["TXN12"] == "missing quantity or price"
    assert "pending" in reasons["TXN13"].lower()
    assert "cancelled" in reasons["TXN14"].lower()
    assert "returned" in reasons["TXN15"].lower()
    assert "refunded" in reasons["TXN16"].lower()
    assert reasons["TXN17"] == "negative discount amount"
    assert reasons["TXN18"] == "discount exceeds gross sales amount"


def test_missing_discount_defaults_to_zero(revenue_db):
    """TXN02 had an empty discount; revenue must equal quantity * unit_price (5 * 200 = 1000)."""
    db_path, _ = revenue_db
    conn = queries.get_conn(db_path)
    try:
        row = conn.execute("SELECT revenue, discount_amount FROM sales WHERE transaction_id = 'TXN02'").fetchone()
        assert row["discount_amount"] == 0.0
        assert row["revenue"] == 1000.0
    finally:
        conn.close()


def test_discount_exact_equals_gross_is_counted(revenue_db):
    """TXN19 has discount equal to gross (revenue = 0); it must be counted as a completed order."""
    db_path, _ = revenue_db
    conn = queries.get_conn(db_path)
    try:
        row = conn.execute("SELECT counted, revenue FROM sales WHERE transaction_id = 'TXN19'").fetchone()
        assert row["counted"] == 1
        assert row["revenue"] == 0.0
    finally:
        conn.close()


def test_revenue_aggregations_are_mathematically_consistent(revenue_db):
    """Total revenue must equal sum of product totals, sum of regional totals, and sum of monthly totals."""
    db_path, _ = revenue_db
    conn = queries.get_conn(db_path)
    try:
        # Expected rows:
        # TXN01: Laptop, North, Jan: 2*1000 - 100 = 1900
        # TXN02: Mouse, South, Jan: 5*200 - 0 = 1000
        # TXN03: Keyboard, North, Jan: 4*300 - 0 = 1200
        # TXN04: Laptop, South, Feb: 1*1000 - 200 = 800
        # TXN05: Monitor, North, Feb: 2*1500 - 500 = 2500
        # TXN19: Mouse, South, Jan: 1*200 - 200 = 0
        # Total: 1900 + 1000 + 1200 + 800 + 2500 + 0 = 7400 across 6 orders.
        tot_res = queries.total_revenue(conn)
        total_rev = tot_res["data"][0]["total_revenue"]
        total_orders = tot_res["data"][0]["orders_counted"]
        assert total_rev == 7400.0
        assert total_orders == 6

        # Product sum consistency
        prod_res = queries.top_product(conn)
        sum_prod_rev = round(sum(p["revenue"] for p in prod_res["data"]), 2)
        assert sum_prod_rev == total_rev
        prod_dict = {p["product"]: p["revenue"] for p in prod_res["data"]}
        assert prod_dict["Laptop"] == 2700.0   # 1900 + 800
        assert prod_dict["Monitor"] == 2500.0  # 2500
        assert prod_dict["Keyboard"] == 1200.0 # 1200
        assert prod_dict["Mouse"] == 1000.0    # 1000 + 0

        # Region sum consistency
        reg_res = queries.top_region(conn)
        sum_reg_rev = round(sum(r["revenue"] for r in reg_res["data"]), 2)
        assert sum_reg_rev == total_rev
        reg_dict = {r["region"]: r["revenue"] for r in reg_res["data"]}
        assert reg_dict["North"] == 5600.0     # 1900 + 1200 + 2500
        assert reg_dict["South"] == 1800.0     # 1000 + 800 + 0

        # Monthly trend sum consistency
        month_res = queries.monthly_trend(conn)
        sum_month_rev = round(sum(m["revenue"] for m in month_res["data"]), 2)
        assert sum_month_rev == total_rev
        month_dict = {m["month"]: m["revenue"] for m in month_res["data"]}
        assert month_dict["2026-01"] == 4100.0 # 1900 + 1000 + 1200 + 0
        assert month_dict["2026-02"] == 3300.0 # 800 + 2500
    finally:
        conn.close()
