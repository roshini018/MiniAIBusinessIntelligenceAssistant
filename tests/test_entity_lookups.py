import pytest
from app.data_loader import load_to_db
from app import queries
from app.queries import AppError, find_product, find_region
from app.intent import keyword_classify
from app.service import answer_question


CSV_ENTITY_DATA = """transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status
E1,05-01-2026,Laptop Stand,Accessories,North,Online,5,1000,0,Completed
E2,10-01-2026,Wireless Mouse,Accessories,South,Retail,10,200,0,Completed
E3,15-02-2026,Office Chair,Furniture,East,Online,2,5000,500,Completed
E4,20-02-2026,Gaming Monitor,Electronics,West,Retail,1,15000,1000,Completed
"""


@pytest.fixture(scope="module")
def entity_db(tmp_path_factory):
    folder = tmp_path_factory.mktemp("entity_data")
    csv_file = folder / "sales.csv"
    csv_file.write_text(CSV_ENTITY_DATA)
    db_file = str(folder / "sales.db")
    load_to_db(str(csv_file), db_file)
    return db_file


# 1. Product Lookups
@pytest.mark.parametrize(
    "query,expected_product,expected_rev,expected_orders",
    [
        ("How much revenue did Laptop Stand generate?", "Laptop Stand", 5000, 1),
        ("How much revenue did the Wireless Mouse generate?", "Wireless Mouse", 2000, 1),
        ("How much revenue did Office Chair generate?", "Office Chair", 9500, 1),
        ("How much revenue did Gaming Monitor generate?", "Gaming Monitor", 14000, 1),
        # Case insensitivity
        ("how much revenue did laptop stand generate?", "Laptop Stand", 5000, 1),
        ("HOW MUCH REVENUE DID GAMING MONITOR GENERATE?", "Gaming Monitor", 14000, 1),
    ],
)
def test_existing_product_lookups(entity_db, query, expected_product, expected_rev, expected_orders):
    res = answer_question(query, db_path=entity_db, classifier=keyword_classify)
    assert res["intent"] == "top_product"
    assert expected_product in res["answer"]
    assert res["supporting_data"][0]["revenue"] == expected_rev
    assert res["supporting_data"][0]["orders_counted"] == expected_orders


def test_unknown_product_raises_404(entity_db):
    conn = queries.get_conn(entity_db)
    try:
        with pytest.raises(AppError) as e:
            queries.top_product(conn, product_name="Virtual Reality Headset")
        assert e.value.status == 404
        assert "Virtual Reality Headset" in e.value.message
    finally:
        conn.close()


# 2. Regional Lookups
@pytest.mark.parametrize(
    "query,expected_region,expected_rev,expected_orders",
    [
        ("How much revenue came from the North region?", "North", 5000, 1),
        ("How much revenue came from the South region?", "South", 2000, 1),
        ("How much revenue came from the East region?", "East", 9500, 1),
        ("How much revenue came from the West region?", "West", 14000, 1),
        # Case insensitivity
        ("how much revenue came from the north region?", "North", 5000, 1),
        ("HOW MUCH REVENUE CAME FROM THE WEST REGION?", "West", 14000, 1),
    ],
)
def test_existing_region_lookups(entity_db, query, expected_region, expected_rev, expected_orders):
    res = answer_question(query, db_path=entity_db, classifier=keyword_classify)
    assert res["intent"] == "top_region"
    assert expected_region in res["answer"]
    assert res["supporting_data"][0]["revenue"] == expected_rev
    assert res["supporting_data"][0]["orders_counted"] == expected_orders


def test_unknown_region_raises_404(entity_db):
    conn = queries.get_conn(entity_db)
    try:
        with pytest.raises(AppError) as e:
            queries.top_region(conn, region_name="Central")
        assert e.value.status == 404
        assert "Central" in e.value.message
    finally:
        conn.close()


# 3. Helper finders robustness
def test_find_product_and_region_helpers(entity_db):
    conn = queries.get_conn(entity_db)
    try:
        # None and empty queries
        assert find_product(conn, "") is None
        assert find_product(conn, None) is None
        assert find_region(conn, "") is None
        assert find_region(conn, None) is None

        # Leading/trailing whitespace
        assert find_product(conn, "   Laptop Stand   ") == "Laptop Stand"
        assert find_region(conn, "   North   ") == "North"

        # "the" prefix and entity suffix stripping
        assert find_product(conn, "the Gaming Monitor") == "Gaming Monitor"
        assert find_product(conn, "Gaming Monitor product") == "Gaming Monitor"
        assert find_region(conn, "the South region") == "South"

        # Embedded in sentence
        assert find_product(conn, "Show me revenue of Office Chair please") == "Office Chair"
        assert find_region(conn, "Total from West territory") == "West"

        # Non-matching
        assert find_product(conn, "MacBook Pro") is None
        assert find_region(conn, "Antarctica") is None
    finally:
        conn.close()


# 4. Month lookups & validation
def test_specific_month_lookups(entity_db):
    # January 2026 has E1(5000) + E2(2000) = 7000 across 2 orders
    res_jan = answer_question("Show revenue for January 2026.", db_path=entity_db, classifier=keyword_classify)
    assert res_jan["intent"] == "monthly_trend"
    assert "2026-01" in res_jan["answer"]
    assert "₹7,000" in res_jan["answer"]
    assert res_jan["supporting_data"][0]["orders_counted"] == 2

    # February 2026 has E3(9500) + E4(14000) = 23500 across 2 orders
    res_feb = answer_question("What was the revenue in February?", db_path=entity_db, classifier=keyword_classify)
    assert res_feb["intent"] == "monthly_trend"
    assert "2026-02" in res_feb["answer"]
    assert "₹23,500" in res_feb["answer"]


def test_invalid_month_format_in_query(entity_db):
    conn = queries.get_conn(entity_db)
    try:
        with pytest.raises(AppError) as e:
            queries.monthly_trend(conn, month="2026-13")
        assert e.value.status == 400
        assert "valid month" in e.value.message.lower()

        with pytest.raises(AppError) as e2:
            queries.monthly_trend(conn, month="not-a-month")
        assert e2.value.status == 400
    finally:
        conn.close()


def test_missing_month_in_database(entity_db):
    """Querying a month that has valid YYYY-MM syntax but no database records returns 404."""
    with pytest.raises(AppError) as e:
        answer_question("Show revenue for November 2026.", db_path=entity_db, classifier=keyword_classify)
    assert e.value.status == 404
    assert "2026-11" in e.value.message
