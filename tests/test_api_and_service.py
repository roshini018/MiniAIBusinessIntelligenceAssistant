import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.data_loader import load_to_db
from app import queries
from app.queries import AppError
from app.service import answer_question
from app.intent import keyword_classify

client = TestClient(app)

CSV_API_DATA = """transaction_id,order_date,product,category,region,sales_channel,quantity,unit_price,discount_amount,status
P1,05-01-2026,Laptop,Electronics,North,Online,1,1000,0,Completed
P2,10-02-2026,Mouse,Accessories,South,Retail,2,500,0,Completed
"""


@pytest.fixture(scope="module")
def api_db(tmp_path_factory):
    folder = tmp_path_factory.mktemp("api_data")
    csv_file = folder / "sales.csv"
    csv_file.write_text(CSV_API_DATA)
    db_file = str(folder / "sales.db")
    load_to_db(str(csv_file), db_file)
    return db_file


@pytest.fixture(autouse=True)
def setup_api_db(api_db, monkeypatch):
    """Point queries default db to the temporary fixture database."""
    monkeypatch.setattr(queries, "DEFAULT_DB_PATH", api_db)


# 1. Input validation & status codes on /ask
def test_ask_empty_and_whitespace_returns_400():
    r1 = client.post("/ask", json={"question": ""})
    assert r1.status_code == 400
    assert "cannot be empty" in r1.json()["error"]

    r2 = client.post("/ask", json={"question": "     "})
    assert r2.status_code == 400
    assert "cannot be empty" in r2.json()["error"]


def test_ask_missing_and_wrong_types_returns_422():
    # Missing question key
    r1 = client.post("/ask", json={})
    assert r1.status_code == 422

    # Wrong type: integer instead of string
    r2 = client.post("/ask", json={"question": 12345})
    assert r2.status_code == 422

    # Wrong type: list
    r3 = client.post("/ask", json={"question": ["What is total revenue?"]})
    assert r3.status_code == 422


def test_ask_ambiguous_returns_400_with_clarification():
    """Ambiguous questions must return 400 and NOT 422 unsupported message."""
    res = client.post("/ask", json={"question": "Which performed best?"})
    assert res.status_code == 400
    error_msg = res.json()["error"]
    assert "clarify" in error_msg.lower()
    assert "can't answer" not in error_msg.lower()


def test_ask_unsupported_returns_422_with_capabilities():
    """Truly out-of-scope questions must return 422 with supported capabilities list."""
    res = client.post("/ask", json={"question": "What is the price of the Laptop?"})
    assert res.status_code == 422
    error_msg = res.json()["error"]
    assert "Total revenue" in error_msg
    assert "Top product by revenue" in error_msg


# 2. Valid response structure on /ask
@pytest.mark.parametrize(
    "question,expected_intent",
    [
        ("What is our total revenue?", "total_revenue"),
        ("Which product earned the most revenue?", "top_product"),
        ("Show monthly revenue trends.", "monthly_trend"),
        ("Which region had the highest sales?", "top_region"),
        ("Compare January and February 2026.", "month_comparison"),
    ],
)
def test_ask_valid_response_schema(question, expected_intent):
    res = client.post("/ask", json={"question": question})
    assert res.status_code == 200
    body = res.json()
    assert body["question"] == question
    assert body["intent"] == expected_intent
    assert isinstance(body["answer"], str)
    assert len(body["answer"]) > 0
    assert isinstance(body["sql_used"], str)
    assert isinstance(body["params"], list)
    assert isinstance(body["supporting_data"], list)
    assert isinstance(body["classified_by"], str)


# 3. Overview endpoints: /health, /kpis, /chart-data
def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_kpis_endpoint_schema():
    res = client.get("/kpis")
    assert res.status_code == 200
    body = res.json()
    assert body["total_revenue"] == 2000.0  # 1000 + 1000
    assert body["orders_counted"] == 2
    assert body["top_product"]["name"] == "Laptop"
    assert body["top_product"]["revenue"] == 1000.0
    assert body["top_region"]["name"] == "North"
    assert body["top_region"]["revenue"] == 1000.0
    assert body["timeframe"]["start_month"] == "2026-01"
    assert body["timeframe"]["end_month"] == "2026-02"
    assert body["timeframe"]["label"] == "Jan – Feb 2026"


def test_chart_data_endpoint_schema():
    res = client.get("/chart-data")
    assert res.status_code == 200
    body = res.json()
    assert "monthly_trend" in body
    assert "products" in body
    assert "regions" in body
    assert len(body["monthly_trend"]) == 2
    assert len(body["products"]) == 2
    assert len(body["regions"]) == 2


# 4. Error isolation & exception handling
def test_database_error_handling(monkeypatch):
    """When a low-level SQLite error occurs, 500 AppError with safe message is returned."""
    def fail_query(conn):
        raise sqlite3.OperationalError("disk I/O error or table corrupted")

    monkeypatch.setattr(queries, "total_revenue", fail_query)

    res = client.post("/ask", json={"question": "What is the total revenue?"})
    assert res.status_code == 500
    assert res.json() == {"error": "A database error occurred."}


def test_unexpected_exception_handler(monkeypatch):
    """Unexpected unhandled exceptions return 500 without leaking stack traces."""
    def crash(body):
        raise RuntimeError("Secret credentials in internal memory")

    monkeypatch.setattr("app.main.answer_question", crash)
    client_safe = TestClient(app, raise_server_exceptions=False)
    res = client_safe.post("/ask", json={"question": "What is our total revenue?"})
    assert res.status_code == 500
    assert res.json() == {"error": "Something went wrong on our side."}


# 5. Database connection closure verification
def test_database_connection_closed_on_success_and_failure(api_db, monkeypatch):
    """Verify that conn.close() is called in finally block on both success and error paths."""
    real_get_conn = queries.get_conn
    closed_conns = []

    class TrackingConn:
        def __init__(self, conn):
            self._conn = conn
        def close(self):
            closed_conns.append(self._conn)
            self._conn.close()
        def __getattr__(self, name):
            return getattr(self._conn, name)

    def tracking_get_conn(path=None):
        return TrackingConn(real_get_conn(path))

    monkeypatch.setattr(queries, "get_conn", tracking_get_conn)

    # Success path
    closed_conns.clear()
    answer_question("What is our total revenue?", db_path=api_db, classifier=keyword_classify)
    assert len(closed_conns) == 1

    # Error path (e.g. 404 entity not found)
    closed_conns.clear()
    try:
        answer_question("How much revenue did NonExistentItem generate?", db_path=api_db, classifier=keyword_classify)
    except AppError:
        pass
    assert len(closed_conns) == 1
