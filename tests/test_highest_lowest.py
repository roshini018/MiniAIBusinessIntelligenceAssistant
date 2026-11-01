import pytest
from app.data_loader import load_to_db
from app import queries
from app.queries import AppError, _fmt_indian
from app.main import _format_timeframe


CSV_TIED_AND_EDGE = """transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status
# Tied top products: Product B and Product A both make 2000 in revenue
T1,10-01-2026,Product B,Electronics,North,Online,2,1000,0,Completed
T2,12-01-2026,Product A,Electronics,South,Online,2,1000,0,Completed

# Tied lowest products: Product D and Product C both make 500 in revenue
T3,15-01-2026,Product D,Accessories,North,Retail,1,500,0,Completed
T4,20-01-2026,Product C,Accessories,South,Retail,1,500,0,Completed

# Gaps in timeline: January 2026 and March 2026 (February is missing)
T5,10-03-2026,Product A,Electronics,North,Online,1,1000,0,Completed
T6,15-03-2026,Product B,Electronics,South,Online,1,1000,0,Completed
"""


@pytest.fixture
def tied_db(tmp_path):
    csv_file = tmp_path / "tied.csv"
    # Filter comments
    lines = [l for l in CSV_TIED_AND_EDGE.splitlines() if not l.startswith("#")]
    csv_file.write_text("\n".join(lines) + "\n")
    db_file = str(tmp_path / "tied.db")
    load_to_db(str(csv_file), db_file)
    return db_file


def test_tied_product_maximum_and_minimum(tied_db):
    """When products tie for revenue, deterministic alphabetical tie-breaking must occur."""
    conn = queries.get_conn(tied_db)
    try:
        # Highest: Product A and Product B tie in revenue in Jan (both 2000 from Jan; in total A has 3000, B has 3000)
        # Total: Product A = 3000, Product B = 3000. Tie broken alphabetically: Product A first!
        top_res = queries.top_product(conn, target="highest")
        assert top_res["data"][0]["product"] == "Product A"
        assert top_res["data"][0]["revenue"] == 3000.0
        assert top_res["data"][1]["product"] == "Product B"
        assert top_res["data"][1]["revenue"] == 3000.0

        # Lowest: Product C (500) and Product D (500) tie.
        # ORDER BY revenue ASC, product ASC -> Product C first!
        lowest_res = queries.top_product(conn, target="lowest")
        assert lowest_res["data"][0]["product"] == "Product C"
        assert lowest_res["data"][0]["revenue"] == 500.0
    finally:
        conn.close()


def test_tied_region_maximum_and_minimum(tied_db):
    """When regions tie in revenue, deterministic alphabetical tie-breaking must occur."""
    conn = queries.get_conn(tied_db)
    try:
        # North: T1(2000) + T3(500) + T5(1000) = 3500
        # South: T2(2000) + T4(500) + T6(1000) = 3500
        # North and South tie at 3500! Alphabetical: North < South
        top_reg = queries.top_region(conn, target="highest")
        assert top_reg["data"][0]["region"] == "North"
        assert top_reg["data"][0]["revenue"] == 3500.0

        lowest_reg = queries.top_region(conn, target="lowest")
        # In ASC: North < South
        assert lowest_reg["data"][0]["region"] == "North"
        assert lowest_reg["data"][0]["revenue"] == 3500.0
    finally:
        conn.close()


def test_missing_month_in_timeline(tied_db):
    """Dataset has 2026-01 and 2026-03 (gap in 2026-02). Querying 2026-02 must return 404."""
    conn = queries.get_conn(tied_db)
    try:
        # Trend data only contains the present months
        trend_res = queries.monthly_trend(conn)
        months_present = [m["month"] for m in trend_res["data"]]
        assert months_present == ["2026-01", "2026-03"]

        # Looking up missing month 2026-02 raises 404 AppError
        with pytest.raises(AppError) as e:
            queries.monthly_trend(conn, month="2026-02")
        assert e.value.status == 404
        assert "2026-02" in e.value.message
    finally:
        conn.close()


def test_one_month_dataset(tmp_path):
    """When dataset only has a single month, peak, lowest, and trajectory must handle it safely."""
    csv_file = tmp_path / "single_month.csv"
    csv_file.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
        "S1,15-05-2026,Laptop,Electronics,North,Online,1,5000,0,Completed\n"
    )
    db_file = str(tmp_path / "single_month.db")
    load_to_db(str(csv_file), db_file)
    conn = queries.get_conn(db_file)
    try:
        # Highest month
        high_res = queries.monthly_trend(conn, target="highest")
        assert "2026-05" in high_res["answer"]
        assert "₹5,000" in high_res["answer"]

        # Lowest month
        low_res = queries.monthly_trend(conn, target="lowest")
        assert "2026-05" in low_res["answer"]
        assert "₹5,000" in low_res["answer"]

        # Trajectory
        traj_res = queries.monthly_trend(conn, target="trajectory")
        assert "steady" in traj_res["answer"]
    finally:
        conn.close()


def test_empty_dataset_handling(tmp_path):
    """Empty dataset must return 0 for total revenue and 404 for queries requiring data."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text(
        "transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status\n"
    )
    db_file = str(tmp_path / "empty.db")
    load_to_db(str(csv_file), db_file)
    conn = queries.get_conn(db_file)
    try:
        tot_res = queries.total_revenue(conn)
        assert tot_res["data"][0]["total_revenue"] == 0
        assert tot_res["data"][0]["orders_counted"] == 0

        with pytest.raises(AppError) as e_prod:
            queries.top_product(conn)
        assert e_prod.value.status == 404

        with pytest.raises(AppError) as e_reg:
            queries.top_region(conn)
        assert e_reg.value.status == 404

        with pytest.raises(AppError) as e_trend:
            queries.monthly_trend(conn)
        assert e_trend.value.status == 404
    finally:
        conn.close()


def test_currency_formatting_indian_system():
    """Verify Indian currency numbering system groupings."""
    assert _fmt_indian(0) == "₹0"
    assert _fmt_indian(500) == "₹500"
    assert _fmt_indian(1500) == "₹1,500"
    assert _fmt_indian(10000) == "₹10,000"
    assert _fmt_indian(100000) == "₹1,00,000"
    assert _fmt_indian(1439200) == "₹14,39,200"
    assert _fmt_indian(10000000) == "₹1,00,00,000"
    assert _fmt_indian(-2500) == "-₹2,500"


def test_timeframe_labels_formatting():
    """Verify timeframe label generation for overview charts and KPIs."""
    assert _format_timeframe("2026-01", "2026-06") == "Jan – Jun 2026"
    assert _format_timeframe("2025-11", "2026-02") == "Nov 2025 – Feb 2026"
    assert _format_timeframe("2026-03", "2026-03") == "Mar – Mar 2026"
    assert _format_timeframe(None, "2026-06") == ""
    assert _format_timeframe("2026-01", None) == ""
    assert _format_timeframe("", "") == ""
    assert _format_timeframe("invalid", "2026-06") == "invalid – 2026-06"
