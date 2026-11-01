import pytest
from app.data_loader import load_to_db
from app import queries
from app.queries import AppError


CSV_TREND_COMPARISONS = """transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status
C1,05-12-2025,Laptop,Electronics,North,Online,1,1000,0,Completed
C2,10-01-2026,Laptop,Electronics,North,Online,2,1000,0,Completed
C3,15-02-2026,Laptop,Electronics,North,Online,2,1000,0,Completed
C4,20-03-2026,Laptop,Electronics,North,Online,4,1000,0,Completed
C5,25-04-2026,Laptop,Electronics,North,Online,1,1000,0,Completed
"""


@pytest.fixture(scope="module")
def trend_db(tmp_path_factory):
    folder = tmp_path_factory.mktemp("trend_data")
    csv_file = folder / "sales.csv"
    csv_file.write_text(CSV_TREND_COMPARISONS)
    db_file = str(folder / "sales.db")
    load_to_db(str(csv_file), db_file)
    return db_file


def test_positive_growth_comparison(trend_db):
    """From Dec 2025 (1000) to Jan 2026 (2000): revenue doubled (+100%)."""
    conn = queries.get_conn(trend_db)
    try:
        res = queries.month_comparison(conn, "2025-12", "2026-01")
        assert res["intent"] == "month_comparison"
        assert "2026-01 had higher revenue than 2025-12" in res["answer"]
        assert "Revenue increased from ₹1,000 in 2025-12 to ₹2,000 in 2026-01" in res["answer"]
        assert "+₹1,000" in res["answer"]
        assert "+100.0%" in res["answer"]
        assert res["data"][2]["revenue"] == 1000.0
        assert res["data"][2]["percent_change"] == 100.0
    finally:
        conn.close()


def test_negative_decline_comparison(trend_db):
    """From Mar 2026 (4000) to Apr 2026 (1000): revenue dropped by 3000 (-75%)."""
    conn = queries.get_conn(trend_db)
    try:
        res = queries.month_comparison(conn, "2026-03", "2026-04")
        assert "2026-03 had higher revenue than 2026-04" in res["answer"]
        assert "Revenue decreased from ₹4,000 in 2026-03 to ₹1,000 in 2026-04" in res["answer"]
        assert "-₹3,000" in res["answer"]
        assert "-75.0%" in res["answer"]
        assert res["data"][2]["revenue"] == -3000.0
        assert res["data"][2]["percent_change"] == -75.0
    finally:
        conn.close()


def test_equal_revenue_comparison(trend_db):
    """Jan 2026 (2000) and Feb 2026 (2000): equal revenue, change = 0."""
    conn = queries.get_conn(trend_db)
    try:
        res = queries.month_comparison(conn, "2026-01", "2026-02")
        assert "Both 2026-01 and 2026-02 generated equal revenue" in res["answer"]
        assert "Revenue did not change" in res["answer"]
        assert res["data"][2]["revenue"] == 0.0
        assert res["data"][2]["percent_change"] == 0.0
    finally:
        conn.close()


def test_zero_baseline_percentage_safety(tmp_path):
    """When baseline month has 0 revenue, percent_change must be None without division error."""
    csv_file = tmp_path / "zero_base.csv"
    csv_file.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "Z1,01-01-2026,Pen,Office,North,Store,1,100,100,Completed\n"  # 1*100 - 100 = 0
        "Z2,01-02-2026,Pen,Office,North,Store,1,500,0,Completed\n"    # 500
    )
    db_file = str(tmp_path / "zero_base.db")
    load_to_db(str(csv_file), db_file)
    conn = queries.get_conn(db_file)
    try:
        res = queries.month_comparison(conn, "2026-01", "2026-02")
        assert res["data"][2]["revenue"] == 500.0
        assert res["data"][2]["percent_change"] is None
        assert "Revenue increased" in res["answer"]
    finally:
        conn.close()


def test_same_month_comparison_rejected(trend_db):
    """Comparing identical months must raise 400 AppError."""
    conn = queries.get_conn(trend_db)
    try:
        with pytest.raises(AppError) as e:
            queries.month_comparison(conn, "2026-01", "2026-01")
        assert e.value.status == 400
        assert "distinct" in e.value.message.lower()
    finally:
        conn.close()


def test_missing_month_in_comparison_raises_404(trend_db):
    """When either month has no records, 404 AppError must be raised."""
    conn = queries.get_conn(trend_db)
    try:
        # First month missing
        with pytest.raises(AppError) as e1:
            queries.month_comparison(conn, "2024-01", "2026-01")
        assert e1.value.status == 404
        assert "2024-01" in e1.value.message

        # Second month missing
        with pytest.raises(AppError) as e2:
            queries.month_comparison(conn, "2026-01", "2026-09")
        assert e2.value.status == 404
        assert "2026-09" in e2.value.message
    finally:
        conn.close()


def test_invalid_month_format_in_comparison(trend_db):
    """Malformed month format in comparison must raise 400."""
    conn = queries.get_conn(trend_db)
    try:
        with pytest.raises(AppError) as e:
            queries.month_comparison(conn, "2026-15", "2026-01")
        assert e.value.status == 400
        assert "valid month" in e.value.message.lower()
    finally:
        conn.close()


def test_trend_direction_variations(tmp_path):
    """Verify trajectory answer for increasing, decreasing, and flat datasets."""
    # 1. Increasing trajectory
    csv_inc = tmp_path / "inc.csv"
    csv_inc.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "I1,01-01-2026,A,C,N,O,1,1000,0,Completed\n"
        "I2,01-02-2026,A,C,N,O,1,2000,0,Completed\n"
    )
    db_inc = str(tmp_path / "inc.db")
    load_to_db(str(csv_inc), db_inc)
    with queries.get_conn(db_inc) as conn_inc:
        res_inc = queries.monthly_trend(conn_inc, target="trajectory")
        assert "increasing" in res_inc["answer"]

    # 2. Decreasing trajectory
    csv_dec = tmp_path / "dec.csv"
    csv_dec.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "D1,01-01-2026,A,C,N,O,1,3000,0,Completed\n"
        "D2,01-02-2026,A,C,N,O,1,1000,0,Completed\n"
    )
    db_dec = str(tmp_path / "dec.db")
    load_to_db(str(csv_dec), db_dec)
    with queries.get_conn(db_dec) as conn_dec:
        res_dec = queries.monthly_trend(conn_dec, target="trajectory")
        assert "decreasing" in res_dec["answer"]

    # 3. Flat/steady trajectory
    csv_flat = tmp_path / "flat.csv"
    csv_flat.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "F1,01-01-2026,A,C,N,O,1,2000,0,Completed\n"
        "F2,01-02-2026,A,C,N,O,1,2000,0,Completed\n"
    )
    db_flat = str(tmp_path / "flat.db")
    load_to_db(str(csv_flat), db_flat)
    with queries.get_conn(db_flat) as conn_flat:
        res_flat = queries.monthly_trend(conn_flat, target="trajectory")
        assert "steady" in res_flat["answer"]
